"""One documented rule for turning a posted salary into the regression target: USD per month.

Rules (write these into the report, section 2 "Data"):
- Range "X - Y"       -> midpoint (X + Y) / 2
- "from X" (только от) -> X            (the lower bound is the only number we have)
- "up to Y"           -> Y
- Currency            -> fixed rates below (one rate for the whole project, so labels don't drift)
- Period              -> year / 12, hour * 168 (21 working days x 8 h)
- Sanity range        -> anything outside 100..20 000 USD/month is treated as an error -> None
"""
from typing import Optional

# Fixed conversion rates (units of currency per 1 USD). Set once; change only with a new
# PROMPT/label version and a note in the experiment log.
RATES_PER_USD = {
    "USD": 1.0,
    "UZS": 12_500.0,
    "RUB": 90.0,
    "EUR": 0.92,
}
HOURS_PER_MONTH = 168
MIN_USD, MAX_USD = 100, 20_000


def to_usd_month(salary_min: Optional[float], salary_max: Optional[float],
                 currency: Optional[str], period: Optional[str] = "month") -> Optional[float]:
    """Return monthly salary in USD, or None when the post gives no usable salary."""
    if salary_min is None and salary_max is None:
        return None
    rate = RATES_PER_USD.get((currency or "").upper())
    if rate is None:
        return None

    if salary_min is not None and salary_max is not None:
        value = (salary_min + salary_max) / 2
    else:
        value = salary_min if salary_min is not None else salary_max

    value = value / rate
    period = (period or "month").lower()
    if period == "year":
        value /= 12
    elif period == "hour":
        value *= HOURS_PER_MONTH

    if not MIN_USD <= value <= MAX_USD:
        return None
    return round(value, 2)
