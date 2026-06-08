from rag_project.llm.openai_compatible import LLMConfig, OpenAICompatibleClient


class FakeTransport:
    def __init__(self):
        self.request = None

    def post_json(self, url, headers, payload, timeout):
        self.request = {
            "url": url,
            "headers": headers,
            "payload": payload,
            "timeout": timeout,
        }
        return {"choices": [{"message": {"content": "诊断报告"}}]}


def test_config_loads_openai_compatible_settings_from_env():
    config = LLMConfig.from_env(
        {
            "BADMINTON_LLM_BASE_URL": "http://localhost:8000/v1",
            "BADMINTON_LLM_API_KEY": "test-key",
            "BADMINTON_LLM_MODEL": "local-model",
        }
    )

    assert config.base_url == "http://localhost:8000/v1"
    assert config.api_key == "test-key"
    assert config.model == "local-model"


def test_openai_compatible_client_sends_chat_completion_payload():
    transport = FakeTransport()
    client = OpenAICompatibleClient(
        LLMConfig(base_url="http://localhost:8000/v1", api_key="test-key", model="local-model"),
        transport=transport,
    )

    result = client.complete([{"role": "user", "content": "hello"}])

    assert result == "诊断报告"
    assert transport.request["url"] == "http://localhost:8000/v1/chat/completions"
    assert transport.request["headers"]["Authorization"] == "Bearer test-key"
    assert transport.request["payload"]["model"] == "local-model"
    assert transport.request["payload"]["messages"][0]["content"] == "hello"
