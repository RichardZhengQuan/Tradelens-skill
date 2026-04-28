# Market Data Settings

TradeLensSkill works even if no provider is configured.

Provider setup is optional. Providers improve analysis quality but do not unlock the product.

Do not store raw API keys in this file. Use environment variables for API keys.

## Modes

### Zero-config mode
- No API key
- No broker connection
- Uses screenshots, pasted text, local markdown, and best-effort public/host data
- Data quality may be low or medium

### Provider-enhanced mode
- User configures one or more market data providers
- Better quote/options/news quality

### Broker-local mode
- User runs Futu OpenD or Moomoo OpenD locally
- TradeLens connects to the local OpenD gateway
- Better personal account and broker workflow support without broker login storage

## Provider Priority

| Capability | Primary | Fallback 1 | Fallback 2 | Public Fallback | Manual Fallback |
|---|---|---|---|---|---|
| Quote | futu-opend / moomoo-opend | finnhub | yahoo | public quote pages | yes |
| Extended-hours quote | futu-opend / moomoo-opend | polygon | yahoo | public quote pages | yes |
| Overnight quote | futu-opend / moomoo-opend | polygon | yahoo | public quote pages | yes |
| Options chain | futu-opend / moomoo-opend | tradier | polygon | optioncharts | yes |
| Greeks / IV | tradier | polygon | futu-opend / moomoo-opend | optioncharts if visible | yes |
| Open interest | tradier | polygon | futu-opend / moomoo-opend | optioncharts | yes |
| News | finnhub | polygon | yahoo | public news pages | yes |
| VIX | yahoo | finnhub | manual | public quote pages | yes |
| UVIX | futu-opend / moomoo-opend | yahoo | finnhub | public quote pages | yes |
| Fear & Greed | cnn | manual | none | CNN Fear & Greed | yes |
| Index context | yahoo | finnhub | futu-opend / moomoo-opend | public quote pages | yes |
| Positions | futu-opend / moomoo-opend | manual | none | none | yes |
| Account summary | futu-opend / moomoo-opend | manual | none | none | yes |

## OpenD Provider

- default_provider: auto
- host: 127.0.0.1
- port: 11111
- require_local_opend: true
- read_only: true
- allow_trading: false
- store_password: false
- allow_remote_host: false

Notes:
- OpenD is a local gateway program.
- If only "OpenD" is requested, auto-detect Futu OpenD versus Moomoo OpenD when possible.
- If auto-detection is ambiguous, ask the user to choose Futu or Moomoo.
- Do not silently install SDK packages or helper tools.
- Ask explicit permission before installing or enabling helper tools.

## Futu OpenD Provider

- enabled: false
- host: 127.0.0.1
- port: 11111
- market: US
- account_type: futu
- require_local_opend: true
- read_only: true
- allow_trading: false
- store_password: false
- allow_remote_host: false
- sdk_package: futu

Notes:
- Futu OpenD connects to Futu servers and uses Futu/Futubull login in the OpenD app.
- TradeLens must never ask for or store broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- Test only with read-only quote requests.
- Trading must remain disabled.
- Data availability depends on user permissions and market subscriptions.

## Moomoo OpenD Provider

- enabled: false
- host: 127.0.0.1
- port: 11111
- market: US
- account_type: moomoo
- require_local_opend: true
- read_only: true
- allow_trading: false
- store_password: false
- allow_remote_host: false
- sdk_package: moomoo

Notes:
- Moomoo OpenD connects to moomoo servers and uses moomoo login in the OpenD app.
- TradeLens must never ask for or store broker passwords, trading passwords, 2FA codes, SMS codes, or recovery codes.
- Test only with read-only quote requests.
- Trading must remain disabled.
- Data availability depends on user permissions and market subscriptions.

## OpenD Provider Status

| Item | Status |
|---|---|
| Provider type | unknown |
| OpenD reachable | no |
| Host | 127.0.0.1 |
| Port | 11111 |
| Read-only mode | yes |
| Trading enabled | no |
| Password stored | no |
| Test quote | failed |

## TradierProvider

- enabled: false
- environment: production
- api_key_env: TRADIER_API_KEY

Notes:
- Real-time U.S. stocks/options data generally requires Tradier Brokerage account access.
- Use for options chain, Greeks, IV, open interest if available.

## PolygonProvider

- enabled: false
- api_key_env: POLYGON_API_KEY

Notes:
- Requires account/API key.
- Does not require brokerage account.
- Data availability depends on subscription plan.

## FinnhubProvider

- enabled: false
- api_key_env: FINNHUB_API_KEY

Notes:
- Useful for quote/news fallback.
- Do not assume complete options support.

## YahooProvider

- enabled: true
- quality: best_effort

Notes:
- Public/best-effort fallback.
- Do not rely on it for broker-grade options analysis.
- Network fetching is only used when the host allows public market-data access.

## Public Fallback Sources

| Source | URL | Capability | Enabled | Notes |
|---|---|---|---|---|
| CNN Fear & Greed | https://www.cnn.com/markets/fear-and-greed | fear_greed | true | Best-effort only; may block automated fetch |
| OptionCharts | https://optioncharts.io/options/ | options_chain, open_interest | true | Best-effort only; may require symbol-specific path |

## Data Freshness Rules

- quote_max_age_seconds: 30
- option_chain_max_age_seconds: 120
- news_max_age_hours: 24
- vix_max_age_seconds: 60
- fear_greed_max_age_hours: 24
- allow_delayed_data: true

## Missing Data Behavior

If data is missing:
- Do not fake it.
- Continue analysis if possible.
- Lower data quality.
- Show missing data in report.
- Use trade_judgment = "no clear edge" if critical data is missing.

## Latest Market Snapshot

Status: no confirmed market data yet.

| Field | Value | Source | Last Updated | Confidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Underlying symbol | unknown | not set | unknown | unknown | Not confirmed |
| Regular-hours price | unknown | not set | unknown | unknown | Not confirmed |
| Premarket price | unknown | not set | unknown | unknown | Not confirmed |
| After-hours price | unknown | not set | unknown | unknown | Not confirmed |
| 24-hour price | unknown | not set | unknown | unknown | Not confirmed |
| Option chain | unknown | not set | unknown | unknown | Not confirmed |
| Option IV / Greeks | unknown | not set | unknown | unknown | Not confirmed |
| Open interest | unknown | not set | unknown | unknown | Not confirmed |
| VIX | unknown | not set | unknown | unknown | Not confirmed |
| UVIX | unknown | not set | unknown | unknown | Fallback only if VIX unavailable |
| Fear & Greed Index | unknown | not set | unknown | unknown | Context only |
| SPY context | unknown | not set | unknown | unknown | Not confirmed |
| QQQ context | unknown | not set | unknown | unknown | Not confirmed |
| SOXX context | unknown | not set | unknown | unknown | Relevant for semiconductors |

## Corrections

Append corrections here instead of deleting historical market data.
