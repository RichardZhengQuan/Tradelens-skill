# Background Update Template

Use this template when the user explicitly confirms long-term investor profile, settings, strategy constraints, mistakes, reminders, analysis preferences, or data-source preferences.

## Proposed Background Update

Date:
Source:
Source command: `/background`

## Visible Facts

- ...

## User Claims

- ...

## AI Inference

- ...

## Missing Data

- ...

## Background Fields

| Field | Proposed Value | Source | Confidence | Notes |
| --- | --- | --- | --- | --- |
| Investor profile | unknown | user/screenshot | unknown | ... |
| Base currency | unknown | user/screenshot | unknown | ... |
| Market | unknown | user/screenshot | unknown | ... |
| Broker | unknown | user/screenshot | unknown | ... |
| Goal | unknown | user | unknown | ... |
| Strategy preference | unknown | user | unknown | ... |
| Risk tolerance | unknown | user | unknown | ... |
| Max position exposure | unknown | user | unknown | ... |
| Max options exposure | unknown | user | unknown | ... |
| Cash reserve rule | unknown | user | unknown | ... |
| Preferred instruments | unknown | user | unknown | ... |
| Forbidden instruments | unknown | user | unknown | ... |
| Personal trading mistakes | unknown | user | unknown | ... |
| Psychological reminders | unknown | user | unknown | ... |
| Analysis style preference | unknown | user | unknown | ... |

## Data Source Settings

| Setting | Proposed Value | Source | Confidence | Notes |
| --- | --- | --- | --- | --- |
| stock_quote_provider | unknown | user | unknown | ... |
| options_chain_provider | unknown | user | unknown | ... |
| news_provider | unknown | user | unknown | ... |
| sentiment_provider | unknown | user | unknown | ... |
| volatility_provider | unknown | user | unknown | ... |
| allow_delayed_data | ask user | user | unknown | ... |
| max_data_age_minutes | ask user | user | unknown | ... |

## Durable Update To Save

Add to section:
- `Background Settings` / `Data Source Settings` / `Trading Objectives` / `Strategy Rules` / `Preferences` / `Personal Mistakes And Psychological Reminders` / `Durable Notes`

Text:

```markdown
### YYYY-MM-DD - Title

Confirmed durable rule or preference:
- ...

Source:
- ...
```

## Next Missing Question

Ask only one next missing background question when the user gives no detail:

```text
What base currency should Trade Lens use for analysis?
```

## Confirmation Prompt

```text
Please confirm or edit this background update before I save it. I will only save durable profile, rules, preferences, or data-source settings that you explicitly confirm.
```

