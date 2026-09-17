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
from app.schemas import ScrapeLinkResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("wishdeck.utils")

router = APIRouter(prefix="/utils", tags=["utils"])

_USER_AGENT = (
    "Mozilla/5.0 (compatible; WishDeckBot/1.0; +https://wishdeck.example/robot)"
)
_TIMEOUT = 10.0

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


async def _fetch_html(url: str) -> str:
    async with httpx2.AsyncClient(
        follow_redirects=True, timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


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
        html = await _fetch_html(url)
    except httpx2.HTTPError as exc:
        logger.warning("Scrape failed for %s: %s", url, exc)
        status_hint = ""
        response = getattr(exc, "response", None)
        if response is not None:
            status_hint = f" ({response.status_code})"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"Unable to fetch URL{status_hint}: {exc}. "
                "Some sites block automated scraping."
            ),
        ) from exc

    data = parse_metadata(html, url)
    # Fall back to the configured default currency when none was detected.
    if data["price"] is not None and not data["currency"]:
        data["currency"] = await effective_value("DEFAULT_CURRENCY", session) or "USD"
    return ScrapeLinkResponse(url=url, **data)


__all__ = ["router", "parse_metadata"]

