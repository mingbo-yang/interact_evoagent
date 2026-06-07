"""Tests for web_fetch and web_search tools (network mocked)."""

import httpx
import pytest

from evoagent.tools import web_tools
from evoagent.tools.web_tools import WebFetchTool, WebSearchTool, html_to_text


def test_html_to_text_strips_tags_and_scripts():
    html = (
        "<html><head><style>.x{color:red}</style>"
        "<script>var a=1;</script></head>"
        "<body><h1>Title</h1><p>Hello &amp; welcome</p></body></html>"
    )
    text = html_to_text(html)
    assert "Title" in text
    assert "Hello & welcome" in text
    assert "color:red" not in text
    assert "var a=1" not in text


def test_search_relevance_requires_multiple_query_tokens():
    hits = [("latest dictionary meaning", "https://dict.example/latest", "latest examples")]
    assert not web_tools._hits_look_relevant("latest python asyncio docs", hits)
    relevant = [("Python asyncio documentation", "https://docs.python.org/asyncio", "asyncio tasks")]
    assert web_tools._hits_look_relevant("latest python asyncio docs", relevant)


def _patch_get(monkeypatch, handler):
    async def fake_get(self, url, follow_redirects=False):
        return handler(url)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


def _allow_egress(monkeypatch):
    monkeypatch.setattr(web_tools, "check_url_allowed", lambda *a, **k: (True, "ok"))


@pytest.mark.asyncio
async def test_web_fetch_returns_text(monkeypatch):
    _allow_egress(monkeypatch)

    def handler(url):
        return httpx.Response(
            200,
            content=b"<html><body><p>Doc body</p></body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, handler)
    tool = WebFetchTool()
    res = await tool.run(url="https://example.com")
    assert res.success
    assert "Doc body" in res.output
    assert res.metadata["status_code"] == 200


@pytest.mark.asyncio
async def test_web_fetch_raw_keeps_html(monkeypatch):
    _allow_egress(monkeypatch)

    def handler(url):
        return httpx.Response(
            200,
            content=b"<p>raw</p>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, handler)
    tool = WebFetchTool()
    res = await tool.run(url="https://example.com", raw=True)
    assert res.success
    assert "<p>raw</p>" in res.output


@pytest.mark.asyncio
async def test_web_fetch_egress_blocked(monkeypatch):
    monkeypatch.setattr(web_tools, "check_url_allowed", lambda *a, **k: (False, "private"))
    tool = WebFetchTool()
    res = await tool.run(url="http://localhost/secret")
    assert res.success is False
    assert "Egress blocked" in res.error


@pytest.mark.asyncio
async def test_web_fetch_follows_redirect(monkeypatch):
    _allow_egress(monkeypatch)
    state = {"n": 0}

    def handler(url):
        if state["n"] == 0:
            state["n"] += 1
            return httpx.Response(
                302,
                headers={"location": "https://example.com/final"},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            content=b"<body>final page</body>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, handler)
    tool = WebFetchTool()
    res = await tool.run(url="https://example.com/start")
    assert res.success
    assert "final page" in res.output


@pytest.mark.asyncio
async def test_web_fetch_http_error(monkeypatch):
    _allow_egress(monkeypatch)

    def handler(url):
        return httpx.Response(404, request=httpx.Request("GET", url))

    _patch_get(monkeypatch, handler)
    tool = WebFetchTool()
    res = await tool.run(url="https://example.com/missing")
    assert res.success is False
    assert "404" in res.error


@pytest.mark.asyncio
async def test_web_search_parses_bing(monkeypatch):
    _allow_egress(monkeypatch)
    bing = (
        '<ol id="b_results">'
        '<li class="b_algo"><h2><a href="https://x.com/a">Result A</a></h2>'
        '<div class="b_caption"><p>Snippet A here</p></div></li>'
        '<li class="b_algo"><h2><a href="https://x.com/b">Result B</a></h2>'
        '<div class="b_caption"><p>Snippet B here</p></div></li>'
        '</ol>'
    )

    def handler(url):
        return httpx.Response(
            200, content=bing.encode(),
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, handler)
    tool = WebSearchTool()
    res = await tool.run(query="anything", max_results=5)
    assert res.success
    assert "Result A" in res.output
    assert "https://x.com/a" in res.output
    assert "Snippet A here" in res.output
    assert res.metadata["results"] == 2
    assert "bing" in res.metadata["engine"]


def test_decode_ddg_uddg():
    from evoagent.tools.web_tools import _decode_ddg_href

    wrapped = "//duckduckgo.com/l/?uddg=https%3A%2F%2Freal.example%2Fpage&rut=abc"
    assert _decode_ddg_href(wrapped) == "https://real.example/page"
    plain = "https://direct.example/x"
    assert _decode_ddg_href(plain) == plain


@pytest.mark.asyncio
async def test_web_search_parses_results(monkeypatch):
    _allow_egress(monkeypatch)
    ddg = (
        '<div class="result">'
        '<a class="result__a" href="https://a.com">First &amp; Best</a>'
        '<a class="result__snippet">Snippet one</a>'
        '</div>'
        '<div class="result">'
        '<a class="result__a" href="https://b.com">Second</a>'
        '<a class="result__snippet">Snippet two</a>'
        '</div>'
    )

    def handler(url):
        return httpx.Response(
            200,
            content=ddg.encode(),
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, handler)
    tool = WebSearchTool()
    res = await tool.run(query="test", max_results=5)
    assert res.success
    assert "First & Best" in res.output
    assert "https://a.com" in res.output
    assert "Snippet one" in res.output
    assert "https://b.com" in res.output
    assert res.metadata["results"] == 2


@pytest.mark.asyncio
async def test_web_search_no_results(monkeypatch):
    _allow_egress(monkeypatch)

    def handler(url):
        return httpx.Response(
            200, content=b"<html></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, handler)
    tool = WebSearchTool()
    res = await tool.run(query="nothing")
    assert res.success
    assert "No results" in res.output


def _patch_post(monkeypatch, handler):
    async def fake_post(self, url, headers=None, json=None):
        return handler(url, headers, json)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)


def _empty_html_get(monkeypatch):
    """Make all HTML backends return no parseable results."""
    def handler(url):
        return httpx.Response(
            200, content=b"<html></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )
    _patch_get(monkeypatch, handler)


@pytest.mark.asyncio
async def test_tavily_used_as_fallback_when_html_empty(monkeypatch):
    _allow_egress(monkeypatch)
    _empty_html_get(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-FAKE-TESTKEY")
    captured = {}

    def post_handler(url, headers, json):
        captured["url"] = url
        captured["auth"] = headers.get("Authorization")
        captured["query"] = json.get("query")
        return httpx.Response(
            200,
            json={"results": [
                {"title": "Result A", "url": "https://a.com", "content": "snippet A"},
                {"title": "Result B", "url": "https://b.com", "content": "snippet B"},
            ]},
            request=httpx.Request("POST", url),
        )

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="async python", max_results=3)
    assert res.success
    assert res.metadata["engine"] == "tavily"
    assert "Result A" in res.output
    assert "https://a.com" in res.output
    assert res.metadata["results"] == 2
    # Correct endpoint + Bearer auth + query forwarded.
    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["auth"] == "Bearer tvly-FAKE-TESTKEY"
    assert captured["query"] == "async python"


@pytest.mark.asyncio
async def test_tavily_not_called_when_html_succeeds(monkeypatch):
    _allow_egress(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-FAKE-TESTKEY")
    bing = (
        '<li class="b_algo"><h2><a href="https://x.com/a">Python asyncio gather</a></h2>'
        '<div class="b_caption"><p>python asyncio snippet</p></div></li>'
    )

    def get_handler(url):
        return httpx.Response(
            200, content=bing.encode(),
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, get_handler)

    called = {"post": False}

    def post_handler(url, headers, json):
        called["post"] = True
        return httpx.Response(200, json={"results": []},
                              request=httpx.Request("POST", url))

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="python asyncio")
    assert res.success
    assert res.metadata["engine"] != "tavily"
    # HTML backend satisfied the query, so the paid API must NOT be called.
    assert called["post"] is False


@pytest.mark.asyncio
async def test_tavily_called_when_html_results_irrelevant(monkeypatch):
    _allow_egress(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-FAKE-TESTKEY")
    # Valid-looking but irrelevant HTML result.
    bing = (
        '<li class="b_algo"><h2><a href="https://sports.example/a">MMA fighter</a></h2>'
        '<div class="b_caption"><p>sports profile</p></div></li>'
    )

    def get_handler(url):
        return httpx.Response(
            200, content=bing.encode(),
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )

    _patch_get(monkeypatch, get_handler)

    def post_handler(url, headers, json):
        return httpx.Response(
            200,
            json={"results": [
                {"title": "EvoAgent GitHub", "url": "https://github.com/mingbo-yang/EvoAgent", "content": "repo"}
            ]},
            request=httpx.Request("POST", url),
        )

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="EvoAgent GitHub")
    assert res.success
    assert res.metadata["engine"] == "tavily"
    assert "EvoAgent GitHub" in res.output


@pytest.mark.asyncio
async def test_tavily_not_called_without_key(monkeypatch):
    _allow_egress(monkeypatch)
    _empty_html_get(monkeypatch)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    called = {"post": False}

    def post_handler(url, headers, json):
        called["post"] = True
        return httpx.Response(200, json={"results": []},
                              request=httpx.Request("POST", url))

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="nothing")
    assert res.success
    assert "No results" in res.output
    assert called["post"] is False


@pytest.mark.asyncio
async def test_tavily_http_error_surfaces(monkeypatch):
    _allow_egress(monkeypatch)
    _empty_html_get(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-FAKE-TESTKEY")

    def post_handler(url, headers, json):
        return httpx.Response(401, json={"error": "unauthorized"},
                              request=httpx.Request("POST", url))

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="nothing")
    assert res.success is False
    assert "Tavily" in res.error


@pytest.mark.asyncio
async def test_tavily_fallback_when_html_unreachable(monkeypatch):
    """An unreachable/egress-blocked HTML backend must still fall back to Tavily."""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-FAKE-TESTKEY")

    # HTML egress check blocks bing/ddg; Tavily endpoint is allowed.
    def egress(url, *a, **k):
        return ("tavily" in url, "ok" if "tavily" in url else "blocked")
    monkeypatch.setattr(web_tools, "check_url_allowed", egress)

    def post_handler(url, headers, json):
        return httpx.Response(
            200,
            json={"results": [{"title": "T", "url": "https://t.com", "content": "c"}]},
            request=httpx.Request("POST", url),
        )

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="x")
    assert res.success
    assert res.metadata["engine"] == "tavily"
    assert "https://t.com" in res.output


@pytest.mark.asyncio
async def test_tavily_fallback_when_html_backend_times_out(monkeypatch):
    import asyncio

    _allow_egress(monkeypatch)
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-FAKE-TESTKEY")
    monkeypatch.setattr(web_tools, "_HTML_SEARCH_TIMEOUT", 0.01)

    async def slow_fetch(client, url, allowlist):
        await asyncio.sleep(1)
        raise AssertionError("should be cancelled by timeout")

    monkeypatch.setattr(web_tools, "_fetch_with_egress", slow_fetch)

    def post_handler(url, headers, json):
        return httpx.Response(
            200,
            json={"results": [{"title": "T", "url": "https://t.com", "content": "c"}]},
            request=httpx.Request("POST", url),
        )

    _patch_post(monkeypatch, post_handler)
    res = await WebSearchTool().run(query="x")
    assert res.success
    assert res.metadata["engine"] == "tavily"
