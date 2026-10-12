# Target architecture sketch (pipeline + static site)

**Audience:** Product Manager  
**Status:** Steps 1–4 are done. Step 4 (remove Streamlit) is done. Adam approved this cleanup. The score, the bands, the weights, `CORE_METRICS`, `compute_index`, and the live number were not changed. `schema_version` stays 1. `methodology_version` stays 1.1.1.  
**Written:** 2026-09-25. Steps 1–3 recorded 2026-10-07. Step 4 recorded 2026-10-12.  
**Shipped path:** pipeline → snapshot → validate → render → GitHub Pages. The contract is [`snapshot-schema.md`](snapshot-schema.md). The C4 diagrams in this folder show that path. The container diagram’s gray box is a local or Pi static preview of `docs/`, not a second publisher. [`ARCHITECTURE_AND_ROADMAP.md`](../../ARCHITECTURE_AND_ROADMAP.md) is the longer written review.

The BugOut Index stays a **directional stress and stability reading**. It places published statistics between fixed endpoints so a reader can see how hard those conditions are pressing. Higher is more stable. It is not a forecast and not a bug-out or historical-crisis siren. The publisher stamps methodology **1.1.1**. Weeks already published stay under the version that produced them. Step 4 did not change that version.

---

## Why this note exists

Adam asked to store a greenfield sketch while he thinks it over. He likes GitHub Pages and the automated weekly build and deploy. He wants a simpler architecture: a smaller surface to secure, to maintain, and to extend. He agrees the product is mostly a static site. He is inclined to change later. He will wait to see the Saturday morning weekly run first. There is no migration in the change that adds this note.

Simplicity is the goal. Fewer runtimes, fewer writers of the public site, and one contract between the pipeline and the pages.

---

## Core thesis

Keep GitHub Pages and the automated weekly build and deploy. The public product is the static site under `docs/`, rebuilt by a Python batch job and served as files.

The weekly site is written by the batch pipeline. A laptop or a Raspberry Pi runs that same pipeline and serves `docs/` with a static file server.

The shape is one pipeline:

```text
fetch → normalize → score → companions → validate → render → publish
```

Each stage reads and writes a typed, versioned snapshot. Static HTML and CSS are rendered at publish time from that snapshot. Charts stay data that the page already holds: inline SVG, as today, or a small script that only draws those numbers. The script does not fetch, score, or call an API.

A laptop or a Pi runs the same pipeline and serves `docs/`. It does not need a second product.

---

## Shape

```text
Public sources                 Pipeline                         Readers
─────────────────              ────────                         ───────
FRED / ALFRED  ──┐
gold-api.com  ───┼─► fetch → normalize → score → companions
annual checklist ┘         │
                           ▼
                       snapshot
                   (schema_version,
                    methodology_version)
                           │
                           ▼
              validate → render → publish
                           │
              ┌────────────┴─────────────┐
              ▼                          ▼
        GitHub Pages                local / Pi
        weekly Action               same pipeline,
                                    serves docs/
```

| Stage | What it owns | What it does not own |
| --- | --- | --- |
| Fetch | Raw values, observation dates, source identity, fetch status | The 0–100 score |
| Normalize | Map each core input onto 0–100 with the versioned endpoints, inversion, and clamp | Which series are companions |
| Score | The headline number and band from the six core inputs only | Markets, pulse, shadows, prose |
| Companions | Markets, pulse, revisions, and shadow series, attached beside the score | `compute_index` |
| Validate | The snapshot matches its schema, every required core input succeeded, and the publish output contains no secret | A second formula |
| Render | HTML and CSS (and, if needed, light chart JS) from the snapshot | Live fetches |
| Publish | Commit the snapshot, history rows, and rendered `docs/` on a green validate | A server process |

The weekly Action remains the publisher for the public site. GitHub Pages keeps serving `/docs` on `main`. The site is files. The number is computed in the batch job.

`schema_version` names the JSON shape. `methodology_version` names the formula. New publishes stamp `schema_version` 1 and `methodology_version` 1.1.1. `docs/data/latest.json` stays the last weekly publish. That contract is written down in [`snapshot-schema.md`](snapshot-schema.md) and checked by `runtime/publish/snapshot_schema.py`. Bump `schema_version` when the shape changes. Old files stay readable under the version they were written with. The schema freeze did not edit `latest.json`, and step 4 did not either.

---

## Fail policies

The policies are explicit. Exit 2 and exit 3 are unchanged. Exit 4 is the schema check from step 1: the job scrubs, validates, and refuses before it writes `docs/`. Shadow and revision carry-forward is unchanged. The same table is in [`snapshot-schema.md`](snapshot-schema.md).

| Failure | Policy |
| --- | --- |
| A core input fails, or fewer than six cores succeed | Refuse the publish before history is appended (exit 2). The live site stays the last good HTML. An RTCI download or national-rate failure is this row: crime is not carried forward. |
| Markets or the pulse return `status: error` | Refuse the publish (exit 3). The index is not written from a run that failed those blocks. |
| The pulse is partial (some series missing) | Log it. The site may still publish. The page says which series are missing. |
| Labor-utilization or food-price shadow fails | Do not refuse the publish. Carry forward the previous block and its observation dates when one exists. The score does not move because a shadow failed. |
| Revisions fetch fails | Copy the previous revisions block forward and mark it reused. Do not rewrite stored index history. |
| Snapshot fails validation (wrong shape, missing required core, secret material in the output) | Refuse the publish (exit 4). Do not write `docs/`. Do not commit partial HTML. |
| Render fails | Refuse the publish. Do not push a half-written `docs/`. |

A refused publish leaves last week’s site up. That is the safe outcome. The Actions run stays red so the miss is visible.

---

## Companions stay outside the score

Markets, the short-term pulse, payroll revisions, labor utilization, and food prices are fetched and shown. They do not enter the headline number. The same rule covers anything still incubating (including the AI Discontinuity Watch): no weight, unless a later methodology version says otherwise.

The score stage cannot import a companion. Validation fails a snapshot that folds a companion into `bugout_index`.

---

## Secrets

`FRED_API_KEY` stays a GitHub Actions secret, or an environment variable on a laptop or Pi. The value is never written into HTML, JSON, CSV, CSS, diagrams, or any other file the publish step commits.

Exception text that might contain a key is redacted before it can land in a published artifact or a committed log. Naming the secret in a diagram or a doc is fine. Drawing or pasting the value is not.

---

## CI

Two jobs, and no new runtime.

**Pull requests.** Tests, plus a dry-run publish: validate and render in the check, and leave `main` and committed `docs/` untouched. A dry run with no `FRED_API_KEY` uses fixtures or skips live fetches, and still checks the schema, the scoring fixtures, and the render. Scoring fixtures run on every pull request, so a formula change is caught before Friday.

**Weekly job.** This already landed on `main` ([#88](https://github.com/adammontville/bugoutindex/pull/88)) and this sketch keeps it:

- Hashed lockfile: `runtime/requirements.in` is the direct list; `runtime/requirements.txt` is the lock; install with `pip install --require-hashes`.
- Actions pinned to commit SHAs (digests), not floating tags.
- Concurrency group `bugoutindex-weekly-publish-<branch>` (`bugoutindex-weekly-publish-main` on the Pages branch). `cancel-in-progress` is false, so a run that has started is not killed mid-commit. A second run waits. Two runs do not push the same branch together.

The weekly schedule stays Friday 23:30 UTC. GitHub often starts that job Saturday morning UTC. `publication_date` stays the America/Chicago calendar date. This note does not edit the workflow.

---

## Local and Pi

A local or Pi run is the same command as the weekly job: fetch, score, validate, render into `docs/`, then serve that directory with a static file server. Preview is opening those files. There is no second history file and no `deployment` branch on the product path.

Publish with `python -m runtime.publish.weekly_run`. Preview with `python -m http.server 8765 --directory docs`. There is no Streamlit viewer. The weekly job does not import one.

---

## What not to do

These would make the surface larger. They are out of the sketch on purpose.

| Idea | Why it stays out |
| --- | --- |
| A React or other SPA homepage | The product is a page rebuilt once a week. A client app adds a build, a dependency tree, and a place for the number to be computed twice. |
| Scoring in the browser | The claim is that a reader can recompute the number from the published snapshot and the versioned formula. The browser is a display. |
| Streamlit as the weekly writer | The Action would depend on an app runtime to emit static files. That is the path this sketch leaves. |
| Microservices | One batch pipeline and one static site. Splitting fetch, score, and render into services adds network, auth, and deploy surface for a job that runs once a week. |

Language models stay off the score, the weights, the bands, and any watch level. A week note, if the pipeline writes one, is generated from the snapshot. That rule is already the product framing in `ARCHITECTURE_AND_ROADMAP.md`.

---

## Migration path

The formula, `CORE_METRICS`, and the live number stayed put through steps 1–4.

1. **Freeze the schema.** Done. The contract is [`snapshot-schema.md`](snapshot-schema.md). `schema_version` is still 1. That freeze left `methodology_version` at 1.0.0 and did not rewrite `docs/data/latest.json`. Later methodology versions (1.1.0, then 1.1.1) stay on schema 1. Step 4 did not change them.
2. **Move `weekly_run` off Streamlit.** Done. The weekly job does not import Streamlit. Fetchers read `FRED_API_KEY` from the environment (`runtime/util/secrets_compat.py`). When this step landed, the Action still installed a hashed lockfile that listed Streamlit, because the viewer was still in the tree. Step 4 removed that dependency.
3. **Demote Streamlit to an optional viewer.** Done. `runtime/main.py` read `docs/data/latest.json` and did not write the weekly site. A local or Pi box runs the same pipeline and serves `docs/`. The public site is still GitHub Pages. Step 4 removed that viewer.
4. **Remove Streamlit.** Done. Adam approved this step. The viewer (`runtime/main.py`, `runtime/pages/`, `runtime/presentation/`, `runtime/viewer_io.py`), the Streamlit-only essays and images under `runtime/static/`, and the `streamlit` dependency are gone. There is no `.streamlit/` config in the repo. The hashed lockfile no longer lists Streamlit. A local or Pi box still publishes with `python -m runtime.publish.weekly_run` and previews with `python -m http.server 8765 --directory docs`. The public site is still GitHub Pages. Scoring, `compute_index`, `schema_version`, and `methodology_version` (1.1.1) were not changed. `docs/data/latest.json` and history were not rewritten.

Stop here. The site is still the static weekly publish.

---

## What this work does not do

- It does not change the score formula, `compute_index`, `CORE_METRICS`, weights, bands, or the live number.
- It does not change `schema_version` (stays 1) or `methodology_version` (stays 1.1.1).
- It does not rewrite `docs/data/latest.json` or history.
- Step 4 removed Streamlit. It did not add a publisher.
- The C4 container diagram’s gray box is the local or Pi static preview. The validate step stays in the `weekly_run` box. The diagram does not draw a separate box for every shadow series.

The shipped path is the weekly Action, `weekly_run`, the formula module, fetchers, the schema 1 snapshot, validation, the static renderer, and GitHub Pages.
