# TradeLens Report Contract

This file is the source of truth for all TradeLens analysis output.

TradeLensSkill evaluates trade quality across time horizons. It answers: "How good is this trade for each time horizon?" It does not answer: "What order should I place?"

## Allowed Judgment Vocabulary

Structured `trade_judgment` values:
- `good`
- `mostly good`
- `neutral`
- `mostly bad`
- `bad`
- `no clear edge`

Display labels:
- `GOOD`
- `MOSTLY GOOD`
- `NEUTRAL`
- `MOSTLY BAD`
- `BAD`
- `NO CLEAR EDGE`

## Forbidden Report Language

Reports must not use action/advice language:
- `wait`
- `buy`
- `sell`
- `hold`
- `roll`
- `close`
- `reduce`
- `add hedge`
- `preferred action`
- `suggested action`
- `recommended action`
- `best action`
- `I recommend`
- `you should`
- `do not buy`
- `do not sell`
- `do not wait`

Allowed quality language:
- `This trade is GOOD for short-term because...`
- `This trade is MOSTLY BAD for long-term because...`
- `This setup has NO CLEAR EDGE because...`
- `This trade becomes worse if...`
- `This trade requires confirmation of...`
- `This trade conflicts with...`
- `This trade depends on...`

## Required Section Order

Every TradeLens analysis report must follow this exact section order regardless of user language:

```markdown
# **[TRADE JUDGMENT] — [Short reason]**

Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.

2-4 line summary.

## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday |  |  |  |
| Short-term |  |  |  |
| Medium-term |  |  |  |
| Long-term |  |  |  |

## Why

## What I Parsed

## Key Numbers

## Risk Check

## Missing Data / Confirmation Needed

## Data Used

## Saved Status
```

## Contract Rules

- Term-Aware Trade Judgment must appear near the top.
- Do not show a single Trade Score before Term-Aware Trade Judgment.
- Do not give only one score without time horizon.
- Overall judgment is allowed only as a summary of the term-aware judgments.
- If the trade is ambiguous, use `NO CLEAR EDGE`.
- If data is missing, explain missing data.
- If the trade is proposed but not confirmed, do not update `trade.md`.
- Analysis history may be saved, but `trade.md` should only update after the user confirms an executed or planned trade.
- `Saved Status` must disclose whether analysis history was saved and whether the trade log was updated.

## Language Rule

- Users may write in any language.
- Detect the user's language when possible.
- User-facing explanatory text may follow the user's language.
- Controlled labels remain stable unless a tested localization map exists.
- Section names remain stable English unless a schema-based localized section map is explicitly implemented and tested.
- Section order, disclaimer, Term-Aware Trade Judgment, allowed labels, forbidden language, missing-data disclosure, and saved-status disclosure must not change based on user language.
