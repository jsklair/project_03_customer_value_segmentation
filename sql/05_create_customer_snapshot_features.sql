-- Project 03: Customer Value & Retention Segmentation
-- Build and validate customer-level measures as at 31 May 2011.
--
-- Eligibility:
--   identifiable customers with at least one qualifying purchase before
--   or during the behavioural window.
--
-- The feature layer uses no information from the held-out validation period.


DROP VIEW IF EXISTS customer_snapshot_features;


CREATE VIEW customer_snapshot_features AS

WITH eligible_customers AS (

    -- A Customer ID alone is not enough for segmentation eligibility.
    -- Require evidence of at least one genuine qualifying purchase before
    -- the snapshot date, including the earlier observed history so that
    -- lapsed customers remain available for reactivation analysis.
    SELECT
        customer_id_clean
    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period IN ('pre_behavioural', 'behavioural')
        AND has_qualifying_activity = 1
    GROUP BY customer_id_clean
),

purchase_history AS (

    SELECT
        customer_id_clean,

        -- Use qualifying purchasing activity for first/last purchase timing.
        -- Returns and other financial adjustments must not artificially make
        -- a customer's purchasing activity appear more recent.
        MIN(
            CASE
                WHEN has_qualifying_activity = 1
                THEN invoice_timestamp
            END
        ) AS first_purchase_timestamp,

        MAX(
            CASE
                WHEN has_qualifying_activity = 1
                THEN invoice_timestamp
            END
        ) AS last_purchase_timestamp,

        SUM(
            CASE
                WHEN analysis_period = 'pre_behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS pre_behavioural_purchase_invoices,

        -- Purchase frequency is defined as distinct qualifying purchase
        -- invoices in the trailing 12-month behavioural window. Because
        -- invoice_summary already has one row per invoice, each qualifying
        -- row here represents one purchase occasion.
        SUM(
            CASE
                WHEN analysis_period = 'behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS purchase_frequency_12m,

        -- Active months captures repeat engagement across time rather than
        -- simply counting several orders made close together.
        COUNT(
            DISTINCT CASE
                WHEN analysis_period = 'behavioural'
                     AND has_qualifying_activity = 1
                THEN strftime('%Y-%m', invoice_timestamp)
            END
        ) AS active_months_12m,

        -- Observed net sales include the signed customer-attributable
        -- financial effects retained by the cleaning methodology, including
        -- returns and relevant customer financial lines.
        SUM(
            CASE
                WHEN analysis_period = 'behavioural'
                THEN observed_invoice_value
                ELSE 0
            END
        ) AS observed_net_sales_12m

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period IN ('pre_behavioural', 'behavioural')

    GROUP BY customer_id_clean
),

product_breadth AS (

    -- Product breadth must be counted across the customer's whole behavioural
    -- window, not summed from invoice-level distinct counts, because the same
    -- product may appear on several invoices.
    SELECT
        customer_id_clean,
        COUNT(DISTINCT stock_code_clean) AS product_breadth_12m

    FROM classified_transactions

    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'
        AND counts_in_product_breadth = 1

    GROUP BY customer_id_clean
)

SELECT
    eligible.customer_id_clean,

    history.first_purchase_timestamp,
    history.last_purchase_timestamp,

    -- Day-level recency is appropriate for this CRM segmentation. Using the
    -- purchase date means a purchase on the snapshot date has recency = 0.
    CAST(
        julianday('2011-05-31')
        - julianday(DATE(history.last_purchase_timestamp))
        AS INTEGER
    ) AS recency_days,

    -- This is observed tenure within the available transaction history, not
    -- necessarily the customer's true lifetime relationship with the retailer.
    CAST(
        julianday('2011-05-31')
        - julianday(DATE(history.first_purchase_timestamp))
        AS INTEGER
    ) AS observed_tenure_days,

    history.pre_behavioural_purchase_invoices,
    history.purchase_frequency_12m,
    history.active_months_12m,
    history.observed_net_sales_12m,

    COALESCE(
        breadth.product_breadth_12m,
        0
    ) AS product_breadth_12m,

    CASE
        WHEN history.purchase_frequency_12m > 0
        THEN 1
        ELSE 0
    END AS is_behavioural_purchaser,

    CASE
        WHEN history.pre_behavioural_purchase_invoices > 0
             AND history.purchase_frequency_12m = 0
        THEN 1
        ELSE 0
    END AS is_historical_only_purchaser

FROM eligible_customers AS eligible

INNER JOIN purchase_history AS history
    ON eligible.customer_id_clean = history.customer_id_clean

LEFT JOIN product_breadth AS breadth
    ON eligible.customer_id_clean = breadth.customer_id_clean;


-- 1. Confirm the final eligible snapshot population.
SELECT
    COUNT(*) AS eligible_customers,
    SUM(is_behavioural_purchaser) AS behavioural_purchasers,
    SUM(is_historical_only_purchaser) AS historical_only_purchasers
FROM customer_snapshot_features;


-- 2. Check that every eligible customer has valid purchase-history dates.
SELECT
    SUM(
        CASE
            WHEN first_purchase_timestamp IS NULL
            THEN 1 ELSE 0
        END
    ) AS missing_first_purchase,

    SUM(
        CASE
            WHEN last_purchase_timestamp IS NULL
            THEN 1 ELSE 0
        END
    ) AS missing_last_purchase
FROM customer_snapshot_features;


-- 3. Inspect the main feature ranges.
SELECT
    MIN(recency_days) AS min_recency_days,
    MAX(recency_days) AS max_recency_days,

    MIN(purchase_frequency_12m) AS min_frequency,
    MAX(purchase_frequency_12m) AS max_frequency,

    MIN(active_months_12m) AS min_active_months,
    MAX(active_months_12m) AS max_active_months,

    ROUND(MIN(observed_net_sales_12m), 2) AS min_observed_net_sales,
    ROUND(MAX(observed_net_sales_12m), 2) AS max_observed_net_sales,

    MIN(product_breadth_12m) AS min_product_breadth,
    MAX(product_breadth_12m) AS max_product_breadth
FROM customer_snapshot_features;


-- 4. Show recency separately for active and historical-only customers.
SELECT
    CASE
        WHEN is_behavioural_purchaser = 1
            THEN 'behavioural purchaser'
        ELSE 'historical-only purchaser'
    END AS customer_group,

    COUNT(*) AS customer_count,
    MIN(recency_days) AS minimum_recency_days,
    ROUND(AVG(recency_days), 1) AS average_recency_days,
    MAX(recency_days) AS maximum_recency_days

FROM customer_snapshot_features

GROUP BY customer_group
ORDER BY customer_group;


-- 5. Reconcile behavioural observed net sales for the eligible segmentation
-- population back to the transaction layer.
--
-- Identified Customer IDs with no qualifying purchase history are deliberately
-- excluded from segmentation. Their financial effects therefore should not
-- be included in this reconciliation.
WITH eligible_customers AS (

    SELECT
        customer_id_clean
    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period IN ('pre_behavioural', 'behavioural')
        AND has_qualifying_activity = 1
    GROUP BY customer_id_clean
)

SELECT
    ROUND(
        (
            SELECT SUM(observed_net_sales_12m)
            FROM customer_snapshot_features
        ),
        2
    ) AS customer_feature_observed_net_sales,

    ROUND(
        SUM(transactions.observed_net_sales),
        2
    ) AS eligible_transaction_observed_net_sales

FROM classified_transactions AS transactions

INNER JOIN eligible_customers AS eligible
    ON transactions.customer_id_clean = eligible.customer_id_clean

WHERE
    transactions.analysis_period = 'behavioural';