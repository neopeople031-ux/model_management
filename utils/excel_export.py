"""
엑셀 다운로드 유틸리티

Pandas DataFrame을 엑셀(.xlsx) 파일로 변환합니다.
"""
import io
import pandas as pd
from datetime import datetime


def dataframe_to_excel(
    df: pd.DataFrame,
    sheet_name: str = "Sheet1",
    filename_prefix: str = "export",
) -> tuple[bytes, str]:
    """
    DataFrame을 엑셀 바이트로 변환합니다.

    Args:
        df: 변환할 DataFrame
        sheet_name: 시트 이름
        filename_prefix: 파일명 접두사

    Returns:
        tuple: (엑셀 바이트 데이터, 추천 파일명)
    """
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

        # 컬럼 너비 자동 조정
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col)),
            )
            adjusted_width = min(max_length + 4, 40)
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=idx + 1).column_letter
            ].width = adjusted_width

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.xlsx"

    return buffer.getvalue(), filename


def models_to_dataframe(models: list[dict], lang: str = "ko") -> pd.DataFrame:
    """모델 리스트를 DataFrame으로 변환합니다."""
    if lang == "ko":
        columns_map = {
            "model_name": "활동명",
            "passport_name": "여권명",
            "nationality": "국적",
            "gender": "성별",
            "height": "키(cm)",
            "bust": "가슴",
            "waist": "허리",
            "hips": "힙",
            "shoe_size": "신발사이즈",
            "mother_agency": "마더에이전시",
            "contract_start": "계약시작일",
            "contract_end": "계약종료일",
            "visa_status": "비자상태",
            "status": "모델상태",
        }
    else:
        columns_map = {
            "model_name": "Stage Name",
            "passport_name": "Passport Name",
            "nationality": "Nationality",
            "gender": "Gender",
            "height": "Height(cm)",
            "bust": "Bust",
            "waist": "Waist",
            "hips": "Hips",
            "shoe_size": "Shoe Size",
            "mother_agency": "Mother Agency",
            "contract_start": "Contract Start",
            "contract_end": "Contract End",
            "visa_status": "Visa Status",
            "status": "Status",
        }

    df = pd.DataFrame(models)

    # 컬럼명 매핑 (존재하는 컬럼만)
    rename_map = {k: v for k, v in columns_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # 표시할 컬럼만 선택
    display_cols = [v for k, v in columns_map.items() if v in df.columns]
    if display_cols:
        df = df[display_cols]

    return df


def generate_upload_template(lang: str = "ko") -> tuple[bytes, str]:
    """
    모델 대량 업로드용 빈 엑셀 템플릿을 생성합니다.

    Args:
        lang: 언어 코드 ("ko" 또는 "en")

    Returns:
        tuple: (엑셀 바이트 데이터, 파일명)
    """
    if lang == "ko":
        headers = [
            "활동명", "여권명", "생년월일", "국적", "성별",
            "키(cm)", "가슴", "허리", "힙", "신발사이즈",
            "마더에이전시", "계약시작일", "계약종료일",
            "개런티(USD)", "MAC비율(%)",
            "비자상태", "입국예정일", "출국예정일", "비고",
        ]
        example = [
            "Jane Doe", "JANE DOE", "2000-01-15", "US", "Female",
            175, 82, 60, 88, "250",
            "IMG Models", "2026-04-01", "2026-06-30",
            5000, 20,
            "접수 전", "2026-04-01", "2026-06-30", "첫 입국",
        ]
    else:
        headers = [
            "Stage Name", "Passport Name", "Date of Birth", "Nationality", "Gender",
            "Height (cm)", "Bust", "Waist", "Hips", "Shoe Size",
            "Mother Agency", "Contract Start", "Contract End",
            "Guarantee (USD)", "MAC Rate (%)",
            "Visa Status", "Arrival Date", "Departure Date", "Notes",
        ]
        example = [
            "Jane Doe", "JANE DOE", "2000-01-15", "US", "Female",
            175, 82, 60, 88, "250",
            "IMG Models", "2026-04-01", "2026-06-30",
            5000, 20,
            "pending", "2026-04-01", "2026-06-30", "First visit",
        ]

    df = pd.DataFrame([example], columns=headers)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Models", index=False)

        worksheet = writer.sheets["Models"]
        for idx, col in enumerate(headers):
            max_length = max(len(str(col)), len(str(example[idx])) if idx < len(example) else 0)
            adjusted_width = min(max_length + 4, 30)
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=idx + 1).column_letter
            ].width = adjusted_width

    filename = f"model_upload_template_{lang}.xlsx"
    return buffer.getvalue(), filename
