-- Supabase Schema for Infostock Crawler
-- 특징 테마 테이블
CREATE TABLE theme_issues (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collected_date DATE NOT NULL,
    theme_name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(collected_date, theme_name)
);

-- 특징 종목 / 상한가 급등 테이블
CREATE TABLE stock_issues (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collected_date DATE NOT NULL,
    category TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    stock_code TEXT,
    change_rate TEXT,
    description TEXT NOT NULL,
    limit_up_days INT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(collected_date, category, stock_code)
);

-- 인덱스
CREATE INDEX idx_theme_issues_date ON theme_issues(collected_date);
CREATE INDEX idx_stock_issues_date ON stock_issues(collected_date);
CREATE INDEX idx_stock_issues_category ON stock_issues(category);
CREATE INDEX idx_stock_issues_code ON stock_issues(stock_code);
