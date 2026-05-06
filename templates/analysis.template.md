# **[TRADE JUDGMENT] — [Short reason]**

Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.

[2-4 lines explaining what the judgment means. Explanation language may follow the user, but section names and controlled labels stay stable.]
trade_judgment: good / mostly good / neutral / mostly bad / bad / no clear edge
score stability: stable / provisional / unstable

## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday |  |  |  |
| Short-term |  |  |  |
| Medium-term |  |  |  |
| Long-term |  |  |  |

## Why
- Causal reason:
- Term fit:
- Scenario profile:
- Data-quality effect:

## What I Parsed
- Confirmation status:
- Related symbol:
- User question:
- Visible facts:
- User claims:
- AI inferences:
- Assumptions:

## Key Numbers
- Overall score summary:
- Expected value:
- Win probability:
- Max reasonable gain:
- Max reasonable loss:
- Capital required:
- Return on capital:
- Underlying price:
- Option mechanics:
  - Option mark:
  - Option bid:
  - Option ask:
  - Open interest:
  - Volume:
  - IV:
  - Delta:

## Risk Check
- Top risks:
- Trade quality worsens if:
- Trade quality improves if:
- Invalidation conditions:

## Missing Data / Confirmation Needed
- Missing data:
- Score notes:
- Confirmation needed:
- Confidence:

## Data Used
- Analysis time:
- Raw provider data quality:
- Classified data quality:
- Reason for downgrade:
- Fallback path used:
- Data quality adjustment:

**Market data status**

| Data | Status | Provider / Source | Freshness | Quality | Notes |
|---|---|---|---|---|---|

**OpenD provider status**

| Item | Status |
|---|---|
| Provider type | Futu OpenD / Moomoo OpenD / unknown |
| OpenD reachable | yes / no |
| Host | 127.0.0.1 |
| Port | 11111 |
| Read-only mode | yes |
| Trading enabled | no |
| Password stored | no |
| Test quote | success / failed |

**Provider attempts**

| Capability | Attempted Provider | Result | Error / Note |
|---|---|---|---|

## Saved Status
- Analysis saved: yes / no
- Analysis path:
- Trade log updated: yes / no
- Reason:
- Feedback status: no feedback / accurate / not accurate

Rules:
- Trade Lens judges trade quality only.
- Trade Lens must not provide user-directed action instructions.
- Do not add action-decision fields; use `trade_judgment`, `term_aware_trade_judgment`, `trade_quality_summary`, `risk_assessment`, `quality_improvement_conditions`, `confirmation_needed`, and `saved_status`.
- Structured `trade_judgment` values must be lowercase.
- Display labels must be uppercase: GOOD, MOSTLY GOOD, NEUTRAL, MOSTLY BAD, BAD, NO CLEAR EDGE.
- Use `no clear edge` for unstable, ambiguous, or missing-critical-data trades.
