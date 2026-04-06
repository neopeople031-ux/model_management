"""
정산 계산 단위 테스트

Earning 합산, MAC 비율 적용, Spending 공제, 최종 net_amount 검증
"""
import pytest
from decimal import Decimal
from utils.settlement_calc import (
    calculate_settlement,
    SettlementResult,
    SpendingItem,
    format_usd,
)


class TestSettlementCalculation:
    """정산 계산 테스트"""

    def test_basic_earning_only(self):
        """Earning만 있는 기본 계산"""
        result = calculate_settlement(
            earning_amounts=[Decimal("1000"), Decimal("2000"), Decimal("1500")],
            mac_rate=Decimal("20"),
        )
        assert result.total_earning == Decimal("4500")
        assert result.mac_amount == Decimal("900.00")
        assert result.total_spending == Decimal("0")
        assert result.net_amount == Decimal("3600.00")

    def test_with_spending(self):
        """Spending이 있는 계산"""
        spending = [
            SpendingItem(category="hospital", description="병원비", amount=Decimal("150")),
            SpendingItem(category="sim_card", description="유심비", amount=Decimal("30")),
        ]
        result = calculate_settlement(
            earning_amounts=[Decimal("5000")],
            mac_rate=Decimal("15"),
            spending_items=spending,
        )
        assert result.total_earning == Decimal("5000")
        assert result.mac_amount == Decimal("750.00")
        assert result.total_spending == Decimal("180")
        assert result.net_amount == Decimal("4070.00")

    def test_zero_mac_rate(self):
        """MAC 비율 0%인 경우"""
        result = calculate_settlement(
            earning_amounts=[Decimal("3000")],
            mac_rate=Decimal("0"),
        )
        assert result.mac_amount == Decimal("0.00")
        assert result.net_amount == Decimal("3000.00")

    def test_high_mac_rate(self):
        """MAC 비율이 높은 경우"""
        result = calculate_settlement(
            earning_amounts=[Decimal("10000")],
            mac_rate=Decimal("40"),
        )
        assert result.mac_amount == Decimal("4000.00")
        assert result.net_amount == Decimal("6000.00")

    def test_no_earnings(self):
        """Earning이 없는 경우"""
        result = calculate_settlement(
            earning_amounts=[],
            mac_rate=Decimal("20"),
        )
        assert result.total_earning == Decimal("0")
        assert result.mac_amount == Decimal("0.00")
        assert result.net_amount == Decimal("0.00")

    def test_mac_rounding(self):
        """MAC 계산 시 반올림 확인"""
        result = calculate_settlement(
            earning_amounts=[Decimal("1111")],
            mac_rate=Decimal("33"),
        )
        # 1111 * 33 / 100 = 366.63
        assert result.mac_amount == Decimal("366.63")

    def test_spending_exceeds_net(self):
        """Spending이 Earning-MAC보다 큰 경우 (음수 정산)"""
        spending = [
            SpendingItem(category="other", description="과다 지출", amount=Decimal("5000")),
        ]
        result = calculate_settlement(
            earning_amounts=[Decimal("1000")],
            mac_rate=Decimal("20"),
            spending_items=spending,
        )
        assert result.net_amount < Decimal("0")


class TestFormatUsd:
    """USD 포맷 테스트"""

    def test_basic(self):
        assert format_usd(Decimal("1000.50")) == "$1,000.50"

    def test_large_number(self):
        assert format_usd(Decimal("1234567.89")) == "$1,234,567.89"

    def test_zero(self):
        assert format_usd(Decimal("0")) == "$0.00"
