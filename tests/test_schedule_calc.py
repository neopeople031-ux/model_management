"""
스케줄 시간 계산 단위 테스트

PRD §6 비즈니스 로직 검증:
- 30분 반올림/버림 규칙
- Half/Full/OT 판별
"""
import pytest
from datetime import datetime
from utils.schedule_calc import round_hours, calculate_work_type, WorkTypeResult


class TestRoundHours:
    """30분 반올림 규칙 테스트"""

    def test_exact_hours(self):
        """정확히 N시간인 경우"""
        assert round_hours(60) == 1
        assert round_hours(120) == 2
        assert round_hours(300) == 5
        assert round_hours(540) == 9

    def test_round_down_30_minutes(self):
        """30분 이하: 버림"""
        assert round_hours(270) == 4   # 4시간 30분 → 4시간
        assert round_hours(150) == 2   # 2시간 30분 → 2시간
        assert round_hours(90) == 1    # 1시간 30분 → 1시간
        assert round_hours(61) == 1    # 1시간 1분 → 1시간

    def test_round_up_31_minutes(self):
        """31분 이상: 올림"""
        assert round_hours(271) == 5   # 4시간 31분 → 5시간
        assert round_hours(151) == 3   # 2시간 31분 → 3시간
        assert round_hours(91) == 2    # 1시간 31분 → 2시간
        assert round_hours(59) == 1    # 0시간 59분 → 올림 → 1시간

    def test_round_at_boundary(self):
        """경계값 테스트"""
        assert round_hours(30) == 0    # 30분 → 0시간 (버림)
        assert round_hours(31) == 1    # 31분 → 1시간 (올림)
        assert round_hours(510) == 8   # 8시간 30분 → 8시간
        assert round_hours(511) == 9   # 8시간 31분 → 9시간


class TestCalculateWorkType:
    """Half/Full/OT 판별 테스트"""

    def _make_times(self, hours: int, minutes: int = 0):
        """테스트용 시작/종료 시간 생성"""
        start = datetime(2025, 1, 1, 9, 0, 0)
        end = datetime(2025, 1, 1, 9 + hours, minutes, 0)
        return start, end

    def test_hours_only_1_to_4(self):
        """1~4시간: 해당 시간 표기"""
        start, end = self._make_times(2, 0)  # 2시간
        result = calculate_work_type(start, end)
        assert result.work_type == "hours_only"
        assert result.rounded_hours == 2
        assert result.display == "2시간"

    def test_hours_only_4h30m(self):
        """4시간 30분: 반올림으로 4시간 → hours_only"""
        start, end = self._make_times(4, 30)
        result = calculate_work_type(start, end)
        assert result.work_type == "hours_only"
        assert result.rounded_hours == 4
        assert result.display == "4시간"

    def test_half_at_4h31m(self):
        """4시간 31분 → 5시간 → Half"""
        start, end = self._make_times(4, 31)
        result = calculate_work_type(start, end)
        assert result.work_type == "half"
        assert result.rounded_hours == 5
        assert result.display == "Half"

    def test_half_at_exact_5h(self):
        """정확히 5시간 → Half"""
        start, end = self._make_times(5, 0)
        result = calculate_work_type(start, end)
        assert result.work_type == "half"
        assert result.rounded_hours == 5
        assert result.display == "Half"

    def test_half_plus(self):
        """7시간 → Half + 2시간"""
        start, end = self._make_times(7, 0)
        result = calculate_work_type(start, end)
        assert result.work_type == "half_plus"
        assert result.rounded_hours == 7
        assert result.display == "Half + 2시간"

    def test_half_plus_6h31m(self):
        """6시간 31분 → 7시간 → Half + 2시간"""
        start, end = self._make_times(6, 31)
        result = calculate_work_type(start, end)
        assert result.work_type == "half_plus"
        assert result.rounded_hours == 7
        assert result.display == "Half + 2시간"

    def test_full_at_8h31m(self):
        """8시간 31분 → 9시간 → Full"""
        start, end = self._make_times(8, 31)
        result = calculate_work_type(start, end)
        assert result.work_type == "full"
        assert result.rounded_hours == 9
        assert result.display == "Full"

    def test_full_at_exact_9h(self):
        """정확히 9시간 → Full"""
        start, end = self._make_times(9, 0)
        result = calculate_work_type(start, end)
        assert result.work_type == "full"
        assert result.rounded_hours == 9
        assert result.display == "Full"

    def test_full_plus(self):
        """12시간 → Full + 3시간"""
        start, end = self._make_times(12, 0)
        result = calculate_work_type(start, end)
        assert result.work_type == "full_plus"
        assert result.rounded_hours == 12
        assert result.display == "Full + 3시간"

    def test_full_plus_10h31m(self):
        """10시간 31분 → 11시간 → Full + 2시간"""
        start, end = self._make_times(10, 31)
        result = calculate_work_type(start, end)
        assert result.work_type == "full_plus"
        assert result.rounded_hours == 11
        assert result.display == "Full + 2시간"

    def test_minimum_1h(self):
        """매우 짧은 시간도 최소 1시간"""
        start, end = self._make_times(0, 20)
        result = calculate_work_type(start, end)
        assert result.rounded_hours >= 1

    def test_invalid_end_before_start(self):
        """종료 시간이 시작 시간보다 이전이면 에러"""
        start = datetime(2025, 1, 1, 10, 0)
        end = datetime(2025, 1, 1, 9, 0)
        with pytest.raises(ValueError):
            calculate_work_type(start, end)
