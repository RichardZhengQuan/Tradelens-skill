"""Core dataclasses for the local Trade Lens workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tradelens.data.market_snapshot import MarketDataBundle


@dataclass
class ExtractionBundle:
    """Separated extraction result from text or image input."""

    visible_facts: List[str] = field(default_factory=list)
    user_claims: List[str] = field(default_factory=list)
    ai_inferences: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    confidence: str = "unknown"


@dataclass
class OrderLine:
    order_line_id: str
    symbol: str = "unknown"
    action: str = "unknown"
    quantity: Optional[float] = None
    instrument: str = "unknown"
    option_type: str = "unknown"
    strike: Optional[float] = None
    expiry: str = "unknown"
    order_price: Optional[float] = None
    filled_price: Optional[float] = None
    status: str = "unknown"
    commission_fees: Optional[float] = None
    order_time: str = "unknown"
    source_screenshot: str = "unknown"
    extraction_confidence: str = "unknown"
    notes: str = ""


@dataclass
class OptionContract:
    symbol: str
    option_type: str
    strike: float
    expiry: str
    quantity: float = 1
    premium: Optional[float] = None
    action: str = "unknown"
    multiplier: int = 100


@dataclass
class Leg:
    leg_id: str
    action: str = "unknown"
    quantity: Optional[float] = None
    symbol: str = "unknown"
    instrument: str = "unknown"
    option_type: str = "unknown"
    strike: Optional[float] = None
    expiry: str = "unknown"
    entry_price: Optional[float] = None
    current_or_exit_price: Optional[float] = None
    status: str = "unknown"
    related_order_lines: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class TradeStrategy:
    trade_id: str
    name: str = "unknown"
    symbol: str = "unknown"
    strategy_type: str = "unknown"
    order_lines: List[OrderLine] = field(default_factory=list)
    legs: List[Leg] = field(default_factory=list)
    status: str = "unknown"
    notes: str = ""


class TradeTerm(str, Enum):
    INTRADAY = "intraday"
    SHORT_TERM = "short-term"
    MEDIUM_TERM = "medium-term"
    LONG_TERM = "long-term"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class TradeIntent:
    intended_term: TradeTerm = TradeTerm.UNKNOWN
    custom_deadline: str = ""
    primary_goal: str = "unknown"
    secondary_goal: str = ""
    must_preserve_long_term_position: str = "unknown"
    willing_to_cap_upside: str = "unknown"
    willing_to_accept_assignment: str = "unknown"


@dataclass
class TermScore:
    term: TradeTerm
    score: float
    label: str
    reason: str
    main_risk: str
    is_intended_term: bool = False


@dataclass
class MarketSnapshot:
    symbol: str
    source: str = "manual"
    last_updated: str = "unknown"
    session: str = "unknown"
    quote_timestamp: str = "unknown"
    regular_hours_price: Optional[float] = None
    premarket_price: Optional[float] = None
    after_hours_price: Optional[float] = None
    twenty_four_hour_price: Optional[float] = None
    data_quality: str = "low"
    missing_data: List[str] = field(default_factory=list)
    stock_price_provider: str = "manual"
    options_provider: str = "manual"
    news_provider: str = "manual"
    volatility_provider: str = "manual"
    data_fetched_successfully: bool = False
    fallback_used: str = "manual"
    option_chain: Optional["OptionChain"] = None
    option_quote: Optional["OptionQuote"] = None
    volatility_symbol: str = "unknown"
    volatility_price: Optional[float] = None
    volatility_timestamp: str = "unknown"
    news_headlines: List[str] = field(default_factory=list)
    context_prices: Dict[str, Optional[float]] = field(default_factory=dict)
    context_timestamps: Dict[str, str] = field(default_factory=dict)


@dataclass
class OptionQuote:
    symbol: str
    expiry: str
    strike: float
    option_type: str
    mark: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    iv: Optional[float] = None
    delta: Optional[float] = None
    source: str = "unknown"
    last_updated: str = "unknown"


@dataclass
class OptionChain:
    symbol: str
    expiry: str
    source: str = "unknown"
    last_updated: str = "unknown"
    options: List[OptionQuote] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)


# Backward-compatible alias for the first skeleton.
MarketDataSnapshot = MarketSnapshot


@dataclass
class Scenario:
    name: str
    probability: Optional[float]
    profit_loss: Optional[float]
    probability_type: str = "scenario"
    estimate_label: str = "scenario estimate"


@dataclass
class ScenarioValidationResult:
    is_valid: bool
    probability_sum: Optional[float]
    warnings: List[str] = field(default_factory=list)
    normalized_scenarios: List[Scenario] = field(default_factory=list)
    error_message: Optional[str] = None
    scenario_confidence: str = "normal"


@dataclass
class ScoreBreakdown:
    reward_risk: float = 0
    probability_setup: float = 0
    position_fit: float = 0
    market_regime: float = 0
    options_structure: float = 0
    psychology_rule_fit: float = 0
    data_quality_adjustment: float = 0


@dataclass
class TradeScore:
    label: str
    score: float
    stability: str
    breakdown: ScoreBreakdown
    scenarios: List[Scenario] = field(default_factory=list)
    expected_value: Optional[float] = None
    win_probability: Optional[float] = None
    max_reasonable_gain: Optional[float] = None
    max_reasonable_loss: Optional[float] = None
    capital_required: Optional[float] = None
    return_on_capital: Optional[float] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    symbol: str
    question: str
    market_snapshot: MarketSnapshot
    scenarios: List[Scenario]
    expected_value: Optional[float]
    win_probability: Optional[float]
    trade_score: TradeScore
    term_scores: List[TermScore] = field(default_factory=list)
    trade_intent: TradeIntent = field(default_factory=TradeIntent)
    trade_judgment: str = "no clear edge"
    market_data_bundle: Optional["MarketDataBundle"] = None
    classified_data_quality: Optional[str] = None
    data_quality_downgrade_reason: str = ""
    scenario_validation: Optional[ScenarioValidationResult] = None
    risk_assessment: List[str] = field(default_factory=list)
    decision_checklist: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)
    what_would_make_this_trade_bad: List[str] = field(default_factory=list)
    what_would_make_this_trade_better: List[str] = field(default_factory=list)
    user_decision_notes: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    visible_facts: List[str] = field(default_factory=list)
    user_claims: List[str] = field(default_factory=list)
    ai_inferences: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    order_lines: List[OrderLine] = field(default_factory=list)
    analysis_saved: bool = False
    analysis_path: str = ""
    trade_log_updated: bool = False
    saved_status_reason: str = "analysis generated as a draft; trade log requires explicit user confirmation"
    feedback_status: str = "no feedback"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnalysisRecord:
    analysis_id: str
    analysis_name: str
    created_at: datetime
    source_command: str
    body: str
