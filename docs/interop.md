# Interoperability: mapping the scorekeeper model onto existing standards

> Addendum-1 §B.1. The commitment model has precise counterparts in two mature
> standards — we map onto them instead of inventing an ontology. This document is
> the P1 deliverable; the exporters (`scorekeeper export --format xaif|prov-json`)
> land in Phase 1–2.

## 1. xAIF (Argument Interchange Format, JSON serialization)

The scoreboard is an argumentation structure; xAIF makes it exchangeable with the
argumentation-mining ecosystem (OVA visualizes xAIF graphs out of the box; oAMF
pipelines consume it) — an immediate academic bridge for the paper.

| scorekeeper | xAIF | Note |
|---|---|---|
| transcript utterance (`entitlement.refs` → `transcript:...`) | **L-node** (locution) | the speech act as uttered |
| `Commitment.claim` | **I-node** (information) | the propositional content |
| the extraction act ("the agent hereby asserts") | **YA-node** (Asserting) | anchors L → I |
| `incompatible_with` (BRANCH-CONFLICT edge) | **CA-node** (conflict application) | conflict between two live I-nodes, never overwrite |
| `consequences` | **RA-node** (inference application) | claim → its inferential consequences |
| SUPERSEDE chain | RA/MA pattern + metadata | see also dcterms mapping below |

Export sketch: one xAIF `nodes`/`edges` document per scoreboard; node IDs reuse
commitment IDs (`c-YYYY-MM-DD-NNNN`).

## 2. W3C PROV-O / PROV-JSON

Entitlement **is** provenance — the mapping is nearly verbatim:

| scorekeeper | PROV-O | Note |
|---|---|---|
| `Commitment` (the claim) | `prov:Entity` | |
| the agent turn / extraction run | `prov:Activity` | one Activity per Stop-hook pass |
| agent / user / tool | `prov:Agent` (Software/Person) | |
| `entitlement.refs` | `prov:wasDerivedFrom` + `prov:used` | refs point at source entities (files, messages) |
| authorship of a claim | `prov:wasAttributedTo` | |
| `supersedes` / `superseded_by` | `dcterms:replaces` / `dcterms:isReplacedBy` | bidirectional chain preserved |
| `entitlement.source == none` | Entity with **no** `wasDerivedFrom` | the hallucination-suspect pattern is a *visible hole* in the provenance graph |

Export sketch: PROV-JSON document per scoreboard; `log.jsonl` supplies Activity
timestamps (`prov:startedAtTime`).

## 3. OpenTelemetry (P2)

Optional span-event emitter so Langfuse / LangSmith / AgentOps users see
scorekeeper events inside their existing traces (we do not build observability):

- `commitment.asserted` {id, kind, entitlement_source}
- `commitment.superseded` {old, new}
- `conflict.detected` {ids, tier, reason}
- `challenge.raised` {id}

## Positioning (vs. observability tooling)

LangSmith, Langfuse, AgentOps, Braintrust are flight recorders of *execution*
(spans, latency, tokens). None of them versions the agent's *epistemic* state —
the evolution of its claims and decisions over time. LangGraph Time Travel comes
closest but versions the technical graph state, not normative structure.

**Observability tools record what the agent did; scorekeeper records what the
agent is committed to.**
