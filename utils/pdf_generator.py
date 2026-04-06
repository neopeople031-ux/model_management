"""
PDF 생성 모듈

- 모델 프로필 제안서 PDF
- 정산 영수증 PDF
- MAC 대리수령 위임장 PDF
"""
import io
from datetime import datetime
from fpdf import FPDF


class ModelProposalPDF(FPDF):
    """모델 프로필 제안서 PDF"""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "MODEL PROFILE", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def add_model_page(self, model: dict):
        """모델 한 명의 프로필 페이지를 추가합니다."""
        self.add_page()
        self.alias_nb_pages()

        # 모델명
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(0, 0, 0)
        self.cell(0, 12, model.get("model_name", ""), ln=True)

        # 여권명
        self.set_font("Helvetica", "", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, model.get("passport_name", ""), ln=True)
        self.ln(8)

        # 프로필 사진 (URL이 있는 경우 - 로컬 파일 경로로 변환 필요)
        photo_url = model.get("profile_photo_url")
        if photo_url and not photo_url.startswith("http"):
            try:
                self.image(photo_url, x=10, y=self.get_y(), w=60)
                self.set_y(self.get_y() + 80)
            except Exception:
                pass

        # 기본 정보 테이블
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(245, 245, 245)

        info_items = [
            ("Nationality", model.get("nationality", "")),
            ("Date of Birth", model.get("date_of_birth", "")),
            ("Height", f"{model.get('height', '')} cm"),
            ("Bust", str(model.get("bust", ""))),
            ("Waist", str(model.get("waist", ""))),
            ("Hips", str(model.get("hips", ""))),
            ("Shoe Size", str(model.get("shoe_size", ""))),
            ("Mother Agency", model.get("mother_agency", "")),
        ]

        for label, value in info_items:
            self.set_font("Helvetica", "B", 10)
            self.cell(50, 8, label, border=1, fill=True)
            self.set_font("Helvetica", "", 10)
            self.cell(0, 8, str(value), border=1, ln=True)


class SettlementReceiptPDF(FPDF):
    """정산 영수증 PDF"""

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "SETTLEMENT RECEIPT", ln=True, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
        self.set_text_color(0, 0, 0)
        self.ln(5)

    def add_settlement(self, model: dict, settlement: dict, spending_items: list):
        """정산 내역 페이지 생성"""
        self.add_page()

        # 모델 정보
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, f"Model: {model.get('model_name', '')}", ln=True)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"Passport Name: {model.get('passport_name', '')}", ln=True)
        self.cell(0, 6, f"Period: {settlement.get('period_start', '')} ~ {settlement.get('period_end', '')}", ln=True)
        self.ln(8)

        # Earning
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, "EARNING SUMMARY", ln=True, fill=True)
        self.set_font("Helvetica", "", 10)
        self.cell(120, 7, "Total Earning (USD)", border=1)
        self.cell(0, 7, f"${settlement.get('total_earning', 0):,.2f}", border=1, ln=True, align="R")

        # MAC
        mac_rate = settlement.get("mac_rate", 0)
        self.cell(120, 7, f"Mother Agency Commission ({mac_rate}%)", border=1)
        self.cell(0, 7, f"-${settlement.get('mac_amount', 0):,.2f}", border=1, ln=True, align="R")
        self.ln(5)

        # Spending
        if spending_items:
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 8, "SPENDING DETAILS", ln=True, fill=True)
            self.set_font("Helvetica", "", 10)

            for item in spending_items:
                self.cell(40, 7, item.get("category", ""), border=1)
                self.cell(80, 7, item.get("description", ""), border=1)
                self.cell(0, 7, f"-${item.get('amount', 0):,.2f}", border=1, ln=True, align="R")

            self.cell(120, 7, "Total Spending", border=1)
            self.cell(0, 7, f"-${settlement.get('total_spending', 0):,.2f}", border=1, ln=True, align="R")
            self.ln(5)

        # 최종 금액
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.cell(120, 10, "NET AMOUNT (USD)", fill=True)
        self.cell(0, 10, f"${settlement.get('net_amount', 0):,.2f}", fill=True, ln=True, align="R")
        self.set_text_color(0, 0, 0)


def generate_proposal_pdf(models: list[dict]) -> bytes:
    """모델 프로필 제안서 PDF를 생성합니다."""
    pdf = ModelProposalPDF()
    for model in models:
        pdf.add_model_page(model)
    return pdf.output()


def generate_receipt_pdf(model: dict, settlement: dict, spending_items: list) -> bytes:
    """정산 영수증 PDF를 생성합니다."""
    pdf = SettlementReceiptPDF()
    pdf.add_settlement(model, settlement, spending_items)
    return pdf.output()


def generate_delegation_pdf(model: dict, settlement: dict) -> bytes:
    """MAC 대리수령 위임장 PDF를 생성합니다."""
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 15, "DELEGATION OF AUTHORITY", ln=True, align="C")
    pdf.cell(0, 10, "FOR AGENCY COMMISSION RECEIPT", ln=True, align="C")
    pdf.ln(15)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, (
        f"This document serves to authorize the collection of agency commission "
        f"on behalf of {model.get('mother_agency', '[Mother Agency]')} "
        f"for the model {model.get('passport_name', '[Model Name]')}."
    ))
    pdf.ln(10)

    # 금액 정보
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(80, 8, "Total Earning:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"${settlement.get('total_earning', 0):,.2f}", ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(80, 8, "Commission Amount:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"${settlement.get('mac_amount', 0):,.2f}", ln=True)
    pdf.ln(20)

    # 서명란
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 8, "____________________________")
    pdf.cell(0, 8, "____________________________", ln=True)
    pdf.cell(90, 6, "Model Signature")
    pdf.cell(0, 6, "Date", ln=True)
    pdf.ln(10)
    pdf.cell(90, 8, "____________________________")
    pdf.cell(0, 8, "____________________________", ln=True)
    pdf.cell(90, 6, "Agency Representative")
    pdf.cell(0, 6, "Date", ln=True)

    return pdf.output()
