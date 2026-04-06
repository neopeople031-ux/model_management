-- =============================================================
-- Model Management System - Supabase 마이그레이션 스크립트
-- =============================================================
-- Supabase SQL Editor에서 실행하세요.
-- =============================================================

-- 1. ENUM 타입 생성
CREATE TYPE user_role AS ENUM ('ceo', 'team_lead', 'booker', 'marketing', 'accounting');
CREATE TYPE visa_status AS ENUM ('pending', 'applied', 'approved', 'expired');
CREATE TYPE model_status AS ENUM ('pre_arrival', 'active', 'departed', 'contract_ended');
CREATE TYPE schedule_status AS ENUM ('scheduled', 'in_progress', 'completed', 'cancelled');
CREATE TYPE work_type AS ENUM ('hours_only', 'half', 'half_plus', 'full', 'full_plus');
CREATE TYPE approval_status AS ENUM ('draft', 'submitted', 'first_approved', 'final_confirmed');
CREATE TYPE user_approval_status AS ENUM ('pending', 'approved', 'rejected');

-- 2. users 테이블 (Google OAuth + 관리자 승인)
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'booker',
    approval_status user_approval_status NOT NULL DEFAULT 'pending',
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. models 테이블
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    passport_name TEXT NOT NULL,
    date_of_birth DATE,
    nationality TEXT,
    gender TEXT,
    height NUMERIC,
    bust NUMERIC,
    waist NUMERIC,
    hips NUMERIC,
    shoe_size TEXT,
    mother_agency TEXT,
    profile_photo_url TEXT,
    portfolio_urls TEXT[],
    contract_start DATE,
    contract_end DATE,
    guarantee_amount NUMERIC DEFAULT 0,
    mac_rate NUMERIC DEFAULT 0,
    visa_status visa_status DEFAULT 'pending',
    arrival_date DATE,
    departure_date DATE,
    status model_status DEFAULT 'pre_arrival',
    assigned_booker_id UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. schedules 테이블
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    google_event_id TEXT,
    title TEXT,
    client_name TEXT,
    schedule_date DATE NOT NULL,
    hmu_start_time TIMESTAMPTZ,
    shoot_start_time TIMESTAMPTZ,
    shoot_end_time TIMESTAMPTZ,
    total_hours NUMERIC,
    work_type work_type,
    work_type_display TEXT,
    earning_usd NUMERIC DEFAULT 0,
    status schedule_status DEFAULT 'scheduled',
    booker_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. settlements 테이블
CREATE TABLE settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_earning NUMERIC DEFAULT 0,
    mac_rate NUMERIC DEFAULT 0,
    mac_amount NUMERIC DEFAULT 0,
    total_spending NUMERIC DEFAULT 0,
    net_amount NUMERIC DEFAULT 0,
    approval_status approval_status DEFAULT 'draft',
    submitted_by UUID REFERENCES users(id),
    first_approved_by UUID REFERENCES users(id),
    final_confirmed_by UUID REFERENCES users(id),
    submitted_at TIMESTAMPTZ,
    first_approved_at TIMESTAMPTZ,
    final_confirmed_at TIMESTAMPTZ,
    pdf_receipt_url TEXT,
    pdf_delegation_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. spending_items 테이블
CREATE TABLE spending_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_id UUID NOT NULL REFERENCES settlements(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    description TEXT,
    amount NUMERIC NOT NULL DEFAULT 0,
    date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- 인덱스 생성
-- =============================================================
CREATE INDEX idx_models_status ON models(status);
CREATE INDEX idx_models_nationality ON models(nationality);
CREATE INDEX idx_models_booker ON models(assigned_booker_id);
CREATE INDEX idx_models_visa ON models(visa_status);
CREATE INDEX idx_schedules_model ON schedules(model_id);
CREATE INDEX idx_schedules_date ON schedules(schedule_date);
CREATE INDEX idx_schedules_status ON schedules(status);
CREATE INDEX idx_schedules_booker ON schedules(booker_id);
CREATE INDEX idx_settlements_model ON settlements(model_id);
CREATE INDEX idx_settlements_status ON settlements(approval_status);
CREATE INDEX idx_spending_settlement ON spending_items(settlement_id);

-- =============================================================
-- updated_at 자동 갱신 트리거
-- =============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER models_updated_at
    BEFORE UPDATE ON models
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER schedules_updated_at
    BEFORE UPDATE ON schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================
-- RLS (Row Level Security) 정책
-- =============================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE models ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE spending_items ENABLE ROW LEVEL SECURITY;

-- 인증된 사용자 전원 읽기 허용
CREATE POLICY "All authenticated users can read users"
    ON users FOR SELECT TO authenticated USING (true);

CREATE POLICY "All authenticated users can read models"
    ON models FOR SELECT TO authenticated USING (true);

CREATE POLICY "All authenticated users can read schedules"
    ON schedules FOR SELECT TO authenticated USING (true);

CREATE POLICY "All authenticated users can read settlements"
    ON settlements FOR SELECT TO authenticated USING (true);

CREATE POLICY "All authenticated users can read spending_items"
    ON spending_items FOR SELECT TO authenticated USING (true);

-- 쓰기 권한: 인증된 사용자
CREATE POLICY "Authenticated users can insert models"
    ON models FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Authenticated users can update models"
    ON models FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert schedules"
    ON schedules FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Authenticated users can update schedules"
    ON schedules FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert settlements"
    ON settlements FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Authenticated users can update settlements"
    ON settlements FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can insert spending_items"
    ON spending_items FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Authenticated users can update spending_items"
    ON spending_items FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Authenticated users can delete spending_items"
    ON spending_items FOR DELETE TO authenticated USING (true);

-- =============================================================
-- Storage 버킷 생성 (Supabase Dashboard에서 수동 생성 권장)
-- =============================================================
-- model-photos: 모델 프로필 사진
-- settlement-documents: 정산 PDF 문서
