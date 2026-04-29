# TradeLensSkill

TradeLensSkill is a local-first trade evaluation skill for AI agents. It helps parse proposed stock and options trades, separate facts from assumptions, evaluate risk and quality across multiple time horizons, and save analysis records as local markdown.

It answers:

```text
How good is this trade for each time horizon?
```

It does not answer:

```text
What order should I place?
```

TradeLensSkill is not a broker, trading bot, native app, hosted service, or portfolio database. It has no SwiftUI UI, no Xcode project, no cloud sync, no broker login, and no trading execution.

## Why It Exists

Trading notes often mix screenshots, quick ideas, emotional bias, market context, account constraints, and order details. TradeLensSkill keeps those pieces explicit:

- Visible facts from screenshots or pasted text
- User claims and stated intent
- AI inferences and assumptions
- Missing or stale market data
- Deterministic calculations for options, scenarios, scoring, and term fit
- A stable evaluation report that avoids action advice

The goal is disciplined trade review, not order placement.

TradeLensSkill does not give action advice. It evaluates trade quality, risk, term fit, and scenario profile without telling the user what order to place.

## What It Does

- Parses broker-style order text and trade descriptions.
- Supports stock trades and common options structures such as covered calls, cash-secured puts, vertical spreads, calendars, LEAPS, PMCCs, iron condors, strangles, wheels, and custom strategies.
- Evaluates trades by term: intraday, short-term, medium-term, long-term, or a custom deadline.
- Uses controlled judgment labels: `good`, `mostly good`, `neutral`, `mostly bad`, `bad`, and `no clear edge`.
- Saves local markdown analysis history.
- Keeps durable local user context in markdown examples such as `background.md`, `assets.md`, `trade.md`, and `market_data.md`.
- Supports optional read-only market data providers, while keeping manual and zero-config use available.

## What It Will Not Do

- It will not tell a user to buy, sell, hold, roll, close, wait, reduce, or hedge.
- It will not place trades or automate brokerage actions.
- It will not ask for broker passwords, trading passwords, 2FA codes, SMS codes, recovery codes, or API secrets.
- It will not store secrets in markdown.
- It will not invent quotes, IV, Greeks, open interest, news, earnings dates, volatility, sentiment, account data, or positions.
- It will not require providers for normal analysis.

## Agent Workflows

The slash-style entries in `AGENTS.md` and `SKILL.md` are agent workflows. They are not shell CLI commands unless `src/tradelens/cli.py` explicitly implements a helper for that behavior.

Canonical workflows include:

- `/tradelens trade`
- `/tradelens assets`
- `/tradelens background`
- `/tradelens history`
- `/tradelens analysis ratio`
- `/tradelens provider setup`
- `/tradelens provider test`

These workflows are meant for AI agents that read the local markdown rules and then perform the safe, confirmation-based workflow.

## CLI Helpers

The Python CLI is intentionally small. It provides local helpers around history and optional provider setup:

```bash
PYTHONPATH=src python3 -m tradelens.cli history
PYTHONPATH=src python3 -m tradelens.cli history --name "covered call"
PYTHONPATH=src python3 -m tradelens.cli provider setup yahoo
PYTHONPATH=src python3 -m tradelens.cli provider add futu-opend
PYTHONPATH=src python3 -m tradelens.cli provider test moomoo-opend
```

Provider setup helpers print safe setup guidance and write only non-secret local provider status/configuration. They do not install apps, SDKs, packages, or helper tools silently.

## Local-First Data Model

TradeLensSkill stores persistent user memory in local markdown files:

- `background.md`: investor profile, constraints, rules, mistakes, reminders, and analysis preferences.
- `assets.md`: account snapshots, positions, buying power, watchlists, and corrections.
- `trade.md`: strategy-level trade records using the `Trade / Strategy -> Order Lines -> Legs -> Adjustments -> Market Context -> AI Analysis -> Feedback` hierarchy.
- `market_data.md`: manually confirmed market snapshots, provider settings, volatility/sentiment/news context, and corrections.
- `analysis_history/`: saved analysis reports.

The repository includes `.example` and template files. Runtime user files are ignored by git so private account context and local analysis history do not get committed accidentally.

## Market Data

Providers are optional. TradeLensSkill works in zero-config/manual mode with pasted text, screenshots, local markdown, and user-confirmed values.

Optional provider targets include:

- Futu OpenD
- Moomoo OpenD
- Tradier
- Polygon
- Finnhub
- Yahoo public fallback
- CNN Fear & Greed public fallback
- OptionCharts public fallback
- ManualProvider

OpenD providers are read-only by default and must keep trading disabled. API providers read keys from environment variables only.

## Report Contract

Every analysis report follows the stable report contract in `docs/report_contract.md`:

1. Title with an allowed trade judgment
2. Standard non-advice disclaimer
3. Short summary
4. Term-Aware Trade Judgment
5. Why
6. What I Parsed
7. Key Numbers
8. Risk Check
9. Missing Data / Confirmation Needed
10. Data Used
11. Saved Status

The report format is deliberately strict so future agents can review, compare, and score prior analysis consistently.

## Repository Layout

```text
AGENTS.md                         Operating rules and workflow behavior
SKILL.md                          Skill metadata and routing guidance
docs/                             Detailed safety, provider, history, and report rules
templates/                        Markdown templates for saved local records
src/tradelens/                    Deterministic parsing, scoring, provider, and storage helpers
tests/                            Unit tests for calculations, providers, storage, and report contracts
assets/                           Project icons and visual assets
*.md.example                      Example local runtime files
```

## Development

Run tests with:

```bash
PYTHONPATH=src python3 -m unittest discover tests
```

The codebase intentionally keeps deterministic calculations in Python and leaves interpretation/explanation to the AI agent layer.

## License

TradeLensSkill is open source under the [Apache License 2.0](LICENSE).
