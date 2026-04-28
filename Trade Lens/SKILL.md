---
name: trade-lens
description: Use when the user wants local markdown-based trading analysis from screenshots or text, including account/position extraction, trade/order/strategy journaling, options strategy analysis, optional read-only market data provider use, agent-workflow history lookup, and feedback tracking. This skill is local-only and must not build UI, database, cloud sync, broker login, server, trading execution, or native app features.
metadata:
  short-description: Local markdown trading analysis workflow
---

# Trade Lens

Trade Lens manages trading context and analysis through local markdown files. It supports screenshots and text input, but it never treats extracted data as confirmed until the user confirms it.

Analysis output must judge trade quality only. Reports must start with `# **[TRADE JUDGMENT] — [Short reason]**`, show the standard disclaimer directly under the title, use structured `trade_judgment` values, and show `## **Term-Aware Trade Judgment**` near the top before any overall score summary.

## Files

- `AGENTS.md`: Full operating rules and command behavior.
- `background.md`: Durable investor profile, constraints, preferences, and strategy rules.
- `assets.md`: Current and historical account/position snapshots.
- `trade.md`: Strategy-level trade records and raw order lines using the `Trade / Strategy -> Order Lines -> Legs -> Adjustments -> Market Context -> AI Analysis -> Feedback` hierarchy.
- `market_data.md`: Local market snapshots and provider settings.
- `analysis_rules.md`: Structured analysis workflow, market data abstraction, and output requirements.
- `analysis_history/`: Saved analysis records.
- `templates/`: Markdown templates for background, assets, trade entries, and analysis records.
- `src/tradelens/`: Local Python helpers for parsing, calculations, scoring, storage, and report writing.
- `tests/`: Unit tests for deterministic calculations.

## Agent Workflow Router

The slash-style entries below are agent workflows for Codex to follow inside this local markdown skill. They are not shell CLI commands unless a separate Python CLI command is explicitly implemented. For the MVP, keep the shell CLI small; implemented helpers include `tradelens history` and safe provider setup/test helpers for OpenD, API, and public fallback providers.

Use `AGENTS.md` as the authoritative command spec:

- `/background`: update or ask for missing investor settings.
- `/assets`: summarize assets or extract/update account and position information.
- `/trade`: extract trade/order/strategy information, confirm it, append to `trade.md`, generate analysis, and save it.
- `/history`: show today's analyses.
- `/history all`: show all analyses.
- `/history --name`: show one analysis by exact or fuzzy name.
- `/history feedback --name`: show one analysis and record feedback.
- `/analysis ratio`: calculate feedback accuracy ratio.
- `/analysis ratio weekly|monthly|yearly`: calculate period feedback ratios with fallback to the previous period if the current period has no feedback.
- `/tradelens provider setup futu-opend|moomoo-opend|tradier|polygon|finnhub|yahoo|optioncharts|cnn-fear-greed`: explain missing setup, official links, safe next steps, and security warnings without installing anything.
- `/tradelens provider add|test opend|futu-opend|moomoo-opend`: configure or test local OpenD providers without secrets or trading enablement.

## Non-Negotiable Rules

- Never assume hidden data from a screenshot.
- Never treat OCR or extraction as confirmed truth before user confirmation.
- Always separate visible facts, user claims, AI inference, assumptions, missing data, and judgment.
- Always state missing data and data quality in the generated evaluation.
- Never provide action advice. Trade Lens may evaluate trade quality, risk, term fit, and scenario profile, but it must not tell the user to buy, sell, roll, close, hold, wait, reduce, or hedge.
- Never provide financial certainty.
- OpenD is a gateway family: use `FutuOpenDProvider` for Futu/Futubull login and `MoomooOpenDProvider` for moomoo login.
- Provider setup is optional and only improves data quality; zero-config/manual mode must keep working.
- Never ask for or store broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- Never store API keys or provider secrets in markdown.
- Do not silently install provider apps, SDKs, helper tools, or packages.
- OpenD providers must remain local-first and read-only by default; trading must stay disabled.
- Preserve prior markdown records; prefer append-only logs.
- If realtime data is unavailable, say so and explain which conclusions are weakened.

## Working Pattern

1. Read the relevant local markdown files.
2. Extract visible or user-provided data into structured fields.
3. Ask the user to confirm or edit extracted data before saving it.
4. Append confirmed data to the correct file.
5. Generate structured analysis using `analysis_rules.md`.
6. Save every analysis in `analysis_history/`.
7. Ask for feedback: `accurate`, `not accurate`, or `no feedback`.
