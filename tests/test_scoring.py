from datetime import date
from app.analysis.scoring import InsiderTransaction, FlowSummary, parse_form4_xml


def make_tx(**kwargs) -> InsiderTransaction:
    defaults = dict(
        cik="0001234567", name="John CEO", ticker="ACME",
        transaction_date=date(2024, 1, 10), transaction_type="P",
        shares=10000, price_per_share=50.0,
        is_direct=True, filed_date=date(2024, 1, 10),
    )
    return InsiderTransaction(**{**defaults, **kwargs})


def test_urgency_score_high_value_same_day_purchase():
    tx = make_tx(shares=100000, price_per_share=15.0)
    assert tx.urgency_score >= 80


def test_urgency_score_sale_lower_than_purchase():
    buy = make_tx(transaction_type="P")
    sell = make_tx(transaction_type="S")
    assert buy.urgency_score > sell.urgency_score


def test_total_value():
    tx = make_tx(shares=1000, price_per_share=25.0)
    assert tx.total_value == 25000.0


def test_total_value_none_price():
    tx = make_tx(price_per_share=None)
    assert tx.total_value is None


def test_urgency_score_capped_at_100():
    tx = make_tx(shares=1_000_000, price_per_share=1000.0)
    assert tx.urgency_score <= 100


def test_flow_summary_bullish():
    tx = make_tx()
    summary = FlowSummary(
        ticker="ACME", period_start=date(2024, 1, 1), period_end=date(2024, 1, 31),
        buy_count=5, sell_count=1, award_count=0,
        total_buy_value=500_000, total_sell_value=10_000,
        top_transactions=[tx],
    )
    assert "bullish" in summary.net_sentiment


def test_flow_summary_bearish():
    summary = FlowSummary(
        ticker="ACME", period_start=date(2024, 1, 1), period_end=date(2024, 1, 31),
        buy_count=1, sell_count=5, award_count=0,
        total_buy_value=5_000, total_sell_value=500_000,
        top_transactions=[],
    )
    assert "bearish" in summary.net_sentiment


def test_buy_sell_ratio_no_sells():
    summary = FlowSummary(
        ticker="X", period_start=date(2024, 1, 1), period_end=date(2024, 1, 31),
        buy_count=3, sell_count=0, award_count=0,
        total_buy_value=0, total_sell_value=0, top_transactions=[],
    )
    assert summary.buy_sell_ratio == 3.0


def test_parse_form4_xml_empty():
    result = parse_form4_xml("<invalid>xml</invalid>")
    assert result == []


def test_parse_form4_xml_valid():
    xml = """<?xml version="1.0"?>
    <ownershipDocument>
      <nonDerivativeTransaction>
        <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
        <transactionDate><value>2024-01-15</value></transactionDate>
        <transactionAmounts>
          <transactionShares><value>1000</value></transactionShares>
          <transactionPricePerShare><value>42.50</value></transactionPricePerShare>
        </transactionAmounts>
        <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
      </nonDerivativeTransaction>
    </ownershipDocument>"""
    result = parse_form4_xml(xml)
    assert len(result) == 1
    assert result[0]["shares"] == 1000.0
