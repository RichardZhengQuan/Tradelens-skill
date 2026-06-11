# Trade Lens Agent Instructions

Trade Lens is a slash-workflow local skill for trading analysis. It uses markdown files only and must work before any native app exists.

Do not build UI, database, cloud sync, broker login, server features, or brokerage automation. Optional read-only market data providers are allowed, but provider setup must never be required for normal analysis.

The slash-style entries in this file are agent workflows for Codex to follow. They are not shell CLI commands unless `src/tradelens/cli.py` explicitly provides them. For the MVP, keep the shell CLI small; implemented shell helpers include `tradelens history` plus safe provider setup/add/test helpers.

## Codex Skill Sync Rule

After changing TradeLensSkill code, docs, templates, tests, or agent instructions in this repository, update the installed Codex skill copy at `/Users/richardq/.codex/skills/Trade Lens` before finishing the turn.

Use `scripts/sync_to_codex_skill.sh` from the repository root. The sync must preserve private runtime files in the installed skill, including `background.md`, `assets.md`, `trade.md`, `market_data.md`, and `analysis_history/`.

## Persistent Product Rules

TradeLensSkill is a local-first trade evaluation skill for AI agents. It evaluates proposed trades across time horizons and answers: "How good is this trade for each time horizon?" It does not answer: "What order should I place?"

Authoritative rule docs:
- `docs/report_contract.md`: fixed analysis report contract, language handling, allowed judgment labels, forbidden report language, and saved-status rules.
- `docs/safety_rules.md`: absolute safety rules for action advice, secrets, missing data, draft status, and local-only memory.
- `docs/provider_rules.md`: Smart Fetch, provider setup, cache, parallel fetch, and OpenD safety rules.
- `docs/analysis_rules.md`: analysis workflow and deterministic-code boundaries.

Persistent rules for all future runs:
- TradeLensSkill evaluates trades; it does not recommend actions.
- Never use action advice language in reports.
- Always use allowed trade judgment labels.
- Always include the standard disclaimer once near the top.
- Always show Term-Aware Trade Judgment near the top.
- Never show only one score without time horizon.
- Keep report structure stable across user languages.
- User-facing explanation may follow the user's language, but the report contract does not change.
- Never fake missing market data.
- Never ask for broker password, trading password, 2FA, SMS code, recovery code, or API secrets.
- Never store API keys in markdown.
- Never write secrets to `analysis_history/`.
- Use local markdown files as user memory.
- Asset checks must try configured read-only provider APIs for account summary and positions before relying on saved `assets.md`.
- Save successful non-secret account/position provider snapshots append-only to `assets.md`.
- Asset checks must use one source mode only: provider account/positions data or local `assets.md` data, never a mix.
- Every trade check must read current `assets.md` and `trade.md` history before judgment, even when the user only asks to "check" or "evaluate" a trade.
- Use configured read-only providers such as Futu OpenD, Moomoo OpenD, or API providers for realtime/latest market data when available; save successful non-secret provider snapshots to `market_data.md`.
- If realtime/latest provider data is unavailable, stale, blocked, or incomplete, fall back to saved local markdown data and disclose which conclusions are weakened.
- Use deterministic code for calculations.
- Use AI only for interpretation and explanation.
- Missing data must be disclosed.
- Ambiguous trades must remain draft or needs-confirmation records.
- Proposed trades may save `analysis_history/` but must not update `trade.md` unless the user confirms the trade is executed or planned to journal.

## User-Facing Output Style

Keep provider/API results concise. For normal successful provider checks, quote lookups, account summaries, funds snapshots, or position refreshes, output the requested data directly with timestamp/source and any material missing data. Do not repeat routine safety boilerplate such as "no SDK install, no broker credentials, no trading unlock, no order calls."

Mention safety constraints only when they are directly relevant: provider setup, installation permission, an unsafe user request, a blocked operation, credentials/secrets, trading/order automation, remote-host risk, or a provider failure caused by permissions.

## Canonical Files

- `AGENTS.md`: Operating rules and command behavior.
- `README.md`: User-facing overview and command reference.
- `background.md`: Durable investor profile, settings, rules, constraints, mistakes, reminders, and analysis preferences.
- `assets.md`: Account, cash, buying power, positions, exposure, watchlist, snapshots, and corrections.
- `trade.md`: Strategy-level trade records and raw order lines using the `Trade / Strategy -> Order Lines -> Legs -> Adjustments -> Market Context -> AI Analysis -> Feedback` hierarchy.
- `market_data.md`: Confirmed or manually provided market snapshots, provider settings, volatility/sentiment/news context, and market-data corrections.
- `analysis_rules.md`: Analyze workflow, market data requirements, data-source abstraction, missing-data handling, and required evaluation-only analysis output.
- `analysis_history/`: One saved markdown file per analysis.
- `templates/background.template.md`: Background update format.
- `templates/assets.template.md`: Asset extraction and snapshot format.
- `templates/trade_entry.template.md`: Trade / strategy, order line, leg, and adjustment format.
- `templates/analysis.template.md`: Saved analysis record format.
- `src/tradelens/`: Local Python helpers for parsing, markdown storage, market-data abstraction, deterministic calculations, scoring, and report writing.
- `tests/`: Unit tests for options, scenarios, and scoring calculations.

## Core Data Rules

- All persistent records are local markdown files.
- For asset checks, local fallback means `assets.md` only after configured read-only account/position APIs are unavailable, stale, blocked, incomplete, or explicitly bypassed by the user.
- Never combine local asset totals, cash, buying power, or positions with realtime quote/option marks in the same asset check.
- Quote-only provider data is not an asset refresh; if account summary or positions API data is missing/null, use only local `assets.md`.
- For trade checks, local context means at minimum `assets.md`, `trade.md`, and relevant `market_data.md` snapshots/settings.
- `assets.md` and `trade.md` must be consulted for position size, cash/buying-power fit, existing exposure, duplicate/overlapping trades, and prior strategy history.
- Never assume hidden information from a screenshot.
- Never treat OCR/extraction as confirmed truth until the user confirms it.
- Always separate:
  - Visible facts
  - User claims
  - AI inferences
  - Assumptions
  - Missing data
  - Analysis and judgment
- Always state missing data and data quality in the generated evaluation.
- Never provide action advice. Trade Lens evaluates trade quality, risk, term fit, and scenario profile; it must not tell the user to buy, sell, roll, close, hold, wait, reduce, or hedge.
- Providers are optional and improve analysis quality; they do not unlock the product.
- Never fake missing market data, IV, Greeks, open interest, volume, news, VIX, UVIX, Fear & Greed, positions, or account data.
- Never require API keys for normal analysis.
- Never store API keys in markdown. API providers must read keys from environment variables only.
- Never ask for a broker password.
- OpenD is a gateway family. Use `FutuOpenDProvider` for Futu/Futubull login and Futu servers, and `MoomooOpenDProvider` for moomoo login and moomoo servers.
- `FutuProvider` is only a compatibility alias for `FutuOpenDProvider`.
- OpenD providers must be local-first, read-only by default, and must keep `store_password: false`, `allow_trading: false`, and `allow_remote_host: false`.
- Simple OpenD quote checks should use direct local OpenD JSON socket requests first; missing `futu-api` or `moomoo-api` must not block quote lookup when direct OpenD succeeds.
- Python OpenD SDK packages are optional quote fallbacks and still require explicit user approval before installation.
- Futu/Moomoo OpenD account summary and position refreshes must use read-only SDK queries (`accinfo_query` and `position_list_query`) when the SDK is installed.
- Never call `unlock_trade`, `place_order`, `modify_order`, or trading/mutation APIs during asset checks.
- Never ask for broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- When a provider is missing an app, SDK, API key, local gateway, or configuration, give the official setup link and safe next steps.
- Do not silently install provider apps, SDKs, helper tools, or packages.
- Ask explicit permission before any installation action.
- Never ask for broker password or 2FA.
- Never store secrets in markdown.
- If provider data is missing, stale, blocked, or permission-limited, report it clearly and continue analysis when possible.
- If critical data is missing, use `trade_judgment = "no clear edge"` when needed.
- Never provide financial certainty.
- Preserve prior records. Do not silently delete, replace, or overwrite history.
- Prefer append-only logs for the MVP.
- If data is unavailable, mark it `unknown` or `unavailable`; do not fake it.

## Code-Backed Analysis Rules

Use deterministic code in `src/tradelens/` for anything that can be calculated:
- Expected value
- Scenario probability validation
- Win probability
- Max profit
- Max loss
- Breakeven
- Distance to strike
- Option moneyness
- Assignment risk
- Trade score
- Term-aware score adjustment
- Data quality penalty
- Analysis history saving
- Feedback ratio

Use AI only for:
- Screenshot extraction
- Interpreting news
- Judging market regime when data is ambiguous
- Explaining the trade assessment in human language

Do not replace deterministic calculation functions with prompt-only reasoning.

## Confirmation Rule

Before updating `background.md`, `assets.md`, or `trade.md` from screenshots or interpreted user text:

1. Show extracted data.
2. Label visible facts, user claims, AI inferences, assumptions, and missing data.
3. Ask the user to confirm or edit.
4. Save only after confirmation, unless the user explicitly asks to save unconfirmed data.

## Agent Workflow System

### `/background`

Purpose: update investment settings one by one.

Fields to ask for or update:
- Investor profile
- Base currency
- Market
- Broker
- Goal
- Strategy preference
- Risk tolerance
- Max position exposure
- Max options exposure
- Cash reserve rule
- Preferred instruments
- Forbidden instruments
- Personal trading mistakes
- Psychological reminders
- Analysis style preference
- Data-source settings from `analysis_rules.md`

Behavior:
- If the user provides new background text, extract the durable settings and ask for confirmation before updating `background.md`.
- If the user gives no details, ask the next missing background question.
- Never overwrite existing background blindly.
- Preserve a change history where useful.
- Temporary ideas or one-off trade context should go in `trade.md` or an analysis record, not `background.md`.

### `/assets`

Purpose: view current assets or update assets from text or image.

Behavior:
- If the user asks to view/check assets, first try configured read-only provider APIs for account summary and positions.
- For Futu/Moomoo OpenD, a real provider refresh means read-only `accinfo_query` and `position_list_query`; unsupported capability stubs do not count as API-first completion.
- If provider refresh succeeds, save the non-secret account/position snapshot append-only to `assets.md`, then summarize the refreshed state with timestamp/source.
- If provider refresh fails, returns null, or is unavailable, summarize only `assets.md` as local fallback and disclose that values may be stale.
- Do not refresh or present quotes, option marks, or `market_data.md` values in an asset check when the account/positions API refresh failed.
- If the user provides text or screenshot, extract visible account and position information.
- Ask the user to confirm or edit extracted information.
- After confirmation, update `assets.md`.
- Keep snapshot date, source, extraction confidence, missing data, and corrections.
- Preserve previous snapshots or at least keep a change log.

### `/trade`

Purpose: input trade information by text or image and start a new analysis.

Behavior:
- Extract trade, order, position, strategy, leg, and adjustment information from text or screenshot.
- Support one or many raw broker-style order lines.
- Treat a trade as a decision unit or strategy unit, not necessarily one order.
- Detect or ask for the intended trade term: intraday, short-term, medium-term, long-term, or custom.
- If intended term is missing, still produce term-aware analysis across intraday, short-term, medium-term, and long-term.
- Store intended term in `trade.md`.
- Store custom deadline if provided.
- Detect whether input is:
  - New strategy
  - Single order
  - Adjustment to an existing strategy
  - Close, roll, assignment, or expiration
  - Analysis-only question
- Ask user to confirm or edit extracted trade data.
- Append confirmed data to `trade.md`.
- Read `background.md`, `assets.md`, and full relevant `trade.md` history before judgment.
- Read `market_data.md` for provider settings and saved local market snapshots.
- Use `assets.md` and `trade.md` to identify current position fit, cash/buying-power fit, existing exposure, duplicate positions, and related open/closed strategy history.
- Collect or request market data if available from configured, user-provided, screenshot, manual, broker, API, or web-search sources.
- Prefer configured read-only providers for realtime/latest quote, option, volatility, news, and index data when available.
- Save successful non-secret realtime/latest provider snapshots to `market_data.md` before or with the analysis record.
- If provider data cannot be fetched, use saved local `market_data.md` data only as fallback and disclose staleness/missing fields.
- Generate a structured analysis using the required format in `analysis_rules.md`.
- Save the analysis to `analysis_history/` with a unique id and name.
- Ask for future feedback.

### `/history`

Purpose: output today's analysis list.

Behavior:
- Show analysis records created today.
- Include analysis name/id, time, symbol, strategy type, short judgment, and feedback status.

### `/history all`

Purpose: output all analysis records.

Behavior:
- Show all analysis records in reverse chronological order.
- Include analysis name/id, date, symbol, strategy type, short judgment, and feedback status.

### `/history --name`

Purpose: output a specific analysis record.

Behavior:
- Find the analysis record by exact or fuzzy name.
- Output full analysis details.
- Include visible facts, user claims, AI inference, assumptions, missing data, trade judgment, risks, data quality, and feedback status.

### `/history feedback --name`

Purpose: output a specific analysis record and record feedback.

Behavior:
- Find the analysis record by exact or fuzzy name.
- Output the analysis details.
- Ask the user to choose exactly one:
  - `accurate`
  - `not accurate`
  - `no feedback`
- Save the feedback into the analysis record.
- Update any feedback index or stats source if one exists.

### `/analysis ratio`

Purpose: output total analysis accuracy ratio.

Behavior:
- Count only records with feedback `accurate` or `not accurate` in the denominator.
- Exclude `no feedback` from the denominator.
- Output:
  - Total analysis count
  - Feedback count
  - Accurate count
  - Not accurate count
  - No feedback count
  - Accuracy ratio

### `/analysis ratio weekly`

Purpose: output this week's analysis accuracy ratio.

Behavior:
- Use records from the current week.
- If this week has no feedback data, output last week's ratio instead.

### `/analysis ratio monthly`

Purpose: output this month's analysis accuracy ratio.

Behavior:
- Use records from the current month.
- If this month has no feedback data, output last month's ratio instead.

### `/analysis ratio yearly`

Purpose: output this year's analysis accuracy ratio.

Behavior:
- Use records from the current year.
- If this year has no feedback data, output last year's ratio instead.

## Trade Data Model

A trade is a decision unit or strategy unit. It may contain one simple order, many broker-style order lines, a complex options strategy, an adjustment to an existing strategy, or only a decision question needing analysis.

In `trade.md`, the saved unit is called a `Trade / Strategy`. Use that term even for a simple single order so the structure remains consistent.

Supported single-leg trades:
- Buy stock
- Sell stock
- Buy call
- Sell call
- Buy put
- Sell put

Supported multi-leg strategies:
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

Supported adjustments:
- Roll
- Close leg
- Add leg
- Reduce size
- Assignment
- Expiration
- Exercise

Use this exact hierarchy in `trade.md`:

```text
Trade / Strategy
  -> Order Lines
  -> Legs
  -> Adjustments
  -> Market Context
  -> AI Analysis
  -> Feedback
```

Order lines should support broker-style rows:
- Order line id
- Order time
- Symbol
- Action
- Quantity
- Instrument
- Option type
- Strike
- Expiry
- Order price
- Filled price
- Status
- Commission / fees
- Source screenshot
- Extraction confidence
- Notes

## Trade Intent Model

Trade term is not the same as option expiry. A weekly covered call can be a good short-term income trade but a bad long-term trade if it caps core stock upside.

Supported trade terms:
- intraday
- short-term
- medium-term
- long-term
- custom

Each `/trade` entry should capture:
- Intended term
- Custom deadline, if any
- Primary goal
- Secondary goal
- Whether the user must preserve the long-term position
- Whether the user is willing to cap upside
- Whether the user is willing to accept assignment

## Analysis Workflow

For `/trade`, run this sequence:

```text
/trade
  -> extract trade/order/strategy information
  -> confirm with user
  -> update trade.md
  -> read background.md
  -> read assets.md for account, position, cash, buying-power, and exposure context
  -> read trade.md for related trade/strategy history
  -> read market_data.md for provider settings and saved local snapshots
  -> collect realtime/latest provider data if configured and available
  -> save successful non-secret provider snapshots into market_data.md
  -> use saved local market data as fallback when realtime/latest data is unavailable
  -> generate structured analysis
  -> save analysis into analysis_history/
  -> allow future feedback
```

Every saved analysis must include:
- A unique analysis id/name in the filename or saved wrapper metadata.
- The exact evaluation-only body defined in `analysis_rules.md` and `templates/analysis.template.md`.

## Analysis Data To Collect Or Request

Collect these when relevant. If unavailable, list them under missing data and explain which conclusions are weakened.

Realtime underlying price:
- Regular-hours price
- Premarket price
- After-hours price
- 24-hour price if supported
- Last updated time
- Data source

Market trend:
- Intraday trend
- 5-day trend
- 1-month trend
- Recent high / low
- Key support / resistance if visible
- Whether current price is near the user's strike / breakeven / cost basis

Options data:
- Highest open interest call strikes
- Highest open interest put strikes
- Current option chain if available
- IV / IV rank if available
- Volume vs open interest if available
- Expiration date
- Distance to strike
- Moneyness: ITM / ATM / OTM
- Assignment risk if short option
- Gamma / pin risk when near high OI strikes

Volatility / fear data:
- VIX realtime price if available
- UVIX realtime price as fallback if VIX is unavailable
- VIX trend
- Market fear regime: low / normal / elevated / panic

Sentiment data:
- Fear & Greed Index if available
- Sentiment classification: extreme fear / fear / neutral / greed / extreme greed
- Use sentiment as context only; do not overweight it.

News / catalyst:
- Newest company news
- Newest sector news
- Earnings date
- Macro event if relevant
- Whether the move is company-specific, sector-wide, or market-wide

Index / sector context:
- SPY
- QQQ
- SOXX for semiconductors
- Compare stock movement with index movement

User context:
- User background rules from `background.md`
- Current assets from `assets.md`
- Existing trades and strategies from `trade.md`
- Cash reserve rule
- Max position exposure
- Options exposure
- User psychological reminders

## Market Data Rules

- Use the provider abstraction in `analysis_rules.md`; do not depend on one fixed provider.
- Supported source types include user-provided text, screenshot extraction, manual quote input, market data API provider, broker API provider, and web search if available in the host environment.
- On trade checks, try configured read-only providers for realtime/latest data before relying on saved local market snapshots.
- Successful provider snapshots must be saved append-only to `market_data.md` without secrets; include symbol, timestamp, provider/source, realtime/delayed status when known, quality, and material missing fields.
- If realtime/latest data cannot be fetched, use saved local `market_data.md` snapshots only as fallback and mark them as local/stale if freshness is uncertain.
- If the user says "Futu", use `FutuOpenDProvider`; if the user says "Moomoo", use `MoomooOpenDProvider`.
- If the user says only "OpenD", try auto-detection by checking available helper skills/tools, installed SDK package, and local OpenD reachability. Ask the user to choose Futu or Moomoo if ambiguous.
- Do not silently install SDK packages or helper tools. Ask explicit permission before installing or enabling helper tools.
- For `/tradelens provider setup <provider>`, check missing components and return official setup/docs links, safe next steps, and security warnings.
- Supported setup targets are `futu-opend`, `moomoo-opend`, `tradier`, `polygon`, `finnhub`, `yahoo`, `optioncharts`, and `cnn-fear-greed`.
- Normalize provider aliases: `futu`, `futu-opend`, `futud` -> `futu-opend`; `moomoo`, `moomoo-opend`, `moomoo openapi` -> `moomoo-opend`; `polygon`, `massive` -> `polygon`; `feargreed`, `cnn` -> `cnn-fear-greed`; `optioncharts`, `option charts` -> `optioncharts`.
- If provider setup is incomplete, keep zero-config/manual mode available and continue analysis with lower data quality.
- Test OpenD connections with read-only quote requests only, and save only non-secret provider status to `market_data.md`.
- Supported provider settings include `stock_quote_provider`, `options_chain_provider`, `news_provider`, `sentiment_provider`, `volatility_provider`, `allow_delayed_data`, and `max_data_age_minutes`.
- If realtime data is unavailable, say:
  - `realtime data unavailable`
  - whether delayed/manual/screenshot data is being used
  - which conclusions are weakened by missing data
- Do not invent quotes, option chains, VIX, sentiment, news, earnings dates, open interest, IV, or index data.

## Required Analysis Output

Every analysis body must follow the evaluation-only section order in `templates/analysis.template.md`:

1. Title: `# **[TRADE JUDGMENT] — [Short reason]**`
2. Standard disclaimer
3. 2-4 line summary without a `## Summary` heading
4. Term-Aware Trade Judgment
5. Why
6. What I Parsed
7. Key Numbers
8. Risk Check
9. Missing Data / Confirmation Needed
10. Data Used
11. Saved Status

The standard disclaimer must appear once, directly under the title:

```text
Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.
```

The structured `trade_judgment` must use one of: `good`, `mostly good`, `neutral`, `mostly bad`, `bad`, or `no clear edge`.
Do not output `final_action`, `preferred_action`, `suggested_action`, `recommended_action`, `decision_gate`, or `best_action` fields.

## Term-Aware Trade Judgment Rules

Every analysis must include `## **Term-Aware Trade Judgment**` near the top.

Rules:
- A trade can be GOOD for short-term and BAD for long-term.
- Trade assessment must explicitly say which term the trade is good or bad for.
- If the user's intended term is known, show that term's score separately.
- If intended term conflicts with background rules, say so directly.
- For covered calls, PMCC, and short calls, always check whether the trade caps long-term upside.
- For CSP, always check whether assignment fits the user's long-term position plan.
- For LEAPS, always check whether time decay and leverage fit the user's intended term.
- For short volatility strategies, always check whether the term is too short for the risk taken.

Use deterministic code in `calculations/term_scoring.py` for term score adjustments. AI may explain the reason, but the score adjustment should come from code.

## Trade Judgment Rules

Every analysis must include `trade_judgment` in the opening summary. Overall score summaries are allowed only after the term-aware judgment table.

Trade judgment values:
- 80-100: `good`
- 65-79: `mostly good`
- 45-64: `neutral`
- 25-44: `mostly bad`
- 0-24: `bad`
- Use `no clear edge` when the score is unstable because key data is missing or scenario probabilities are invalid.

Default scoring structure:
- Reward / Risk: 0-25
- Probability Setup: 0-20
- Position Fit: 0-20
- Market Regime: 0-15
- Options Structure: 0-15
- Psychology / Rule Fit: 0-10
- Data Quality Adjustment: -20 to 0

Probability estimates must be labeled as one of:
- `Market-implied probability`: option delta, option chain, IV, or breakeven.
- `Scenario probability`: trend, news, VIX, high OI, and user position.
- `User-defined probability`: the user's stated belief.

Never mix these probability types without labeling them. Do not invent precise probabilities when data is weak. If probability estimates use incomplete data, label them as `rough estimate`, `model estimate`, `scenario estimate`, or `low confidence estimate`. When market data is weak, stale, or missing, prefer probability ranges, `unknown`, or a clearly labeled low-confidence estimate over precise percentages.

The trade assessment must start directly, for example:

```text
# **GOOD — Strong short-term income setup**

Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.
```

Then summarize estimated scenarios, estimated EV, term fit, risk assessment, invalidation conditions, and what would make the trade profile better or worse.

## Feedback Rules

After saving an analysis, ask:

```text
Feedback for this analysis: accurate / not accurate / no feedback?
```

If feedback is provided:
- `accurate`: append feedback status, timestamp, and any user note.
- `not accurate`: ask what was wrong, then append correction, status, and timestamp.
- `no feedback`: record only when the user wants it saved or when the command explicitly requires it.
