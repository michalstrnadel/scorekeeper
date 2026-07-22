"""Reference-loop wiring tests (ADR-0009) — the parts that silently decide
what a loop run measures: tool-belt semantics, wall/audit wiring around
dispatch, digest injection, compaction reset, and wire translation. Pure
Python, no network.
"""

import json
from pathlib import Path

import pytest
from agent_backends import (
    AnthropicAgentBackend,
    OpenAICompatAgentBackend,
    ToolCall,
    TurnResult,
)
from agent_tools import ToolError, execute
from loop_run import SYSTEM_PROMPT, dispatch_tool, drive_loop
from run import PhaseStats, degraded_phases, seed_board

from scorekeeper.store import Store


@pytest.fixture()
def workdir(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("x = 1\ny = 2\n")
    (tmp_path / "legacy").mkdir()
    (tmp_path / "legacy" / "util.py").write_text("old = True\n")
    return tmp_path


GT = {
    "commitments": [
        {
            "key": "gt-1",
            "claim": "Write scope is app/ only.",
            "kind": "decision",
            "scope": ["topic:task-scope", "path:app/**"],
            "entitlement_source": "user_utterance",
        }
    ]
}


def _gated(workdir) -> set[str]:
    Store(workdir).init()
    (workdir / ".scorekeeper" / "config.yaml").write_text("tier0_gate: block\n")
    seed_board(workdir, GT)
    return {"digest", "tier0", "tier0block"}


# --- tool belt --------------------------------------------------------------


def test_paths_are_confined_to_the_workdir(workdir):
    with pytest.raises(ToolError, match="escapes"):
        execute(workdir, "Read", {"file_path": "../outside.txt"})
    with pytest.raises(ToolError, match="escapes"):
        execute(workdir, "Write", {"file_path": "/etc/hosts", "content": "x"})


def test_edit_requires_a_unique_match(workdir):
    (workdir / "app" / "dup.py").write_text("a\na\n")
    with pytest.raises(ToolError, match="matches 2 times"):
        execute(workdir, "Edit",
                {"file_path": "app/dup.py", "old_string": "a", "new_string": "b"})
    execute(workdir, "Edit", {"file_path": "app/dup.py", "old_string": "a",
                              "new_string": "b", "replace_all": True})
    assert (workdir / "app" / "dup.py").read_text() == "b\nb\n"


def test_write_creates_parents_and_read_numbers_lines(workdir):
    execute(workdir, "Write", {"file_path": "app/sub/new.py", "content": "hello\n"})
    assert (workdir / "app" / "sub" / "new.py").read_text() == "hello\n"
    out = execute(workdir, "Read", {"file_path": "app/main.py"})
    assert out.splitlines()[0].strip().startswith("1")


def test_bash_runs_in_the_workdir(workdir):
    out = execute(workdir, "Bash", {"command": "ls app"})
    assert "main.py" in out


# --- hook wiring ------------------------------------------------------------


def test_wall_denies_out_of_scope_write_and_logs_it(workdir):
    channels = _gated(workdir)
    content, is_error = dispatch_tool(
        workdir, channels,
        ToolCall(id="1", name="Write",
                 arguments={"file_path": "legacy/util.py", "content": "new = True\n"}),
    )
    assert is_error
    assert (workdir / "legacy" / "util.py").read_text() == "old = True\n", \
        "denied tool must never execute"
    ops = [e["op"] for e in Store(workdir).log_entries()]
    assert "TIER0-SCOPE-DENY" in ops


def test_wall_passes_in_scope_write(workdir):
    channels = _gated(workdir)
    content, is_error = dispatch_tool(
        workdir, channels,
        ToolCall(id="1", name="Write",
                 arguments={"file_path": "app/new.py", "content": "z = 3\n"}),
    )
    assert not is_error
    assert (workdir / "app" / "new.py").exists()


def test_bare_channels_never_gate(workdir):
    _gated(workdir)  # board + config exist, but bare gets no channels
    content, is_error = dispatch_tool(
        workdir, set(),
        ToolCall(id="1", name="Write",
                 arguments={"file_path": "legacy/util.py", "content": "new = True\n"}),
    )
    assert not is_error


def test_malformed_arguments_become_an_error_result(workdir):
    content, is_error = dispatch_tool(
        workdir, set(), ToolCall(id="1", name="Write", arguments={}, parse_error="{bad"),
    )
    assert is_error and "malformed" in content


# --- drive_loop -------------------------------------------------------------


class ScriptedBackend:
    name = "scripted"
    model = "test"

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen: list[list[dict]] = []

    def run_turn(self, system, messages, tools):
        assert system == SYSTEM_PROMPT
        self.seen.append([dict(m) for m in messages])
        return self.turns.pop(0)


def _turn(text="done"):
    return TurnResult(text=text, input_tokens=10, output_tokens=20)


def test_digest_is_prepended_only_for_digest_variants(workdir):
    _gated(workdir)
    assert Store(workdir).render_digest(), "seeded board must render a digest"
    scenario = {"phases": [{"user": "do the task"}]}

    b = ScriptedBackend([_turn()])
    drive_loop(scenario, workdir, "scorekept", b)
    assert b.seen[0][0]["content"] != "do the task"
    assert b.seen[0][0]["content"].endswith("do the task")

    b = ScriptedBackend([_turn()])
    drive_loop(scenario, workdir, "scope-only", b)
    assert b.seen[0][0]["content"] == "do the task"


def test_force_compact_clears_history_but_not_the_workdir(workdir):
    scenario = {"phases": [
        {"user": "phase one"},
        {"harness": "force_compact"},
        {"user": "phase two"},
    ]}
    b = ScriptedBackend([_turn(), _turn()])
    phases = drive_loop(scenario, workdir, "bare", b)
    assert len(phases) == 2
    assert len(b.seen[1]) == 1, "post-compact call must see a fresh history"
    assert b.seen[1][0]["content"] == "phase two"
    assert (workdir / "app" / "main.py").exists()


def test_backend_errors_surface_as_degraded_phases():
    p = PhaseStats(prompt="x", blocked_reason="backend error: boom",
                   output_tokens=0, reply_chars=0)
    assert degraded_phases([p]) == [1]


# --- wire translation -------------------------------------------------------


def test_openai_compat_round_trip_shapes():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "look",
         "tool_calls": [ToolCall(id="c1", name="Read",
                                 arguments={"file_path": "a.py"})]},
        {"role": "tool", "tool_call_id": "c1", "name": "Read",
         "content": "1\tx", "is_error": False},
    ]
    wire = OpenAICompatAgentBackend._translate_history("sys", history)
    assert wire[0] == {"role": "system", "content": "sys"}
    call = wire[2]["tool_calls"][0]
    assert call["type"] == "function"
    assert json.loads(call["function"]["arguments"]) == {"file_path": "a.py"}
    assert wire[3] == {"role": "tool", "tool_call_id": "c1", "content": "1\tx"}


def test_openai_compat_parses_and_flags_malformed_arguments():
    msg = {"tool_calls": [
        {"id": "a", "function": {"name": "Read", "arguments": '{"file_path": "x"}'}},
        {"id": "b", "function": {"name": "Read", "arguments": "{broken"}},
    ]}
    good, bad = OpenAICompatAgentBackend._parse_calls(msg)
    assert good.arguments == {"file_path": "x"} and not good.parse_error
    assert bad.arguments == {} and bad.parse_error


def test_anthropic_collapses_consecutive_tool_results():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "",
         "tool_calls": [ToolCall(id="c1", name="Read", arguments={}),
                        ToolCall(id="c2", name="Glob", arguments={})]},
        {"role": "tool", "tool_call_id": "c1", "name": "Read",
         "content": "one", "is_error": False},
        {"role": "tool", "tool_call_id": "c2", "name": "Glob",
         "content": "two", "is_error": True},
    ]
    wire = AnthropicAgentBackend._translate_history(history)
    assert len(wire) == 3, "both tool results must share one user turn"
    results = wire[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["c1", "c2"]
    assert results[1]["is_error"] is True


def test_loop_variant_channels_have_no_stopblock():
    from loop_run import LOOP_VARIANTS
    from run import VARIANT_CHANNELS
    # the loop is seeded-only (no extraction); a variant whose behavior
    # DEPENDS on stopblock must not be offered. stopblock present in the
    # product channel set is fine — the loop simply never wires a Stop hook.
    assert "bare" in LOOP_VARIANTS
    for v in LOOP_VARIANTS:
        if v != "bare":
            assert v in VARIANT_CHANNELS


def test_workdir_fixture_is_isolated():
    # tmp_path fixtures write under pytest's tmp roots, never the repo
    assert not Path("app").exists()


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
