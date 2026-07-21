"""Harness wiring tests — the parts of run.py that silently decide what a
run measures. Every case here is anchored on a live defect (F19).
"""

import run


def _matcher(hooks: dict, event: str) -> str:
    return hooks[event][0].matcher


def test_sdk_sessions_load_no_user_settings():
    """F19: without this the SDK loaded the operator's own settings — personal
    skills and a personal PreToolUse hook demonstrably ran inside benchmark
    sessions, and a skill's spec document landed in a run workdir."""
    opts = run.make_options(run.Path("/tmp/x"), "bare", None)
    assert opts.setting_sources == []


def test_bash_is_audited_but_never_gated():
    """The post hook's shell-audit branch (TIER0-SHELL-AUDIT) was unreachable
    in bench runs, so the plugin's "workarounds are audited" deterrent did not
    exist here. Bash must reach PostToolUse — and must NOT reach PreToolUse,
    where it would gate a channel ADR-0008 documents as ungated in v1."""
    hooks = run.make_hooks(run.Path("/tmp/x"), {"tier0", "tier0block"})
    assert "Bash" in _matcher(hooks, "PostToolUse")
    assert "Bash" not in _matcher(hooks, "PreToolUse")


def test_scope_wall_variants_carry_the_gate_channel():
    """The 2x2's gated arms must actually request the wall; a variant table
    typo would score a wall cell that never ran one."""
    for variant in ("blocking", "scope-only"):
        assert "tier0block" in run.VARIANT_CHANNELS[variant]
        assert run.GATE_MODE[variant] == "block"
    # the digest-only arm keeps the claims wall but switches the scope wall off
    assert run.SCOPE_MODE["blocking-claims-only"] == "off"
    # and the bare arm gets no hooks at all
    assert run.make_options(run.Path("/tmp/x"), "bare", None).hooks is None


def test_digest_channel_decides_the_prompt_hook():
    """scope-only is the wall-without-digest cell: if UserPromptSubmit leaked
    in, the cell would silently re-test the digest instead."""
    with_digest = run.make_hooks(run.Path("/tmp/x"), {"digest", "tier0", "tier0block"})
    without = run.make_hooks(run.Path("/tmp/x"), {"tier0", "tier0block"})
    assert "UserPromptSubmit" in with_digest
    assert "UserPromptSubmit" not in without
    # extraction writes the board in every non-bare variant, digest or not
    assert "Stop" in with_digest and "Stop" in without
