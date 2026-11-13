import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import html2text
import httpx

from app.rag.sources import SOURCE_URLS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


@dataclass
class CrawledPage:
    url: str
    markdown: str


def slug_for(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def _converter() -> html2text.HTML2Text:
    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_images = True
    h.ignore_links = True
    h.ignore_emphasis = True
    return h


def _fetch(client: httpx.Client, url: str) -> tuple[str, str] | None:
    try:
        response = client.get(url, headers=HEADERS, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("crawl failed url=%s error=%s", url, exc)
        return None
    markdown = _converter().handle(response.text)
    return response.text, markdown


def crawl_all(cache_dir: str = "data/raw", transport: httpx.BaseTransport | None = None) -> list[CrawledPage]:
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    pages: list[CrawledPage] = []
    with httpx.Client(follow_redirects=True, transport=transport) as client:
        for url in SOURCE_URLS:
            cached_md = cache / f"{slug_for(url)}.md"
            if cached_md.exists():
                pages.append(CrawledPage(url=url, markdown=cached_md.read_text(encoding="utf-8")))
                continue
            result = _fetch(client, url)
            if result is None:
                continue
            raw_html, markdown = result
            (cache / f"{slug_for(url)}.html").write_text(raw_html, encoding="utf-8")
            cached_md.write_text(markdown, encoding="utf-8")
            pages.append(CrawledPage(url=url, markdown=markdown))
            logger.info("crawled url=%s chars=%d", url, len(markdown))
    logger.info("crawl finished pages=%d/%d", len(pages), len(SOURCE_URLS))
    return pages
