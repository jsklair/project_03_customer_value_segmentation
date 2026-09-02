-- Project 03: Customer Value & Retention Segmentation
-- Reconcile the SQLite transaction layer against the validated pandas
-- cleaning output before building invoice- or customer-level measures.

-- 1. Overall source dimensions
SELECT
    COUNT(*) AS row_count
FROM classified_transactions;


-- 2. Analytical-period separation
-- The behavioural period will be used for segment construction.
-- The validation period must remain held out from those definitions.
SELECT
    analysis_period,
    COUNT(*) AS row_count
FROM classified_transactions
GROUP BY analysis_period
ORDER BY analysis_period;


-- 3. Transaction-class reconciliation
-- This checks that the cleaning classifications reached SQLite without
-- changing their row counts or signed monetary treatment.
SELECT
    transaction_class,
    COUNT(*) AS row_count,
    ROUND(SUM(raw_line_value), 2) AS raw_line_value,
    ROUND(SUM(classified_net_sales), 2) AS classified_net_sales,
    ROUND(SUM(observed_net_sales), 2) AS observed_net_sales
FROM classified_transactions
GROUP BY transaction_class
ORDER BY row_count DESC;


-- 4. Customer-identification coverage
-- Transactions without a Customer ID remain in the source for
-- reconciliation but cannot contribute to customer-level measures.
SELECT
    CASE
        WHEN customer_id_clean IS NULL THEN 'missing_customer_id'
        ELSE 'identified_customer'
    END AS customer_status,
    COUNT(*) AS row_count,
    ROUND(SUM(classified_net_sales), 2) AS classified_net_sales,
    ROUND(SUM(observed_net_sales), 2) AS observed_net_sales
FROM classified_transactions
GROUP BY customer_status
ORDER BY customer_status;


-- 5. Positive classified value excluded from customer attribution
-- This reproduces the key cleaning-stage limitation reported publicly:
-- around 15% of positive classified value cannot be attributed to a
-- known customer.
WITH positive_value AS (
    SELECT
        SUM(
            CASE
                WHEN classified_net_sales > 0
                THEN classified_net_sales
                ELSE 0
            END
        ) AS total_positive_value,

        SUM(
            CASE
                WHEN classified_net_sales > 0
                     AND customer_id_clean IS NULL
                THEN classified_net_sales
                ELSE 0
            END
        ) AS unidentified_positive_value
    FROM classified_transactions
)
SELECT
    ROUND(total_positive_value, 2) AS total_positive_value,
    ROUND(unidentified_positive_value, 2) AS unidentified_positive_value,
    ROUND(
        100.0 * unidentified_positive_value / total_positive_value,
        1
    ) AS unidentified_positive_share_pct
FROM positive_value;


-- 6. Behavioural-window population
-- This establishes the transaction and identifiable-customer population
-- available at the 31 May 2011 snapshot.
SELECT
    COUNT(*) AS behavioural_rows,
    COUNT(DISTINCT customer_id_clean) AS identifiable_customers,
    COUNT(DISTINCT invoice_clean) AS invoices
FROM classified_transactions
WHERE analysis_period = 'behavioural';


-- 7. Validation-window population
-- These records are reserved for later held-out validation and must not
-- influence the snapshot segmentation.
SELECT
    COUNT(*) AS validation_rows,
    COUNT(DISTINCT customer_id_clean) AS identifiable_customers,
    COUNT(DISTINCT invoice_clean) AS invoices
FROM classified_transactions
WHERE analysis_period = 'validation';

-- 8. SQLite transaction-table schema
-- Inspect the exact fields and SQLite data types before defining
-- invoice-level aggregation logic.
PRAGMA table_info(classified_transactions);