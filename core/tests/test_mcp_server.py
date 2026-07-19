"""MCP server tests — every write routes through the operator door (c-0008)."""

import pytest

pytest.importorskip("mcp")

from scorekeeper import (  # noqa: E402
    Status,
    Store,
    mcp_server,  # noqa: E402
)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOREKEEPER_ROOT", str(tmp_path))
    # no model backend in tests: tier0-only paths
    for var in ("SCOREKEEPER_MODEL_URL", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def test_assert_and_digest(root):
    out = mcp_server.assert_commitment(
        "The primary database is PostgreSQL 16.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    )
    assert len(out["asserted"]) == 1
    assert "PostgreSQL 16" in mcp_server.get_digest()
    assert "PostgreSQL 16" in mcp_server.get_scoreboard()


def test_assert_drift_conflicts_via_operators(root):
    mcp_server.assert_commitment(
        "The primary database is PostgreSQL 16.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    )
    out = mcp_server.assert_commitment(
        "Activity feed storage uses MongoDB.",
        scope=["topic:persistence", "attr:persistence.primary_db=mongodb"],
        source="prior_inference",
    )
    assert len(out["conflicts"]) == 1
    assert out["conflicts"][0]["reason"].startswith("tier0")


def test_check_compatibility_dry_run(root):
    mcp_server.assert_commitment(
        "The primary database is PostgreSQL 16.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    )
    out = mcp_server.check_compatibility(
        "Use MongoDB for the feed.", scope=["attr:persistence.primary_db=mongodb"]
    )
    assert len(out["tier0_collisions"]) == 1
    assert len(Store(root).active()) == 1  # nothing written


def test_supersede_requires_external_entitlement(root):
    out = mcp_server.assert_commitment(
        "Caching uses Redis.", scope=["topic:caching", "attr:caching.backend=redis"]
    )
    cid = out["asserted"][0]
    with pytest.raises(ValueError, match="external entitlement"):
        mcp_server.supersede(cid, "Caching uses an LRU.", source="prior_inference")
    result = mcp_server.supersede(cid, "Caching uses an in-process LRU.")
    old = Store(root).load(result["superseded"])
    new = Store(root).load(result["by"])
    assert old.status == Status.SUPERSEDED and old.superseded_by == new.id
    assert new.supersedes == old.id


def test_challenge_and_retract(root):
    out = mcp_server.assert_commitment(
        "httpmini supports automatic retries.", kind="assertion",
        scope=["topic:vendored-lib"], source="none",
    )
    cid = out["asserted"][0]
    ch = mcp_server.challenge(cid, "no source read")
    assert ch["suspect"] is True
    rt = mcp_server.retract(cid, "could not back it")
    assert rt["retracted"] == cid
    assert Store(root).load(cid).status == Status.RETRACTED
    assert Store(root).active() == []


def test_supersede_drops_stale_attr_pins_by_default(root):
    """Regression: supersede copied the old scope verbatim, so the replacement
    kept the OLD claim's attr pins and Tier-0 went on enforcing the replaced
    choice against the very technology the supersede just introduced."""
    out = mcp_server.assert_commitment(
        "The primary database is PostgreSQL 16.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    )
    result = mcp_server.supersede(out["asserted"][0], "The primary database is MongoDB.")
    new = Store(root).load(result["by"])
    assert new.scope == ["topic:persistence"]  # topics carry over, pins don't
    probe = mcp_server.check_compatibility(
        "Store the feed in MongoDB.", scope=["attr:persistence.primary_db=mongodb"]
    )
    assert probe["tier0_collisions"] == []


def test_supersede_explicit_scope_pins_the_new_choice(root):
    out = mcp_server.assert_commitment(
        "The primary database is PostgreSQL 16.",
        scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    )
    result = mcp_server.supersede(
        out["asserted"][0],
        "The primary database is MongoDB.",
        scope=["topic:persistence", "attr:persistence.primary_db=mongodb"],
    )
    new = Store(root).load(result["by"])
    assert "attr:persistence.primary_db=mongodb" in new.scope


def test_write_tools_report_their_resolved_root(root):
    """Hooks resolve the store from the session cwd, the MCP server from
    SCOREKEEPER_ROOT — when they diverge, supersede writes a board the wall
    never reads. Every write tool reports which root it acted on."""
    out = mcp_server.assert_commitment(
        "Caching uses Redis.", scope=["topic:caching", "attr:caching.backend=redis"]
    )
    assert out["root"] == str(root.resolve())
    sup = mcp_server.supersede(out["asserted"][0], "Caching uses an in-process LRU.")
    assert sup["root"] == str(root.resolve())
