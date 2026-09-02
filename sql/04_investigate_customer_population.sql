-- Project 03: Customer Value & Retention Segmentation
-- Investigate the customer population available at the 31 May 2011 snapshot.
--
-- The objective is to decide whether segmentation should include only
-- customers with qualifying purchases in the trailing 12-month behavioural
-- window or also previously observed purchasers with no recent purchase.
--
-- Validation-period information is deliberately excluded from this decision.


-- 1. Build pre-snapshot customer purchasing histories.
WITH customer_history AS (
    SELECT
        customer_id_clean,

        SUM(
            CASE
                WHEN analysis_period = 'pre_behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS pre_behavioural_purchase_invoices,

        SUM(
            CASE
                WHEN analysis_period = 'behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS behavioural_purchase_invoices,

        SUM(
            CASE
                WHEN analysis_period = 'behavioural'
                THEN observed_invoice_value
                ELSE 0
            END
        ) AS behavioural_observed_value

    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period IN ('pre_behavioural', 'behavioural')
    GROUP BY customer_id_clean
)
SELECT
    COUNT(*) AS identified_pre_snapshot_customers,

    SUM(
        CASE
            WHEN behavioural_purchase_invoices > 0
            THEN 1 ELSE 0
        END
    ) AS behavioural_purchasers,

    SUM(
        CASE
            WHEN pre_behavioural_purchase_invoices > 0
                 AND behavioural_purchase_invoices = 0
            THEN 1 ELSE 0
        END
    ) AS historical_only_purchasers,

    SUM(
        CASE
            WHEN pre_behavioural_purchase_invoices = 0
                 AND behavioural_purchase_invoices = 0
            THEN 1 ELSE 0
        END
    ) AS no_qualifying_purchase_customers

FROM customer_history;


-- 2. Show the mutually exclusive pre-snapshot customer groups.
WITH customer_history AS (
    SELECT
        customer_id_clean,

        SUM(
            CASE
                WHEN analysis_period = 'pre_behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS pre_behavioural_purchase_invoices,

        SUM(
            CASE
                WHEN analysis_period = 'behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS behavioural_purchase_invoices

    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period IN ('pre_behavioural', 'behavioural')
    GROUP BY customer_id_clean
)
SELECT
    CASE
        WHEN behavioural_purchase_invoices > 0
            THEN 'behavioural purchaser'
        WHEN pre_behavioural_purchase_invoices > 0
            THEN 'historical purchaser, no behavioural purchase'
        ELSE 'identified but no qualifying purchase'
    END AS customer_group,
    COUNT(*) AS customer_count
FROM customer_history
GROUP BY customer_group
ORDER BY customer_count DESC;


-- 3. Inspect behavioural purchase-frequency distribution.
-- Frequency candidate = number of distinct qualifying purchase invoices
-- in the trailing 12-month behavioural window.
WITH behavioural_frequency AS (
    SELECT
        customer_id_clean,
        COUNT(*) AS purchase_frequency
    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'
        AND has_qualifying_activity = 1
    GROUP BY customer_id_clean
)
SELECT
    purchase_frequency,
    COUNT(*) AS customer_count
FROM behavioural_frequency
GROUP BY purchase_frequency
ORDER BY purchase_frequency;


-- 4. Summarise the proposed frequency measure.
WITH behavioural_frequency AS (
    SELECT
        customer_id_clean,
        COUNT(*) AS purchase_frequency
    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'
        AND has_qualifying_activity = 1
    GROUP BY customer_id_clean
)
SELECT
    COUNT(*) AS customers_with_behavioural_purchase,
    ROUND(AVG(purchase_frequency), 2) AS average_purchase_frequency,
    MIN(purchase_frequency) AS minimum_purchase_frequency,
    MAX(purchase_frequency) AS maximum_purchase_frequency
FROM behavioural_frequency;


-- 5. Check how many historical-only purchasers would receive a zero
-- trailing-12-month frequency if they were retained for reactivation analysis.
WITH customer_history AS (
    SELECT
        customer_id_clean,

        SUM(
            CASE
                WHEN analysis_period = 'pre_behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS pre_behavioural_purchase_invoices,

        SUM(
            CASE
                WHEN analysis_period = 'behavioural'
                     AND has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS behavioural_purchase_invoices

    FROM invoice_summary
    WHERE
        has_customer_id = 1
        AND analysis_period IN ('pre_behavioural', 'behavioural')
    GROUP BY customer_id_clean
)
SELECT
    COUNT(*) AS historical_only_purchasers
FROM customer_history
WHERE
    pre_behavioural_purchase_invoices > 0
    AND behavioural_purchase_invoices = 0;