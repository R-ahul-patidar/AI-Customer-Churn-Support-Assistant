-- ==============================================================================
-- AI Customer Churn & Support Assistant — Database Schema (SQLite / PostgreSQL)
-- Assessment Deliverable: Database setup / schema script
-- ==============================================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    age INTEGER NOT NULL CHECK (age >= 18),
    plan VARCHAR(50) NOT NULL CHECK (plan IN ('Basic', 'Standard', 'Premium')),
    monthly_spend REAL NOT NULL CHECK (monthly_spend >= 0),
    tenure_months INTEGER NOT NULL CHECK (tenure_months >= 0),
    support_tickets INTEGER NOT NULL DEFAULT 0 CHECK (support_tickets >= 0),
    last_login_days INTEGER NOT NULL CHECK (last_login_days >= 0),
    satisfaction_score REAL NOT NULL CHECK (satisfaction_score >= 1.0 AND satisfaction_score <= 10.0),
    churn BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_customers_plan ON customers(plan);
CREATE INDEX IF NOT EXISTS idx_customers_churn ON customers(churn);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_monthly_spend ON customers(monthly_spend);
