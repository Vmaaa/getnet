from app.agents.support import MAX_TOOL_STEPS, SupportAgent
from fakes import FakeToolModel, ai_final, ai_tool


def test_answered_with_tools_used():
    model = FakeToolModel(
        [
            ai_tool("get_transactions", {"user_id": "cliente1988"}, "c1"),
            ai_final("Sales from yesterday settle tomorrow per settlement_date [tx001]."),
        ]
    )
    result = SupportAgent(chat_model=model).run("When will yesterday's sales be deposited?", "cliente1988")
    assert result.status == "answered"
    assert result.tools_used == ["get_transactions"]
    assert "settle" in result.answer


def test_step_cap_enforced():
    script = [ai_tool("get_transactions", {"user_id": "cliente1988"}, f"c{i}") for i in range(10)]
    model = FakeToolModel(script)
    result = SupportAgent(chat_model=model).run("give me everything", "cliente1988")
    assert result.status == "needs_help"
    assert model.calls == MAX_TOOL_STEPS


def test_tools_used_only_actual_executions():
    model = FakeToolModel(
        [
            ai_tool("get_device_status", {"user_id": "cliente1988"}, "c1"),
            ai_final("Your Get Smart 2 is offline. You mentioned transactions but I did not need them."),
        ]
    )
    result = SupportAgent(chat_model=model).run("machine offline?", "cliente1988")
    assert result.tools_used == ["get_device_status"]


def test_unknown_user_short_circuit():
    model = FakeToolModel([])
    result = SupportAgent(chat_model=model).run("when is my money coming?", "ghost_user")
    assert result.status == "answered"
    assert result.answer == "User ghost_user not found."
    assert result.tools_used == ["get_user_profile"]
    assert model.calls == 0


def test_missing_user_id_needs_help():
    result = SupportAgent(chat_model=FakeToolModel([])).run("when is my money coming?", None)
    assert result.status == "needs_help"
    assert result.gap == "user identifier missing"
