# TradeLens Analysis Rules

- Read local markdown memory before analysis when relevant: `background.md`, `assets.md`, `trade.md`, and `market_data.md`.
- For every trade check/evaluation, `assets.md` and relevant `trade.md` history are required context, not optional context.
- Use `assets.md` for account size, cash/buying power, position exposure, concentration, and assignment capacity checks.
- Use `trade.md` for related strategy history, duplicate/overlapping exposure, open adjustments, prior feedback, and whether the proposal is new, existing, or an adjustment.
- Use configured read-only providers for realtime/latest market data when available; save successful non-secret provider snapshots to `market_data.md`.
- If realtime/latest provider data is unavailable, use saved local `market_data.md` snapshots or user-confirmed manual data as fallback and disclose staleness or missing fields.
- Separate visible facts, user claims, AI inferences, assumptions, missing data, and judgment.
- Use deterministic code for expected value, win probability, scenario validation, score labels, term-aware scoring, option mechanics, data-quality penalties, storage, and feedback ratio.
- Use AI only for extraction, ambiguous interpretation, news/context explanation, and final language.
- Every analysis must follow `docs/report_contract.md`.
- Term-Aware Trade Judgment is the main result.
- Overall judgment is only a summary of term-aware judgments.
- Missing data must weaken confidence and be disclosed.
- If critical data is missing or scenarios are invalid, use `no clear edge`.
- If the user proposes a trade but does not confirm it as executed or planned to journal, save analysis history if appropriate but do not update `trade.md`.
