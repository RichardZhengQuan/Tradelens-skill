# TradeLens Stats Rules

- Accuracy ratios count only records with feedback `accurate` or `not accurate` in the denominator.
- Exclude `no feedback` from the denominator.
- Report total analysis count, feedback count, accurate count, not accurate count, no feedback count, and accuracy ratio.
- Weekly, monthly, and yearly ratios use the current period; if there is no feedback data, use the previous period.
- Stats commands do not fetch market data.
