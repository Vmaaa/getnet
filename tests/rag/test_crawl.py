import httpx
import pytest

from app.rag.crawl import crawl_all, slug_for
from app.rag.sources import SOURCE_URLS

PAGE_HTML = "<html><body><h1>Get Smart</h1><p>Máquina de cartão.</p></body></html>"


def _mock_transport(failing_url: str | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if failing_url and request.url.host == failing_url:
            return httpx.Response(403)
        return httpx.Response(200, html=PAGE_HTML)

    return httpx.MockTransport(handler)


def test_slug_is_deterministic():
    assert slug_for(SOURCE_URLS[0]) == slug_for(SOURCE_URLS[0])
    assert len(slug_for(SOURCE_URLS[0])) == 12


def test_crawl_all_converts_to_markdown(tmp_path):
    pages = crawl_all(cache_dir=str(tmp_path), transport=_mock_transport())
    assert len(pages) == len(SOURCE_URLS)
    assert "# Get Smart" in pages[0].markdown
    assert (tmp_path / f"{slug_for(SOURCE_URLS[0])}.md").exists()
    assert (tmp_path / f"{slug_for(SOURCE_URLS[0])}.html").exists()


def test_crawl_all_reuses_cache(tmp_path):
    crawl_all(cache_dir=str(tmp_path), transport=_mock_transport())
    dead_transport = httpx.MockTransport(
        lambda request: (_ for _ in ()).throw(AssertionError("network hit on cached crawl"))
    )
    pages = crawl_all(cache_dir=str(tmp_path), transport=dead_transport)
    assert len(pages) == len(SOURCE_URLS)


def test_crawl_all_skips_failures(tmp_path):
    pages = crawl_all(cache_dir=str(tmp_path), transport=_mock_transport(failing_url="site.getnet.com.br"))
    assert len(pages) < len(SOURCE_URLS)
    assert all(p.markdown for p in pages)
