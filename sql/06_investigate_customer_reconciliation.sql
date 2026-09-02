-- Project 03: Customer Value & Retention Segmentation
-- Investigate the customer-feature monetary reconciliation difference.
--
-- The segmentation population excludes identified Customer IDs that have
-- never recorded a qualifying purchase before the snapshot. Those customers
-- may nevertheless have customer-attributable financial adjustments or
-- returns, so their exclusion can legitimately change the population-level
-- observed net-sales total.


-- 1. Compare eligible and excluded identified customers.
WITH customer_eligibility AS (

    SELECT
        customer_id_clean,

        MAX(
            CASE
                WHEN has_qualifying_activity = 1
                     AND analysis_period IN (
                         'pre_behavioural',
                         'behavioural'
                     )
                THEN 1
                ELSE 0
            END
        ) AS is_eligible

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period IN (
            'pre_behavioural',
            'behavioural'
        )

    GROUP BY customer_id_clean
),

behavioural_value AS (

    SELECT
        customer_id_clean,
        SUM(observed_invoice_value) AS observed_net_sales_12m

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'

    GROUP BY customer_id_clean
)

SELECT
    CASE
        WHEN eligibility.is_eligible = 1
            THEN 'eligible customer'
        ELSE 'excluded: no qualifying purchase'
    END AS customer_group,

    COUNT(*) AS customer_count,

    SUM(
        CASE
            WHEN value.observed_net_sales_12m IS NOT NULL
            THEN 1
            ELSE 0
        END
    ) AS customers_with_behavioural_value,

    ROUND(
        SUM(
            COALESCE(value.observed_net_sales_12m, 0)
        ),
        2
    ) AS behavioural_observed_net_sales

FROM customer_eligibility AS eligibility

LEFT JOIN behavioural_value AS value
    ON eligibility.customer_id_clean = value.customer_id_clean

GROUP BY customer_group
ORDER BY customer_group;


-- 2. Explicitly reconcile the eligible, excluded and overall values.
WITH customer_eligibility AS (

    SELECT
        customer_id_clean,

        MAX(
            CASE
                WHEN has_qualifying_activity = 1
                     AND analysis_period IN (
                         'pre_behavioural',
                         'behavioural'
                     )
                THEN 1
                ELSE 0
            END
        ) AS is_eligible

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period IN (
            'pre_behavioural',
            'behavioural'
        )

    GROUP BY customer_id_clean
),

behavioural_value AS (

    SELECT
        customer_id_clean,
        SUM(observed_invoice_value) AS observed_net_sales_12m

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'

    GROUP BY customer_id_clean
)

SELECT
    ROUND(
        (
            SELECT SUM(observed_net_sales_12m)
            FROM customer_snapshot_features
        ),
        2
    ) AS feature_population_value,

    ROUND(
        SUM(
            CASE
                WHEN eligibility.is_eligible = 1
                THEN COALESCE(value.observed_net_sales_12m, 0)
                ELSE 0
            END
        ),
        2
    ) AS eligible_transaction_value,

    ROUND(
        SUM(
            CASE
                WHEN eligibility.is_eligible = 0
                THEN COALESCE(value.observed_net_sales_12m, 0)
                ELSE 0
            END
        ),
        2
    ) AS excluded_customer_value,

    ROUND(
        SUM(
            COALESCE(value.observed_net_sales_12m, 0)
        ),
        2
    ) AS all_identified_transaction_value

FROM customer_eligibility AS eligibility

LEFT JOIN behavioural_value AS value
    ON eligibility.customer_id_clean = value.customer_id_clean;


-- 3. Inspect excluded customers with the largest behavioural financial effects.
WITH customer_eligibility AS (

    SELECT
        customer_id_clean,

        MAX(
            CASE
                WHEN has_qualifying_activity = 1
                     AND analysis_period IN (
                         'pre_behavioural',
                         'behavioural'
                     )
                THEN 1
                ELSE 0
            END
        ) AS is_eligible

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period IN (
            'pre_behavioural',
            'behavioural'
        )

    GROUP BY customer_id_clean
),

behavioural_value AS (

    SELECT
        customer_id_clean,
        SUM(observed_invoice_value) AS observed_net_sales_12m

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'

    GROUP BY customer_id_clean
)

SELECT
    eligibility.customer_id_clean,
    ROUND(value.observed_net_sales_12m, 2) AS observed_net_sales_12m

FROM customer_eligibility AS eligibility

INNER JOIN behavioural_value AS value
    ON eligibility.customer_id_clean = value.customer_id_clean

WHERE
    eligibility.is_eligible = 0

ORDER BY ABS(value.observed_net_sales_12m) DESC
LIMIT 20;