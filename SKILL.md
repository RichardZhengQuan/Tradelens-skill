---
name: tradelensskill
description: "Use when Codex is asked to modify, review, debug, or plan work for TradeLensSkill: a local markdown-first trading analysis skill. This repository is not a native macOS app, has no SwiftUI UI, has no Xcode project, has no broker login, and must keep user trading data local in markdown files."
---

# TradeLensSkill

## Overview

TradeLensSkill is a local markdown-first trading analysis skill. It helps an AI agent extract, confirm, analyze, and journal trading context using local files such as `background.md`, `assets.md`, `trade.md`, `market_data.md`, and `analysis_history/`.

This checkout is not a native macOS app. It has no SwiftUI UI, no Xcode project, no broker login, no trading execution, no server sync, and no requirement to send user trading data to any server.

## Active Product

Treat `Trade Lens/` as the active skill bundle:

- `Trade Lens/SKILL.md`: skill trigger metadata and core workflow.
- `Trade Lens/AGENTS.md`: authoritative operating rules for agent workflows.
- `Trade Lens/background.md`: durable investor profile, constraints, preferences, and rules.
- `Trade Lens/assets.md`: local account and position snapshots.
- `Trade Lens/trade.md`: strategy-level trade journal.
- `Trade Lens/market_data.md`: local market snapshots and provider settings.
- `Trade Lens/analysis_rules.md`: analysis workflow and required report format.
- `Trade Lens/analysis_history/`: saved local markdown analyses.
- `Trade Lens/templates/`: markdown templates.
- `Trade Lens/src/tradelens/`: Python helpers for parsing, calculations, scoring, storage, and report writing.
- `Trade Lens/tests/`: unit tests for deterministic local behavior.

## Product Constraints

Follow these rules unless the user explicitly changes the product direction:

- Keep the product local-first and markdown-first.
- Do not add SwiftUI files.
- Do not add an Xcode project.
- Do not add broker login, broker automation, or trading execution.
- Do not add server sync, cloud storage, accounts, payments, or web backends.
- Do not send user trading data to any server.
- Store and read durable context through local markdown files.
- Preserve prior markdown records; prefer append-only history.
- Never invent market data, option-chain data, scenario probabilities, or profit/loss values.
- Keep deterministic calculations in `Trade Lens/src/tradelens/`.
- Keep analysis reports aligned with the evaluation-only template in `Trade Lens/AGENTS.md`, `Trade Lens/analysis_rules.md`, and `Trade Lens/templates/analysis.template.md`.
- TradeLensSkill evaluates trade quality, risk, term fit, and scenario profile. It must not tell the user to buy, sell, roll, close, hold, wait, reduce, or hedge.

## Working Pattern

For skill changes:

1. Read `Trade Lens/AGENTS.md` and the relevant source or markdown file.
2. Keep edits scoped to the local markdown skill.
3. Separate visible facts, user claims, AI inferences, assumptions, missing data, and trade judgment in generated analysis.
4. Add or update focused tests for changed deterministic behavior.
5. Run the local unittest suite from the skill bundle when possible:

```bash
python3 -m unittest discover -s tests
```

## Future Wrapper Boundary

A native wrapper could be considered in the future, but it is not the current product in this repository. Current work must keep TradeLensSkill usable as a local markdown-based skill without any native app, server, broker login, or cloud dependency.
