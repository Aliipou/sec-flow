"""Unusual activity scoring for insider transactions and institutional flows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class InsiderTransaction:
    cik: str
    name: str
    ticker: str | None
    transaction_date: date
    transaction_type: str      # "P" purchase, "S" sale, "A" award, etc.
    shares: float
    price_per_share: float | None
    is_direct: bool
    filed_date: date

    @property
    def total_value(self) -> float | None:
        if self.price_per_share is None:
            return None
        return self.shares * self.price_per_share

    @property
    def urgency_score(self) -> int:
        """0-100. Higher = more unusual/significant."""
        score = 0
        if self.transaction_type == "P":
            score += 40                         # Purchases > awards > sales for bullish signal
        elif self.transaction_type == "A":
            score += 15
        val = self.total_value
        if val:
            if val > 1_000_000:
                score += 30
            elif val > 100_000:
                score += 15
            elif val > 10_000:
                score += 5
        days_to_file = (self.filed_date - self.transaction_date).days
        if days_to_file <= 1:
            score += 20      # same-day filing = very deliberate
        elif days_to_file <= 3:
            score += 10
        if self.is_direct:
            score += 10      # direct holdings > derivative
        return min(score, 100)


@dataclass
class FlowSummary:
    ticker: str
    period_start: date
    period_end: date
    buy_count: int
    sell_count: int
    award_count: int
    total_buy_value: float
    total_sell_value: float
    top_transactions: list[InsiderTransaction]

    @property
    def net_sentiment(self) -> str:
        if self.buy_count > self.sell_count * 1.5:
            return "strongly_bullish"
        if self.buy_count > self.sell_count:
            return "bullish"
        if self.sell_count > self.buy_count * 1.5:
            return "bearish"
        if self.sell_count > self.buy_count:
            return "slightly_bearish"
        return "neutral"

    @property
    def buy_sell_ratio(self) -> float:
        if self.sell_count == 0:
            return float(self.buy_count)
        return self.buy_count / self.sell_count


def parse_form4_xml(xml_text: str) -> list[dict[str, Any]]:
    """Extract transaction records from Form 4 XML."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    ns = {"": ""}
    transactions = []
    for tx in root.findall(".//{*}nonDerivativeTransaction"):
        tx_data: dict[str, Any] = {}
        tx_data["type"] = _text(tx, "transactionCoding/transactionCode")
        tx_data["date"] = _text(tx, "transactionDate/value")
        tx_data["shares"] = _float(tx, "transactionAmounts/transactionShares/value")
        tx_data["price"] = _float(tx, "transactionAmounts/transactionPricePerShare/value")
        tx_data["ownership"] = _text(tx, "ownershipNature/directOrIndirectOwnership/value")
        if tx_data.get("shares"):
            transactions.append(tx_data)
    return transactions


def _text(element: Any, path: str) -> str | None:
    found = element.find(f".//{{{path.split('/')[0]}}}" if "{" not in path else f".//{path}")
    if found is None:
        found = element.find(f".//{path.split('/')[-1]}")
    return found.text.strip() if found is not None and found.text else None


def _float(element: Any, path: str) -> float | None:
    val = _text(element, path)
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None
