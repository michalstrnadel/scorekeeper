# API reference

The public surface of `scorekeeper`: the Python library, the `scorekeeper` CLI, and the
`scorekeeper-mcp` MCP server. Anything not listed here is internal and may change without notice.

Install: `pip install scorekeeper` (extras: `[anthropic]` for the Anthropic API backend, `[mcp]`
for the MCP server). Requires Python >= 3.11.

---

## Python API

Top-level exports (`from scorekeeper import ...`): `Commitment`, `Entitlement`,
`EntitlementSource`, `ExtractedCommitment`, `Kind`, `Status`, `Store`, `new_id`, plus
`__version__`. Everything else is imported from its submodule as shown below.

### Commitment model — `scorekeeper.model`

The deontic vocabulary as a schema: commitment → `Commitment` record, entitlement →
`Commitment.entitlement`, incompatibility → `Commitment.incompatible_with` plus detector verdicts.

#### Enums

```python
class Kind(StrEnum):               # what kind of commitment
    DECISION, ASSERTION, PROMISE, ASSUMPTION

class Status(StrEnum):             # lifecycle state (transitions only; nothing is deleted)
    ACTIVE, REFINED, SUPERSEDED, CONFLICTED, RETRACTED

class EntitlementSource(StrEnum):  # provenance of the reason behind a commitment
    USER_UTTERANCE, TOOL_OUTPUT, DOCUMENT, PRIOR_INFERENCE, NONE
```

#### `Entitlement`

```python
class Entitlement(BaseModel):
    source: EntitlementSource = EntitlementSource.NONE
    refs: list[str] = []
    note: str = ""

    @property
    def is_suspect(self) -> bool   # True when source == NONE (hallucination candidate)
```

A commitment with `source == "none"` is legal and significant: hallucination, in this vocabulary,
is a commitment without entitlement.

#### `Commitment`

```python
class Commitment(BaseModel):
    id: str                        # "c-YYYY-MM-DD-NNNN"
    ts: datetime
    session: str = ""
    claim: str
    kind: Kind
    scope: list[str] = []          # "topic:..." tags and "attr:key=value" hard attributes
    entitlement: Entitlement = Entitlement()
    consequences: list[str] = []
    incompatible_with: list[str] = []
    status: Status = Status.ACTIVE
    supersedes: str | None = None
    superseded_by: str | None = None

    @property
    def scope_attrs(self) -> dict[str, str]  # parsed "attr:key=value" entries — the Tier-0 surface
    @property
    def topics(self) -> set[str]             # "topic:..." tags — Tier-1 candidate selection
```

#### `new_id`

```python
def new_id(existing: list[str], now: datetime | None = None) -> str
```

Next id in the `c-YYYY-MM-DD-NNNN` series. The counter is global across days, not per-day.

### Store — `scorekeeper.store`

Transparent, git-committable storage under `<root>/.scorekeeper/`: one YAML file per commitment
(`commitments/<id>.yaml`), an append-only `log.jsonl` audit trail, and a generated
`scoreboard.md`. Nothing is ever deleted — statuses transition.

```python
class Store:
    def __init__(self, root: Path | str)

    # lifecycle
    def init(self) -> None                    # create the directory layout (idempotent)
    exists: bool                              # property; True once init() has run
    def write_lock(self, blocking: bool = True)   # context manager; flock serializing all
                                                  # writers (hooks, workers, MCP tools).
                                                  # blocking=False raises BlockingIOError
                                                  # when the lock is held

    # records
    def save(self, c: Commitment) -> None     # atomic write of commitments/<id>.yaml
    def load(self, cid: str) -> Commitment
    def all(self) -> list[Commitment]         # every record, sorted by id
    def active(self) -> list[Commitment]      # status ACTIVE or CONFLICTED (conflicts stay visible)
    def ids(self) -> list[str]

    # audit log
    def log(self, op: str, commitment_id: str = "", detail: str = "", **extra) -> None
    def log_entries(self) -> list[dict]

    # rendered views
    def render_scoreboard(self) -> str        # full scoreboard.md content
    def write_scoreboard(self) -> None
    def render_digest(self, max_lines: int = 50) -> str   # compact digest for context injection:
                                                          # conflicts first, then unbacked
                                                          # suspects, then active, newest first
```

### Operators — `scorekeeper.operators`

The seven operators (SPEC §4.3). `apply()` runs the first six; RETRACT is a status transition
exposed via the MCP `retract` tool (or a manual edit of the YAML record).

| Operator | Meaning |
|---|---|
| ASSERT | new commitment: validate, write, assign scope |
| SUPPORT | duplicate claim or attribute agreement — refs extended, no new record |
| REFINE | added specificity without replacement ("Postgres" → "Postgres 16") |
| SUPERSEDE | *entitled* revision — old record superseded, both chain directions kept |
| BRANCH-CONFLICT | incompatibility *without* entitlement to revise — both records `conflicted` |
| CHALLENGE | commitment with `source: none` — logged as a suspect |
| RETRACT | withdrawal; record kept (MCP tool, not part of `apply()`) |

SUPERSEDE vs BRANCH-CONFLICT is the project's core distinction: a revision is entitled when its
provenance is external to the agent — `user_utterance`, `tool_output`, or `document`
(`ENTITLED_TO_REVISE`). Revisions grounded only in `prior_inference` or nothing are drift.

```python
def apply(
    store: Store,
    extracted: list[ExtractedCommitment],
    backend: ModelBackend | None = None,   # enables Tier-1; Tier-0 always runs
    session: str = "",
    refs: list[str] | None = None,
) -> ApplyResult
```

Runs each extracted commitment through Tier 0 (and Tier 1 when a backend is given), writes the
outcome, and regenerates `scoreboard.md`. An entitled Tier-0 collision is confirmed with Tier 1
before superseding: a `refines` verdict refines, `compatible`/`needs_clarification` waives the
collision (logged as `COEXIST` — dev cache vs prod cache may coexist); without a backend the
deterministic supersede stands.

```python
@dataclass
class Conflict:
    new_id: str
    existing_id: str
    reason: str

@dataclass
class ApplyResult:
    asserted: list[str]
    supported: list[str]
    refined: list[tuple[str, str]]      # (old_id, new_id)
    superseded: list[tuple[str, str]]   # (old_id, new_id)
    conflicts: list[Conflict]
    challenges: list[str]               # ids of unbacked commitments

    @property
    def has_findings(self) -> bool      # True when conflicts or challenges exist
```

Usage:

```python
from scorekeeper import Store
from scorekeeper.extract import ExtractedCommitment
from scorekeeper.operators import apply

store = Store("/path/to/project")
result = apply(store, [ExtractedCommitment(
    claim="The primary database is PostgreSQL 16.",
    kind="decision",
    scope=["topic:persistence", "attr:persistence.primary_db=postgresql"],
    entitlement={"source": "user_utterance"},
)])
print(store.render_digest())
```

### Model backends — `scorekeeper.backends`

Backends are dumb: they take `(system, user)`, return the model's raw text. Schema validation and
retry-with-repair live in the callers (extractor, Tier-1 judge), not here.

#### The protocol

```python
@runtime_checkable
class ModelBackend(Protocol):
    name: str
    def complete(self, system: str, user: str) -> str   # one isolated completion
```

Any object with a `name` attribute and that method is a valid backend — pass it to `apply()`,
`extract_commitments()`, or `tier1.judge()` directly:

```python
class MyBackend:
    name = "my_backend"
    def complete(self, system: str, user: str) -> str:
        return call_my_model(system, user)

result = apply(store, extracted, backend=MyBackend())
```

Raise `BackendError` from `complete()` when the call itself fails; the callers fail open.

#### Shipped backends

```python
AnthropicBackend(model="claude-haiku-4-5-20251001", api_key=None,
                 max_tokens=2048, timeout=60.0)          # needs the [anthropic] extra

OpenAICompatBackend(base_url, model="qwen3:8b", api_key="",
                    timeout=120.0, temperature=0.0,      # Ollama / LM Studio / vLLM;
                    budget=180.0)                        # stdlib-only; retries transient errors
                                                         # but never past `budget` seconds total
                                                         # per complete() (hook deadlines)

ClaudeCLIBackend(model="haiku", timeout=120.0)           # headless `claude -p`; slowest, last in
                                                         # auto-detect order; system prompt goes
                                                         # via --append-system-prompt
ClaudeCLIBackend.available() -> bool                     # is `claude` on PATH?
```

#### Auto-detection

```python
def detect_backend(root: Path | str | None = None, env: dict | None = None) -> ModelBackend
```

Order (env overrides config — the same rule as the gate and extract settings):
`SCOREKEEPER_MODEL_URL` (OpenAI-compat; config fills `model`/`api_key` gaps it doesn't set) →
explicit config in `<root>/.scorekeeper/config.yaml` (`backend: {kind, url, model, api_key}`,
kind one of `openai_compat | anthropic_api | claude_cli`) → passive auto-detect:
`ANTHROPIC_API_KEY` (Haiku) → `claude` CLI on PATH. Raises `BackendError` when nothing is
available; a malformed `config.yaml` degrades to auto-detect.

#### Errors and JSON helpers

```python
class BackendError(RuntimeError)         # the backend call itself failed
class JSONParseError(ValueError)         # model replied, but no JSON object recovered (.raw kept)

def parse_json_object(text: str) -> dict                             # tolerates fences and prose
def complete_json(backend: ModelBackend, system: str, user: str) -> dict
```

### Extraction — `scorekeeper.extract`

Isolated, context-poor scorer call: the extractor sees the turn text and the current digest —
never the agent's private reasoning. Write-path validation: nothing enters the store unless it
passes the schema.

```python
class ExtractedCommitment(BaseModel):    # the only door into the store; lives in
                                         # scorekeeper.model (re-exported here and top-level)
    claim: str                           # 10–500 chars
    kind: Kind
    scope: list[str] = []                # max 6; each entry must start with "topic:" or
                                         # "attr:" (attr entries must be key=value)
    entitlement: Entitlement = Entitlement()
    consequences: list[str] = []         # max 5

def build_turn_text(user: str, assistant: str, tools_used: list[str] | None = None) -> str

def extract_commitments(
    backend: ModelBackend,
    turn_text: str,
    digest: str = "",                    # current scoreboard digest, for context
    on_error=None,                       # callable(Exception) — called on final failure
) -> list[ExtractedCommitment]           # one call + one repair retry; [] on failure

def suspect_note(c: ExtractedCommitment) -> str | None   # CHALLENGE line for unbacked, else None
```

### Detection — `scorekeeper.detect`

#### Tier 0 — `scorekeeper.detect.tier0`

Deterministic scope-attribute collisions. No LLM, ~ms. Same key + different value = collision;
same key + same value = agreement (SUPPORT candidate).

```python
@dataclass
class Collision:  key: str; new_value: str; existing: Commitment; existing_value: str
@dataclass
class Agreement:  key: str; value: str; existing: Commitment

def check(new_attrs: dict[str, str], active: list[Commitment]
          ) -> tuple[list[Collision], list[Agreement]]
```

#### Tier-0 content scan — `scorekeeper.detect.tier0_content`

Instant rival-technology warnings on written/edited text, against a small high-precision lexicon
of mutually exclusive technology families (`FAMILIES`).

```python
@dataclass
class ContentWarning:  commitment_id: str; key: str; pinned_value: str; rival_found: str

def scan(content: str, active: list[Commitment],
         exhaustive: bool = False) -> list[ContentWarning]
    # default: one warning per commitment attr; exhaustive=True reports every rival (gate needs it)

def novel(warnings: list[ContentWarning], baseline: str,
          active: list[Commitment]) -> list[ContentWarning]
    # drop pairs already present in baseline (an Edit's old_string) — an edit that removes
    # a rival must not warn

def format_warnings(warnings: list[ContentWarning]) -> str
```

#### Tier-0 blocking gate — `scorekeeper.detect.tier0_gate`

Turns the content scan into a PreToolUse deny (ADR-0007). Two modes:

```python
@dataclass
class GateDecision:  reason: str; warnings: list[ContentWarning]

def evaluate_wall(content: str, active: list[Commitment],
                  baseline: str = "") -> GateDecision | None
    # mode "block" (v2, recommended): the deny stands while the pinned commitment is ACTIVE —
    # only the board recording an entitled SUPERSEDE lifts it. Stateless.

def evaluate(content: str, active: list[Commitment], state_path: Path,
             baseline: str = "") -> GateDecision | None
    # mode "bump" (v1, kept as an ablation): deny once per (commitment, rival) pair; an
    # instructed retry passes within REARM_SECONDS (15 min). State in .scorekeeper/tier0-gate.json.
```

Both return `None` to allow. `baseline` is the edit's `old_string`: rivals already present there
are not new conflicts.

#### Scope wall — also in `scorekeeper.detect.tier0_gate` (ADR-0008)

The actions-axis twin: denies writes whose *target* falls outside the union of
`path:<glob>` pins on active commitments with **external** entitlement
(user_utterance / tool_output / document) — a self-asserted pin cannot widen
the agent's own scope. Stateless; inert when no entitled pins exist.

```python
@dataclass
class ScopePin:      commitment_id: str; pattern: str

@dataclass
class ScopeDecision: reason: str; target: str; pins: list[ScopePin]

def collect_scope_pins(active: list[Commitment]) -> list[ScopePin]
    # entitled path: pins only, deterministic order

def normalize_target(file_path: str, root: Path) -> str | None
    # realpath (symlink evasion) -> root-relative posix, casefolded; None = escapes root

def path_in_scope(rel: str, patterns: list[str]) -> bool
    # fnmatch + explicit "dir/**" / "dir/" subtree rule; malformed pins skipped

def evaluate_scope(file_path: str, active: list[Commitment],
                   root: Path) -> ScopeDecision | None
    # None = allow (in scope, or no entitled pins active)

def format_scope_warning(target: str, pins: list[ScopePin]) -> str
    # advisory PostToolUse twin (TIER0-SCOPE-WARNING)
```

#### Tier 1 — `scorekeeper.detect.tier1`

Material incompatibility judged by an isolated, context-poor LLM call. Precision beats recall:
when unsure, the prompt says compatible.

```python
class Verdict(StrEnum):
    COMPATIBLE, INCOMPATIBLE, REFINES, NEEDS_CLARIFICATION

class CandidateVerdict(BaseModel):
    id: str            # existing commitment id
    verdict: Verdict
    rationale: str = ""

def select_candidates(new_topics: set[str], active: list[Commitment],
                      limit: int = 12) -> list[Commitment]
    # scope-based selection — never ship the whole scoreboard to the model

def judge(backend: ModelBackend, new_claim: str, candidates: list[Commitment],
          on_error=None) -> list[CandidateVerdict]
    # one isolated call over all candidates; fails open ([]) — never crashes
```

`CandidateVerdict` and `Verdict` are re-exported from `scorekeeper.detect`.

### Transcript reader — `scorekeeper.transcript`

Tolerant Claude Code transcript (JSONL) reader used by the Stop hook.

```python
@dataclass
class Turn:
    user_text: str = ""
    assistant_text: str = ""
    tools_used: list[str] = []
    empty: bool                      # property; no user or assistant text

def read_last_turn(path: Path | str) -> Turn
```

---

## CLI

Entry point: `scorekeeper` (installed by the package). Subcommands:

### `scorekeeper init [--root DIR]`

Create `.scorekeeper/` under the project root (default: cwd) and write an empty scoreboard.

### `scorekeeper digest [--root DIR]`

Print the compact normative digest (`Store.render_digest()`); empty output when the scoreboard
is empty.

### `scorekeeper report [--root DIR]`

Print the full human-readable scoreboard (`Store.render_scoreboard()`).

### `scorekeeper board [--root DIR] [--events N] [--no-color]`

Colored terminal dashboard: header counts (active / challenged / conflicted / denies today),
active commitments with scope pins and provenance glyphs (★ external / ⚠ unentitled), recent
events colored by op class. Color auto-disables on non-tty or `NO_COLOR`.

### `scorekeeper worker PAYLOAD_FILE`

Internal: the detached async-extraction worker spawned by the stop hook (ADR-0006). Reads a saved
hook payload, extracts under the store's write lock, appends findings to
`.scorekeeper/pending-findings.md`, and deletes the payload file. Not for direct use.

### `scorekeeper hook EVENT`

Claude Code hook handler. Contract: the hook payload arrives as **JSON on stdin**; a decision
object is printed as **JSON on stdout** (nothing when there is nothing to say); the process
**always exits 0** — a broken scorer must never break the agent (errors go to stderr and the
audit log). The project root is taken from the payload's `cwd`, falling back to the process cwd.

Events (payload fields used → output):

| Event | Behavior |
|---|---|
| `session-start` | Renders the digest. Output: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <digest>}}`, or nothing when empty. |
| `pre-tool-use` | **Scope wall first (ADR-0008):** when the gate is enabled and entitled `path:` pins are active, a `file_path`/`notebook_path` outside their union is denied (`TIER0-SCOPE-DENY`) — runs before the doc exemption (a drive-by `.md` edit outside scope is still barging) and before the empty-content bail. Kill switch: `scope_gate: off` / `SCOREKEEPER_SCOPE_GATE=off`; `=block` force-enables the scope wall alone. **Then the claims gate (ADR-0007)**, opt-in via `SCOREKEEPER_TIER0_GATE=block\|bump` or `tier0_gate:` in config: scans `tool_input.content` / `new_string` / `new_source` (baseline: `old_string`); files ending in `.md`/`.rst`/`.txt` are exempt from the claims gate only. On conflict: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": ...}}` and a `TIER0-GATE-DENY` audit entry. |
| `post-tool-use` | Advisory channel. For `Bash`, rival mentions in the command are logged (`TIER0-SHELL-AUDIT`), no output. For edits: a landed write outside the entitled scope logs `TIER0-SCOPE-WARNING` (fires regardless of gate mode — the audit floor under the wall), and novel rival warnings are logged (`TIER0-CONTENT-WARNING`); both are returned via `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ...}}`. |
| `stop` | Turn-end extraction. Reads the last turn from `transcript_path`, extracts commitments, runs `apply()`. Mode `sync` (default): findings block the turn — `{"decision": "block", "reason": <findings>}`. Mode `async` (`SCOREKEEPER_EXTRACT=async` or `extract:` in config): spawns a detached worker and returns immediately. No-op when `stop_hook_active` is set (never loop). |
| `user-prompt-submit` | Drains `.scorekeeper/pending-findings.md` (written by async workers) into `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ...}}`. Skips (non-blocking lock) while a worker is mid-extraction. |
| `pre-compact` | Backs up the scoreboard to `.scorekeeper/backups/scoreboard-<stamp>.md`. No output. |

---

## MCP server

`scorekeeper-mcp` — stdio transport, requires the `[mcp]` extra. Project root:
`$SCOREKEEPER_ROOT` or cwd. `assert_commitment` routes through the same validated operator
pipeline as the hooks, so an agent given these tools still cannot silently rewrite its own
board; `supersede`/`retract` are explicit, entitlement-gated status transitions (see
`mcp/README.md` for the design constraint).

Write results share one summary shape (mirrors `ApplyResult`):

```json
{"root": "/abs/project/root",
 "asserted": [...], "supported": [...], "refined": [["old", "new"], ...],
 "superseded": [["old", "new"], ...],
 "conflicts": [{"new": "...", "existing": "...", "reason": "..."}], "challenges": [...]}
```

Every write tool reports the `root` it acted on: hooks resolve the store from the session's
cwd but this server resolves it from `$SCOREKEEPER_ROOT` (or its own cwd) — if the two diverge,
`supersede` writes a board the Tier-0 wall never reads and the wall never lifts. Set
`$SCOREKEEPER_ROOT` explicitly when launching the server.

### `get_scoreboard() -> str`

Full human-readable scoreboard (active + superseded/retracted history).

### `get_digest() -> str`

Compact normative digest (< 50 lines); `"(scoreboard is empty)"` when there is nothing.

### `assert_commitment(claim, kind="decision", scope=None, source="user_utterance", note="", consequences=None) -> dict`

Record a commitment through the full operator pipeline. `kind`:
`decision|assertion|promise|assumption`. `scope`: `topic:...` tags and `attr:key=value` hard
attributes. `source`: `user_utterance|tool_output|document|prior_inference|none`. Returns the
result summary above. Tier 1 runs only when a backend is configured; Tier 0 always runs.

### `check_compatibility(claim, scope=None) -> dict`

Dry run — nothing is written. Returns:

```json
{"tier0_collisions": [{"key", "existing", "existing_value", "new_value"}],
 "tier0_agreements": [{"key", "value", "existing"}],
 "tier1_verdicts":  [{"id", "verdict", "rationale"}]}
```

With no backend configured, `tier1_verdicts` is empty and a `note` field says so.

### `supersede(old_id, claim, source="user_utterance", note="", scope=None) -> dict`

Explicitly replace a commitment with an entitled revision. `source` must be external to the
agent (`user_utterance|tool_output|document`) — anything else raises `ValueError` (an unentitled
replacement is drift; use `assert_commitment` and let the operators flag it). The new record
inherits the old one's kind. `scope` tags the **new** claim; when omitted, `topic:`/`repo:` tags
carry over but the old `attr:key=value` pins are dropped — they encode the replaced claim's
content, and carrying them over would leave Tier-0 enforcing the old choice against the new one.
Pass explicit `attr:` pins to keep the new choice gate-protected. Both directions of the chain
are kept. Returns `{"superseded": old_id, "by": new_id}`.

### `challenge(commitment_id, reason="") -> dict`

Demand the reason behind a commitment. The commitment stays active; a `CHALLENGE` entry is
logged. Returns `{"challenged", "claim", "entitlement", "suspect"}`.

### `retract(commitment_id, reason="") -> dict`

Retract a commitment — a status transition, the record is kept. Returns `{"retracted": id}`.

---

## Environment variables

| Variable | Used by | Meaning |
|---|---|---|
| `SCOREKEEPER_MODEL_URL` | backend selection | Base URL of an OpenAI-compatible endpoint (Ollama, LM Studio, vLLM — `<url>/chat/completions`). Wins over config `backend.kind` (env overrides config). |
| `SCOREKEEPER_MODEL` | backend auto-detect | Model name for the OpenAI-compat backend (default `qwen3:8b`). |
| `SCOREKEEPER_MODEL_API_KEY` | backend auto-detect | Bearer token for the OpenAI-compat endpoint (optional). |
| `ANTHROPIC_API_KEY` | backend auto-detect | Enables the Anthropic API backend (Haiku-class default) when no local URL is set. |
| `SCOREKEEPER_TIER0_GATE` | `hook pre-tool-use` | `block` (board-adjudicated wall, recommended) \| `bump` (one-shot deny, ablation) \| `warn` (force-disable the gate, advisory only). Overrides `tier0_gate:` in config in both directions. Unset: config decides; default off. |
| `SCOREKEEPER_SCOPE_GATE` | `hook pre-tool-use` | `off` (disable just the scope wall — claims-only ablation/emergency) \| `block` (force-enable the scope wall even with the claims gate off). Unset: the scope wall rides `tier0_gate` (active whenever the gate is enabled). Overrides `scope_gate:` in config. |
| `SCOREKEEPER_EXTRACT` | `hook stop` | `sync` (findings block the turn; library default) \| `async` (detached worker, findings on the next prompt). Overrides `extract:` in config. |
| `SCOREKEEPER_EXTRACT_DEFAULT` | `hook stop` | Surface default consulted only when neither `SCOREKEEPER_EXTRACT` nor config `extract:` decides — the plugin's hooks.json sets it to `async` without shadowing the config key. |
| `SCOREKEEPER_ROOT` | `scorekeeper-mcp` | Project root for the MCP server (default: cwd). |

`.scorekeeper/config.yaml` (all keys optional) is the file-based counterpart:

```yaml
backend:
  kind: openai_compat        # openai_compat | anthropic_api | claude_cli
  url: http://localhost:11434/v1
  model: qwen3:8b
  api_key: ""
tier0_gate: block            # block | bump (absent = gate off)
scope_gate: block            # off | block (absent = rides tier0_gate; ADR-0008)
extract: async               # sync | async
```
