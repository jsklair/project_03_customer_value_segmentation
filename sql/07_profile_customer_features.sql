-- Project 03: Customer Value & Retention Segmentation
-- Profile the snapshot customer features before designing segments.
--
-- This stage is deliberately exploratory. The purpose is to understand
-- distribution shape, concentration, redundancy and extreme-customer
-- influence before choosing segmentation dimensions or thresholds.
--
-- Nothing in this file uses the held-out validation period.


-- 1. Establish the basic feature-population shape.
--
-- In particular, distinguish historical-only customers from behavioural
-- purchasers and quantify customers whose observed net sales are zero or
-- negative. Financial effects such as returns can make observed value
-- non-positive even for an otherwise valid segmentation customer.
SELECT
    COUNT(*) AS eligible_customers,

    SUM(is_behavioural_purchaser)
        AS behavioural_purchasers,

    SUM(is_historical_only_purchaser)
        AS historical_only_purchasers,

    SUM(
        CASE
            WHEN purchase_frequency_12m = 0
            THEN 1 ELSE 0
        END
    ) AS zero_frequency_customers,

    SUM(
        CASE
            WHEN observed_net_sales_12m < 0
            THEN 1 ELSE 0
        END
    ) AS negative_net_sales_customers,

    SUM(
        CASE
            WHEN observed_net_sales_12m = 0
            THEN 1 ELSE 0
        END
    ) AS zero_net_sales_customers,

    SUM(
        CASE
            WHEN observed_net_sales_12m > 0
            THEN 1 ELSE 0
        END
    ) AS positive_net_sales_customers,

    SUM(
        CASE
            WHEN product_breadth_12m = 0
            THEN 1 ELSE 0
        END
    ) AS zero_product_breadth_customers,

    ROUND(
        SUM(observed_net_sales_12m),
        2
    ) AS total_observed_net_sales,

    ROUND(
        SUM(
            CASE
                WHEN observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        ),
        2
    ) AS total_positive_observed_net_sales,

    ROUND(
        SUM(
            CASE
                WHEN observed_net_sales_12m < 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        ),
        2
    ) AS total_negative_observed_net_sales

FROM customer_snapshot_features;


-- 2. Profile empirical feature distributions.
--
-- Report both:
--   a) all eligible customers; and
--   b) behavioural-window purchasers only.
--
-- This distinction matters because the 584 historical-only customers
-- legitimately have zero 12-month purchase frequency and activity measures.
--
-- CUME_DIST gives empirical percentile cut-points without assuming that these
-- strongly skewed customer measures follow a normal distribution. These are
-- descriptive percentiles only and are NOT proposed segmentation thresholds.
WITH feature_values AS (

    SELECT
        'all eligible' AS population,
        'recency_days' AS feature,
        CAST(recency_days AS REAL) AS feature_value
    FROM customer_snapshot_features

    UNION ALL

    SELECT
        'all eligible',
        'purchase_frequency_12m',
        CAST(purchase_frequency_12m AS REAL)
    FROM customer_snapshot_features

    UNION ALL

    SELECT
        'all eligible',
        'active_months_12m',
        CAST(active_months_12m AS REAL)
    FROM customer_snapshot_features

    UNION ALL

    SELECT
        'all eligible',
        'observed_net_sales_12m',
        CAST(observed_net_sales_12m AS REAL)
    FROM customer_snapshot_features

    UNION ALL

    SELECT
        'all eligible',
        'product_breadth_12m',
        CAST(product_breadth_12m AS REAL)
    FROM customer_snapshot_features

    UNION ALL

    SELECT
        'all eligible',
        'observed_tenure_days',
        CAST(observed_tenure_days AS REAL)
    FROM customer_snapshot_features

    UNION ALL

    SELECT
        'behavioural purchasers',
        'recency_days',
        CAST(recency_days AS REAL)
    FROM customer_snapshot_features
    WHERE is_behavioural_purchaser = 1

    UNION ALL

    SELECT
        'behavioural purchasers',
        'purchase_frequency_12m',
        CAST(purchase_frequency_12m AS REAL)
    FROM customer_snapshot_features
    WHERE is_behavioural_purchaser = 1

    UNION ALL

    SELECT
        'behavioural purchasers',
        'active_months_12m',
        CAST(active_months_12m AS REAL)
    FROM customer_snapshot_features
    WHERE is_behavioural_purchaser = 1

    UNION ALL

    SELECT
        'behavioural purchasers',
        'observed_net_sales_12m',
        CAST(observed_net_sales_12m AS REAL)
    FROM customer_snapshot_features
    WHERE is_behavioural_purchaser = 1

    UNION ALL

    SELECT
        'behavioural purchasers',
        'product_breadth_12m',
        CAST(product_breadth_12m AS REAL)
    FROM customer_snapshot_features
    WHERE is_behavioural_purchaser = 1

    UNION ALL

    SELECT
        'behavioural purchasers',
        'observed_tenure_days',
        CAST(observed_tenure_days AS REAL)
    FROM customer_snapshot_features
    WHERE is_behavioural_purchaser = 1
),

ranked_features AS (

    SELECT
        population,
        feature,
        feature_value,

        CUME_DIST() OVER (
            PARTITION BY population, feature
            ORDER BY feature_value
        ) AS cumulative_distribution

    FROM feature_values
)

SELECT
    population,
    feature,

    COUNT(*) AS customer_count,

    ROUND(MIN(feature_value), 2) AS minimum,

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

    ROUND(MAX(feature_value), 2) AS maximum

FROM ranked_features

GROUP BY
    population,
    feature

ORDER BY
    population,
    feature;


-- 3. Examine the historical-only population separately.
--
-- These customers are commercially important for reactivation but their
-- behavioural-window purchase measures are structurally zero. Their recency
-- distribution and any residual financial activity therefore deserve a
-- separate view rather than being hidden inside the overall distributions.
WITH historical_only AS (

    SELECT
        *,
        CUME_DIST() OVER (
            ORDER BY recency_days
        ) AS recency_distribution

    FROM customer_snapshot_features

    WHERE is_historical_only_purchaser = 1
)

SELECT
    COUNT(*) AS historical_only_customers,

    MIN(recency_days) AS minimum_recency_days,

    MIN(
        CASE
            WHEN recency_distribution >= 0.25
            THEN recency_days
        END
    ) AS p25_recency_days,

    MIN(
        CASE
            WHEN recency_distribution >= 0.50
            THEN recency_days
        END
    ) AS median_recency_days,

    ROUND(
        AVG(recency_days),
        1
    ) AS average_recency_days,

    MIN(
        CASE
            WHEN recency_distribution >= 0.75
            THEN recency_days
        END
    ) AS p75_recency_days,

    MAX(recency_days) AS maximum_recency_days,

    SUM(
        CASE
            WHEN observed_net_sales_12m < 0
            THEN 1 ELSE 0
        END
    ) AS customers_with_negative_behavioural_value,

    SUM(
        CASE
            WHEN observed_net_sales_12m > 0
            THEN 1 ELSE 0
        END
    ) AS customers_with_positive_behavioural_value,

    ROUND(
        SUM(observed_net_sales_12m),
        2
    ) AS behavioural_observed_net_sales

FROM historical_only;


-- 4. Measure customer-value concentration.
--
-- Rank the full eligible segmentation population by observed 12-month net
-- sales, but calculate shares against positive observed value. This prevents
-- negative returns/financial adjustments from making the concentration
-- denominator misleading.
--
-- NTILE(100) creates approximately 1%-wide customer groups. The resulting
-- figures are descriptive concentration measures, not segmentation cut-offs.
WITH ranked_customers AS (

    SELECT
        customer_id_clean,
        observed_net_sales_12m,

        NTILE(100) OVER (
            ORDER BY
                observed_net_sales_12m DESC,
                customer_id_clean
        ) AS customer_percentile

    FROM customer_snapshot_features
),

totals AS (

    SELECT
        SUM(
            CASE
                WHEN observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        ) AS total_positive_value

    FROM customer_snapshot_features
)

SELECT
    COUNT(*) AS eligible_customers,

    ROUND(
        MAX(totals.total_positive_value),
        2
    ) AS total_positive_observed_value,

    ROUND(
        100.0
        * MAX(
            CASE
                WHEN ranked_customers.observed_net_sales_12m > 0
                THEN ranked_customers.observed_net_sales_12m
                ELSE 0
            END
        )
        / MAX(totals.total_positive_value),
        2
    ) AS largest_customer_share_pct,

    SUM(
        CASE
            WHEN customer_percentile <= 1
            THEN 1 ELSE 0
        END
    ) AS top_1pct_customer_count,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 1
                     AND observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        )
        / MAX(totals.total_positive_value),
        2
    ) AS top_1pct_value_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 5
                     AND observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        )
        / MAX(totals.total_positive_value),
        2
    ) AS top_5pct_value_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 10
                     AND observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        )
        / MAX(totals.total_positive_value),
        2
    ) AS top_10pct_value_share_pct,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_percentile <= 20
                     AND observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        )
        / MAX(totals.total_positive_value),
        2
    ) AS top_20pct_value_share_pct

FROM ranked_customers

CROSS JOIN totals;


-- 5. Compare other customer measures across purchase-frequency bands.
--
-- These bands merely compress a highly skewed frequency distribution into a
-- readable diagnostic table. They are NOT proposed segment thresholds.
WITH frequency_bands AS (

    SELECT
        *,

        CASE
            WHEN purchase_frequency_12m = 0 THEN '0'
            WHEN purchase_frequency_12m = 1 THEN '1'
            WHEN purchase_frequency_12m = 2 THEN '2'
            WHEN purchase_frequency_12m BETWEEN 3 AND 4 THEN '3-4'
            WHEN purchase_frequency_12m BETWEEN 5 AND 9 THEN '5-9'
            WHEN purchase_frequency_12m BETWEEN 10 AND 19 THEN '10-19'
            ELSE '20+'
        END AS frequency_band,

        CASE
            WHEN purchase_frequency_12m = 0 THEN 0
            WHEN purchase_frequency_12m = 1 THEN 1
            WHEN purchase_frequency_12m = 2 THEN 2
            WHEN purchase_frequency_12m BETWEEN 3 AND 4 THEN 3
            WHEN purchase_frequency_12m BETWEEN 5 AND 9 THEN 4
            WHEN purchase_frequency_12m BETWEEN 10 AND 19 THEN 5
            ELSE 6
        END AS frequency_band_order

    FROM customer_snapshot_features
)

SELECT
    frequency_band,
    COUNT(*) AS customer_count,

    ROUND(
        AVG(recency_days),
        1
    ) AS average_recency_days,

    ROUND(
        AVG(active_months_12m),
        2
    ) AS average_active_months,

    ROUND(
        AVG(observed_net_sales_12m),
        2
    ) AS average_observed_net_sales,

    ROUND(
        AVG(product_breadth_12m),
        1
    ) AS average_product_breadth,

    ROUND(
        AVG(observed_tenure_days),
        1
    ) AS average_observed_tenure_days,

    ROUND(
        SUM(observed_net_sales_12m),
        2
    ) AS total_observed_net_sales

FROM frequency_bands

GROUP BY
    frequency_band_order,
    frequency_band

ORDER BY frequency_band_order;


-- 6. Examine active months against purchase frequency and the other features.
--
-- Restrict this comparison to behavioural purchasers. Historical-only
-- customers necessarily have zero active months, so including them would
-- mechanically strengthen the apparent relationship.
SELECT
    active_months_12m,
    COUNT(*) AS customer_count,

    ROUND(
        AVG(purchase_frequency_12m),
        2
    ) AS average_purchase_frequency,

    MIN(purchase_frequency_12m)
        AS minimum_purchase_frequency,

    MAX(purchase_frequency_12m)
        AS maximum_purchase_frequency,

    ROUND(
        AVG(recency_days),
        1
    ) AS average_recency_days,

    ROUND(
        AVG(observed_net_sales_12m),
        2
    ) AS average_observed_net_sales,

    ROUND(
        AVG(product_breadth_12m),
        1
    ) AS average_product_breadth

FROM customer_snapshot_features

WHERE is_behavioural_purchaser = 1

GROUP BY active_months_12m

ORDER BY active_months_12m;


-- 7. Check how strongly observed tenure is affected by the left boundary of
-- the source history.
--
-- Customers first observed near 1 December 2009 may have purchased before the
-- dataset begins. A large concentration at the beginning of the source would
-- make observed tenure a weaker proxy for true relationship tenure.
SELECT
    COUNT(*) AS eligible_customers,

    SUM(
        CASE
            WHEN DATE(first_purchase_timestamp) <= '2009-12-31'
            THEN 1 ELSE 0
        END
    ) AS first_observed_in_source_month,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN DATE(first_purchase_timestamp) <= '2009-12-31'
                THEN 1 ELSE 0
            END
        )
        / COUNT(*),
        1
    ) AS first_source_month_pct,

    SUM(
        CASE
            WHEN DATE(first_purchase_timestamp) <= '2010-01-31'
            THEN 1 ELSE 0
        END
    ) AS first_observed_within_two_months,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN DATE(first_purchase_timestamp) <= '2010-01-31'
                THEN 1 ELSE 0
            END
        )
        / COUNT(*),
        1
    ) AS first_two_months_pct,

    SUM(
        CASE
            WHEN DATE(first_purchase_timestamp) <= '2010-02-28'
            THEN 1 ELSE 0
        END
    ) AS first_observed_within_three_months,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN DATE(first_purchase_timestamp) <= '2010-02-28'
                THEN 1 ELSE 0
            END
        )
        / COUNT(*),
        1
    ) AS first_three_months_pct

FROM customer_snapshot_features;


-- 8. Inspect the highest observed-value customers.
--
-- The purpose is to see whether a very small number of wholesale-scale
-- customers could dominate means, concentration measures or naive thresholds.
SELECT
    customer_id_clean,
    recency_days,
    purchase_frequency_12m,
    active_months_12m,
    ROUND(observed_net_sales_12m, 2)
        AS observed_net_sales_12m,
    product_breadth_12m,
    observed_tenure_days

FROM customer_snapshot_features

ORDER BY
    observed_net_sales_12m DESC,
    customer_id_clean

LIMIT 10;


-- 9. Inspect the most negative observed-value customers.
--
-- Negative 12-month value can arise from retained returns and other signed
-- customer financial effects. These customers should be understood before
-- value is converted into any segmentation rule.
SELECT
    customer_id_clean,
    recency_days,
    purchase_frequency_12m,
    active_months_12m,
    ROUND(observed_net_sales_12m, 2)
        AS observed_net_sales_12m,
    product_breadth_12m,
    observed_tenure_days

FROM customer_snapshot_features

ORDER BY
    observed_net_sales_12m ASC,
    customer_id_clean

LIMIT 10;