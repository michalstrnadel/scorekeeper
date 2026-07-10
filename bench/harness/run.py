"""Phase-0 eval harness — planted scenarios, with/without scorekeeper.

    uv run python run.py --scenario scenario-01-db-choice --variant scorekept
    uv run python run.py --all                     # full matrix (bare + scorekept)

Per run: copies the scenario seed repo to a temp workdir, drives the agent
through the phases via the Claude Agent SDK, and (scorekept variant) attaches
the SAME handler functions the plugin uses — UserPromptSubmit digest injection
(the harness twin of SessionStart, ADR-0002), PostToolUse tier0 content scan,
Stop extraction + operators with block-on-findings.

``harness: force_compact`` is emulated by restarting the session (fresh
context) for BOTH variants — post-compact context loss, deterministically;
the scorekept variant then re-injects the digest, which is exactly the
mechanism under test.

Outputs bench/results/run-<stamp>/results.json + summary.md with SCR (judge
verdicts), normative events vs ground truth (incl. must_not_fire FPR probes),
and token overhead.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

from datetime import UTC, datetime

from judge import judge_trajectory
from stats import summarize_binary, summarize_latency
from scorekeeper.cli import hook_post_tool_use, hook_stop
from scorekeeper.model import Commitment, Entitlement, EntitlementSource, Kind
from scorekeeper.store import Store

TASKS_DIR = Path(__file__).parent.parent / "tasks"
RESULTS_DIR = Path(__file__).parent.parent / "results"

def seed_board(workdir: Path, ground_truth: dict) -> int:
    """Pre-populate the scoreboard with the scenario's ground-truth commitments.

    Isolates the steering hypothesis (does a commitment ON the board prevent
    drift?) from extraction reliability (does the Stop hook build the board?) —
    the latter is a separate axis. Mirrors the F0 dogfood board: the commitment
    is present by construction, exactly as if an earlier, cleanly-extracted turn
    had recorded it. Uses the same model/store path as the operators.
    """
    store = Store(workdir)
    store.init()
    seeded = 0
    for i, gt in enumerate(ground_truth.get("commitments", []), 1):
        c = Commitment(
            id=f"c-{datetime.now(UTC):%Y-%m-%d}-{i:04d}",
            ts=datetime.now(UTC),
            session="seed",
            claim=gt["claim"],
            kind=Kind(gt.get("kind", "decision")),
            scope=gt.get("scope", []),
            entitlement=Entitlement(
                source=EntitlementSource(gt.get("entitlement_source", "user_utterance")),
                note="seeded from ground truth (pre-established commitment)",
            ),
        )
        store.save(c)
        store.log("ASSERT", c.id, f"seeded: {c.claim}")
        seeded += 1
    store.write_scoreboard()
    return seeded


@dataclass
class PhaseStats:
    prompt: str
    prompt_full: str = ""
    reply_chars: int = 0
    reply_tail: str = ""
    reply_text: str = ""
    tools_used: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    wall_seconds: float = 0.0
    blocked_reason: str = ""


@dataclass
class RunResult:
    scenario: str
    variant: str
    phases: list[PhaseStats] = field(default_factory=list)
    judge: dict = field(default_factory=dict)
    events: dict = field(default_factory=dict)
    scoreboard_log: list = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    wall_seconds: float = 0.0
    error: str = ""


def load_scenario(name: str, tasks_dir: Path = TASKS_DIR) -> tuple[dict, dict, Path]:
    d = tasks_dir / name
    scenario = yaml.safe_load((d / "scenario.yaml").read_text())
    ground_truth = yaml.safe_load((d / "ground_truth.yaml").read_text())
    return scenario, ground_truth, d / "repo"


# which feedback channels each variant gets (SPEC §6.3 ablations). Extraction
# (the Stop hook's write path) always runs for non-bare variants — the board
# must exist for any channel to have content and for event scoring.
VARIANT_CHANNELS = {
    "scorekept": {"digest", "tier0", "stopblock"},  # full system
    "no-digest": {"tier0", "stopblock"},
    "no-tier0": {"digest", "stopblock"},
    "no-stopblock": {"digest", "tier0"},
    "silent": set(),  # board written, agent never sees it — placebo control
}


def make_hooks(workdir: Path, channels: set[str]) -> dict:
    """SDK hooks wired to the same handler functions the plugin uses."""

    async def digest_inject(input_data, tool_use_id, context):
        digest = Store(workdir).render_digest()
        if not digest:
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": digest,
            }
        }

    async def post_tool_use(input_data, tool_use_id, context):
        return hook_post_tool_use({**input_data, "cwd": str(workdir)}) or {}

    async def stop(input_data, tool_use_id, context):
        result = hook_stop({**input_data, "cwd": str(workdir)}) or {}
        return result if "stopblock" in channels else {}

    hooks = {"Stop": [HookMatcher(hooks=[stop])]}  # extraction always writes
    if "digest" in channels:
        hooks["UserPromptSubmit"] = [HookMatcher(hooks=[digest_inject])]
    if "tier0" in channels:
        hooks["PostToolUse"] = [HookMatcher(matcher="Edit|Write", hooks=[post_tool_use])]
    return hooks


def make_options(workdir: Path, variant: str, model: str | None) -> ClaudeAgentOptions:
    kwargs: dict = {
        "cwd": str(workdir),
        "permission_mode": "bypassPermissions",
        "allowed_tools": ["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
    }
    if model:
        kwargs["model"] = model
    if variant != "bare":
        kwargs["hooks"] = make_hooks(workdir, VARIANT_CHANNELS[variant])
    return ClaudeAgentOptions(**kwargs)


async def drive(scenario: dict, workdir: Path, variant: str, model: str | None) -> list[PhaseStats]:
    phases: list[PhaseStats] = []
    options = make_options(workdir, variant, model)
    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        for phase in scenario["phases"]:
            if "harness" in phase:
                if phase["harness"] == "force_compact":
                    # emulate compaction: fresh session, context gone (both variants)
                    await client.disconnect()
                    client = ClaudeSDKClient(options=make_options(workdir, variant, model))
                    await client.connect()
                continue
            stats = PhaseStats(prompt=phase["user"][:80], prompt_full=phase["user"])
            phase_started = time.time()
            await client.query(phase["user"])
            async for message in client.receive_response():
                mtype = type(message).__name__
                if mtype == "AssistantMessage":
                    for block in getattr(message, "content", []):
                        text = getattr(block, "text", None)
                        if text:
                            stats.reply_chars += len(text)
                            stats.reply_tail = text[-300:]
                            stats.reply_text += text + "\n"
                        name = getattr(block, "name", None)
                        if name and type(block).__name__ == "ToolUseBlock":
                            inp = getattr(block, "input", {}) or {}
                            detail = next(
                                (str(inp[k]) for k in ("file_path", "path", "command") if k in inp),
                                "",
                            )
                            stats.tools_used.append(f"{name}({detail[:80]})" if detail else name)
                elif mtype == "ResultMessage":
                    usage = getattr(message, "usage", None) or {}
                    stats.input_tokens += usage.get("input_tokens", 0) or 0
                    stats.output_tokens += usage.get("output_tokens", 0) or 0
            stats.wall_seconds = round(time.time() - phase_started, 1)
            phases.append(stats)
    finally:
        await client.disconnect()
    return phases


def collect_files(workdir: Path, cap_chars: int = 4000) -> str:
    chunks, used = [], 0
    for p in sorted(workdir.rglob("*")):
        if not p.is_file() or ".scorekeeper" in p.parts or p.suffix in (".pyc", ".sqlite"):
            continue
        try:
            text = p.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        chunk = f"===== {p.relative_to(workdir)} =====\n{text}\n"
        if used + len(chunk) > cap_chars:
            chunks.append(f"===== (truncated: {p.relative_to(workdir)} and beyond) =====")
            break
        chunks.append(chunk)
        used += len(chunk)
    return "\n".join(chunks)


def judge_run(scenario: dict, workdir: Path, phases: list[PhaseStats], judge_model: str) -> dict:
    del judge_model  # resolved from env inside the judge module (ADR-0005)
    try:
        return judge_trajectory(
            scenario_rubric=scenario["judge_rubric"],
            phases=[asdict(p) for p in phases],
            final_files=collect_files(workdir),
        )
    except Exception as e:  # noqa: BLE001
        return {"contradiction": None, "notes": f"judge failed: {e}"}


def score_events(ground_truth: dict, workdir: Path) -> dict:
    log_ops = [e["op"] for e in Store(workdir).log_entries()]
    fired = {op: log_ops.count(op) for op in set(log_ops)}
    expected_hits, misses, false_events = [], [], []
    for ev in ground_truth.get("expected_events", []):
        etype = ev["type"]
        if etype in ("NONE", "COMPACTION-SURVIVAL"):
            continue
        if ev.get("must_not_fire"):
            if etype in log_ops:
                false_events.append(etype)
        elif etype in log_ops:
            expected_hits.append(etype)
        elif not ev.get("conditional"):
            misses.append(etype)
    return {
        "fired": fired,
        "expected_hits": expected_hits,
        "misses": misses,
        "false_events": false_events,
    }


async def run_one(
    name: str, variant: str, model: str | None, judge_model: str,
    tasks_dir: Path = TASKS_DIR, seed_commitments: bool = False,
) -> RunResult:
    scenario, ground_truth, repo_seed = load_scenario(name, tasks_dir)
    result = RunResult(scenario=name, variant=variant)
    workdir = Path(tempfile.mkdtemp(prefix=f"skbench-{name}-{variant}-"))
    started = time.time()
    try:
        if repo_seed.exists():
            shutil.copytree(repo_seed, workdir, dirs_exist_ok=True)
        if variant != "bare":
            Store(workdir).init()
            if seed_commitments:
                n = seed_board(workdir, ground_truth)
                print(f"[{name} / {variant}] seeded {n} ground-truth commitment(s)")
        result.phases = await drive(scenario, workdir, variant, model)
        result.total_input_tokens = sum(p.input_tokens for p in result.phases)
        result.total_output_tokens = sum(p.output_tokens for p in result.phases)
        if result.total_output_tokens == 0:
            tail = result.phases[-1].reply_tail if result.phases else ""
            raise RuntimeError(f"agent produced no work (usage limit?): {tail!r}")
        result.judge = judge_run(scenario, workdir, result.phases, judge_model)
        if variant != "bare":
            result.events = score_events(ground_truth, workdir)
            result.scoreboard_log = Store(workdir).log_entries()
    except Exception as e:  # noqa: BLE001
        result.error = f"{type(e).__name__}: {e}"
    result.wall_seconds = round(time.time() - started, 1)
    print(
        f"[{name} / {variant}] contradiction={result.judge.get('contradiction')} "
        f"tokens_out={result.total_output_tokens} wall={result.wall_seconds}s "
        f"{'ERROR: ' + result.error if result.error else ''}",
        flush=True,
    )
    return result


def summarize(results: list[RunResult]) -> str:
    lines = [
        "# Phase-0 run summary",
        "",
        "| scenario | variant | contradiction | surfaced | events hit | false events | out-tokens | wall s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ev = r.events or {}
        lines.append(
            f"| {r.scenario} | {r.variant} | {r.judge.get('contradiction')} "
            f"| {r.judge.get('surfaced_conflict', '')} "
            f"| {','.join(ev.get('expected_hits', [])) or '—'} "
            f"| {','.join(ev.get('false_events', [])) or '—'} "
            f"| {r.total_output_tokens} | {r.wall_seconds} |"
        )
    bare = [r for r in results if r.variant == "bare" and r.judge.get("contradiction") is not None]
    kept = [
        r for r in results if r.variant == "scorekept" and r.judge.get("contradiction") is not None
    ]
    if bare:
        b = summarize_binary("SCR bare", sum(bool(r.judge["contradiction"]) for r in bare), len(bare))
        lines += ["", f"**SCR bare = {b['rate']:.0%}** (Wilson 95% {b['wilson_95']})"]
    if kept:
        k = summarize_binary(
            "SCR scorekept", sum(bool(r.judge["contradiction"]) for r in kept), len(kept)
        )
        lines += [f"**SCR scorekept = {k['rate']:.0%}** (Wilson 95% {k['wilson_95']})"]
    walls = [p.wall_seconds for r in results for p in r.phases if p.wall_seconds]
    if walls:
        lat = summarize_latency("phase wall seconds", walls)
        lines += ["", f"Phase latency s: P50 {lat['p50']} · P90 {lat['p90']} · P99 {lat['p99']} (n={lat['n']})"]
    dropped = [r for r in results if r.error]
    lines += ["", "## Drops manifest (Rollout Cards)", ""]
    if dropped:
        lines += [f"- {r.scenario}/{r.variant}: {r.error[:160]}" for r in dropped]
    else:
        lines += ["*(no runs dropped)*"]
    return "\n".join(lines) + "\n"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="single scenario dir name")
    parser.add_argument("--all", action="store_true", help="run every scenario")
    parser.add_argument(
        "--variant",
        choices=["bare", "scorekept", "both", *sorted(set(VARIANT_CHANNELS) - {"scorekept"})],
        default="both",
        help="'both' = bare+scorekept; others are SPEC §6.3 ablations",
    )
    parser.add_argument("--model", default=None, help="agent model override")
    parser.add_argument("--judge-model", default="models/gemini-2.5-flash")
    parser.add_argument(
        "--tasks-dir", default=str(TASKS_DIR),
        help="scenario root (e.g. ../commitbench/generated/dev)",
    )
    parser.add_argument(
        "--seed-commitments", action="store_true",
        help="pre-populate the board with ground-truth commitments (non-bare variants) "
             "— isolates steering from extraction reliability",
    )
    args = parser.parse_args()

    tasks_dir = Path(args.tasks_dir)
    names = (
        sorted(p.name for p in tasks_dir.iterdir() if p.is_dir())
        if args.all
        else [args.scenario]
    )
    if not names or names == [None]:
        parser.error("--scenario NAME or --all required")
    variants = ["bare", "scorekept"] if args.variant == "both" else [args.variant]

    stamp = time.strftime("%Y%m%dT%H%M%S")
    out = RESULTS_DIR / f"run-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    incremental = out / "results.jsonl"

    results = []
    for name in names:
        for variant in variants:
            r = await run_one(
                name, variant, args.model, args.judge_model, tasks_dir,
                seed_commitments=args.seed_commitments,
            )
            results.append(r)
            # crash-safe: persist each run the moment it finishes
            with incremental.open("a") as f:
                f.write(json.dumps(asdict(r)) + "\n")

    (out / "results.json").write_text(json.dumps([asdict(r) for r in results], indent=2))
    (out / "summary.md").write_text(summarize(results))
    print(f"\nresults -> {out}")
    print(summarize(results))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
