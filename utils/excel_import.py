"""
엑셀 대량 업로드 유틸리티

엑셀 파일을 파싱하여 models 테이블에 삽입할 수 있는 형태로 변환합니다.
"""
import io
import pandas as pd
from datetime import date, datetime

# 한국어 헤더 → DB 컬럼 매핑
KO_HEADER_MAP = {
    "활동명": "model_name",
    "여권명": "passport_name",
    "생년월일": "date_of_birth",
    "국적": "nationality",
    "성별": "gender",
    "키(cm)": "height",
    "키 (cm)": "height",
    "가슴": "bust",
    "허리": "waist",
    "힙": "hips",
    "신발사이즈": "shoe_size",
    "신발 사이즈": "shoe_size",
    "마더에이전시": "mother_agency",
    "마더 에이전시": "mother_agency",
    "계약시작일": "contract_start",
    "계약 시작일": "contract_start",
    "계약종료일": "contract_end",
    "계약 종료일": "contract_end",
    "개런티(USD)": "guarantee_amount",
    "개런티 (USD)": "guarantee_amount",
    "MAC비율(%)": "mac_rate",
    "MAC 비율 (%)": "mac_rate",
    "비자상태": "visa_status",
    "비자 상태": "visa_status",
    "입국예정일": "arrival_date",
    "입국 예정일": "arrival_date",
    "출국예정일": "departure_date",
    "출국 예정일": "departure_date",
    "비고": "notes",
}

# 영어 헤더 → DB 컬럼 매핑
EN_HEADER_MAP = {
    "Stage Name": "model_name",
    "Passport Name": "passport_name",
    "Date of Birth": "date_of_birth",
    "Nationality": "nationality",
    "Gender": "gender",
    "Height(cm)": "height",
    "Height (cm)": "height",
    "Bust": "bust",
    "Waist": "waist",
    "Hips": "hips",
    "Shoe Size": "shoe_size",
    "Mother Agency": "mother_agency",
    "Contract Start": "contract_start",
    "Contract End": "contract_end",
    "Guarantee(USD)": "guarantee_amount",
    "Guarantee (USD)": "guarantee_amount",
    "MAC Rate(%)": "mac_rate",
    "MAC Rate (%)": "mac_rate",
    "Visa Status": "visa_status",
    "Arrival Date": "arrival_date",
    "Departure Date": "departure_date",
    "Notes": "notes",
}

# 필수 필드
REQUIRED_FIELDS = ["model_name", "passport_name"]

# 날짜 필드
DATE_FIELDS = ["date_of_birth", "contract_start", "contract_end", "arrival_date", "departure_date"]

# 숫자 필드
NUMERIC_FIELDS = ["height", "bust", "waist", "hips", "guarantee_amount", "mac_rate"]

# 유효한 ENUM 값
VALID_GENDER = ["Male", "Female"]
VALID_VISA_STATUS = ["pending", "applied", "approved", "expired"]

# 비자 상태 한국어 → ENUM 매핑
VISA_STATUS_MAP = {
    "접수 전": "pending",
    "접수전": "pending",
    "접수 완료": "applied",
    "접수완료": "applied",
    "승인": "approved",
    "만료": "expired",
    "pending": "pending",
    "applied": "applied",
    "approved": "approved",
    "expired": "expired",
}


def _detect_header_map(columns: list[str]) -> dict[str, str]:
    """컬럼 헤더를 보고 한국어/영어 매핑을 자동 감지합니다."""
    combined = {**KO_HEADER_MAP, **EN_HEADER_MAP}
    mapping = {}
    for col in columns:
        col_stripped = col.strip()
        if col_stripped in combined:
            mapping[col_stripped] = combined[col_stripped]
        elif col_stripped.lower() in {k.lower(): v for k, v in combined.items()}:
            # 대소문자 무시 매핑
            lower_map = {k.lower(): v for k, v in combined.items()}
            mapping[col_stripped] = lower_map[col_stripped.lower()]
    return mapping


def _parse_date(value) -> str | None:
    """다양한 날짜 형식을 ISO 포맷으로 변환합니다."""
    if pd.isna(value) or value == "" or value is None:
        return None

    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")

    value_str = str(value).strip()
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(value_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def _parse_numeric(value) -> float | None:
    """숫자 값을 파싱합니다."""
    if pd.isna(value) or value == "" or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_excel(file_bytes: bytes) -> tuple[pd.DataFrame, list[dict]]:
    """
    업로드된 엑셀 파일을 파싱합니다.

    Returns:
        tuple: (정제된 DataFrame, 에러 리스트)
        에러 형식: {"row": int, "field": str, "message": str}
    """
    errors: list[dict] = []

    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as e:
        errors.append({"row": 0, "field": "", "message": f"엑셀 파일 읽기 실패: {e}"})
        return pd.DataFrame(), errors

    if df.empty:
        errors.append({"row": 0, "field": "", "message": "엑셀 파일에 데이터가 없습니다."})
        return pd.DataFrame(), errors

    # 빈 행 제거
    df = df.dropna(how="all").reset_index(drop=True)

    if df.empty:
        errors.append({"row": 0, "field": "", "message": "유효한 데이터 행이 없습니다."})
        return pd.DataFrame(), errors

    # 헤더 매핑
    header_map = _detect_header_map(list(df.columns))
    if not header_map:
        errors.append({"row": 0, "field": "", "message": "인식 가능한 컬럼 헤더가 없습니다. 템플릿을 확인하세요."})
        return pd.DataFrame(), errors

    df = df.rename(columns=header_map)

    # 매핑된 컬럼만 유지
    valid_cols = [c for c in df.columns if c in set(header_map.values())]
    df = df[valid_cols]

    # 행별 유효성 검증
    for idx, row in df.iterrows():
        row_num = idx + 2  # 엑셀 행 번호 (헤더=1행)

        # 필수 필드 검증
        for field in REQUIRED_FIELDS:
            if field in df.columns:
                val = row.get(field)
                if pd.isna(val) or str(val).strip() == "":
                    errors.append({"row": row_num, "field": field, "message": f"필수 항목 '{field}'이(가) 비어 있습니다."})

        # 성별 검증
        if "gender" in df.columns:
            gender = row.get("gender")
            if not pd.isna(gender) and str(gender).strip() != "":
                gender_str = str(gender).strip()
                if gender_str not in VALID_GENDER:
                    # 약어 / 한국어 매핑 시도
                    gender_map = {"M": "Male", "F": "Female", "남": "Male", "여": "Female", "남성": "Male", "여성": "Female", "male": "Male", "female": "Female"}
                    mapped = gender_map.get(gender_str)
                    if mapped:
                        df.at[idx, "gender"] = mapped
                    else:
                        errors.append({"row": row_num, "field": "gender", "message": f"성별 값 '{gender_str}'이 올바르지 않습니다. (Male/Female)"})

        # 비자 상태 매핑
        if "visa_status" in df.columns:
            visa = row.get("visa_status")
            if not pd.isna(visa) and str(visa).strip() != "":
                visa_str = str(visa).strip()
                mapped = VISA_STATUS_MAP.get(visa_str)
                if mapped:
                    df.at[idx, "visa_status"] = mapped
                else:
                    errors.append({"row": row_num, "field": "visa_status", "message": f"비자 상태 '{visa_str}'이 올바르지 않습니다."})

        # 날짜 필드 검증
        for field in DATE_FIELDS:
            if field in df.columns:
                val = row.get(field)
                if not pd.isna(val) and str(val).strip() != "":
                    parsed = _parse_date(val)
                    if parsed is None:
                        errors.append({"row": row_num, "field": field, "message": f"날짜 형식이 올바르지 않습니다: '{val}'"})
                    else:
                        df.at[idx, field] = parsed

        # 숫자 필드 검증
        for field in NUMERIC_FIELDS:
            if field in df.columns:
                val = row.get(field)
                if not pd.isna(val) and str(val).strip() != "":
                    parsed = _parse_numeric(val)
                    if parsed is None:
                        errors.append({"row": row_num, "field": field, "message": f"숫자 형식이 올바르지 않습니다: '{val}'"})
                    else:
                        df.at[idx, field] = parsed

    return df, errors


def dataframe_to_db_records(df: pd.DataFrame) -> list[dict]:
    """
    검증된 DataFrame을 Supabase insert용 dict 리스트로 변환합니다.
    """
    records = []

    for _, row in df.iterrows():
        record = {}

        for col in df.columns:
            val = row[col]

            if pd.isna(val) or (isinstance(val, str) and val.strip() == ""):
                # 필수 필드가 아니면 None
                if col in REQUIRED_FIELDS:
                    continue
                record[col] = None
                continue

            if col in DATE_FIELDS:
                record[col] = _parse_date(val)
            elif col in NUMERIC_FIELDS:
                record[col] = _parse_numeric(val)
            else:
                record[col] = str(val).strip()

        # 필수 필드가 있는 경우에만 추가
        if all(record.get(f) for f in REQUIRED_FIELDS):
            records.append(record)

    return records
