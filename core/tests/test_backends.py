"""Backend plumbing tests — JSON recovery, auto-detect order. No network."""

import pytest

from scorekeeper.backends import (
    AnthropicBackend,
    BackendError,
    ClaudeCLIBackend,
    JSONParseError,
    OpenAICompatBackend,
    detect_backend,
    parse_json_object,
)


class FakeBackend:
    name = "fake"

    def __init__(self, text: str):
        self.text = text

    def complete(self, system: str, user: str) -> str:
        return self.text


# -- JSON recovery -------------------------------------------------------------


def test_parse_plain_json():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_fenced_json():
    text = 'Here you go:\n```json\n{"a": 1}\n```\nHope that helps!'
    assert parse_json_object(text) == {"a": 1}


def test_parse_json_with_prose_prefix():
    text = 'Sure! The result is {"commitments": []} as requested.'
    assert parse_json_object(text) == {"commitments": []}


def test_parse_rejects_non_object():
    with pytest.raises(JSONParseError) as exc:
        parse_json_object("[1, 2, 3] no object here")
    assert exc.value.raw.startswith("[1")


def test_parse_garbage_raises():
    with pytest.raises(JSONParseError):
        parse_json_object("I cannot answer that.")


# -- auto-detect order (ADR-0003) -----------------------------------------------


def test_detect_prefers_local_url(tmp_path):
    backend = detect_backend(
        tmp_path,
        env={"SCOREKEEPER_MODEL_URL": "http://localhost:11434/v1", "ANTHROPIC_API_KEY": "sk-x"},
    )
    assert isinstance(backend, OpenAICompatBackend)
    assert backend.base_url == "http://localhost:11434/v1"


def test_detect_falls_to_anthropic(tmp_path, monkeypatch):
    pytest.importorskip("anthropic")
    backend = detect_backend(tmp_path, env={"ANTHROPIC_API_KEY": "sk-x"})
    assert isinstance(backend, AnthropicBackend)


def test_detect_falls_to_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(ClaudeCLIBackend, "available", staticmethod(lambda: True))
    backend = detect_backend(tmp_path, env={})
    assert isinstance(backend, ClaudeCLIBackend)


def test_detect_nothing_available(tmp_path, monkeypatch):
    monkeypatch.setattr(ClaudeCLIBackend, "available", staticmethod(lambda: False))
    with pytest.raises(BackendError, match="no model backend"):
        detect_backend(tmp_path, env={})


def test_config_overrides_env(tmp_path):
    cfg_dir = tmp_path / ".scorekeeper"
    cfg_dir.mkdir()
    (cfg_dir / "config.yaml").write_text(
        "backend:\n  kind: openai_compat\n  url: http://box:8000/v1\n  model: llama3.1:8b\n"
    )
    backend = detect_backend(tmp_path, env={"ANTHROPIC_API_KEY": "sk-x"})
    assert isinstance(backend, OpenAICompatBackend)
    assert backend.base_url == "http://box:8000/v1"
    assert backend.model == "llama3.1:8b"


# -- openai_compat response handling --------------------------------------------


def test_openai_compat_parses_response(monkeypatch):
    backend = OpenAICompatBackend("http://x/v1")
    monkeypatch.setattr(
        backend,
        "_post",
        lambda payload: {"choices": [{"message": {"content": '{"ok": true}'}}]},
    )
    assert backend.complete("s", "u") == '{"ok": true}'


def test_openai_compat_malformed_response(monkeypatch):
    backend = OpenAICompatBackend("http://x/v1")
    monkeypatch.setattr(backend, "_post", lambda payload: {"error": "boom"})
    with pytest.raises(BackendError, match="malformed"):
        backend.complete("s", "u")


def test_retry_delay_parsing():
    import io
    import urllib.error

    def herr(headers=None):
        return urllib.error.HTTPError("http://x", 429, "Too Many", headers or {}, io.BytesIO())

    d = OpenAICompatBackend._retry_delay(herr(), 'quota... Please retry in 36.07s.')
    assert 36 < d < 38
    d = OpenAICompatBackend._retry_delay(herr(), "no hint here")
    assert d == 30.0
    d = OpenAICompatBackend._retry_delay(herr(), "retry in 500s")
    assert d == 65.0
