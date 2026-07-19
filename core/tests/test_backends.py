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


def test_detect_backend_tolerates_malformed_config(tmp_path):
    """Regression: an unparseable config.yaml crashed detect_backend with a
    YAMLError (which MCP assert_commitment does not catch) while the gate and
    extract readers silently degraded — one file, one failure policy."""
    cfg_dir = tmp_path / ".scorekeeper"
    cfg_dir.mkdir()
    (cfg_dir / "config.yaml").write_text("backend: [unclosed\n  kind: ][")
    backend = detect_backend(tmp_path, env={"SCOREKEEPER_MODEL_URL": "http://localhost:1/v1"})
    assert backend.name.startswith("openai_compat")  # fell back to env auto-detect


def test_env_url_overrides_config_pinned_kind(tmp_path):
    """Env wins over config — the unified precedence rule (audit 2026-07-19):
    a user pointing SCOREKEEPER_MODEL_URL at a local model was silently
    ignored when config pinned kind: anthropic_api."""
    cfg_dir = tmp_path / ".scorekeeper"
    cfg_dir.mkdir()
    (cfg_dir / "config.yaml").write_text("backend:\n  kind: anthropic_api\n  model: opus\n")
    backend = detect_backend(tmp_path, env={"SCOREKEEPER_MODEL_URL": "http://localhost:11434/v1"})
    assert isinstance(backend, OpenAICompatBackend)
    assert backend.base_url == "http://localhost:11434/v1"


def test_env_url_takes_model_from_config_when_env_omits_it(tmp_path):
    cfg_dir = tmp_path / ".scorekeeper"
    cfg_dir.mkdir()
    (cfg_dir / "config.yaml").write_text(
        "backend:\n  kind: openai_compat\n  url: http://box:8000/v1\n  model: llama3.1:8b\n"
    )
    backend = detect_backend(tmp_path, env={"SCOREKEEPER_MODEL_URL": "http://other:9000/v1"})
    assert backend.base_url == "http://other:9000/v1"  # env url wins
    assert backend.model == "llama3.1:8b"  # config fills the gap


def test_openai_compat_budget_bounds_retries(monkeypatch):
    """One complete() must not sleep-retry past its time budget — callers sit
    under hard hook deadlines."""
    import io
    import urllib.error
    import urllib.request

    def always_429(req, timeout):
        raise urllib.error.HTTPError(
            req.full_url, 429, "rate limited", {}, io.BytesIO(b"retry in 60s")
        )

    sleeps: list[float] = []
    monkeypatch.setattr(urllib.request, "urlopen", always_429)
    monkeypatch.setattr("scorekeeper.backends.openai_compat.time.sleep", sleeps.append)
    backend = OpenAICompatBackend("http://localhost:1/v1", budget=5.0)
    with pytest.raises(BackendError, match="budget"):
        backend.complete("s", "u")
    assert sleeps == []  # the 61s hinted delay exceeded the 5s budget outright


def test_claude_cli_passes_real_system_prompt(monkeypatch):
    """The system prompt goes through --append-system-prompt, not folded into
    the user turn (instruction adherence on the weakest backend)."""
    import subprocess

    seen: dict = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv

        class P:
            returncode = 0
            stdout = "{}"
            stderr = ""

        return P()

    monkeypatch.setattr(ClaudeCLIBackend, "available", staticmethod(lambda: True))
    monkeypatch.setattr(subprocess, "run", fake_run)
    ClaudeCLIBackend().complete("SYSTEM RULES", "user text")
    argv = seen["argv"]
    assert argv[argv.index("--append-system-prompt") + 1] == "SYSTEM RULES"
    assert argv[-1] == "user text"
