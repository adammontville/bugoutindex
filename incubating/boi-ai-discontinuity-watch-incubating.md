**Disclaimer**: This measure is part of the "Incubating" section of the BugOutIndex and is under development. Content is experimental, subject to change, and not finalized. Redistribution or use without explicit permission is prohibited.

# AI Discontinuity Watch (AIDW)

**Version**: 0.1.0 (incubating)
**Effective Date**: July 23, 2026

---

## Purpose

The **AI Discontinuity Watch (AIDW)** is an optional companion measure to the BugOut Index (BOI). It provides a transparent, periodically scored watch level that monitors accumulating evidence of an **AI-driven technological discontinuity** — a rapid, hard-to-reverse shift in what artificial intelligence systems can reliably do.

AIDW exists because the signals that would precede a genuine discontinuity (broadening capability, lengthening autonomous task horizons, AI accelerating its own research, economic substitution, and strategic/self-replication capability) are not the same signals that BOI tracks for observed societal stability. AIDW watches the *upstream* technological indicators; BOI measures *downstream* societal conditions.

## Scope

AIDW is scoped to **evidence of AI capability discontinuity**, not to AI's downstream social effects (those, when they materialize, flow into BOI's core metrics such as labor utilization, inflation, or trust). AIDW is deliberately global and technology-facing, because leading AI capability is developed by a small number of frontier labs whose results are observable through publications, evaluations, and independent benchmarks rather than through national statistics.

AIDW does **not** attempt to estimate a probability of AGI, a "years to AGI" figure, or a countdown. It reports a **watch level** with explicit confidence and evidence, and nothing more.

## Relationship to BOI (What AIDW Is and Is Not)

- **AIDW is NOT a core BOI metric.** It is not one of the weighted inputs described in [METRICS.md](../METRICS.md), and it has **no weight** in the composite.
- **AIDW does NOT change the BOI score.** The BOI number is computed exactly as documented in the core methodology, with or without AIDW. Publishing AIDW alongside BOI never alters, rescales, or reweights BOI.
- **BOI measures observed societal stability.** AIDW monitors evidence of an AI-driven technological discontinuity. They answer different questions and must be read separately.
- **The one-number BOI philosophy is preserved.** AIDW is reported as a distinct, clearly labeled watch level next to BOI, never merged into it. If AI-driven stress on society becomes observable, it is expected to appear in BOI *through the existing core metrics*, not through AIDW.

This document adds a non-core cross-reference under "Future Metrics in Development" so the measure is discoverable, consistent with how other incubating documents are listed. It changes no core weights and no existing metric files' methodology.

## Operational Distinctions

These three terms are frequently conflated in public discussion. AIDW treats them as **distinct, operationally defined conditions**, and does not assume any of them has a crisp, universally observable date.

- **AGI-like capability**: An AI system (or tightly integrated system-of-systems) that reliably performs at or above competent-human level across a **broad** range of economically and cognitively significant tasks, including tasks it was not specifically trained or scaffolded for, with autonomy over **long task horizons** and without task-specific human hand-holding. "AGI-like" is used deliberately: it denotes convergent evidence of broad, reliable, autonomous competence, not a certified philosophical threshold. This aligns conceptually with the graded framing in the DeepMind *Levels of AGI* work (see Sources).
- **Superintelligence**: Capability that **reliably and substantially exceeds** the best human experts across essentially all relevant cognitive domains, including scientific research, strategy, and self-improvement. Superintelligence is a strictly higher and more speculative bar than AGI-like capability and should be treated with correspondingly higher evidential demands.
- **Singularity**: A hypothesized **regime** — not a single event and not a date — in which AI-driven improvement (especially AI accelerating AI R&D) becomes fast and compounding enough that prediction of subsequent capability breaks down. AIDW treats "singularity" as a *characterization of a dynamic* (runaway, self-reinforcing acceleration), evidenced by sustained AI R&D acceleration, and explicitly avoids asserting it as a timestamped occurrence.

AIDW never claims any of these has "happened" on a specific day. It reports the **weight of convergent evidence** that the system is approaching or exhibiting one of these conditions.

## Five Evidence Dimensions

AIDW scores evidence across five independent dimensions. No single dimension can, by itself, move the watch level into the upper bands; **level transitions require convergence across multiple independent dimensions** (see the rubric).

1. **Capability generality** — Breadth of competent performance across diverse, unrelated task domains, including transfer to tasks and modalities not specifically trained for. Evidence: multi-domain evaluations, out-of-distribution transfer, reduced need for task-specific fine-tuning. Reference framing: DeepMind *Levels of AGI*; Stanford AI Index technical-performance chapter.
2. **Autonomous task horizon** — The length and complexity of real tasks an AI can complete autonomously and reliably (minutes → hours → days → multi-week projects) at a given success rate, without human intervention. Evidence: METR-style task-completion time-horizon measurements and their reliability thresholds (e.g., 50% vs 80% success).
3. **AI R&D acceleration** — The degree to which AI systems measurably speed up AI research and development itself (code, experiment design, model improvement, automated evaluation). This is the dimension most relevant to a "singularity"-type dynamic. Evidence: reproducible productivity gains in frontier R&D attributable to AI, automation of nontrivial research steps.
4. **Economic substitution / diffusion** — The extent to which deployed AI reliably substitutes for skilled human labor at scale in production settings, not just in demos. Evidence: durable task/occupation substitution, measurable diffusion across industries. When and if this dimension produces genuine societal stress, it is expected to register in BOI's **core** metrics (e.g., labor utilization), not in AIDW.
5. **Control, replication, and strategic capability** — Evidence bearing on autonomous self-replication, resource acquisition, deception or evaluation-gaming, resistance to shutdown/oversight, and strategically significant capabilities. Evidence: results from dangerous-capability and control evaluations by labs and independent evaluators. This dimension is weighted heavily in the two highest watch levels.

Each dimension is assessed independently and carries its own confidence label and evidence record.

## Watch-Level Rubric (0–5)

The watch level is an **ordinal** signal, not a score, probability, or countdown. Higher levels require **convergent** evidence across multiple dimensions from **multiple independent** sources — never a single benchmark result or a single company announcement.

| Level | Name | Convergence required |
|-------|------|----------------------|
| 0 | Routine Progress | Normal incremental improvement; no dimension elevated. |
| 1 | Rapid Advancement | Accelerating progress visible in ≥1 dimension, corroborated. |
| 2 | Strategic Concern | ≥2 dimensions elevated with independent corroboration. |
| 3 | Discontinuity Plausible | ≥3 dimensions elevated, including autonomous task horizon **or** AI R&D acceleration. |
| 4 | AGI-like Capability Evidenced | Broad, reliable, autonomous competence convergently evidenced across ≥4 dimensions by multiple independent evaluators. |
| 5 | Superintelligence Warning | Sustained, reproducible evidence of reliably super-human breadth **and** self-improving AI R&D acceleration, independently replicated. |

### Level 0 — Routine Progress
- **Observable criteria**: Benchmarks improve incrementally; new models are better but within the established trajectory; autonomous task horizons grow slowly; no credible evidence of AI meaningfully accelerating AI R&D; no dangerous-capability findings beyond prior baselines.
- **Evidence expectations**: Standard release notes, routine benchmark deltas, ordinary peer-reviewed and preprint publication cadence.
- **Monitoring implications**: Maintain the normal review cadence (e.g., monthly/quarterly). No change to BOI reporting. No escalation.

### Level 1 — Rapid Advancement
- **Observable criteria**: Clear acceleration in at least one dimension (e.g., a step-change in autonomous task horizon or in generality) that exceeds the recent trend and is corroborated beyond a single lab's own reporting.
- **Evidence expectations**: Independent benchmark confirmation; at least one non-vendor source; results that survive basic contamination/cherry-picking scrutiny.
- **Monitoring implications**: Increase review frequency for the affected dimension; begin tracking whether the acceleration is broad or narrow. Note in the AIDW change log.

### Level 2 — Strategic Concern
- **Observable criteria**: At least **two** independent dimensions are simultaneously elevated (e.g., generality **and** autonomous task horizon), each independently corroborated, suggesting the advance is not confined to a single narrow capability.
- **Evidence expectations**: Multiple independent evaluators; measured (not demoed) capability; explicit accounting of scaffolding, compute, and cost.
- **Monitoring implications**: Formal watch. Document evidence-for and counterevidence per dimension. Prepare (do not yet apply) an assessment of whether any downstream stress is appearing in BOI's core metrics.

### Level 3 — Discontinuity Plausible
- **Observable criteria**: At least **three** dimensions elevated, and the set **must include autonomous task horizon or AI R&D acceleration**, indicating a plausible move away from incremental progress.
- **Evidence expectations**: Reproducible results across independent labs/evaluators; deployed (not merely demonstrated) reliability on nontrivial task horizons; transparent methodology; freshness within the current review window.
- **Monitoring implications**: Elevated cadence and explicit uncertainty statement. Continue to report BOI separately and unchanged. Flag for governance review.

### Level 4 — AGI-like Capability Evidenced
- **Observable criteria**: Broad, reliable, **autonomous** competence across ≥4 dimensions — competent-human-level or better across many unrelated domains, sustained over long task horizons, with minimal task-specific human intervention — evidenced convergently.
- **Evidence expectations**: Independent replication by multiple credible evaluators; robustness to benchmark contamination and saturation; deployed reliability (not one-off demonstrations); documented human-intervention rates near zero on the claimed tasks.
- **Monitoring implications**: Highest routine escalation. AIDW states "AGI-like capability evidenced" with explicit confidence and full evidence dossier. **BOI remains a separate number and is unaffected.** Mandatory governance review and external sanity-check.

### Level 5 — Superintelligence Warning
- **Observable criteria**: Sustained, reproducible evidence of capability **reliably and substantially exceeding** the best human experts across essentially all cognitive domains, **and** self-reinforcing AI R&D acceleration (dimension 3) consistent with a singularity-type dynamic, plus material findings in control/replication/strategic capability (dimension 5).
- **Evidence expectations**: Independent replication of super-human breadth; reproducible, compounding AI-driven R&D speedups; rigorous, independently audited dangerous-capability and control evaluations. This is the **highest evidential bar** in AIDW and is intentionally hard to reach.
- **Monitoring implications**: Maximum escalation and immediate governance notification. AIDW explicitly states this is a *warning based on convergent evidence*, not a claim that a dated "singularity event" has occurred. BOI reporting continues separately.

## Confidence, Evidence, and Change-Log Requirements

Every AIDW publication **must** include, for the overall level and for each of the five dimensions:

- **Confidence label**: `low` / `medium` / `high`, reflecting evidence quality, independence, and replication — not the assessor's intuition.
- **Evidence-for**: The specific observations supporting the assessed level, with inline source links.
- **Counterevidence**: Observations that argue *against* the assessed level (contradicting results, failed replications, negative deployments). A publication with no counterevidence section is incomplete.
- **Uncertainty**: An explicit statement of what is unknown or contested, and what would change the level up or down.
- **Source freshness**: The date of each key source and whether it falls within the current review window; stale evidence must be flagged.
- **Change log**: What changed since the last publication (level, dimensions, sources, methodology), and why.

## Anti-Hype Safeguards

AIDW is designed to resist over-reaction. Assessors **must** apply the following before elevating a level:

- **Demonstration vs. deployment**: Distinguish a curated demo or leaderboard result from **reliable, repeated, deployed** capability under realistic conditions.
- **Benchmark contamination & saturation**: Discount benchmarks that may be in training data, and treat near-ceiling ("saturated") benchmarks as uninformative about the frontier.
- **Cherry-picking**: Prefer distributions and failure rates over best-case examples; require reported success thresholds (e.g., 50% vs 80%).
- **Scaffolding**: Separate the base model's capability from elaborate tool/agent scaffolding, retrieval, or prompt engineering; note what the scaffolding contributes.
- **Compute and cost**: Record the compute and dollar cost of a result; a capability that is only achievable at extreme cost is not the same as a deployable one.
- **Human intervention**: Require reported human-intervention/takeover rates for autonomy claims; "autonomous" means measured low intervention, not assumed.
- **Replication**: Require independent replication before upper-band elevation; a single result is not evidence of a discontinuity.
- **Independent evaluation**: Weight independent evaluators (e.g., third-party orgs and academic indices) above vendor self-reports.

## Suggested Source Classes and Primary Sources

**Source classes** (in rough order of evidentiary weight): independent third-party evaluators; peer-reviewed research; multi-lab reproductions; academic/industry indices; frontier-lab technical reports and system cards (treated as vendor claims requiring corroboration); reputable technical journalism (for leads, not as primary evidence).

**Primary / authoritative sources** used by AIDW where relevant:

- Google DeepMind — *Levels of AGI* (framework for graded, operationalized capability levels): <https://deepmind.google/research/publications/66938/>
- METR — *Task-completion time horizons* (measuring autonomous task horizon and reliability thresholds): <https://metr.org/time-horizons/>
- METR — *GPT-5.6 Sol evaluation* (worked example of independent autonomous-capability evaluation): <https://metr.org/blog/2026-06-26-gpt-5-6-sol/>
- Stanford HAI — *AI Index 2026, Technical Performance chapter* (independent, longitudinal capability and benchmark tracking): <https://hai.stanford.edu/assets/files/ai_index_report_2026_chapter_2_technical.pdf>

Additional sources should be added with their own freshness dates and independence notes as the watch evolves.

## Recommended Publication Block

AIDW must always be published **beside** BOI, with each number clearly attributed to its own measure so neither is mistaken for the other:

```
BugOut Index (BOI):   62.4   [core societal-stability score; methodology v1.0.0]
AI Discontinuity Watch (AIDW):
  Level:       2 — Strategic Concern
  Confidence:  medium
  Date:        2026-07-23
  Rationale:   Autonomous task horizon and capability generality are both
               elevated with independent corroboration, but no evidence of
               AI R&D acceleration or deployed substitution at scale.

Note: AIDW is a companion measure, not a BOI input. It does not change the BOI score.
```

The one-sentence rationale is mandatory and must be defensible from the evidence dossier.

## Governance and Versioning

- AIDW follows the project's explicit-versioning convention (see [METRICS.md](../METRICS.md)). This document is **v0.1.0 (incubating)**.
- Any change to the dimensions, rubric thresholds, or convergence rules is a **methodology version bump** recorded in the version history below and in the per-publication change log.
- AIDW levels are **never** back-dated silently; historical AIDW levels are recomputed only under an explicitly stated version.
- Promotion out of "incubating" (if ever) requires the backtesting described below and does **not** grant AIDW any weight in the core BOI composite.

## Backtesting / Retrospective Validation Proposal

Because AIDW cannot be validated against a future it is trying to watch, it should be validated **retrospectively** against past AI milestones. Proposed protocol:

1. **Select milestones** across the modern era (e.g., ImageNet/AlexNet 2012, AlphaGo 2016, transformer/large-LM scaling 2018–2020, instruction-tuned assistants 2022–2023, agentic/long-horizon systems 2024–2026).
2. **Reconstruct the evidence available at each date** (what was known then, not with hindsight), using contemporaneous sources.
3. **Blind-score** the five dimensions and assign the watch level using only that contemporaneous evidence.
4. **Check calibration**: Did AIDW avoid premature upper-band elevation on hyped-but-narrow results? Did it register genuine step-changes (e.g., long-horizon autonomy) without over-reacting to single benchmarks?
5. **Tune the convergence thresholds** so the rubric would have been neither chronically over-alarmed nor blind to real inflection points — explicitly optimizing for *false-alarm resistance* alongside sensitivity.
6. **Record** the backtest, its data vintage, and any threshold changes as a version bump.

The success criterion is **calibration and restraint**, not the ability to have "called AGI early." A validated AIDW is one that stays low during hype cycles and elevates only when independent, deployed, replicated evidence converges.

## Position Statement

AIDW gives BugOut Index users a disciplined way to watch AI capability without corrupting the core index. BOI stays a single, honest number about observed societal stability. AIDW stays a separate, evidence-bound watch level about technological discontinuity — with confidence, counterevidence, and anti-hype safeguards built in, and with no pretense of a probability, a countdown, or a date for AGI, superintelligence, or a singularity.

---

## Version History

| **Version** | **Date**       | **Changes**                                              |
|-------------|----------------|----------------------------------------------------------|
| 0.1.0       | July 23, 2026  | Initial incubating draft of the AI Discontinuity Watch.  |
