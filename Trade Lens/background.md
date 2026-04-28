# Background

This file stores durable user profile, investment settings, strategy rules, constraints, personal mistakes, psychological reminders, analysis preferences, and data-source preferences.

It should change slowly. Temporary trade comments belong in `trade.md`; one-time analysis belongs in `analysis_history/`.

## Last Updated

- Created: 2026-04-27
- Last confirmed update: not set

## Background Settings

| Field | Current Value | Source | Confidence | Last Updated | Notes |
| --- | --- | --- | --- | --- | --- |
| Investor profile | unknown | not set | unknown | not set | Ask with `/background` |
| Base currency | unknown | not set | unknown | not set | Example: USD, HKD, CNY |
| Market | unknown | not set | unknown | not set | Example: US stocks, HK stocks |
| Broker | unknown | not set | unknown | not set | Do not assume from screenshots unless visible |
| Goal | unknown | not set | unknown | not set | Income, growth, hedge, learning, etc |
| Strategy preference | unknown | not set | unknown | not set | Example: options income, long equity |
| Risk tolerance | unknown | not set | unknown | not set | User-defined only |
| Max position exposure | unknown | not set | unknown | not set | Percent or currency |
| Max options exposure | unknown | not set | unknown | not set | Percent or currency |
| Cash reserve rule | unknown | not set | unknown | not set | Minimum cash or buying power |
| Preferred instruments | unknown | not set | unknown | not set | Stock, ETF, options, spreads, etc |
| Forbidden instruments | unknown | not set | unknown | not set | Instruments to avoid |
| Personal trading mistakes | unknown | not set | unknown | not set | Durable reminders only |
| Psychological reminders | unknown | not set | unknown | not set | Durable reminders only |
| Analysis style preference | unknown | not set | unknown | not set | Concise, detailed, risk-first, etc |

## Data Source Settings

| Setting | Current Value | Source | Confidence | Last Updated | Notes |
| --- | --- | --- | --- | --- | --- |
| stock_quote_provider | unknown | not set | unknown | not set | User-provided, screenshot, API, broker, web search, etc |
| options_chain_provider | unknown | not set | unknown | not set | Options chain, OI, IV, Greeks |
| news_provider | unknown | not set | unknown | not set | Company, sector, earnings, macro |
| sentiment_provider | unknown | not set | unknown | not set | Fear & Greed or similar |
| volatility_provider | unknown | not set | unknown | not set | VIX, UVIX fallback, or other |
| allow_delayed_data | ask user | not set | unknown | not set | Do not assume delayed data is acceptable |
| max_data_age_minutes | ask user | not set | unknown | not set | Ask before relying on stale data |

## User Profile

Visible facts:
- None confirmed yet.

User claims:
- None confirmed yet.

AI inference:
- None recorded. Do not infer user identity, account size, broker, country, tax status, risk tolerance, or experience level unless the user confirms it.

## Trading Objectives

Confirmed:
- Not set.

Open questions:
- What market and base currency should Trade Lens use?
- What instruments does the user trade?
- What time horizon is typical?
- Is the focus income, growth, hedging, learning, or another objective?
- What maximum loss, exposure, or drawdown limits has the user chosen?
- What cash reserve rule should be respected?

## Strategy Rules

Confirmed rules:
- Not set.

Rules to confirm before use:
- Entry criteria: unknown.
- Exit criteria: unknown.
- Position sizing: unknown.
- Stop loss policy: unknown.
- Take profit policy: unknown.
- Risk per trade: unknown.
- Maximum number of open positions: unknown.
- Max position exposure: unknown.
- Max options exposure: unknown.
- Cash reserve rule: unknown.
- Event/news restrictions: unknown.
- Assignment/expiration preferences: unknown.

## Preferences

Analysis preferences:
- Start with missing data and limitations.
- Separate visible facts, user claims, AI inference, and analysis.
- Use scenario-based reasoning instead of certainty.
- Ask for confirmation before saving extracted screenshot data.
- Consider background rules and assets before suggesting action.

Output preferences:
- Be concise but practical.
- Use markdown.
- Keep local files append-friendly.

## Personal Mistakes And Psychological Reminders

Confirmed reminders:
- Not set.

Do not invent reminders. Add only after explicit user confirmation.

## Durable Notes

Add dated notes here only after explicit user confirmation.

```markdown
### YYYY-MM-DD - Note Title

Visible facts:
- ...

User claims:
- ...

Confirmed durable rule or preference:
- ...
```

## Change Log

- 2026-04-27: Initial local background file created.

