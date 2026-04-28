# Trade Lens

Trade Lens is a local markdown skill for trading analysis. It supports screenshots and text input, keeps account/trade context in markdown, generates structured analysis, and tracks feedback.

This is not a full app. It has no UI, database, cloud sync, broker login, server, or trading execution. Optional read-only market data providers can improve analysis quality, but they are not required.

## Local File Layout

The core local files are:

```text
TradeLensSkill/
  AGENTS.md
  README.md
  background.md
  assets.md
  trade.md
  market_data.md
  analysis_rules.md
  analysis_history/
  templates/
    background.template.md
    assets.template.md
    trade_entry.template.md
    analysis.template.md
  src/
    tradelens/
      __init__.py
      cli.py
      models.py
      parsers/
      data/
      calculations/
      storage/
      analysis/
  tests/
```

The active installed skill may be named `Trade Lens`, but the markdown workflow above is the required data model.

## File Meanings

- `AGENTS.md`: AI operating instructions, command behavior, confirmation rules, and safety rules.
- `README.md`: User-facing overview and command reference.
- `background.md`: Investor profile, base currency, market, broker, goals, strategy preferences, risk tolerance, exposure rules, forbidden instruments, mistakes, reminders, and analysis style.
- `assets.md`: Current assets, account snapshots, positions, exposure, watchlist, extraction confidence, missing data, and corrections.
- `trade.md`: Strategy-level trade records and raw order lines using the `Trade / Strategy -> Order Lines -> Legs -> Adjustments -> Market Context -> AI Analysis -> Feedback` hierarchy.
- `market_data.md`: Local market snapshots, provider settings, quote freshness, volatility/sentiment/news context, and corrections.
- `analysis_rules.md`: Analyze workflow, data-source abstraction, data collection checklist, missing-data behavior, and required evaluation-only analysis output.
- `analysis_history/`: Saved analysis records. Each analysis gets a unique id/name.
- `templates/background.template.md`: Background update template.
- `templates/assets.template.md`: Asset update template.
- `templates/trade_entry.template.md`: Trade / strategy, order line, leg, and adjustment template.
- `templates/analysis.template.md`: Saved analysis record template.
- `src/tradelens/`: Local Python helpers for parsing, market data abstraction, deterministic calculations, scoring, markdown storage, and report writing.
- `tests/`: Unit tests for calculation behavior.

## Core Concept

Trade Lens manages trading analysis through local markdown files. It must separate:
- Visible facts
- User claims
- AI inferences
- Assumptions
- Missing data
- Analysis and judgment

Extraction from screenshots or OCR is not confirmed truth until the user confirms it.

TradeLensSkill evaluates trades; it does not give action advice. It can say a trade is good, weak, bad, term-dependent, assignment-sensitive, IV-dependent, or missing clear edge, but it must not tell the user to buy, sell, roll, close, hold, wait, reduce, or hedge.

## Market Data Modes

TradeLensSkill works in three modes:

1. Zero-config mode
- No API key
- No broker connection
- Uses screenshots, pasted text, local markdown, and best-effort public/host data
- Data quality may be low or medium

2. Provider-enhanced mode
- User configures one or more market data providers
- Better quote/options/news quality
- API keys should be stored in environment variables, not markdown files

3. Broker-local mode
- User runs Futu OpenD or Moomoo OpenD locally
- TradeLens connects to the local OpenD gateway
- Better personal account and broker workflow support

Providers are optional. If no provider is configured, TradeLens will still attempt best-effort discovery and continue analysis with lower confidence when data is missing. OpenD is a gateway family: Futu OpenD connects to Futu servers with Futu/Futubull login, while Moomoo OpenD connects to moomoo servers with moomoo login. TradeLens never asks for or stores broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes. Missing data lowers confidence but does not crash analysis.

## Provider Setup

Providers are optional. TradeLens works without providers in zero-config/manual mode using screenshots, pasted text, local markdown, and user-confirmed values.

If a provider is missing an app, SDK, API key, local gateway, or required configuration, TradeLens should explain what is missing and provide official setup links. It must not silently install apps, SDKs, helper tools, or packages. Any installation action requires explicit user permission first.

Security rules:
- TradeLens never asks for broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- API keys should be stored in environment variables or an OS keychain, not markdown files.
- TradeLens must never store passwords or API keys in `market_data.md`.
- Provider setup improves data quality; it does not unlock the product.
- If provider setup is incomplete, analysis continues in zero-config/manual mode.

Provider setup helpers:

```bash
tradelens provider setup futu-opend
tradelens provider setup moomoo-opend
tradelens provider setup tradier
tradelens provider setup polygon
tradelens provider setup finnhub
tradelens provider setup yahoo
tradelens provider setup optioncharts
tradelens provider setup cnn-fear-greed
```

Common aliases include `tradelens provider add futu`, `tradelens provider add moomoo`, `tradelens futu setup`, `tradelens moomoo setup`, `tradelens opend setup`, `tradelens provider test futu`, and `tradelens provider test moomoo`.

Futu OpenD and Moomoo OpenD are separate data sources. Futu OpenD uses the official Futu/OpenD flow and `futu-api`; Moomoo OpenD uses the official moomoo/OpenD flow and `moomoo-api`. TradeLens connects only to local OpenD by default, keeps read-only mode on, and keeps trading disabled.

## Code-Backed Analysis

Trade Lens uses deterministic Python code in `src/tradelens/` for calculations:
- Expected value and win probability
- Scenario validation
- Max profit, max loss, breakeven, distance to strike
- Option moneyness and assignment risk
- Trade-quality score and data quality penalty
- Term-aware score adjustment
- Analysis history saving and feedback ratio

AI is reserved for screenshot extraction, news interpretation, ambiguous market-regime judgment, and human-readable explanation. It should not invent calculated values that the code can compute.

## Trade Model

A trade is not always one order. A trade can be:
- One simple order
- Multiple order lines
- A complex options strategy
- An adjustment to an existing strategy
- A decision question that needs analysis

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

Order lines support broker-style rows:
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

Supported examples:
- Single-leg trades: buy stock, sell stock, buy call, sell call, buy put, sell put.
- Multi-leg strategies: covered call, cash-secured put, wheel, LEAPS, PMCC, vertical spread, calendar spread, iron condor, strangle, custom strategies.
- Adjustments: roll, close leg, add leg, reduce size, assignment, expiration, exercise.

## Agent Workflows

The slash-style entries below are prompts/workflows for Codex or another agent to follow while working with the local markdown files. They are not shell CLI commands unless `src/tradelens/cli.py` explicitly provides them.

For the MVP, the shell CLI intentionally stays small. Implemented shell helpers are:

```bash
tradelens history
tradelens provider setup futu-opend
tradelens provider setup moomoo-opend
tradelens provider setup tradier
tradelens provider setup polygon
tradelens provider setup finnhub
tradelens provider setup yahoo
tradelens provider setup optioncharts
tradelens provider setup cnn-fear-greed
tradelens provider add opend
tradelens provider add futu
tradelens provider add futu-opend
tradelens provider add moomoo
tradelens provider add moomoo-opend
tradelens provider test opend
tradelens provider test futu
tradelens provider test futu-opend
tradelens provider test moomoo
tradelens provider test moomoo-opend
```

### `/background`

Purpose: update investment settings one by one.

Fields:
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

Behavior:
- If you provide new text, Trade Lens extracts durable settings and asks for confirmation before updating `background.md`.
- If you provide no detail, Trade Lens asks the next missing background question.
- Existing background is not overwritten blindly.
- Change history is preserved where useful.

### `/assets`

Purpose: output current assets or update assets by text or image.

Behavior:
- If you ask to view assets, Trade Lens summarizes `assets.md`.
- If you provide text or screenshot, Trade Lens extracts visible asset information.
- It asks you to confirm or edit extracted information.
- After confirmation, it updates `assets.md`.
- Snapshots keep date, source, extraction confidence, and missing data.
- Previous snapshots are preserved or tracked in a change log.

### `/trade`

Purpose: input trade by text or image and start a new analysis.

Behavior:
- Extracts trade/order/position information from text or screenshot.
- Supports one or many order lines.
- Detects or asks for intended trade term: intraday, short-term, medium-term, long-term, or custom.
- If intended term is missing, still produces term-aware analysis across intraday, short-term, medium-term, and long-term.
- Stores intended term in `trade.md`.
- Stores custom deadline if provided.
- Detects whether the input is:
  - New strategy
  - Single order
  - Adjustment to existing strategy
  - Close / roll / assignment / expiration
  - Analysis-only question
- Asks you to confirm or edit extracted trade data.
- Appends confirmed data to `trade.md`.
- Generates new analysis using `background.md`, `assets.md`, `trade.md`, and the current input.
- Saves the analysis into `analysis_history/`.
- Each analysis has a unique analysis name/id.

Analyze flow:

```text
/trade
  -> extract trade/order/strategy information
  -> confirm with user
  -> update trade.md
  -> read background.md
  -> read assets.md
  -> read trade.md
  -> collect market data if available
  -> generate structured analysis
  -> save analysis into analysis_history/
  -> allow future feedback
```

### `/tradelens provider add opend`

Purpose: configure a local OpenD provider family safely.

Behavior:
- Checks helper/tool availability, installed SDK packages, and local OpenD reachability when available.
- If Futu versus moomoo is ambiguous, asks the user to choose.
- Does not silently install packages or enable helper tools.
- Does not ask for broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- Keeps read-only mode on and trading disabled.

### `/tradelens provider add futu-opend`

Purpose: configure Futu OpenD as a local-first read-only provider.

Behavior:
- Uses `FutuOpenDProvider`.
- Keeps `read_only: true`, `allow_trading: false`, `store_password: false`, and `allow_remote_host: false`.
- Does not install the `futu` SDK unless the user explicitly approves installation separately.

### `/tradelens provider add moomoo-opend`

Purpose: configure Moomoo OpenD as a local-first read-only provider.

Behavior:
- Uses `MoomooOpenDProvider`.
- Keeps `read_only: true`, `allow_trading: false`, `store_password: false`, and `allow_remote_host: false`.
- Does not install the `moomoo` SDK unless the user explicitly approves installation separately.

### `/tradelens provider test opend`

Purpose: test a local OpenD provider safely.

Behavior:
- Auto-detects Futu versus moomoo when possible.
- If ambiguous, asks the user to choose.
- Tests with a read-only quote request only.
- Saves only non-secret provider status to `market_data.md`.

### `/tradelens provider test futu-opend`

Purpose: test Futu OpenD safely.

Behavior:
- Uses `FutuOpenDProvider`.
- Performs a read-only quote request only.
- Saves only non-secret provider status to `market_data.md`.

### `/tradelens provider test moomoo-opend`

Purpose: test Moomoo OpenD safely.

Behavior:
- Uses `MoomooOpenDProvider`.
- Performs a read-only quote request only.
- Saves only non-secret provider status to `market_data.md`.

### `/history`

Purpose: output today's analysis list.

Behavior:
- Shows analysis records created today.
- Includes analysis name/id, time, symbol, strategy type, short judgment, and feedback status.

### `/history all`

Purpose: output all analysis records.

Behavior:
- Shows all analysis records in reverse chronological order.
- Includes analysis name/id, date, symbol, strategy type, short judgment, and feedback status.

### `/history --name`

Purpose: output specific analysis data.

Behavior:
- Finds the analysis record by exact or fuzzy name.
- Outputs full analysis details.
- Includes visible facts, user claims, AI inference, assumptions, missing data, trade judgment, risks, data quality, and feedback status.

### `/history feedback --name`

Purpose: output specific analysis data and let the user choose feedback.

Behavior:
- Finds the analysis record by exact or fuzzy name.
- Outputs analysis details.
- Asks the user to choose `accurate`, `not accurate`, or `no feedback`.
- Saves the feedback into the analysis record.
- Updates any feedback index or stats source if one exists.

### `/analysis ratio`

Purpose: output total analysis accuracy ratio.

Behavior:
- Counts only records with feedback `accurate` or `not accurate` in the denominator.
- Excludes `no feedback` from the denominator.
- Outputs total analysis count, feedback count, accurate count, not accurate count, no feedback count, and accuracy ratio.

### `/analysis ratio weekly`

Purpose: output this week's analysis accuracy ratio.

Behavior:
- Uses this week's feedback records.
- If this week has no feedback data, outputs last week's ratio instead.

### `/analysis ratio monthly`

Purpose: output this month's analysis accuracy ratio.

Behavior:
- Uses this month's feedback records.
- If this month has no feedback data, outputs last month's ratio instead.

### `/analysis ratio yearly`

Purpose: output this year's analysis accuracy ratio.

Behavior:
- Uses this year's feedback records.
- If this year has no feedback data, outputs last year's ratio instead.

## Analysis Record Fields

Each saved analysis gets a unique id/name in the filename or saved wrapper metadata. The analysis body follows the evaluation-only structure in `templates/analysis.template.md`:

1. Title: `# **[TRADE JUDGMENT] — [Short reason]**`
2. Standard disclaimer
3. Summary
4. Term-Aware Trade Judgment
5. Why
6. What I Parsed
7. Key Numbers
8. Risk Check
9. Missing Data / Confirmation Needed
10. Data Used
11. Saved Status

The standard disclaimer appears once directly under the title:

```text
Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.
```

Structured `trade_judgment` must use one of: `good`, `mostly good`, `neutral`, `mostly bad`, `bad`, or `no clear edge`.

Trade Lens evaluates trade quality, risk, term fit, and scenario profile. It must not tell the user to buy, sell, roll, close, hold, wait, reduce, or hedge.

## Trade Judgment

Every analysis must judge trade quality only. The term-aware judgment table must appear near the top before any overall score summary.

Judgments:
- 80-100: `good`
- 65-79: `mostly good`
- 45-64: `neutral`
- 25-44: `mostly bad`
- 0-24: `bad`
- `no clear edge`: use when the score is unstable because key data is missing or scenario probabilities are invalid.

Score components:
- Reward / Risk: 0-25
- Probability Setup: 0-20
- Position Fit: 0-20
- Market Regime: 0-15
- Options Structure: 0-15
- Psychology / Rule Fit: 0-10
- Data Quality Adjustment: -20 to 0

Trade judgment output includes:
- Trade judgment and term-aware 0-100 scores
- Base, downside, and worst reasonable scenarios
- Probability-weighted expected return
- Max reasonable gain and loss
- Capital required
- Return on capital if calculable

Probability estimates must be labeled:
- `Market-implied probability`: option delta, option chain, IV, or breakeven.
- `Scenario probability`: trend, news, VIX, high OI, and user position.
- `User-defined probability`: the user's stated belief.

Never mix probability types without labeling them. Do not invent precise probabilities when data is weak. If estimates use incomplete data, label them as `rough estimate`, `model estimate`, `scenario estimate`, or `low confidence estimate`. When market data is weak, stale, or missing, prefer probability ranges, `unknown`, or a clearly labeled low-confidence estimate over precise percentages.

Trade assessments should start directly:

```text
# **GOOD — Strong short-term income setup**

Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.
```

Then explain why this is good, mostly good, neutral, mostly bad, bad, or no clear edge for each term.

## Term-Aware Trade Judgment

Trade term is not the same as option expiry. A weekly covered call can be a good short-term income trade but a bad long-term trade if it caps core stock upside.

Supported terms:
- intraday
- short-term
- medium-term
- long-term
- custom

Each trade entry stores:
- Intended term
- Custom deadline
- Primary and secondary goals
- Whether long-term position must be preserved
- Whether upside capping is acceptable
- Whether assignment is acceptable

Every analysis includes:

```markdown
## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday |  |  |  |
| Short-term |  |  |  |
| Medium-term |  |  |  |
| Long-term |  |  |  |
```

The assessment must state which term the trade is good or bad for. If intended term is known, that term's score must be shown separately. Term score adjustment comes from deterministic code in `calculations/term_scoring.py`; AI may only explain the result.

## Analysis Data Collection

Trade Lens collects or requests these data points when relevant. If unavailable, it lists them as missing before judgment.

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
- Whether current price is near user's strike / breakeven / cost basis

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
- Used as context only, not overweighted.

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

## Market Data Sources

Trade Lens does not depend on one fixed provider. Supported source examples:
- User-provided data pasted as text
- Screenshot extraction
- Manual quote input
- Market data API provider
- Broker API provider
- Local OpenD gateway provider: Futu OpenD or Moomoo OpenD
- Web search if available in the host environment

Supported provider settings:
- `opend.default_provider`
- `futu_opend.enabled`
- `moomoo_opend.enabled`
- `stock_quote_provider`
- `options_chain_provider`
- `news_provider`
- `sentiment_provider`
- `volatility_provider`
- `allow_delayed_data`
- `max_data_age_minutes`

If realtime data is unavailable, Trade Lens must say:
- `realtime data unavailable`
- whether delayed/manual/screenshot data is being used
- which conclusion is weakened because of missing data

## Data Rules

- Never pretend to know hidden data from screenshots.
- Never treat OCR/extraction as confirmed truth until the user confirms it.
- Never provide financial certainty.
- Always separate visible facts, user claims, AI inferences, assumptions, missing data, and judgment.
- Always state missing data.
- Always preserve prior records.
- Never silently delete or overwrite history.
- Prefer markdown append-only logs for MVP.
- The skill must work without a native app.

## Suggested Prompt

```text
Use Trade Lens. /trade I am attaching a trading screenshot. Extract visible facts only, ask me to confirm them, update the markdown files, then generate and save structured analysis.
```
