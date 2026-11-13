import pytest

from app.agents.router import GapExhausted, IntentDecision, RouterAgent, heuristic_intent
from app.contracts import AgentResult


class FakeStructured:
    def __init__(self, outcome):
        self.outcome = outcome

    def invoke(self, messages):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeClassifier:
    def __init__(self, outcome):
        self.outcome = outcome
        self.prompts = []

    def with_structured_output(self, schema):
        assert schema.__name__ == "IntentDecision"
        return FakeStructured(self.outcome)


class FakeAgent:
    def __init__(self, agent_name, results):
        self.agent_name = agent_name
        self.results = list(results)
        self.calls = []

    def run(self, message, user_id=None):
        self.calls.append((message, user_id))
        if isinstance(self.results[0], Exception):
            raise self.results.pop(0)
        return self.results.pop(0)


def _result(agent="knowledge", status="answered", gap=None):
    return AgentResult(agent=agent, status=status, answer="ok", gap=gap)


def _router(knowledge_results, support_results, classifier=None):
    knowledge = FakeAgent("knowledge", knowledge_results)
    support = FakeAgent("support", support_results)
    router = RouterAgent(knowledge, support, chat_model=classifier)
    return router, knowledge, support


def test_route_dispatches_to_knowledge():
    router, knowledge, support = _router([_result()], [_result(agent="support")])
    result = router.route("What is Get Smart?", "cliente1988")
    assert result.status == "answered"
    assert knowledge.calls and not support.calls


def test_route_dispatches_to_support():
    router, knowledge, support = _router([_result()], [_result(agent="support")])
    router.route("When will my money be deposited?", "cliente1988")
    assert support.calls and not knowledge.calls


def test_heuristic_fallback_on_classifier_failure():
    classifier = FakeClassifier(RuntimeError("boom"))
    router, knowledge, support = _router([_result()], [_result(agent="support")], classifier=classifier)
    intent, reasoning = router.classify("Where is my money from yesterday?")
    assert intent == "support"
    assert reasoning == "heuristic fallback"


def test_replan_injects_gap_and_registers():
    captured = {}

    class CaptureStructured:
        def invoke(self, messages):
            captured["messages"] = messages
            return IntentDecision(intent="support", reasoning="ok")

    class CaptureClassifier:
        def with_structured_output(self, schema):
            assert schema.__name__ == "IntentDecision"
            return CaptureStructured()

    router, knowledge, support = _router([_result()], [_result(agent="support")], classifier=CaptureClassifier())
    result = router.replan("settlement dates missing", "when is my money coming?", "cliente1988")
    user_content = captured["messages"][1]["content"]
    assert "settlement dates missing" in user_content
    assert router.has_gap("SETTLEMENT dates missing")
    assert not router.has_gap("different gap")


def test_replan_same_gap_raises():
    router, knowledge, support = _router(
        [_result(status="needs_help", gap="g1"), _result(agent="support")],
        [],
    )
    router.replan("g1", "question", "cliente1988")
    with pytest.raises(GapExhausted):
        router.replan("g1 ", "question", "cliente1988")


def test_reset_gaps():
    router, _, _ = _router([_result()], [])
    router.register_gap("g1")
    router.reset_gaps()
    assert not router.has_gap("g1")


def test_heuristic_intent_rules():
    assert heuristic_intent("What is the Get Smart?") == "knowledge"
    assert heuristic_intent("My card machine won't connect") == "support"
    assert heuristic_intent("What's the weather in Porto Alegre?") == "knowledge"
    assert heuristic_intent("When will the money from yesterday's sales be deposited?") == "support"
