"""Position sizing and exposure helpers."""

from __future__ import annotations


def stock_market_value(quantity: float, price: float) -> float:
    return quantity * price


def option_contract_notional(contracts: float, underlying_price: float, multiplier: int = 100) -> float:
    return contracts * multiplier * underlying_price


def exposure_ratio(exposure_value: float, account_value: float) -> float:
    if account_value <= 0:
        raise ValueError("account_value must be positive")
    return exposure_value / account_value


def return_on_capital(profit_loss: float, capital_required: float) -> float:
    if capital_required <= 0:
        raise ValueError("capital_required must be positive")
    return profit_loss / capital_required

