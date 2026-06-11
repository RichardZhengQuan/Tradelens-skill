# Trade / Strategy Journal

This file stores confirmed strategy-level records and raw broker-style order lines. It is append-first.

Important design rule: a trade is not always one order. In Trade Lens, a trade is treated as a decision unit or strategy unit. It may be one simple order, multiple order lines, a complex options strategy, an adjustment to an existing strategy, or a decision question that needs analysis.

Do not rewrite prior entries except to append corrections, feedback, links to analyses, or follow-up notes. Do not assume hidden order details from screenshots.

## Required Hierarchy

Use this hierarchy for every saved record:

```text
Trade / Strategy
  -> Order Lines
  -> Legs
  -> Adjustments
  -> Market Context
  -> AI Analysis
  -> Feedback
```

## Supported Trade Types

Single orders and single-leg trades:
- Buy stock
- Sell stock
- Buy call
- Sell call
- Buy put
- Sell put

Multi-leg strategies:
- Covered call
- Cash-secured put
- Wheel
- LEAPS
- PMCC
- Vertical spread
- Calendar spread
- Iron condor
- Strangle
- Custom strategies

Adjustments:
- Roll
- Close leg
- Add leg
- Reduce size
- Assignment
- Expiration
- Exercise

Analysis-only records:
- Decision question
- Trade review
- Risk check
- What-if scenario

## Trade / Strategy Index

| Trade / Strategy ID | Name | Symbol | Strategy Type | Status | Opened | Last Updated | Related Analysis | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | No confirmed trade or strategy records yet |

## Raw Order Line Index

Use this index for broker-style raw rows. One trade or strategy may have zero, one, or many order lines.

| Order Line ID | Trade / Strategy ID | Order Time | Symbol | Action | Quantity | Instrument | Option Type | Strike | Expiry | Order Price | Filled Price | Status | Commission / Fees | Source Screenshot | Extraction Confidence | Notes |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- | --- |
| unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | No confirmed order lines yet |

## Trade / Strategy Records

Append confirmed records below.

```markdown
### TRD-YYYYMMDD-HHMMSS - Symbol Trade Or Strategy Name

Record type:
- new strategy / single order / multiple order lines / adjustment / close / roll / assignment / expiration / exercise / analysis-only question / unknown

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
| Open date | unknown | user/screenshot | unknown | ... |
| Target close / expiry date | unknown | user/screenshot | unknown | ... |
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
| unknown | unknown | roll / close leg / add leg / reduce size / assignment / expiration / exercise / unknown | unknown | unknown | unknown | unknown | No adjustments yet |

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

## Corrections

Append corrections here or under the relevant trade / strategy record.
