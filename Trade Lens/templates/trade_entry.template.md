# Trade / Strategy Entry Template

Use this template for screenshots or user notes about single orders, multiple order lines, complex options strategies, adjustments, closes, rolls, assignments, expirations, exercises, or analysis-only decision questions.

Important design rule: a trade is not always one order. Treat every trade as a decision unit or strategy unit.

Required hierarchy:

```text
Trade / Strategy
  -> Order Lines
  -> Legs
  -> Adjustments
  -> Market Context
  -> AI Analysis
  -> Feedback
```

## Extraction To Confirm

Source command: `/trade`
Screenshot/user source:
Input source: text / image / screenshot / manual
Extraction time:

## Classification

Detected input type:
- new strategy / single order / multiple order lines / adjustment to existing strategy / close / roll / assignment / expiration / analysis-only question / unknown

Detected strategy type:
- buy stock / sell stock / buy call / sell call / buy put / sell put / covered call / cash-secured put / wheel / LEAPS / PMCC / vertical spread / calendar spread / iron condor / strangle / custom / unknown

Existing trade / strategy match:
- Trade / Strategy ID: unknown
- Match confidence: unknown
- Reason:

## Visible Facts From Screenshot Or Input

- ...

## User Claims

- ...

## AI Inferences

- ...

## Missing Data

- ...

## Trade Intent
- Intended term: intraday / short-term / medium-term / long-term / custom / unknown
- Custom deadline:
- Primary goal: income / growth / hedge / repair / reduce risk / speculation / preserve core position
- Secondary goal:
- Must preserve long-term position: yes / no / unknown
- Willing to cap upside: yes / no / unknown
- Willing to accept assignment: yes / no / unknown

## Trade / Strategy

| Field | Value | Source | Confidence | Notes |
| --- | --- | --- | --- | --- |
| Trade / Strategy ID | TRD-YYYYMMDD-HHMMSS | system | high | ... |
| Name | unknown | user/screenshot/system | unknown | ... |
| Symbol / underlying | unknown | user/screenshot | unknown | ... |
| Strategy type | unknown | user/screenshot/inference | unknown | single order, covered call, PMCC, spread, custom, etc |
| Direction / bias | unknown | user/inference | unknown | bullish, bearish, neutral, income, hedge |
| Decision intent | unknown | user/inference | unknown | entry, exit, roll, income, speculation, hedge, repair, etc |
| Open date | unknown | user/screenshot | unknown | ... |
| Target close / expiry date | unknown | user/screenshot | unknown | ... |
| Cost basis / net debit / net credit | unknown | user/screenshot/calculation | unknown | only if enough data exists |
| Breakeven | unknown | calculation | unknown | only if enough data exists |
| Max profit | unknown | calculation | unknown | only if determinable |
| Max loss / capital at risk | unknown | calculation | unknown | only if determinable |

## Order Lines

Use one row per broker-style order line. Order lines are execution records and may not map one-to-one with legs.

| Order Line ID | Order Time | Symbol | Action | Quantity | Instrument | Option Type | Strike | Expiry | Order Price | Filled Price | Status | Commission / Fees | Source Screenshot | Extraction Confidence | Notes |
| --- | --- | --- | --- | ---: | --- | --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- | --- |
| ORD-YYYYMMDD-HHMMSS-01 | unknown | unknown | unknown | unknown | stock / option / unknown | call / put / n/a / unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | ... |

## Legs

Use one row per economic leg. A single stock trade has one leg; a covered call usually has stock plus a short call; a PMCC usually has a long call plus a short call.

| Leg ID | Leg Role | Action | Quantity | Symbol / Underlying | Instrument | Option Type | Strike | Expiry | Entry Price | Current / Exit Price | Status | Related Order Lines | Notes |
| --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |
| LEG-01 | unknown | unknown | unknown | unknown | stock / option / cash / unknown | call / put / n/a / unknown | unknown | unknown | unknown | unknown | unknown | unknown | ... |

## Adjustments

Use this section when the input changes an existing trade or strategy.

| Adjustment ID | Time | Type | Affected Legs | Related Order Lines | Reason | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ADJ-YYYYMMDD-HHMMSS-01 | unknown | roll / close leg / add leg / reduce size / assignment / expiration / exercise / unknown | unknown | unknown | unknown | unknown | ... |

## Market Context

Only include values that are visible, user-provided, or retrieved from an available source. Do not invent data.

- Underlying price:
- Market session:
- Intraday trend:
- 5-day trend:
- 1-month trend:
- Volatility / fear:
- News / catalyst:
- Data source:
- Data last updated:

## Proposed Save Block

```markdown
### TRD-YYYYMMDD-HHMMSS - Symbol Trade Or Strategy Name

Record type:
- new strategy / single order / multiple order lines / adjustment / close / roll / assignment / expiration / analysis-only question / unknown

Status:
- planned / open / partially open / adjusted / closing / closed / expired / assigned / exercised / unknown

Created at:
Last updated:
Source command:
Input source: text / image / screenshot / manual
Source screenshot:

#### Visible Facts
- ...

#### User Claims
- ...

#### AI Inferences
- ...

#### Missing Data
- ...

#### Trade Intent
- Intended term: intraday / short-term / medium-term / long-term / custom / unknown
- Custom deadline:
- Primary goal: income / growth / hedge / repair / reduce risk / speculation / preserve core position
- Secondary goal:
- Must preserve long-term position: yes / no / unknown
- Willing to cap upside: yes / no / unknown
- Willing to accept assignment: yes / no / unknown

#### Trade / Strategy
| Field | Value | Source | Confidence | Notes |
| --- | --- | --- | --- | --- |
| Trade / Strategy ID | TRD-YYYYMMDD-HHMMSS | system | high | ... |
| Name | unknown | user/screenshot/system | unknown | ... |
| Symbol / underlying | unknown | user/screenshot | unknown | ... |
| Strategy type | unknown | user/screenshot/inference | unknown | single order, covered call, PMCC, spread, custom, etc |
| Direction / bias | unknown | user/inference | unknown | bullish, bearish, neutral, income, hedge |
| Decision intent | unknown | user/inference | unknown | entry, exit, roll, income, speculation, hedge, repair, etc |
| Cost basis / net debit / net credit | unknown | user/screenshot/calculation | unknown | only if enough data exists |
| Breakeven | unknown | calculation | unknown | only if enough data exists |
| Max profit | unknown | calculation | unknown | only if determinable |
| Max loss / capital at risk | unknown | calculation | unknown | only if determinable |

#### Order Lines
| Order Line ID | Order Time | Symbol | Action | Quantity | Instrument | Option Type | Strike | Expiry | Order Price | Filled Price | Status | Commission / Fees | Source Screenshot | Extraction Confidence | Notes |
| --- | --- | --- | --- | ---: | --- | --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- | --- |
| ORD-YYYYMMDD-HHMMSS-01 | unknown | unknown | unknown | unknown | stock / option / unknown | call / put / n/a / unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | ... |

#### Legs
| Leg ID | Leg Role | Action | Quantity | Symbol / Underlying | Instrument | Option Type | Strike | Expiry | Entry Price | Current / Exit Price | Status | Related Order Lines | Notes |
| --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |
| LEG-01 | unknown | unknown | unknown | unknown | stock / option / cash / unknown | call / put / n/a / unknown | unknown | unknown | unknown | unknown | unknown | unknown | ... |

#### Adjustments
| Adjustment ID | Time | Type | Affected Legs | Related Order Lines | Reason | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| unknown | unknown | roll / close leg / add leg / reduce size / assignment / expiration / exercise / unknown | unknown | unknown | unknown | unknown | ... |

#### Market Context
- Underlying price:
- Market session:
- Trend:
- Volatility / fear:
- News / catalyst:
- Data source:
- Data last updated:

#### AI Analysis
- Related analysis id:
- Related analysis file:
- Judgment:
- Suggested action:
- Confidence:
- Summary:

#### Feedback
- Feedback status: no feedback
- Feedback note:
- Feedback updated at:
```

## Confirmation Prompt

```text
Please confirm or edit this trade/strategy, order line, leg, and adjustment data. I will append it to trade.md only after confirmation.
```
