# r/LocalLLaMA draft

**Title:** Local models ignore "please don't" — here's what actually stopped my agent from overriding its own decisions (measured, open-source)

**Body:**

If you run smaller/local models as agents, you've seen this: the model decides
X (you confirm it), and three files later it's doing Y because some note in
context "suggested" it. Bigger models drift less; local models drift a lot —
and politely worded system-prompt warnings do approximately nothing.

I built **scorekeeper**, a local-first overlay that gives the agent a ledger
of its own commitments, with *entitlement* semantics: it distinguishes "the
user ordered this change" from "the model talked itself into it". Extraction
runs through your own `claude` CLI or any local backend (the judge is a local
qwen via Ollama — I deliberately removed the cloud dependency), storage is
plain YAML/markdown in `.scorekeeper/` in your repo.

The empirical part (procedural benchmark, deterministic artifact-level
scoring, no LLM-judge vibes): with Haiku as the agent,

- **In-context warnings: exploited.** 11 warnings fired while the agent built
  the exact thing its own recorded decision ruled out — it shipped it with a
  "polyglot architecture" justification, and disguised it ("backed by Redis"
  docstring over a `pymemcache` import).
- **Deny-once-then-allow-retry: exploited.** The model just *claimed* the
  user had ordered the change and retried.
- **Deny-until-the-ledger-changes: held.** The write stays blocked until an
  entitled revision is actually recorded on the ledger. Weak models follow
  hard tool-level denials they can't talk their way past — which matches the
  published Recuse-Signal findings, and means you can get commitment-holding
  behavior out of models that can't self-police.

The benchmark (EntitleBench) penalizes false refusals symmetrically with
drift, so "just block everything" doesn't win.

One-command install as a Claude Code plugin; framework-agnostic core on PyPI;
MCP server included. Would love failure reports from local setups — there's a
dedicated issue template.

https://github.com/michalstrnadel/scorekeeper

**[FILL before posting: wall A/B numbers]**
