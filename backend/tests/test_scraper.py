from __future__ import annotations

from app.api.v1.utils import parse_metadata, _parse_jina_response, extract_links


HTML = """
<html>
  <head>
    <meta property="og:title" content="Awesome Gadget">
    <meta property="og:description" content="The best gadget ever.">
    <meta property="og:image" content="/img/gadget.png">
    <meta property="og:price:amount" content="$1,299.00">
    <meta property="og:price:currency" content="USD">
    <meta property="product:price:amount" content="1299.00">
    <link rel="icon" href="/favicon.ico">
    <title>Fallback Title</title>
  </head>
  <body></body>
</html>
"""


def test_parse_metadata_extracts_fields():
    data = parse_metadata(HTML, "https://shop.example.com/product/1")
    assert data["title"] == "Awesome Gadget"
    assert data["description"] == "The best gadget ever."
    assert data["image_url"] == "https://shop.example.com/img/gadget.png"
    assert data["price"] == 1299.00
    assert data["currency"] == "USD"
    assert data["favicon"] == "https://shop.example.com/favicon.ico"


def test_parse_metadata_relative_url_resolution():
    data = parse_metadata(HTML, "https://shop.example.com/p/1")
    assert data["image_url"].startswith("https://")


def test_parse_metadata_missing_fields():
    data = parse_metadata("<html><head><title>Hi</title></head></html>", "https://x.com")
    assert data["title"] == "Hi"
    assert data["price"] is None


JINA_MARKDOWN = """---
title: "Awesome Gadget"
description: "The best gadget ever."
url: "https://shop.example.com/product/1"
---

# Awesome Gadget

The best gadget ever. Only **$1,299.00** today.
"""


def test_parse_jina_response_extracts_frontmatter():
    data = _parse_jina_response(JINA_MARKDOWN, "https://shop.example.com/product/1")
    assert data["title"] == "Awesome Gadget"
    assert data["description"] == "The best gadget ever."
    assert data["price"] == 1299.00
    assert data["currency"] == "USD"


def test_parse_jina_response_fallback_to_heading_and_paragraph():
    markdown = "# Fallback Title\n\nFallback description paragraph.\n"
    data = _parse_jina_response(markdown, "https://x.com")
    assert data["title"] == "Fallback Title"
    assert data["description"] == "Fallback description paragraph."


async def test_extract_links_parses_html_anchors():
    html = """
    <div>
      <a href="https://example.com/one">First link</a>
      <a href="https://example.com/two">Second link</a>
      <a href="mailto:nope@example.com">Email</a>
      <a href="https://example.com/one">Duplicate</a>
    </div>
    """
    links = await extract_links({"html": html})
    assert len(links) == 2
    assert links[0].title == "First link"
    assert links[0].url == "https://example.com/one"
    assert links[1].title == "Second link"
    assert links[1].url == "https://example.com/two"
