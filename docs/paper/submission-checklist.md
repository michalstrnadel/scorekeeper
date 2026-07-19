# Pre-submission checklist (E&D standards, NeurIPS/ICLR/ICML 2026)

> Distilled 2026-07-19 from the evaluation-methodology deep-research report
> (venue guidelines summarized there; single-source items marked
> **[1 source]**). Work through this BEFORE any submission — several items are
> desk-reject triggers, not score deductions.

## Desk-reject triggers

- [ ] **Double-blind repo**: code + logs linked via Anonymous GitHub (or
  equivalent), no personal GitHub links, author identity scrubbed from
  dataset metadata and commit trails in the anonymized bundle.
- [ ] **Executable code included**: "no code = reject" for E&D tracks. The
  deterministic oracle must be runnable without paid API keys — our
  classifier (tree diff + marker banks) and generator qualify; verify the
  repro path works from a clean clone (`scripts/e2e.sh` + generator seeds).
- [ ] **ICLR reviewer nomination** (if ICLR): nominate a qualified author as
  reviewer; their non-performance desk-rejects the paper **[1 source]**.

## Mandatory checks

- [ ] **Croissant metadata** for any released dataset split + RAI declaration
  (biases of the detection mechanisms, intended use, measurement limits, no
  PII — scenarios already use synthetic placeholders).
- [ ] **Pinning**: exact model tags + API execution dates (not just the model
  family), agent-library versions, all generator/prompt seeds, and the exact
  detection regexes (marker banks are versioned in-repo — cite the commit).
- [ ] **Cluster-aware uncertainty**: no IID bootstrap over runs — CIs via
  cluster bootstrap resampling whole scenarios; GEE (exchangeable working
  correlation, sandwich variance) or scenario-level permutation tests for
  the ablation p-values. Fixed allocation only — adaptive sampling
  invalidates the frequentist inference (SNARE uses Thompson sampling for
  elicitation, never for A/B inference).
- [ ] **ICC pilot before the full run**: ~10 scenarios to estimate the
  intraclass correlation (budget math assumes ICC≈0.3; the empirical value
  for overreach behavior on identical seeds is unmeasured in the literature).
- [ ] **LLM-assistance disclosure + ethics**: declare tools used in
  composing the work; dual-use discussion (the benchmark elicits overreach);
  full author responsibility for any generated text.

## Reporting form (from the metrics report)

- [ ] Report ORR/URR as marginal rates AND the paired view (the isogenic
  sibling pairs license it); optionally an AgentAbstain-style paired
  accuracy as a secondary composite — never as the primary (it hides the
  failure direction).
- [ ] Report the UnderSpecBench-style *acted-runs* conditional rate as a
  secondary denominator view.
- [ ] First-use terminology disambiguation for ORR/SCR/FRR (QUESTIONS Q12;
  related-work.md terminology guard).
- [ ] Cost/compute reporting: not formally mandated, but report API spend
  and run counts as best practice.
