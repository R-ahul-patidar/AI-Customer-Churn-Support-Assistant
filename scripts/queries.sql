-- ==============================================================================
-- AI Customer Churn & Support Assistant — Required SQL Queries
-- Assessment Section 1: Dataset & SQL (15 Marks)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Top 10 customers by monthly spend
-- Identifies the highest value accounts in the customer base.
-- ------------------------------------------------------------------------------
SELECT 
    customer_id,
    name,
    email,
    plan,
    monthly_spend,
    tenure_months,
    churn
FROM customers
ORDER BY monthly_spend DESC
LIMIT 10;


-- ------------------------------------------------------------------------------
-- 2. Average spend by subscription plan
-- Summarizes customer count and mean monthly revenue per plan tier.
-- ------------------------------------------------------------------------------
SELECT 
    plan,
    ROUND(AVG(monthly_spend), 2) AS avg_monthly_spend,
    COUNT(customer_id) AS total_customers
FROM customers
GROUP BY plan
ORDER BY avg_monthly_spend DESC;


-- ------------------------------------------------------------------------------
-- 3. Customers with more than 5 support tickets
-- Identifies accounts with high support burden (leading churn indicator).
-- ------------------------------------------------------------------------------
SELECT 
    customer_id,
    name,
    email,
    plan,
    support_tickets,
    satisfaction_score,
    last_login_days,
    churn
FROM customers
WHERE support_tickets > 5
ORDER BY support_tickets DESC;


-- ------------------------------------------------------------------------------
-- 4. Churn rate by subscription plan
-- Calculates churn percentage per plan tier.
-- ------------------------------------------------------------------------------
SELECT 
    plan,
    COUNT(customer_id) AS total_customers,
    SUM(CASE WHEN churn = 1 THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(SUM(CASE WHEN churn = 1 THEN 1.0 ELSE 0.0 END) / COUNT(customer_id) * 100, 2) AS churn_rate_percent
FROM customers
GROUP BY plan
ORDER BY churn_rate_percent DESC;


-- ------------------------------------------------------------------------------
-- 5. Customers with high churn-risk indicators
-- Filters active (non-churned) customers meeting at least 2 risk conditions:
--   - support_tickets > 5
--   - satisfaction_score < 5.0
--   - last_login_days > 30
-- Ordered by lowest satisfaction score and highest ticket count.
-- ------------------------------------------------------------------------------
SELECT 
    customer_id,
    name,
    email,
    plan,
    monthly_spend,
    support_tickets,
    satisfaction_score,
    last_login_days,
    (
        (CASE WHEN support_tickets > 5 THEN 1 ELSE 0 END) +
        (CASE WHEN satisfaction_score < 5.0 THEN 1 ELSE 0 END) +
        (CASE WHEN last_login_days > 30 THEN 1 ELSE 0 END)
    ) AS risk_factor_count
FROM customers
WHERE churn = 0
  AND (
      (CASE WHEN support_tickets > 5 THEN 1 ELSE 0 END) +
      (CASE WHEN satisfaction_score < 5.0 THEN 1 ELSE 0 END) +
      (CASE WHEN last_login_days > 30 THEN 1 ELSE 0 END)
  ) >= 2
ORDER BY satisfaction_score ASC, support_tickets DESC;
