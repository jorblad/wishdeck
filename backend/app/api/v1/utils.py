"""Link scraping / auto-fill utilities.

Accepts a product URL and extracts OpenGraph / JSON-LD / generic metadata:
title, description, price, currency, image_url and favicon.

Uses httpx2 for fetching and BeautifulSoup4 for parsing. Runs in a threadpool
because the libraries are currently synchronous.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx2
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import effective_value
from app.db.session import get_session
from app.schemas import ExtractedLink, ScrapeLinkResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("wishdeck.utils")

router = APIRouter(prefix="/utils", tags=["utils"])

_TIMEOUT = 10.0

# Rotating real browser UAs helps with simple bot-protection that keys on the
# User-Agent string (403/406/429 responses). We try a few common desktop/mobile
# browsers before falling back to a reader service.
_BROWSER_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]

# Status codes that usually mean the site is actively blocking our request.
_BLOCK_CODES = frozenset({403, 429, 406, 502, 503, 504})

# Helpers for parsing free-text / pasted wish lists.
_BULK_URL_RE = re.compile(r"https?://[^\s<>\)\"]+")
_BULK_TRAILING_SEP_RE = re.compile(r"[\-–—|]+\s*$")
_BULK_EMPTY_PARENS_RE = re.compile(r"\s*[\(\[\{]\s*[\)\]\}]\s*$")


def parse_bulk_items(text: str) -> list[dict[str, str | None]]:
    """Parse a free-text wish list into (title, url) entries."""
    items: list[dict[str, str | None]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _BULK_URL_RE.search(line)
        url = match.group(0).rstrip(".,;:!?>)") if match else None
        if match:
            title = (line[: match.start()] + line[match.end() :]).strip()
        else:
            title = line
        title = _BULK_TRAILING_SEP_RE.sub("", title)
        title = _BULK_EMPTY_PARENS_RE.sub("", title)
        title = re.sub(r"\s+", " ", title).strip()
        if title:
            items.append({"title": title, "url": url})
    return items


def _browser_headers(user_agent: str) -> dict[str, str]:
    """Return a set of headers that looks like a real browser navigation."""
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }


class ScrapeFetchError(Exception):
    """Raised when every fetching strategy failed."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

# Map common currency symbols / prefixes to ISO-4217 codes.
_CURRENCY_SYMBOLS = {
    "$": "USD", "US$": "USD", "C$": "CAD", "A$": "AUD", "S$": "SGD",
    "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY", "¥": "CNY",
    "kr": "SEK", "zł": "PLN", "₽": "RUB", "₩": "KRW", "₺": "TRY",
    "CHF": "CHF", "R$": "BRL", "R": "ZAR", "₪": "ILS", "฿": "THB",
    "₴": "UAH", "Kč": "CZK", "Ft": "HUF", "din": "RSD", "лв": "BGN",
}
# A price is digits with optional thousands/decimal separators and 0-2 decimals.
_PRICE_RE = re.compile(r"[0-9][0-9 .,\s]*[0-9](?:[.,][0-9]{1,2})?")
_CODE_RE = re.compile(r"\b([A-Z]{3})\b")
_SYMBOL_RE = re.compile("|".join(re.escape(s) for s in _CURRENCY_SYMBOLS))


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find(
            "meta", attrs={"name": name}
        )
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _first_code(text: str) -> str | None:
    m = _CODE_RE.search(text or "")
    return m.group(1) if m else None


def _detect_currency(text: str | None) -> str | None:
    if not text:
        return None
    sym = _SYMBOL_RE.search(text)
    if sym:
        return _CURRENCY_SYMBOLS[sym.group(0)]
    return _first_code(text)


def _normalise_number(raw: str) -> float | None:
    s = re.sub(r"[^0-9.,]", "", raw)
    if not s:
        return None
    if "," in s and "." in s:
        # Rightmost separator is the decimal point.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_amount(text: str) -> tuple[float | None, str | None]:
    """Return (value, currency_hint) from a single candidate string."""
    m = _PRICE_RE.search(text)
    if not m:
        return None, _detect_currency(text)
    value = _normalise_number(m.group(0))
    if value is None:
        return None, _detect_currency(text)
    # Currency may appear before or after the number.
    pre = text[: m.start()].strip()
    post = text[m.end():].strip()
    currency = _detect_currency(post) or _detect_currency(pre)
    return value, currency


def _collect_price_candidates(soup: BeautifulSoup) -> list[str]:
    candidates: list[str] = []
    for name in ("og:price:amount", "product:price:amount", "twitter:data1"):
        v = _meta(soup, name)
        if v:
            candidates.append(v)
    # JSON-LD structured data (Product / Offer).
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        blob = script.string or script.get_text() or ""
        try:
            data = json.loads(blob)
        except (ValueError, TypeError):
            continue
        for node in (data if isinstance(data, list) else [data]):
            offers = node.get("offers") if isinstance(node, dict) else None
            if isinstance(offers, list):
                offers = offers[0] if offers else None
            if isinstance(offers, dict):
                price = offers.get("price")
                if price is not None:
                    cur = offers.get("priceCurrency")
                    candidates.append(
                        f"{price} {cur}" if cur else str(price)
                    )
    # Elements whose class hints at a price.
    for el in soup.find_all(class_=re.compile(r"price", re.I)):
        txt = el.get_text(" ", strip=True)
        if _PRICE_RE.search(txt):
            candidates.append(txt)
    return candidates


def parse_metadata(html: str, base_url: str) -> dict[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    title = _meta(soup, "og:title", "twitter:title") or (
        soup.title.string.strip() if soup.title and soup.title.string else None
    )
    description = _meta(
        soup, "og:description", "twitter:description", "description"
    )
    image_url = _meta(soup, "og:image", "twitter:image", "image")

    # JSON-LD often carries the richest product metadata.
    ld_title = ld_desc = ld_image = None
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text() or "")
        except (ValueError, TypeError):
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict):
                ld_title = ld_title or node.get("name")
                ld_desc = ld_desc or node.get("description")
                img = node.get("image")
                if isinstance(img, list):
                    img = img[0] if img else None
                ld_image = ld_image or img

    title = title or ld_title
    description = description or ld_desc
    image_url = image_url or ld_image

    # Pick the first candidate that yields a usable number.
    price = currency = None
    for cand in _collect_price_candidates(soup):
        price, currency = _parse_amount(cand)
        if price is not None:
            break

    favicon = None
    icon_tag = soup.find("link", attrs={"rel": "icon"}) or soup.find(
        "link", attrs={"rel": "shortcut icon"}
    )
    if icon_tag and icon_tag.get("href"):
        favicon = urljoin(base_url, icon_tag["href"])

    if image_url:
        image_url = urljoin(base_url, image_url)

    return {
        "title": title,
        "description": description,
        "price": price,
        "currency": currency,
        "image_url": image_url,
        "favicon": favicon,
    }


def _parse_jina_response(markdown: str, base_url: str) -> dict[str, str | None]:
    """Extract metadata from Jina AI Reader's frontmatter markdown output."""
    title = description = image_url = favicon = None
    price = currency = None

    # Parse YAML frontmatter if present.
    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---\s*\n", markdown, re.DOTALL)
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        title_match = re.search(r'^title:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
        desc_match = re.search(r'^description:\s*"?([^"\n]+)"?', fm, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None
        description = desc_match.group(1).strip() if desc_match else None
        # Remove frontmatter so we don't parse the title twice.
        markdown = markdown[frontmatter_match.end():]

    # Fallback title from first Markdown heading.
    if not title:
        heading_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if heading_match:
            title = heading_match.group(1).strip()

    # Fallback description from first substantial paragraph.
    if not description:
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                description = stripped
                break

    # Look for a price anywhere in the remaining text.
    price, currency = _parse_amount(markdown)

    return {
        "title": title,
        "description": description,
        "price": price,
        "currency": currency,
        "image_url": image_url,
        "favicon": favicon,
    }


def _jina_reader_url(url: str) -> str:
    """Build a Jina AI Reader URL that fetches and extracts the target page."""
    return f"https://r.jina.ai/{url}"


async def _fetch_jina(url: str) -> str:
    """Fetch extracted markdown for a URL via Jina AI Reader."""
    jina_url = _jina_reader_url(url)
    async with httpx2.AsyncClient(
        follow_redirects=True,
        timeout=_TIMEOUT,
        headers={"User-Agent": _BROWSER_UAS[0], "X-Respond-With": "frontmatter"},
    ) as client:
        resp = await client.get(jina_url)
        resp.raise_for_status()
        return resp.text


async def _fetch_html(url: str) -> tuple[str, str]:
    """Fetch page HTML, trying browser UAs and then a reader fallback.

    Returns (content, source) where source is ``browser`` or ``jina``.
    """
    last_status: int | None = None
    last_error: Exception | None = None

    for ua in _BROWSER_UAS:
        async with httpx2.AsyncClient(
            follow_redirects=True, timeout=_TIMEOUT, headers=_browser_headers(ua)
        ) as client:
            try:
                resp = await client.get(url)
            except httpx2.HTTPError as exc:
                last_error = exc
                continue

            if resp.status_code in _BLOCK_CODES:
                logger.info(
                    "Scrape %s returned %s with UA %r; rotating...",
                    url,
                    resp.status_code,
                    ua[:40],
                )
                last_status = resp.status_code
                continue

            try:
                resp.raise_for_status()
            except httpx2.HTTPError as exc:
                last_error = exc
                continue

            return resp.text, "browser"

    # Last resort: use Jina AI Reader. It renders JS and often bypasses simple
    # bot protection, but returns markdown instead of raw HTML.
    logger.info("Browser fetch blocked for %s; trying Jina AI reader fallback", url)
    try:
        return await _fetch_jina(url), "jina"
    except httpx2.HTTPError as exc:
        last_error = exc

    hint = f" ({last_status})" if last_status else ""
    raise ScrapeFetchError(
        f"Unable to fetch URL{hint}: all browser UAs blocked or request failed.",
        status_code=last_status,
    ) from last_error


async def _scrape_link_data(url: str, session: AsyncSession | None = None) -> dict[str, Any]:
    """Fetch and parse metadata for a single URL."""
    content, source = await _fetch_html(url)
    if source == "jina":
        data = _parse_jina_response(content, url)
    else:
        data = parse_metadata(content, url)
        # Some sites return a 200 OK bot/captcha page with no useful metadata.
        # Give Jina AI Reader a second chance before giving up.
        if not data.get("title") and not data.get("description"):
            logger.info("Browser scrape returned no metadata for %s; trying Jina fallback", url)
            try:
                jina_data = _parse_jina_response(await _fetch_jina(url), url)
                if jina_data.get("title") or jina_data.get("description"):
                    data = {**data, **{k: v for k, v in jina_data.items() if v is not None}}
            except httpx2.HTTPError:
                pass

    # Fall back to the configured default currency when none was detected.
    if data["price"] is not None and not data["currency"] and session is not None:
        data["currency"] = await effective_value("DEFAULT_CURRENCY", session) or "USD"
    return data


@router.post("/scrape-link", response_model=ScrapeLinkResponse, status_code=status.HTTP_200_OK)
async def scrape_link(
    payload: dict,
    session: AsyncSession = Depends(get_session),
) -> ScrapeLinkResponse:
    """Extract product metadata from a URL for quick-add auto-fill."""
    url = (payload or {}).get("url")
    if not url or not urlparse(url).scheme.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid http(s) URL is required.",
        )
    try:
        data = await _scrape_link_data(url, session)
    except ScrapeFetchError as exc:
        logger.warning("Scrape failed for %s: %s", url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"Unable to fetch URL{f' ({exc.status_code})' if exc.status_code else ''}: {exc}. "
                "Some sites block automated scraping."
            ),
        ) from exc

    return ScrapeLinkResponse(url=url, **data)


@router.post("/extract-links", response_model=list[ExtractedLink])
async def extract_links(payload: dict) -> list[ExtractedLink]:
    """Extract titled links from pasted HTML or plain text.

    Useful when copying from OneNote only yields the link text; exporting the
    page or copying the underlying HTML preserves the actual hrefs. Plain text
    lines like ``Title - https://...`` are also accepted.
    """
    html = (payload or {}).get("html", "")
    plain = (payload or {}).get("text", "")
    source = html or plain
    if not source:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="HTML or text content is required.",
        )

    results: list[ExtractedLink] = []
    seen: set[str] = set()

    if html:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a", href=True):
            url = tag["href"].strip()
            if not url.startswith(("http://", "https://")):
                continue
            if url in seen:
                continue
            seen.add(url)
            title = tag.get_text(strip=True) or None
            results.append(ExtractedLink(title=title, url=url))
    else:
        for entry in parse_bulk_items(plain):
            url = entry.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            results.append(ExtractedLink(title=entry.get("title") or None, url=url))

    return results


__all__ = ["router", "parse_metadata", "parse_bulk_items"]

