from typing import Literal

from pydantic import ValidationError
import pytest

from app.agents.knowledge import KnowledgeAgent, KnowledgeDecision, needs_web_search
from app.contracts import Passage


class FakeStructured:
    def __init__(self, decision):
        self.decision = decision

    def invoke(self, messages):
        return self.decision


class FakeChatModel:
    def __init__(self, decision):
        self.decision = decision
        self.prompts = []

    def with_structured_output(self, schema):
        assert schema is KnowledgeDecision
        return FakeStructured(self.decision)


def _passage(score=0.9, text="Get Smart has a touchscreen.", url="https://site.getnet.com.br/get-smart", title="Get Smart"):
    return Passage(text=text, url=url, title=title, score=score)


def test_answered_citations_mirror_context():
    passages = [_passage(), _passage(text="Get Clássica is basic.", url="u2", title="Clássica")]
    agent = KnowledgeAgent(
        chat_model=FakeChatModel(KnowledgeDecision(status="answered", answer="Get Smart has a touchscreen [1].")),
        retriever=lambda q: passages,
        web_search=lambda q: [],
    )
    result = agent.run("difference between get classica and smart?")
    assert result.status == "answered"
    assert [c.ref for c in result.citations] == [1, 2]
    assert result.citations[0].text == passages[0].text
    assert result.citations[1].url == "u2"


def test_needs_help_returns_gap_without_citations():
    agent = KnowledgeAgent(
        chat_model=FakeChatModel(KnowledgeDecision(status="needs_help", gap="missing pricing table")),
        retriever=lambda q: [_passage()],
        web_search=lambda q: [],
    )
    result = agent.run("what is the price?")
    assert result.status == "needs_help"
    assert result.gap == "missing pricing table"
    assert result.citations == []


def test_no_passages_no_web_results_needs_help():
    agent = KnowledgeAgent(
        chat_model=FakeChatModel(KnowledgeDecision(status="answered")),
        retriever=lambda q: [],
        web_search=lambda q: [],
    )
    result = agent.run("obscure question")
    assert result.status == "needs_help"
    assert "no information" in result.gap


def test_web_search_triggered_on_low_score():
    calls = []

    def fake_web(q):
        calls.append(q)
        return [_passage(score=0.5, text="web snippet")]

    agent = KnowledgeAgent(
        chat_model=FakeChatModel(KnowledgeDecision(status="answered", answer="from web [1]")),
        retriever=lambda q: [_passage(score=0.1)],
        web_search=fake_web,
    )
    result = agent.run("who is the ceo of getnet?")
    assert calls
    assert result.status == "answered"
    assert len(result.citations) == 2


def test_general_purpose_question_triggers_web():
    assert needs_web_search("What's the weather forecast in Porto Alegre tomorrow?", [_passage(score=0.99)])


def test_high_score_product_question_skips_web():
    assert not needs_web_search("What is the Get Smart?", [_passage(score=0.9)])


def test_decision_rejects_bad_status():
    with pytest.raises(ValidationError):
        KnowledgeDecision(status="maybe")
