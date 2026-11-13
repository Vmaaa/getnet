from fastapi.testclient import TestClient

from app.api.main import create_app
from app.contracts import AgentResult, Citation
from app.graph.state import FinalResponse, TraceEntry


class FakeOrchestrator:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def handle(self, message, user_id=None):
        self.calls.append((message, user_id))
        return self.response


def _final(status="answered", citations=None, tools=None):
    return FinalResponse(
        status=status,
        answer="an answer",
        citations=citations or [],
        tools_used=tools or [],
        agent_trace=[TraceEntry(attempt=1, agent="knowledge", status="answered")],
        session_id="s123",
    )


def _client(orchestrator):
    return TestClient(create_app(orchestrator=orchestrator))


def test_chat_knowledge_intent_returns_schema():
    citations = [Citation(ref=1, url="u", title="t", text="exact")]
    fake = FakeOrchestrator(_final(citations=citations))
    response = _client(fake).post("/chat", json={"message": "What is Get Smart?", "user_id": "cliente1988"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert [c["ref"] for c in body["citations"]] == [1]
    assert body["agent_trace"][0]["agent"] == "knowledge"
    assert body["session_id"] == "s123"
    assert fake.calls == [("What is Get Smart?", "cliente1988")]


def test_chat_support_tools_passthrough():
    fake = FakeOrchestrator(_final(tools=["get_transactions"]))
    response = _client(fake).post("/chat", json={"message": "When is my money deposited?", "user_id": "cliente1988"})
    assert response.status_code == 200
    assert response.json()["tools_used"] == ["get_transactions"]


def test_chat_triage_envelope():
    fake = FakeOrchestrator(_final(status="triage"))
    response = _client(fake).post("/chat", json={"message": "anything weird"})
    assert response.status_code == 200
    assert response.json()["status"] == "triage"


def test_validation_error_on_empty_message():
    response = _client(FakeOrchestrator(_final())).post("/chat", json={"message": "", "user_id": "u"})
    assert response.status_code == 422


def test_validation_error_on_missing_message():
    response = _client(FakeOrchestrator(_final())).post("/chat", json={"user_id": "u"})
    assert response.status_code == 422


def test_health_reports_state():
    fake = FakeOrchestrator(_final())
    with TestClient(create_app(orchestrator=fake)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "chroma_chunks" in body
    assert "embedder" in body
