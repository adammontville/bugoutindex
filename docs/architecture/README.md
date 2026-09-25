# BugOut Index architecture diagrams

These are the C4 Context and Container diagrams for BugOut Index.

| Diagram | File |
| --- | --- |
| Context | [c4-context.drawio](c4-context.drawio) |
| Container | [c4-container.drawio](c4-container.drawio) |

The Context diagram shows who uses the public site, the weekly software system, and the external sources it talks to (FRED / ALFRED, gold-api.com, AH-Datalytics RTCI, manual HUD and Edelman inputs, GitHub Actions and Pages). The Container diagram shows the weekly path inside that system: the GitHub Action, `weekly_run`, the v1.0.0 formula module, fetchers, committed data files, the static renderer, and the Pages site.

## How to open

- **diagrams.net / draw.io:** open [app.diagrams.net](https://app.diagrams.net) and use **Open Existing Diagram** on the `.drawio` file.
- **VS Code:** install the [Draw.io Integration](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) extension and open the `.drawio` file in the editor.

## Narrative companion

The written review of the same system is [ARCHITECTURE_AND_ROADMAP.md](../../ARCHITECTURE_AND_ROADMAP.md) at the repository root. These diagrams do not replace that document.

## Deferred sketch

[Target architecture sketch (pipeline + static site)](target-architecture-sketch.md) is a later-consideration note. It is not started. It does not change these diagrams, the score, or the weekly job.

## Notes

- No secrets are on the diagrams. `FRED_API_KEY` is named only as a GitHub Actions secret; the value is not drawn.
- An **UNKNOWN** label means that relationship was not invented. If the repository does not show an edge, it is not drawn as a fact.
- HUD homelessness and Edelman trust are annual checklist rows in `runtime/data/annual_inputs.csv`. The weekly job reads that table and does not invent a newer value or a fetch timestamp. See `runtime/data/ANNUAL_INPUTS.md`.
