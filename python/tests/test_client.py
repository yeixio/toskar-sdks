import json

import httpx
import pytest
import respx

from toskar import CONTRACT_VERSION, AsyncToskar, Done, ErrorCodes, Token, Toskar, ToskarError, models, read_events

BASE = "http://127.0.0.1:7331"


def sse(*events: str) -> httpx.Response:
    return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, content="".join(events).encode())


@respx.mock
def test_reaches_this_computer_says_its_contract_and_sends_a_key():
    route = respx.get(f"{BASE}/api/v1/version").respond(json={"version": "1.11.0", "commit": "abc", "build_date": "2026-10-23", "product": "Toskar Core", "license": "AGPL-3.0", "source": "https://github.com/yeixio/toskar-core", "contract": {"version": "1.56", "major": 1}})
    v = Toskar(api_key="tk_test").version()
    assert v.version == "1.11.0"
    request = route.calls.last.request
    assert request.headers["Toskar-Client-Contract"] == CONTRACT_VERSION
    assert request.headers["Authorization"] == "Bearer tk_test"


@respx.mock
def test_reads_the_url_and_key_from_the_environment(monkeypatch):
    monkeypatch.setenv("TOSKAR_URL", "http://studio.local:7331/")
    monkeypatch.setenv("TOSKAR_API_KEY", "tk_env")
    route = respx.get("http://studio.local:7331/api/v1/models").respond(json=[])
    assert Toskar().api.list_models() == []
    assert route.calls.last.request.headers["Authorization"] == "Bearer tk_env"


@respx.mock
def test_chats_waiting_for_the_whole_answer():
    route = respx.post(f"{BASE}/api/v1/chat").respond(json={"content": "Hello!", "metrics": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5, "ttft_ms": 1, "prompt_ms": 1, "eval_ms": 1, "total_ms": 2, "prompt_tok_per_sec": 1, "eval_tok_per_sec": 1}})
    answer = Toskar().chat("Hi", profile_id="default", conversation_id=None)
    assert answer.content == "Hello!" and answer.metrics.prompt_tokens == 3
    assert json.loads(route.calls.last.request.content) == {"message": "Hi", "profile_id": "default", "stream": False}


@respx.mock
def test_streams_an_answer_as_it_is_written():
    respx.post(f"{BASE}/api/v1/chat").mock(return_value=sse('event: token\ndata: {"content":"Hel"}\n\n', ": ping\n\n", 'event: token\ndata: {"content":"lo"}\n\n', "event: done\ndata: {}\n\n"))
    assert list(Toskar().chat_stream("Hi")) == [Token("Hel"), Token("lo"), Done()]


@respx.mock
def test_raises_a_streamed_failure_with_its_code():
    respx.post(f"{BASE}/api/v1/chat").mock(return_value=sse('event: token\ndata: {"content":"Hi"}\n\n', 'event: error_code\ndata: {"code":"MODEL_NOT_INSTALLED","message":"model x is not installed","details":{"model_id":"x"}}\n\n', "event: error\ndata: model x is not installed\n\n"))
    with pytest.raises(ToskarError) as err:
        list(Toskar().chat_stream("Hi"))
    assert err.value.code == ErrorCodes.MODEL_NOT_INSTALLED and err.value.details == {"model_id": "x"}


@respx.mock
def test_says_when_a_stream_was_cut_off():
    respx.post(f"{BASE}/api/v1/chat").mock(return_value=sse('event: token\ndata: {"content":"Hi"}\n\n'))
    with pytest.raises(ToskarError) as err:
        list(Toskar().chat_stream("Hi"))
    assert err.value.code == "CONNECTION_LOST"


@respx.mock
def test_turns_an_error_answer_into_a_toskar_error():
    respx.post(f"{BASE}/api/v1/chat").respond(401, json={"error": {"code": "API_KEY_REQUIRED", "message": "an API key is required"}})
    with pytest.raises(ToskarError) as err:
        Toskar().chat("Hi")
    assert (err.value.status, err.value.code, str(err.value)) == (401, "API_KEY_REQUIRED", "an API key is required")


@respx.mock
def test_retries_a_safe_request_but_never_a_chat(monkeypatch):
    monkeypatch.setattr("toskar._client._Options.backoff", staticmethod(lambda attempt: 0))
    models_route = respx.get(f"{BASE}/api/v1/models").mock(side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(200, json=[])])
    assert Toskar().api.list_models() == []
    assert models_route.call_count == 3
    chat = respx.post(f"{BASE}/api/v1/chat").respond(503)
    with pytest.raises(ToskarError):
        Toskar().chat("Hi")
    assert chat.call_count == 1


@respx.mock
def test_every_route_is_typed():
    respx.post(f"{BASE}/api/v1/conversations").respond(201, json={"id": "c1", "title": "Trip", "memory_off": False, "compact_off": False, "created_at": "2026-10-23T00:00:00Z", "updated_at": "2026-10-23T00:00:00Z", "a_newer_field": 1})
    conv = Toskar().api.create_conversation(body={"title": "Trip"})
    assert isinstance(conv, models.Conversation) and conv.id == "c1"
    respx.get(f"{BASE}/api/v1/conversations/c1/messages").respond(json=[])
    assert Toskar().api.list_conversation_messages("c1") == []


@respx.mock
def test_reads_the_events_stream():
    respx.get(f"{BASE}/api/v1/events").mock(return_value=sse('event: model.unloaded\ndata: {"id":"e1","type":"model.unloaded","timestamp":"2026-10-23T00:00:00Z","contract":"1.56","data":{"model_id":"m"}}\n\n'))
    assert [e.type for e in Toskar().events()] == ["model.unloaded"]


@pytest.mark.asyncio
@respx.mock
async def test_async_streams_too():
    respx.post(f"{BASE}/api/v1/chat").mock(return_value=sse('event: token\ndata: {"content":"Hi"}\n\n', "event: done\ndata: {}\n\n"))
    async with AsyncToskar() as toskar:
        assert [e async for e in toskar.chat_stream("Hi")] == [Token("Hi"), Done()]


def test_read_events_reads_names_data_on_several_lines_and_skips_comments():
    lines = ["event: a", "data: 1", "data: 2", "", ": ping", "", "data: plain"]
    assert [(e.event, e.data) for e in read_events(lines)] == [("a", "1\n2"), ("message", "plain")]
