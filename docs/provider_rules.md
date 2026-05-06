# TradeLens Provider Rules

TradeLens has one user-facing market-data behavior: Smart Fetch.

Do not expose user-facing fetch modes such as quick, balanced, deep, off, or no-public-fetch. Internally, Smart Fetch uses capability planning, caching, and safe parallel fetches.

## Provider Output Style

- Successful provider/API results should be short and data-first.
- For normal successful provider/API results, output the requested values without safety preface text.
- Include timestamp/source and material missing-data notes when useful.
- Do not repeat routine safety boilerplate for every successful lookup, such as "no SDK install, no broker credentials, no trading unlock, no order calls."
- Mention safety constraints only when they are directly relevant to setup, installation permission, secrets, unsafe order/trading requests, remote-host risk, or provider permission failures.

## Smart Fetch

- Fetch only data needed for the command and trade type.
- Asset checks require account-summary and positions refresh through configured read-only provider APIs when available.
- Saved `assets.md` snapshots are fallback for asset checks, not the first source, unless the user explicitly asks for local-only data.
- Asset checks must use exactly one source mode. Provider mode uses provider account summary plus provider positions only; local mode uses `assets.md` only.
- Do not mix provider quote data with local asset data.
- Do not combine local asset totals, cash, or positions with realtime quotes or option marks. If account/positions API refresh fails or returns null, do not fetch, save, or present quote-only data as an asset refresh.
- Trade checks always combine provider data with local `assets.md`, `trade.md`, and `market_data.md` context.
- When configured read-only providers are available, trade checks should try realtime/latest provider data before falling back to saved local market snapshots.
- History commands fetch no market data.
- Provider setup commands fetch no market data.
- Provider test commands use only a read-only test quote when needed.
- Assets commands first try read-only account/position provider refresh. Quote-only refresh is not part of an asset check unless provider account summary and positions are also available from APIs.
- Stock-only trades require quote data and local assets/trade context; options, news, Fear & Greed, broad volatility, and broad option-chain data are not required by default.
- Option trades require quote plus relevant option data when expiry/strike are known.
- News, earnings, FOMC, Fear & Greed, OI, IV, Greeks, VIX, UVIX, and index context are fetched when explicitly requested or directly relevant.
- Skipped data must be reported as `not required`, `not requested`, `unavailable`, `missing`, `found`, `cached`, or `provider unavailable`.
- Reports must never mention quick, balanced, or deep mode.

## Cache And Parallel Fetching

- Use a per-run TTL cache for market-data lookups.
- Default TTLs: quote 15 seconds; VIX/UVIX 30 seconds; index context 30 seconds; news 10 minutes; Fear & Greed 30 minutes; option chain 60 seconds.
- Public quote/index/volatility fetches may run in parallel where safe.
- If one public request fails, record missing data and continue.
- Do not parallelize broker/account operations unless clearly safe.
- Do not cache secrets or broker credentials.
- Cache OpenD SDK availability and host/port reachability per run.

## Local Market Data Persistence

- Save successful non-secret realtime/latest provider snapshots append-only to `market_data.md`.
- Save successful non-secret account-summary and position provider snapshots append-only to `assets.md`.
- Persist symbol, fetch timestamp, provider/source, realtime or delayed status when known, quote timestamp, data quality, fallback path, and material missing fields.
- Persist account/position snapshots with provider/source, refresh timestamp, account summary fields, positions, and material missing fields.
- Do not persist quote-only `market_data.md` snapshots as part of a failed asset check fallback.
- Persist option, volatility, news, and index context only when the provider actually returned it.
- Do not persist API keys, tokens, account passwords, broker credentials, trading passwords, 2FA codes, SMS codes, or recovery codes.
- If provider data cannot be fetched, use saved local `market_data.md` snapshots only as fallback and mark stale, delayed, or freshness-unknown data clearly in the report.
- Do not overwrite or delete prior market snapshots silently.

## Provider Setup

Provider setup must be persistent and safe. If a provider is missing, output what is missing, official setup links, docs links where available, safe next steps, and security warnings.

Do not silently install apps, SDKs, helper tools, or packages. Ask explicit permission before installation. Do not ask for passwords.

Supported setup targets:
- Futu OpenD: https://www.futunn.com/en/download/OpenAPI
- Moomoo OpenD: https://www.moomoo.com/download/OpenAPI
- Tradier: https://documentation.tradier.com/
- Polygon: https://polygon.io/docs
- Finnhub: https://finnhub.io/docs/api
- Yahoo public fallback
- CNN Fear & Greed public fallback: https://www.cnn.com/markets/fear-and-greed
- OptionCharts public fallback: https://optioncharts.io/options/
- ManualProvider

Futu/Moomoo OpenD rules:
- Futu OpenD and Moomoo OpenD are separate providers.
- Default host is `127.0.0.1`.
- Read-only by default.
- Trading disabled by default.
- Remote OpenD disabled by default.
- The user logs in only through the official OpenD flow.
- TradeLens never asks for or stores broker passwords.
- For simple quote checks, use the direct local OpenD JSON socket path first.
- The Python SDK (`futu-api` or `moomoo-api`) is optional for quote checks and should be used only as fallback when installed.
- Missing Python SDK must not block a read-only quote if local OpenD is reachable and direct OpenD quote succeeds.
- Account summary and positions require the Python OpenD SDK and must use read-only `accinfo_query` and `position_list_query`.
- Never call `unlock_trade`, `place_order`, `modify_order`, or any trading/mutation method for asset checks.
- If the SDK is missing or account/position permissions are unavailable, disclose the provider failure and only then use saved `assets.md` as fallback.
