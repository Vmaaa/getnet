from langchain_core.messages import AIMessage


class FakeToolModel:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def bind_tools(self, tools):
        assert {t.name for t in tools} >= {"get_user_profile", "get_transactions", "get_device_status"}
        return self

    def invoke(self, messages):
        self.calls += 1
        if not self.script:
            raise AssertionError("loop exceeded scripted steps")
        return self.script.pop(0)


def ai_tool(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def ai_final(text):
    return AIMessage(content=text)
