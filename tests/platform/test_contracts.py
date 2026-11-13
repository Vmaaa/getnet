import pytest
from pydantic import ValidationError

from app.contracts import AgentResult, Citation, Passage


def test_agent_result_defaults():
    r = AgentResult(agent="knowledge", status="answered", answer="ok")
    assert r.citations == []
    assert r.tools_used == []
    assert r.gap is None


def test_agent_result_rejects_bad_status():
    with pytest.raises(ValidationError):
        AgentResult(agent="knowledge", status="unknown")


def test_agent_result_rejects_bad_agent():
    with pytest.raises(ValidationError):
        AgentResult(agent="triage", status="answered")


def test_agent_result_needs_help_with_gap():
    r = AgentResult(agent="support", status="needs_help", gap="settlement date missing")
    assert r.status == "needs_help"
    assert r.gap == "settlement date missing"


def test_citation_fields():
    c = Citation(ref=1, url="https://site.getnet.com.br/get-tap/", title="Get Tap", text="exact passage")
    assert c.ref == 1


def test_citation_ref_must_be_int():
    with pytest.raises(ValidationError):
        Citation(ref="one", url="u", title="t", text="x")


def test_passage_defaults():
    p = Passage(text="t", url="u", title="T")
    assert p.lang == "pt-BR"
    assert p.breadcrumbs == ""
    assert p.score == 0.0
