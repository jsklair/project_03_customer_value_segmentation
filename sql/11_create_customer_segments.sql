-- Project 03: Customer Value & Retention Segmentation
-- Create the final snapshot-only customer segmentation.
--
-- The segment design was chosen after profiling feature distributions,
-- customer-value concentration, feature redundancy and historical-only
-- customer behaviour.
--
-- Design:
--
-- Behavioural purchasers:
--   * high-value customers = top 20% by observed 12-month net sales;
--   * high-value customers are separated by <=180 vs >180 day recency;
--   * remaining customers with 5+ purchases and <=180 day recency form
--     the established repeat-customer group;
--   * lower-frequency customers are separated by <=90, 91-180 and >180
--     day recency.
--
-- Historical-only customers:
--   * kept separate because their trailing-12-month purchasing measures
--     are structurally zero;
--   * top 20% by available prior observed net sales receive a separate
--     high-value reactivation designation.
--
-- The segmentation uses only information available by 31 May 2011.
-- The held-out validation period is not used anywhere in segment assignment.


DROP VIEW IF EXISTS customer_segments;


CREATE VIEW customer_segments AS

WITH behavioural_value_rank AS (

    SELECT
        customer_id_clean,

        NTILE(5) OVER (
            ORDER BY
                observed_net_sales_12m DESC,
                customer_id_clean
        ) AS behavioural_value_fifth

    FROM customer_segmentation_features

    WHERE is_behavioural_purchaser = 1
),

historical_value_rank AS (

    SELECT
        customer_id_clean,

        NTILE(5) OVER (
            ORDER BY
                prior_observed_net_sales DESC,
                customer_id_clean
        ) AS historical_value_fifth

    FROM customer_segmentation_features

    WHERE is_historical_only_purchaser = 1
),

ranked_features AS (

    SELECT
        features.*,

        behavioural.behavioural_value_fifth,
        historical.historical_value_fifth

    FROM customer_segmentation_features AS features

    LEFT JOIN behavioural_value_rank AS behavioural
        ON features.customer_id_clean = behavioural.customer_id_clean

    LEFT JOIN historical_value_rank AS historical
        ON features.customer_id_clean = historical.customer_id_clean
)

SELECT
    ranked.*,

    CASE

        -- Reactivation population.
        WHEN is_historical_only_purchaser = 1
             AND historical_value_fifth = 1
            THEN 'High-value lapsed'

        WHEN is_historical_only_purchaser = 1
            THEN 'Lapsed'

        -- High-value retention population.
        WHEN behavioural_value_fifth = 1
             AND recency_days <= 180
            THEN 'High-value active'

        WHEN behavioural_value_fifth = 1
            THEN 'High-value at risk'

        -- Established repeat customers outside the top-value tier.
        WHEN purchase_frequency_12m >= 5
             AND recency_days <= 180
            THEN 'Core repeat'

        -- Lower-frequency customers are separated by recency.
        WHEN recency_days <= 90
            THEN 'Recent low-frequency'

        WHEN recency_days <= 180
            THEN 'Cooling low-frequency'

        ELSE 'Drifting'

    END AS customer_segment

FROM ranked_features AS ranked;


-- 1. Final MECE validation.
SELECT
    COUNT(*) AS assigned_customers,

    COUNT(DISTINCT customer_id_clean)
        AS unique_customers,

    SUM(
        CASE
            WHEN customer_segment IS NULL
            THEN 1 ELSE 0
        END
    ) AS unassigned_customers,

    COUNT(DISTINCT customer_segment)
        AS segment_count

FROM customer_segments;


-- 2. Final segment membership.
SELECT
    customer_segment,
    COUNT(*) AS customer_count,

    ROUND(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        1
    ) AS customer_share_pct

FROM customer_segments

GROUP BY customer_segment

ORDER BY
    CASE customer_segment
        WHEN 'High-value active' THEN 1
        WHEN 'High-value at risk' THEN 2
        WHEN 'Core repeat' THEN 3
        WHEN 'Recent low-frequency' THEN 4
        WHEN 'Cooling low-frequency' THEN 5
        WHEN 'Drifting' THEN 6
        WHEN 'High-value lapsed' THEN 7
        WHEN 'Lapsed' THEN 8
        ELSE 9
    END;


-- 3. Final behavioural-segment snapshot profile.
WITH positive_value_total AS (

    SELECT
        SUM(
            CASE
                WHEN observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        ) AS total_positive_value

    FROM customer_segments

    WHERE is_behavioural_purchaser = 1
)

SELECT
    customer_segment,

    COUNT(*) AS customer_count,

    ROUND(
        AVG(recency_days),
        1
    ) AS average_recency_days,

    ROUND(
        AVG(purchase_frequency_12m),
        2
    ) AS average_purchase_frequency,

    ROUND(
        AVG(active_months_12m),
        2
    ) AS average_active_months,

    ROUND(
        AVG(observed_net_sales_12m),
        2
    ) AS average_observed_net_sales,

    ROUND(
        SUM(observed_net_sales_12m),
        2
    ) AS total_observed_net_sales,

    ROUND(
        AVG(product_breadth_12m),
        1
    ) AS average_product_breadth,

    ROUND(
        AVG(average_qualifying_purchase_invoice_value_12m),
        2
    ) AS average_purchase_invoice_value,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN observed_net_sales_12m > 0
                THEN observed_net_sales_12m
                ELSE 0
            END
        )
        / MAX(positive_value_total.total_positive_value),
        1
    ) AS positive_value_share_pct

FROM customer_segments

CROSS JOIN positive_value_total

WHERE is_behavioural_purchaser = 1

GROUP BY customer_segment

ORDER BY
    CASE customer_segment
        WHEN 'High-value active' THEN 1
        WHEN 'High-value at risk' THEN 2
        WHEN 'Core repeat' THEN 3
        WHEN 'Recent low-frequency' THEN 4
        WHEN 'Cooling low-frequency' THEN 5
        WHEN 'Drifting' THEN 6
        ELSE 7
    END;


-- 4. Final historical-only profile using the earlier measures relevant to
-- reactivation prioritisation.
SELECT
    customer_segment,

    COUNT(*) AS customer_count,

    ROUND(
        AVG(recency_days),
        1
    ) AS average_recency_days,

    ROUND(
        AVG(prior_purchase_invoices),
        2
    ) AS average_prior_purchase_invoices,

    ROUND(
        AVG(prior_observed_net_sales),
        2
    ) AS average_prior_observed_net_sales,

    ROUND(
        SUM(prior_observed_net_sales),
        2
    ) AS total_prior_observed_net_sales,

    ROUND(
        AVG(prior_product_breadth),
        1
    ) AS average_prior_product_breadth

FROM customer_segments

WHERE is_historical_only_purchaser = 1

GROUP BY customer_segment

ORDER BY
    CASE customer_segment
        WHEN 'High-value lapsed' THEN 1
        WHEN 'Lapsed' THEN 2
        ELSE 3
    END;


-- 5. Make the derived value boundaries explicit.
SELECT
    ROUND(
        MIN(
            CASE
                WHEN behavioural_value_fifth = 1
                THEN observed_net_sales_12m
            END
        ),
        2
    ) AS minimum_behavioural_high_value,

    ROUND(
        MAX(
            CASE
                WHEN behavioural_value_fifth > 1
                THEN observed_net_sales_12m
            END
        ),
        2
    ) AS maximum_other_behavioural_value,

    ROUND(
        MIN(
            CASE
                WHEN historical_value_fifth = 1
                THEN prior_observed_net_sales
            END
        ),
        2
    ) AS minimum_high_value_lapsed,

    ROUND(
        MAX(
            CASE
                WHEN historical_value_fifth > 1
                THEN prior_observed_net_sales
            END
        ),
        2
    ) AS maximum_other_lapsed_value

FROM customer_segments;


-- 6. Preserve the validated monetary reconciliation.
SELECT
    ROUND(
        SUM(observed_net_sales_12m),
        2
    ) AS final_segment_population_observed_net_sales

FROM customer_segments;