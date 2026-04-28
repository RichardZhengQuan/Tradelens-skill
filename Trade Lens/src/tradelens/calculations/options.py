"""Deterministic option calculations used by Trade Lens."""

from __future__ import annotations

from typing import Optional


def option_intrinsic_value(underlying_price: float, strike: float, option_type: str) -> float:
    option = option_type.lower()
    if option == "call":
        return max(0.0, underlying_price - strike)
    if option == "put":
        return max(0.0, strike - underlying_price)
    raise ValueError("option_type must be 'call' or 'put'")


def option_moneyness(underlying_price: float, strike: float, option_type: str, atm_tolerance: float = 0.01) -> str:
    if underlying_price <= 0:
        raise ValueError("underlying_price must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    distance = abs(underlying_price - strike) / strike
    if distance <= atm_tolerance:
        return "ATM"
    option = option_type.lower()
    if option == "call":
        return "ITM" if underlying_price > strike else "OTM"
    if option == "put":
        return "ITM" if underlying_price < strike else "OTM"
    raise ValueError("option_type must be 'call' or 'put'")


def distance_to_strike_pct(underlying_price: float, strike: float) -> float:
    """Signed distance from underlying to strike.

    Positive means the strike is above the current underlying price; negative
    means the strike is below it.
    """

    if underlying_price <= 0:
        raise ValueError("underlying_price must be positive")
    return (strike - underlying_price) / underlying_price


def covered_call_breakeven(stock_cost_basis: float, premium_received: float) -> float:
    return stock_cost_basis - premium_received


def covered_call_max_profit(stock_cost_basis: float, strike: float, premium_received: float, shares: int = 100) -> float:
    return (strike - stock_cost_basis + premium_received) * shares


def cash_secured_put_breakeven(strike: float, premium_received: float) -> float:
    return strike - premium_received


def cash_secured_put_max_loss(strike: float, premium_received: float, contracts: int = 1, multiplier: int = 100) -> float:
    return (strike - premium_received) * contracts * multiplier


def short_call_assignment_risk(
    underlying_price: float,
    strike: float,
    days_to_expiry: int,
    delta: Optional[float] = None,
) -> str:
    if delta is not None and delta >= 0.75:
        return "high"
    money = option_moneyness(underlying_price, strike, "call", atm_tolerance=0.02)
    if money == "ITM" and days_to_expiry <= 7:
        return "high"
    if money == "ATM" and days_to_expiry <= 7:
        return "elevated"
    if money == "ITM":
        return "elevated"
    return "normal"


# Backward-compatible wrappers from the first skeleton.
def intrinsic_value(underlying_price: float, strike: float, option_type: str) -> float:
    return option_intrinsic_value(underlying_price, strike, option_type)


def moneyness(underlying_price: float, strike: float, option_type: str, atm_tolerance: float = 0.01) -> str:
    return option_moneyness(underlying_price, strike, option_type, atm_tolerance)


def short_option_assignment_risk(underlying_price: float, strike: float, option_type: str, days_to_expiry: int) -> str:
    if option_type.lower() == "call":
        return short_call_assignment_risk(underlying_price, strike, days_to_expiry)
    money = option_moneyness(underlying_price, strike, option_type, atm_tolerance=0.02)
    if money == "ITM" and days_to_expiry <= 7:
        return "high"
    if money == "ATM" and days_to_expiry <= 7:
        return "elevated"
    if money == "ITM":
        return "elevated"
    return "normal"
