# Analysis Rules

Trade Lens analysis is local markdown output built from confirmed user input, local context files, and any available market data. It must be useful without pretending that missing data exists.

Do not build UI, database, cloud sync, broker login, trading execution, or native app features. Optional read-only market data providers are allowed and must remain non-blocking.

## Analyze Workflow

For `/trade`, use this workflow:

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

If extracted screenshot data has not been confirmed by the user, do not use it as confirmed input. Present it as unconfirmed extraction and ask for confirmation first.

## Deterministic Calculation Requirement

Use code from `src/tradelens/` for anything that can be calculated:
- `calculations/scenarios.py`: expected value, win probability, scenario validation
- `calculations/options.py`: intrinsic value, moneyness, distance to strike, breakeven, max profit/loss, assignment risk
- `calculations/scoring.py`: scoring components, data quality penalty, score label, total trade-quality score
- `calculations/term_scoring.py`: term-aware score adjustments and term labels
- `storage/history_store.py`: analysis saving and feedback ratio

Use AI only for screenshot extraction, interpreting news, ambiguous market-regime judgment, and final human-language explanation.

## Data-Source Abstraction

Trade Lens must not depend on one fixed provider. The analysis engine can use any available source, but it must identify the source and freshness for each data category.

Supported provider examples:
- User-provided data pasted as text
- Screenshot extraction
- Manual quote input
- Market data API provider
- Broker API provider
- Local OpenD gateway provider: Futu OpenD or Moomoo OpenD
- Web search if available in the host environment

Supported provider settings:

| Setting | Purpose | Default |
| --- | --- | --- |
| `opend.default_provider` | Auto, Futu OpenD, or Moomoo OpenD family selection | auto |
| `futu_opend.enabled` | Enable Futu OpenD provider | false |
| `moomoo_opend.enabled` | Enable Moomoo OpenD provider | false |
| `stock_quote_provider` | Underlying stock/ETF quote source | unknown |
| `options_chain_provider` | Options chain, open interest, IV, Greeks | unknown |
| `news_provider` | Company, sector, earnings, macro news | unknown |
| `sentiment_provider` | Fear & Greed or similar sentiment source | unknown |
| `volatility_provider` | VIX, UVIX fallback, or volatility source | unknown |
| `allow_delayed_data` | Whether delayed data can be used | ask user |
| `max_data_age_minutes` | Maximum acceptable data age | ask user |

If realtime data is unavailable, clearly say:
- `realtime data unavailable`
- whether delayed/manual/screenshot data is being used
- which conclusion is weakened because of missing data

Never fake or infer unavailable realtime market data.

OpenD provider rules:
- OpenD is the local gateway program, not a single broker provider.
- Futu OpenD connects to Futu servers and uses Futu/Futubull login.
- Moomoo OpenD connects to moomoo servers and uses moomoo login.
- Both are local-first and read-only by default.
- Neither may ask for or store broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- Trading must remain disabled.
- If only "OpenD" is requested, auto-detect when possible and ask the user to choose Futu or Moomoo if ambiguous.
- Test connections with read-only quote requests only.

## Data Points To Collect Or Request

Collect or request these when relevant. If unavailable, list them under missing data.

### 1. Realtime Underlying Price

- Regular-hours price
- Premarket price
- After-hours price
- 24-hour price if supported
- Last updated time
- Data source

### 2. Market Trend

- Intraday trend
- 5-day trend
- 1-month trend
- Recent high / low
- Key support / resistance if visible
- Whether current price is near user's strike / breakeven / cost basis

### 3. Options Data

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

### 4. Volatility / Fear Data

- VIX realtime price if available
- UVIX realtime price as fallback if VIX is unavailable
- VIX trend
- Market fear regime: low / normal / elevated / panic

### 5. Sentiment Data

- Fear & Greed Index if available
- Classify sentiment as extreme fear / fear / neutral / greed / extreme greed
- Do not overweight it; use it as context only

### 6. News / Catalyst

- Newest company news
- Newest sector news
- Earnings date
- Macro event if relevant
- Whether the move is company-specific, sector-wide, or market-wide

### 7. Index / Sector Context

- SPY
- QQQ
- SOXX for semiconductors
- Compare stock movement with index movement

### 8. User Context

- User background rules from `background.md`
- Current assets from `assets.md`
- Existing trades and strategies from `trade.md`
- Cash reserve rule
- Max position exposure
- Options exposure
- User psychological reminders

## Required Analysis Output

Every saved analysis in `analysis_history/` must evaluate trade quality without giving action advice. Use this structure:

```markdown
# **[TRADE JUDGMENT] — [Short reason]**

Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.

## **Summary**
[2-4 plain-English lines explaining what the judgment means.]

- trade_judgment: good / mostly good / neutral / mostly bad / bad / no clear edge
- score stability: stable / provisional / unstable

## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday |  |  |  |
| Short-term |  |  |  |
| Medium-term |  |  |  |
| Long-term |  |  |  |

## **Why**

## **What I Parsed**

## **Key Numbers**

## **Risk Check**

## **Missing Data / Confirmation Needed**

## **Data Used**

## **Saved Status**
```

Structured `trade_judgment` values must be lowercase and must be one of `good`, `mostly good`, `neutral`, `mostly bad`, `bad`, or `no clear edge`. Display labels must be `GOOD`, `MOSTLY GOOD`, `NEUTRAL`, `MOSTLY BAD`, `BAD`, or `NO CLEAR EDGE`.

Trade Lens must not output coaching-style action language. It may say the trade is good, mostly good, neutral, mostly bad, bad, or no clear edge for a given term.

## Trade Judgment Rules

The final analysis must judge trade quality, not user action.

Trade judgment values:
- 80-100: `good`
- 65-79: `mostly good`
- 45-64: `neutral`
- 25-44: `mostly bad`
- 0-24: `bad`
- Use `no clear edge` when the score is unstable because key data is missing or scenario probabilities are invalid.

Default scoring structure:

| Component | Range | Questions |
| --- | ---: | --- |
| Reward / Risk | 0-25 | Is the possible reward worth the possible loss? Is max loss acceptable? Is expected value positive? |
| Probability Setup | 0-20 | Does the trade have favorable estimated probability? Is it supported by options data, price trend, and volatility? |
| Position Fit | 0-20 | Does this trade fit current assets? Does it preserve core positions? Does it avoid unwanted assignment or forced selling? |
| Market Regime | 0-15 | Does the trade match current trend, VIX, Fear & Greed, and sector/index context? |
| Options Structure | 0-15 | Are strike, expiry, IV, open interest, and moneyness reasonable? Is there pin/gamma/assignment risk? |
| Psychology / Rule Fit | 0-10 | Does the trade fit the user's written background rules? Does it avoid the user's common mistakes? |
| Data Quality Adjustment | -20 to 0 | Penalize stale, missing, or low-confidence data. |

Probability labeling:
- `Market-implied probability`: based on option delta, option chain, IV, or breakeven.
- `Scenario probability`: based on trend, news, VIX, high OI, and user position.
- `User-defined probability`: based on the user's stated belief.

Never mix probability sources without labeling them. If estimates are based on incomplete data, label them as one of:
- `rough estimate`
- `model estimate`
- `scenario estimate`
- `low confidence estimate`

Do not invent precise probabilities when data is weak. If the score is unstable, still include term-aware 0-100 scores when possible, but label the score `unstable` and use `no clear edge` when the numeric score should not drive trade quality.

When market data is weak, stale, or missing, prefer probability ranges, `unknown`, or a clearly labeled low-confidence estimate over precise percentages.

Trade assessment opening format:

```text
# **GOOD — Strong short-term income setup**

Not financial advice. This assessment is based only on information you provided, local TradeLens records, and available public/provider data; missing or stale data may change the result.

## **Term-Aware Trade Judgment**

| Term | Judgment | Score | Why |
|---|---|---:|---|
| Intraday | NEUTRAL | 58 | no same-session edge confirmed |
| Short-term | GOOD | 82 | income profile fits the near-expiry term |
| Medium-term | MOSTLY GOOD | 70 | risk/reward remains constructive |
| Long-term | NEUTRAL | 55 | core exposure impact is mixed |
```

After the opening, explain why the judgment is good, mostly good, neutral, mostly bad, bad, or no clear edge for each term.

## Rules

- Never pretend to know unavailable realtime data.
- Never treat extracted screenshot data as confirmed until user confirms.
- Never give financial certainty.
- Always separate visible facts, user claims, AI inference, assumptions, missing data, and judgment.
- Always state missing data and data quality.
- Always consider user background and assets before evaluating trade quality.
- The trade assessment must be useful but not overconfident.
- The trade judgment must be quality-focused, and uncertainty and weak data must be explicit.
- Never provide action advice.
