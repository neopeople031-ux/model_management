"""
정산 금액 계산 모듈

Earning, MAC(마더 에이전시 커미션), Spending을 바탕으로 최종 정산 금액을 계산합니다.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class SpendingItem:
    """지출 항목"""
    category: str
    description: str
    amount: Decimal
    date: str = ""


@dataclass
class SettlementResult:
    """정산 계산 결과"""
    total_earning: Decimal           # 총 Earning (USD)
    mac_rate: Decimal                # MAC 비율 (%)
    mac_amount: Decimal              # MAC 금액 (자동 계산)
    spending_items: list[SpendingItem] = field(default_factory=list)
    total_spending: Decimal = Decimal("0")  # 총 Spending
    net_amount: Decimal = Decimal("0")      # 최종 정산 금액

    def __post_init__(self):
        self.calculate()

    def calculate(self):
        """정산 금액을 재계산합니다."""
        # MAC 계산: total_earning * mac_rate / 100
        self.mac_amount = (
            self.total_earning * self.mac_rate / Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Spending 합산
        self.total_spending = sum(
            (item.amount for item in self.spending_items),
            Decimal("0"),
        )

        # 최종 정산 금액 = Earning - MAC - Spending
        self.net_amount = self.total_earning - self.mac_amount - self.total_spending


def calculate_settlement(
    earning_amounts: list[Decimal],
    mac_rate: Decimal,
    spending_items: list[SpendingItem] | None = None,
) -> SettlementResult:
    """
    정산 금액을 계산합니다.

    Args:
        earning_amounts: 각 스케줄별 Earning 금액 리스트
        mac_rate: MAC(마더 에이전시 커미션) 비율 (%)
        spending_items: 지출 항목 리스트

    Returns:
        SettlementResult: 계산 결과
    """
    total_earning = sum(earning_amounts, Decimal("0"))

    return SettlementResult(
        total_earning=total_earning,
        mac_rate=mac_rate,
        mac_amount=Decimal("0"),  # __post_init__에서 계산됨
        spending_items=spending_items or [],
    )


def format_usd(amount: Decimal) -> str:
    """USD 포맷 문자열 반환"""
    return f"${amount:,.2f}"
