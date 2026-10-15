import pytest

from chaperone import gateway, policy


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for dest in ("INTERNAL", "EXTERNAL"):
        monkeypatch.setenv(f"{dest}_LLM_BASE_URL", "http://llm.invalid/v1")
        monkeypatch.setenv(f"{dest}_LLM_MODEL", "stub")
    monkeypatch.setenv("AUDIT_HMAC_KEY", "test-key-not-secret")
    monkeypatch.setattr(gateway, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(policy, "LOCAL_PATH", tmp_path / "policies.local.yaml")  # tests never touch real edits
    gateway.SESSIONS.clear()


# stands in for the remote model, records exactly what reached it; local Ollama calls go through
class StubLLM:
    def __init__(self, real_post, reply="ok"):
        self.real_post, self.reply, self.calls = real_post, reply, []

    def __call__(self, url, json, **kwargs):
        import httpx

        if "llm.invalid" not in url:
            return self.real_post(url, json=json, **kwargs)
        self.calls.append(json)
        reply = self.reply(json) if callable(self.reply) else self.reply
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]},
                              request=httpx.Request("POST", url))


@pytest.fixture
def llm(monkeypatch):
    stub = StubLLM(gateway.httpx.post)
    monkeypatch.setattr(gateway.httpx, "post", stub)
    return stub
