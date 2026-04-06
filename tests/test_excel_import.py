"""
엑셀 대량 업로드 유틸리티 테스트
"""
import io
import pytest
import pandas as pd
from datetime import date

from utils.excel_import import (
    parse_excel,
    dataframe_to_db_records,
    _detect_header_map,
    _parse_date,
    _parse_numeric,
)
from utils.excel_export import generate_upload_template


def _make_excel_bytes(data: list[list], columns: list[str]) -> bytes:
    """테스트용 엑셀 바이트 생성 헬퍼"""
    df = pd.DataFrame(data, columns=columns)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


# ─── 헤더 감지 테스트 ───────────────────────────

class TestHeaderDetection:
    def test_korean_headers(self):
        columns = ["활동명", "여권명", "국적"]
        mapping = _detect_header_map(columns)
        assert mapping["활동명"] == "model_name"
        assert mapping["여권명"] == "passport_name"
        assert mapping["국적"] == "nationality"

    def test_english_headers(self):
        columns = ["Stage Name", "Passport Name", "Nationality"]
        mapping = _detect_header_map(columns)
        assert mapping["Stage Name"] == "model_name"
        assert mapping["Passport Name"] == "passport_name"

    def test_unknown_headers_ignored(self):
        columns = ["활동명", "알수없는컬럼", "여권명"]
        mapping = _detect_header_map(columns)
        assert "알수없는컬럼" not in mapping
        assert len(mapping) == 2


# ─── 날짜 파싱 테스트 ───────────────────────────

class TestDateParsing:
    def test_iso_format(self):
        assert _parse_date("2026-04-01") == "2026-04-01"

    def test_slash_format(self):
        assert _parse_date("2026/04/01") == "2026-04-01"

    def test_dot_format(self):
        assert _parse_date("2026.04.01") == "2026-04-01"

    def test_date_object(self):
        assert _parse_date(date(2026, 4, 1)) == "2026-04-01"

    def test_none_value(self):
        assert _parse_date(None) is None

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_invalid_date(self):
        assert _parse_date("not-a-date") is None


# ─── 숫자 파싱 테스트 ───────────────────────────

class TestNumericParsing:
    def test_integer(self):
        assert _parse_numeric(175) == 175.0

    def test_float(self):
        assert _parse_numeric(82.5) == 82.5

    def test_string_number(self):
        assert _parse_numeric("175") == 175.0

    def test_none(self):
        assert _parse_numeric(None) is None

    def test_invalid(self):
        assert _parse_numeric("abc") is None


# ─── 엑셀 파싱 테스트 ───────────────────────────

class TestParseExcel:
    def test_valid_korean_excel(self):
        data = [
            ["Jane Doe", "JANE DOE", "2000-01-15", "US", "Female",
             175, 82, 60, 88, "250", "IMG Models",
             "2026-04-01", "2026-06-30", 5000, 20,
             "접수 전", "2026-04-01", "2026-06-30", "테스트"],
        ]
        columns = [
            "활동명", "여권명", "생년월일", "국적", "성별",
            "키(cm)", "가슴", "허리", "힙", "신발사이즈", "마더에이전시",
            "계약시작일", "계약종료일", "개런티(USD)", "MAC비율(%)",
            "비자상태", "입국예정일", "출국예정일", "비고",
        ]
        excel_bytes = _make_excel_bytes(data, columns)
        df, errors = parse_excel(excel_bytes)

        assert df is not None
        assert len(df) == 1
        assert "model_name" in df.columns
        assert df.iloc[0]["model_name"] == "Jane Doe"
        # 비자 상태 매핑 확인
        assert df.iloc[0]["visa_status"] == "pending"

    def test_missing_required_field(self):
        data = [
            ["", "JANE DOE", "US"],
        ]
        columns = ["활동명", "여권명", "국적"]
        excel_bytes = _make_excel_bytes(data, columns)
        df, errors = parse_excel(excel_bytes)

        # 활동명 누락 에러
        assert any(e["field"] == "model_name" for e in errors)

    def test_invalid_gender(self):
        data = [
            ["Jane", "JANE", "InvalidGender"],
        ]
        columns = ["활동명", "여권명", "성별"]
        excel_bytes = _make_excel_bytes(data, columns)
        df, errors = parse_excel(excel_bytes)

        assert any(e["field"] == "gender" for e in errors)

    def test_gender_mapping(self):
        data = [
            ["Jane", "JANE", "여"],
        ]
        columns = ["활동명", "여권명", "성별"]
        excel_bytes = _make_excel_bytes(data, columns)
        df, errors = parse_excel(excel_bytes)

        # "여" → "Female" 자동 매핑
        gender_errors = [e for e in errors if e["field"] == "gender"]
        assert len(gender_errors) == 0
        assert df.iloc[0]["gender"] == "Female"

    def test_empty_rows_removed(self):
        data = [
            ["Jane", "JANE DOE"],
            [None, None],
        ]
        columns = ["활동명", "여권명"]
        excel_bytes = _make_excel_bytes(data, columns)
        df, errors = parse_excel(excel_bytes)

        assert len(df) == 1

    def test_empty_file(self):
        df_empty = pd.DataFrame()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_empty.to_excel(writer, index=False)
        df, errors = parse_excel(buffer.getvalue())

        assert len(errors) > 0


# ─── DB 레코드 변환 테스트 ──────────────────────

class TestDataframeToDbRecords:
    def test_basic_conversion(self):
        df = pd.DataFrame([{
            "model_name": "Jane Doe",
            "passport_name": "JANE DOE",
            "nationality": "US",
            "height": 175.0,
            "date_of_birth": "2000-01-15",
        }])
        records = dataframe_to_db_records(df)

        assert len(records) == 1
        assert records[0]["model_name"] == "Jane Doe"
        assert records[0]["height"] == 175.0
        assert records[0]["date_of_birth"] == "2000-01-15"

    def test_skips_rows_without_required_fields(self):
        df = pd.DataFrame([{
            "model_name": "",
            "passport_name": "JANE DOE",
        }])
        records = dataframe_to_db_records(df)

        assert len(records) == 0


# ─── 템플릿 생성 테스트 ─────────────────────────

class TestGenerateTemplate:
    def test_korean_template(self):
        tmpl_bytes, filename = generate_upload_template("ko")
        assert filename == "model_upload_template_ko.xlsx"
        assert len(tmpl_bytes) > 0

        # 생성된 템플릿이 파싱 가능한지 확인
        df = pd.read_excel(io.BytesIO(tmpl_bytes))
        assert "활동명" in df.columns
        assert len(df) == 1  # 예시 데이터 1행

    def test_english_template(self):
        tmpl_bytes, filename = generate_upload_template("en")
        assert filename == "model_upload_template_en.xlsx"

        df = pd.read_excel(io.BytesIO(tmpl_bytes))
        assert "Stage Name" in df.columns

    def test_template_roundtrip(self):
        """템플릿 생성 → 파싱 라운드트립 테스트"""
        tmpl_bytes, _ = generate_upload_template("ko")
        df, errors = parse_excel(tmpl_bytes)

        assert len(df) == 1
        # 심각한 에러 없이 파싱 성공
        fatal_errors = [e for e in errors if e["row"] == 0]
        assert len(fatal_errors) == 0
