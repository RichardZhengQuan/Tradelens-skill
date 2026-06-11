# TradeLens Assets Rules

- Use `assets.md` as local markdown memory for confirmed account, cash, buying power, positions, exposure, watchlist, snapshots, and corrections.
- Asset checks are API-first when configured read-only providers are available.
- When the user asks to check/view assets, first try configured read-only provider APIs for account summary and positions when available.
- For Futu/Moomoo OpenD, account summary and positions must use the read-only SDK queries `accinfo_query` and `position_list_query`; do not treat unsupported stubs as a real provider refresh.
- Never call `unlock_trade`, `place_order`, `modify_order`, or any trading/mutation method for asset checks.
- Use one asset data source mode per asset check: provider mode or local mode.
- Do not mix provider quote data with local asset data.
- Provider mode requires both provider account summary and provider positions. If either is missing, null, blocked, or stale, do not use any realtime quote details in that asset check.
- Local mode uses only `assets.md`; do not combine saved cash/total assets/positions with refreshed quotes, option marks, or `market_data.md` snapshots.
- Quote-only data is market context, not an asset refresh, and must not be used to estimate account value when account/positions API refresh failed.
- Save successful non-secret provider account/position snapshots append-only to `assets.md`.
- Use saved local `assets.md` data only when provider refresh is unavailable, blocked, stale, incomplete, or the user explicitly asks for local-only data.
- Do not treat OCR or screenshot extraction as confirmed truth until the user confirms it.
- Separate visible facts, user claims, AI inferences, assumptions, and missing data.
- Preserve previous snapshots and corrections.
- Disclose provider failures, stale local snapshots, missing buying power, margin requirement, option exposure, or unconfirmed values.
- Never ask for broker passwords, trading passwords, 2FA codes, SMS codes, recovery codes, or API secrets.
