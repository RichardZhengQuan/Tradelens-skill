---
name: trade-lens
description: Local-first trade evaluation skill for AI agents. Use when the user wants to parse, evaluate, confirm, journal, or review proposed stock/options trades with term-aware trade quality, risk, scenario profile, missing-data disclosure, local markdown memory, and optional read-only market data providers. TradeLensSkill is not a trade coach and must not give broker execution advice.
---

# TradeLensSkill

TradeLensSkill is a local-first trade evaluation skill for AI agents.

It remains a local markdown-first trading analysis skill: persistent user memory lives in local markdown files.

It answers: "How good is this trade for each time horizon?"

It does not answer: "What order should I place?"

TradeLensSkill is not a native macOS app. It has no broker execution, no broker login, no cloud sync, no database, no native app requirement, no SwiftUI UI, and no Xcode project.

## When To Use

- Evaluate a proposed stock, ETF, or options trade.
- Compare intraday, short-term, medium-term, and long-term trade quality.
- Parse trade/order text or screenshots.
- Update confirmed `background.md`, `assets.md`, or `trade.md`.
- Save and inspect `analysis_history/`.
- Configure or test optional read-only data providers.
- For asset checks, try configured read-only account/positions APIs first, save successful non-secret snapshots to `assets.md`, and use local `assets.md` only as fallback.
- For every trade check/evaluation, load `assets.md`, relevant `trade.md` history, and `market_data.md` provider/snapshot context before judging the trade.

## Canonical Agent Workflows

These slash-style entries are agent workflows. They are not shell CLI commands unless `src/tradelens/cli.py` explicitly implements a helper.

- `/tradelens trade`
- `/tradelens assets`
- `/tradelens background`
- `/tradelens history`
- `/tradelens analysis ratio`
- `/tradelens provider setup`
- `/tradelens provider test`

## Absolute Safety Rules

- Never give action advice or broker execution advice.
- Never tell the user to buy, sell, hold, roll, close, wait, reduce, or hedge.
- Always use the allowed judgment labels from `docs/report_contract.md`.
- Always include Term-Aware Trade Judgment near the top of analysis reports.
- Never fake market data, account data, option data, news, volatility, sentiment, scenario probabilities, or profit/loss values.
- Never ask for broker passwords, trading passwords, 2FA codes, SMS codes, recovery codes, or API secrets.
- Never store secrets in markdown or `analysis_history/`.
- Proposed trades may save an analysis record, but must not update `trade.md` unless the user confirms the trade is executed or planned to journal.
- Asset checks must not default to saved local snapshots when configured read-only account/positions APIs are available.
- Unsupported account/position capability stubs do not count as an API-first asset refresh; Futu/Moomoo OpenD should use read-only SDK account and position queries when available.
- Asset checks must not mix source modes: if provider account/positions refresh fails or returns null, use only local `assets.md` and do not add realtime quote details.
- Trade checks must use configured read-only providers for realtime/latest market data when available, save successful non-secret provider snapshots to `market_data.md`, and fall back to saved local market data only when realtime/latest data is unavailable.

## Output Style

- For normal successful provider/API lookups, show the requested data directly and briefly.
- Do not repeat routine safety boilerplate in every successful provider response.
- Mention provider safety only when it affects the current task, such as setup, install permission, blocked credentials, unsafe order/trading requests, remote-host risk, or permission failures.

## Command-Specific Docs

Load only the docs needed for the command:

- `/tradelens trade`: `docs/report_contract.md`, `docs/analysis_rules.md`, `docs/provider_rules.md`, `docs/safety_rules.md`
- `/tradelens assets`: `docs/assets_rules.md`, `docs/safety_rules.md`
- `/tradelens background`: `docs/background_rules.md`, `docs/safety_rules.md`
- `/tradelens history`: `docs/history_rules.md`
- `/tradelens analysis ratio`: `docs/history_rules.md`, `docs/stats_rules.md`
- `/tradelens provider setup`: `docs/provider_rules.md`, `docs/safety_rules.md`
- `/tradelens provider test`: `docs/provider_rules.md`, `docs/safety_rules.md`

For small commands, do not load full analysis docs.
