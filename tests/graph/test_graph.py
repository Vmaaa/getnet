from app.contracts import AgentResult, Citation
from app.graph.builder import MAX_PASSES, Orchestrator
from app.agents.router import RouterAgent


class FakeRouter:
    def __init__(self, intents, knowledge_results, support_results):
        self.intents = list(intents)
        self.knowledge = FakeAgent("knowledge", knowledge_results)
        self.support = FakeAgent("support", support_results)
        self._ledger = set()
        self.classify_calls = []

    def reset_gaps(self):
        self._ledger.clear()

    def has_gap(self, gap):
        return gap.lower() in self._ledger

    def register_gap(self, gap):
        self._ledger.add(gap.lower())

    def classify(self, message, gap=None):
        self.classify_calls.append(gap)
        return self.intents.pop(0), "reasoning"


class FakeAgent:
    def __init__(self, name, results):
        self.name = name
        self.results = list(results)
        self.calls = []

    def run(self, message, user_id=None):
        self.calls.append((message, user_id))
        return self.results.pop(0)


def _answered(text="here you go", citations=None, tools=None):
    return AgentResult(
        agent="knowledge",
        status="answered",
        answer=text,
        citations=citations or [],
        tools_used=tools or [],
    )


def _needs_help(gap):
    return AgentResult(agent="knowledge", status="needs_help", gap=gap)


def test_answered_first_pass_single_trace():
    router = FakeRouter(["knowledge"], [_answered()], [])
    response = Orchestrator(router).handle("What is Get Smart?", "cliente1988")
    assert response.status == "answered"
    assert len(response.agent_trace) == 1
    assert response.agent_trace[0].attempt == 1


def test_second_pass_recovers():
    router = FakeRouter(
        ["knowledge", "knowledge"],
        [_needs_help("pricing table missing"), _answered("price is R$X")],
        [],
    )
    response = Orchestrator(router).handle("how much is Get Tap?", None)
    assert response.status == "answered"
    assert [e.attempt for e in response.agent_trace] == [1, 2]
    assert response.agent_trace[1].gap is None
    assert router.classify_calls[1] == "pricing table missing"


def test_exhaustion_two_passes_triage():
    router = FakeRouter(
        ["knowledge", "knowledge"],
        [_needs_help("g1"), _needs_help("g2")],
        [],
    )
    response = Orchestrator(router).handle("weird question", None)
    assert response.status == "triage"
    assert "human support" in response.answer
    assert [e.attempt for e in response.agent_trace] == [1, 2]


def test_repeated_gap_triages_on_second_occurrence():
    router = FakeRouter(
        ["knowledge", "knowledge"],
        [_needs_help("same gap"), _needs_help("same gap")],
        [],
    )
    response = Orchestrator(router).handle("question", None)
    assert response.status == "triage"
    assert [e.attempt for e in response.agent_trace] == [1, 2]
    assert response.agent_trace[1].gap == "same gap"


def test_needs_help_without_gap_triages_without_replan():
    router = FakeRouter(["knowledge"], [AgentResult(agent="knowledge", status="needs_help", gap=None)], [])
    response = Orchestrator(router).handle("question", None)
    assert response.status == "triage"
    assert len(response.agent_trace) == 1


def test_citations_and_tools_passthrough():
    citations = [Citation(ref=1, url="u", title="t", text="exact")]
    router = FakeRouter(
        ["support"],
        [],
        [AgentResult(agent="support", status="answered", answer="settles today", tools_used=["get_transactions"])],
    )
    router.knowledge.results = [_answered(citations=citations)]
    response = Orchestrator(router).handle("when is my money?", "cliente1988")
    assert response.status == "answered"
    assert response.tools_used == ["get_transactions"]
    assert response.citations == []


def test_pass_cap_is_two():
    assert MAX_PASSES == 2


def test_ledger_resets_between_sessions():
    router = FakeRouter(
        ["knowledge", "knowledge"],
        [_needs_help("g1"), _needs_help("g1")],
        [],
    )
    orchestrator = Orchestrator(router)
    first = orchestrator.handle("q", None)
    assert first.status == "triage"
    assert router.has_gap("g1")
    router.intents = ["knowledge"]
    router.knowledge.results = [_answered()]
    second = orchestrator.handle("q", None)
    assert second.status == "answered"
    assert not router.has_gap("g1")
