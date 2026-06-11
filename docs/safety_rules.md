# TradeLens Safety Rules

- TradeLensSkill evaluates trades; it does not recommend actions.
- Never use action advice language in reports.
- Never tell the user to buy, sell, hold, roll, close, wait, reduce, or hedge.
- Never provide financial certainty.
- Never fake missing market data, option chains, IV, Greeks, open interest, volume, news, VIX, UVIX, Fear & Greed, account data, positions, scenario probabilities, or profit/loss values.
- Always disclose missing data and data quality.
- Ambiguous trades must remain draft or needs-confirmation records.
- Proposed trades may save `analysis_history/`, but must not update `trade.md` unless the user confirms the trade is executed or planned to journal.
- Never ask for broker passwords, trading passwords, 2FA codes, SMS codes, recovery codes, or API secrets.
- Never store API keys or secrets in markdown.
- Never write secrets to `analysis_history/`.
- Use deterministic code for calculations.
- Use AI only for extraction, interpretation, news/context explanation, and final language.
- Enforce provider safety internally, but do not repeat routine safety boilerplate in normal successful provider/API responses.
- Mention provider safety only when it is directly relevant to setup, installation permission, secrets, unsafe order/trading requests, remote-host risk, or provider permission failures.
