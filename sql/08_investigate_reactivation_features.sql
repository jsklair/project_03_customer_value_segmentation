-- Project 03: Customer Value & Retention Segmentation
-- Investigate useful reactivation features for historical-only customers.
--
-- Historical-only customers have a genuine qualifying purchase before the
-- behavioural window but no qualifying purchase during the trailing 12 months.
--
-- Their behavioural-window frequency, active months and product breadth are
-- therefore structurally zero. Behavioural observed net sales may also contain
-- returns or other signed financial effects without representing recent buying.
--
-- This investigation asks whether the available pre-behavioural history can
-- provide useful measures of previous customer value and engagement.
--
-- The pre-behavioural history begins on 1 December 2009, so these measures are
-- observed-history measures rather than true lifetime customer measures.
--
-- Temporary views are used because the same investigation populations are
-- needed by several separate SELECT statements. A CTE would exist only for
-- the single statement immediately following its WITH clause.


DROP VIEW IF EXISTS temp.historical_features;
DROP VIEW IF EXISTS temp.historical_only_ids;


CREATE TEMP VIEW historical_only_ids AS

SELECT
    customer_id_clean,
    recency_days,
    observed_net_sales_12m

FROM customer_snapshot_features

WHERE is_historical_only_purchaser = 1;


CREATE TEMP VIEW historical_features AS

WITH prior_invoice_metrics AS (

    SELECT
        invoices.customer_id_clean,

        -- Count only genuine qualifying purchase occasions. Returns and
        -- financial adjustments must not manufacture previous purchase
        -- frequency.
        SUM(
            CASE
                WHEN invoices.has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS prior_purchase_invoices,

        -- Active months measure how widely the customer's qualifying purchases
        -- were distributed across the available pre-behavioural history.
        COUNT(
            DISTINCT CASE
                WHEN invoices.has_qualifying_activity = 1
                THEN strftime('%Y-%m', invoices.invoice_timestamp)
            END
        ) AS prior_active_months,

        -- Preserve the signed customer-attributable financial effects from the
        -- same historical period rather than treating purchases and subsequent
        -- returns as unrelated customer value.
        SUM(invoices.observed_invoice_value)
            AS prior_observed_net_sales

    FROM invoice_summary AS invoices

    INNER JOIN historical_only_ids AS historical
        ON invoices.customer_id_clean = historical.customer_id_clean

    WHERE invoices.analysis_period = 'pre_behavioural'

    GROUP BY invoices.customer_id_clean
),

prior_product_breadth AS (

    -- Product breadth is calculated directly from eligible transaction lines
    -- so repeated purchases of the same product do not inflate breadth.
    SELECT
        transactions.customer_id_clean,

        COUNT(DISTINCT transactions.stock_code_clean)
            AS prior_product_breadth

    FROM classified_transactions AS transactions

    INNER JOIN historical_only_ids AS historical
        ON transactions.customer_id_clean = historical.customer_id_clean

    WHERE
        transactions.analysis_period = 'pre_behavioural'
        AND transactions.counts_in_product_breadth = 1

    GROUP BY transactions.customer_id_clean
)

SELECT
    historical.customer_id_clean,
    historical.recency_days,

    prior.prior_purchase_invoices,
    prior.prior_active_months,
    prior.prior_observed_net_sales,

    COALESCE(
        breadth.prior_product_breadth,
        0
    ) AS prior_product_breadth,

    historical.observed_net_sales_12m
        AS behavioural_observed_net_sales

FROM historical_only_ids AS historical

INNER JOIN prior_invoice_metrics AS prior
    ON historical.customer_id_clean = prior.customer_id_clean

LEFT JOIN prior_product_breadth AS breadth
    ON historical.customer_id_clean = breadth.customer_id_clean;


-- 1. Confirm coverage and the basic commercial shape of the historical-only
-- population.
SELECT
    COUNT(*) AS historical_only_customers,

    SUM(
        CASE
            WHEN prior_purchase_invoices > 0
            THEN 1 ELSE 0
        END
    ) AS customers_with_prior_purchase,

    SUM(
        CASE
            WHEN prior_observed_net_sales > 0
            THEN 1 ELSE 0
        END
    ) AS positive_prior_value_customers,

    SUM(
        CASE
            WHEN prior_observed_net_sales = 0
            THEN 1 ELSE 0
        END
    ) AS zero_prior_value_customers,

    SUM(
        CASE
            WHEN prior_observed_net_sales < 0
            THEN 1 ELSE 0
        END
    ) AS negative_prior_value_customers,

    ROUND(
        SUM(prior_observed_net_sales),
        2
    ) AS total_prior_observed_net_sales,

    ROUND(
        SUM(
            CASE
                WHEN prior_observed_net_sales > 0
                THEN prior_observed_net_sales
                ELSE 0
            END
        ),
        2
    ) AS total_positive_prior_value,

    ROUND(
        SUM(behavioural_observed_net_sales),
        2
    ) AS behavioural_observed_net_sales

FROM historical_features;


-- 2. Profile the available previous-customer measures.
--
-- These empirical percentiles are descriptive only. They are not proposed
-- reactivation thresholds.
WITH feature_values AS (

    SELECT
        'recency_days' AS feature,
        CAST(recency_days AS REAL) AS feature_value
    FROM historical_features

    UNION ALL

    SELECT
        'prior_purchase_invoices',
        CAST(prior_purchase_invoices AS REAL)
    FROM historical_features

    UNION ALL

    SELECT
        'prior_active_months',
        CAST(prior_active_months AS REAL)
    FROM historical_features

    UNION ALL

    SELECT
        'prior_observed_net_sales',
        CAST(prior_observed_net_sales AS REAL)
    FROM historical_features

    UNION ALL

    SELECT
        'prior_product_breadth',
        CAST(prior_product_breadth AS REAL)
    FROM historical_features
),

ranked_features AS (

    SELECT
        feature,
        feature_value,

        CUME_DIST() OVER (
            PARTITION BY feature
            ORDER BY feature_value
        ) AS cumulative_distribution

    FROM feature_values
)

SELECT
    feature,
    COUNT(*) AS customer_count,

    ROUND(MIN(feature_value), 2)
        AS minimum,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.10
                THEN feature_value
            END
        ),
        2
    ) AS p10,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.25
                THEN feature_value
            END
        ),
        2
    ) AS p25,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.50
                THEN feature_value
            END
        ),
        2
    ) AS median,

    ROUND(
        AVG(feature_value),
        2
    ) AS average,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.75
                THEN feature_value
            END
        ),
        2
    ) AS p75,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.90
                THEN feature_value
            END
        ),
        2
    ) AS p90,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.95
                THEN feature_value
            END
        ),
        2
    ) AS p95,

    ROUND(
        MIN(
            CASE
                WHEN cumulative_distribution >= 0.99
                THEN feature_value
            END
        ),
        2
    ) AS p99,

    ROUND(MAX(feature_value), 2)
        AS maximum

FROM ranked_features

GROUP BY feature

ORDER BY feature;


-- 3. Measure concentration of previous positive value within the
-- historical-only population.
--
-- If previous value is extremely concentrated, raw monetary thresholds would
-- again be vulnerable to a handful of unusually large customers.
WITH ranked_customers AS (

    SELECT
        customer_id_clean,
        prior_observed_net_sales,

        NTILE(100) OVER (
            ORDER BY
                prior_observed_net_sales DESC,
                customer_id_clean
        ) AS customer_percentile

    FROM historical_features
),

totals AS (

    SELECT
        SUM(
            CASE
                WHEN prior_observed_net_sales > 0
                THEN prior_observed_net_sales
                ELSE 0
            END
        ) AS total_positive_prior_value

    FROM historical_features
)

SELECT
    COUNT(*) AS historical_only_customers,

    ROUND(
        MAX(totals.total_positive_prior_value),
        2
    ) AS total_positive_prior_value,

    ROUND(
        100.0
        * MAX(
            CASE
                WHEN ranked_customers.prior_observed_net_sales > 0
                THEN ranked_customers.prior_observed_net_sales
                ELSE 0
            END
        )
        / MAX(totals.total_positive_prior_value),
        2
    ) AS largest_customer_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 5
                     AND prior_observed_net_sales > 0
                THEN prior_observed_net_sales
                ELSE 0
            END
        )
        / MAX(totals.total_positive_prior_value),
        2
    ) AS top_5pct_value_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 10
                     AND prior_observed_net_sales > 0
                THEN prior_observed_net_sales
                ELSE 0
            END
        )
        / MAX(totals.total_positive_prior_value),
        2
    ) AS top_10pct_value_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 20
                     AND prior_observed_net_sales > 0
                THEN prior_observed_net_sales
                ELSE 0
            END
        )
        / MAX(totals.total_positive_prior_value),
        2
    ) AS top_20pct_value_share_pct

FROM ranked_customers

CROSS JOIN totals;


-- 4. Explain behavioural-period financial effects for historical-only
-- customers.
--
-- This checks why customers with no qualifying behavioural-window purchase
-- nevertheless have non-zero observed net sales during that period.
SELECT
    transactions.transaction_class,

    COUNT(*) AS transaction_rows,

    COUNT(
        DISTINCT transactions.customer_id_clean
    ) AS customer_count,

    ROUND(
        SUM(transactions.observed_net_sales),
        2
    ) AS observed_net_sales

FROM classified_transactions AS transactions

INNER JOIN historical_only_ids AS historical
    ON transactions.customer_id_clean = historical.customer_id_clean

WHERE
    transactions.analysis_period = 'behavioural'
    AND transactions.observed_net_sales <> 0

GROUP BY transactions.transaction_class

ORDER BY observed_net_sales;


-- 5. Inspect the previously highest-value historical-only customers.
--
-- These are candidates that a CRM stakeholder might care about for
-- reactivation, but no segment definition should be fixed from this list.
SELECT
    customer_id_clean,
    recency_days,
    prior_purchase_invoices,
    prior_active_months,

    ROUND(
        prior_observed_net_sales,
        2
    ) AS prior_observed_net_sales,

    prior_product_breadth,

    ROUND(
        behavioural_observed_net_sales,
        2
    ) AS behavioural_observed_net_sales

FROM historical_features

ORDER BY
    prior_observed_net_sales DESC,
    customer_id_clean

LIMIT 15;


-- 6. Inspect historical-only customers whose available previous observed
-- value is zero or negative despite having a genuine qualifying purchase.
--
-- This is a useful warning against treating a single net-sales field as a
-- complete description of past customer importance.
SELECT
    customer_id_clean,
    recency_days,
    prior_purchase_invoices,
    prior_active_months,

    ROUND(
        prior_observed_net_sales,
        2
    ) AS prior_observed_net_sales,

    prior_product_breadth,

    ROUND(
        behavioural_observed_net_sales,
        2
    ) AS behavioural_observed_net_sales

FROM historical_features

WHERE prior_observed_net_sales <= 0

ORDER BY
    prior_observed_net_sales,
    customer_id_clean;