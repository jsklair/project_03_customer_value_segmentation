-- Project 03: Customer Value & Retention Segmentation
-- Create the enriched customer feature layer used for segment design.
--
-- The validated customer_snapshot_features table remains the stable base layer.
-- This second layer adds features that became useful only after feature
-- profiling, particularly:
--
--   * previous observed customer value for historical-only customers;
--   * previous purchasing behaviour for reactivation interpretation;
--   * average qualifying purchase-invoice value;
--   * recent versus previous three-month purchasing activity.
--
-- All fields remain snapshot-valid at 31 May 2011.
-- No held-out validation-period information is used.


DROP TABLE IF EXISTS customer_segmentation_features;


-- Materialise this customer-grain feature layer because the final
-- segmentation and validation stages reuse these calculations repeatedly.
CREATE TABLE customer_segmentation_features AS

WITH prior_invoice_metrics AS (

    SELECT
        customer_id_clean,

        -- These are observed pre-behavioural measures, not lifetime measures.
        -- The source starts on 1 December 2009, so earlier customer history
        -- may be unavailable.
        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS prior_purchase_invoices,

        COUNT(
            DISTINCT CASE
                WHEN has_qualifying_activity = 1
                THEN strftime('%Y-%m', invoice_timestamp)
            END
        ) AS prior_active_months,

        -- Include all signed customer-attributable financial effects in the
        -- observed historical period so previous value follows the same
        -- commercial treatment as the 12-month snapshot value.
        SUM(observed_invoice_value)
            AS prior_observed_net_sales

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period = 'pre_behavioural'

    GROUP BY customer_id_clean
),

prior_product_breadth AS (

    -- Count distinct eligible merchandise across the available earlier
    -- history. Repeated purchases of one StockCode therefore count once.
    SELECT
        customer_id_clean,

        COUNT(DISTINCT stock_code_clean)
            AS prior_product_breadth

    FROM classified_transactions

    WHERE
        has_customer_id = 1
        AND analysis_period = 'pre_behavioural'
        AND counts_in_product_breadth = 1

    GROUP BY customer_id_clean
),

behavioural_purchase_metrics AS (

    SELECT
        customer_id_clean,

        -- This value is deliberately restricted to invoices containing a
        -- genuine qualifying purchase. Standalone later returns or financial
        -- adjustments therefore do not enter the average-purchase denominator
        -- or numerator.
        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                THEN observed_invoice_value
                ELSE 0
            END
        ) AS qualifying_purchase_invoice_value_12m,

        -- Two equal three-month windows give an interpretable view of recent
        -- purchasing direction without using future data.
        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                     AND DATE(invoice_timestamp)
                         BETWEEN '2010-12-01' AND '2011-02-28'
                THEN 1
                ELSE 0
            END
        ) AS previous_3m_purchase_frequency,

        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                     AND DATE(invoice_timestamp)
                         BETWEEN '2011-03-01' AND '2011-05-31'
                THEN 1
                ELSE 0
            END
        ) AS recent_3m_purchase_frequency,

        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                     AND DATE(invoice_timestamp)
                         BETWEEN '2010-12-01' AND '2011-02-28'
                THEN observed_invoice_value
                ELSE 0
            END
        ) AS previous_3m_purchase_value,

        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                     AND DATE(invoice_timestamp)
                         BETWEEN '2011-03-01' AND '2011-05-31'
                THEN observed_invoice_value
                ELSE 0
            END
        ) AS recent_3m_purchase_value

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period = 'behavioural'

    GROUP BY customer_id_clean
)

SELECT
    snapshot.*,

    COALESCE(
        prior.prior_purchase_invoices,
        0
    ) AS prior_purchase_invoices,

    COALESCE(
        prior.prior_active_months,
        0
    ) AS prior_active_months,

    COALESCE(
        prior.prior_observed_net_sales,
        0
    ) AS prior_observed_net_sales,

    COALESCE(
        prior_breadth.prior_product_breadth,
        0
    ) AS prior_product_breadth,

    COALESCE(
        behavioural.qualifying_purchase_invoice_value_12m,
        0
    ) AS qualifying_purchase_invoice_value_12m,

    -- Average qualifying purchase-invoice value describes purchase size.
    -- It is intentionally different from observed customer net sales, which
    -- also includes separate signed returns/financial effects.
    CASE
        WHEN snapshot.purchase_frequency_12m > 0
        THEN
            behavioural.qualifying_purchase_invoice_value_12m
            / snapshot.purchase_frequency_12m
        ELSE NULL
    END AS average_qualifying_purchase_invoice_value_12m,

    COALESCE(
        behavioural.previous_3m_purchase_frequency,
        0
    ) AS previous_3m_purchase_frequency,

    COALESCE(
        behavioural.recent_3m_purchase_frequency,
        0
    ) AS recent_3m_purchase_frequency,

    COALESCE(
        behavioural.previous_3m_purchase_value,
        0
    ) AS previous_3m_purchase_value,

    COALESCE(
        behavioural.recent_3m_purchase_value,
        0
    ) AS recent_3m_purchase_value,

    -- The categorical pattern is easier to interpret than a raw percentage
    -- growth measure when many customers have zero purchases in one or both
    -- three-month comparison periods.
    CASE
        WHEN snapshot.is_historical_only_purchaser = 1
            THEN 'historical only'

        WHEN COALESCE(
                 behavioural.previous_3m_purchase_frequency,
                 0
             ) > 0
             AND COALESCE(
                 behavioural.recent_3m_purchase_frequency,
                 0
             ) > 0
            THEN 'both periods'

        WHEN COALESCE(
                 behavioural.previous_3m_purchase_frequency,
                 0
             ) = 0
             AND COALESCE(
                 behavioural.recent_3m_purchase_frequency,
                 0
             ) > 0
            THEN 'recent only'

        WHEN COALESCE(
                 behavioural.previous_3m_purchase_frequency,
                 0
             ) > 0
             AND COALESCE(
                 behavioural.recent_3m_purchase_frequency,
                 0
             ) = 0
            THEN 'previous only'

        ELSE 'neither period'
    END AS recent_activity_pattern

FROM customer_snapshot_features AS snapshot

LEFT JOIN prior_invoice_metrics AS prior
    ON snapshot.customer_id_clean = prior.customer_id_clean

LEFT JOIN prior_product_breadth AS prior_breadth
    ON snapshot.customer_id_clean = prior_breadth.customer_id_clean

LEFT JOIN behavioural_purchase_metrics AS behavioural
    ON snapshot.customer_id_clean = behavioural.customer_id_clean;


CREATE UNIQUE INDEX idx_customer_segmentation_features_customer
    ON customer_segmentation_features (customer_id_clean);


-- 1. Preserve the validated segmentation population exactly.
SELECT
    COUNT(*) AS eligible_customers,

    COUNT(DISTINCT customer_id_clean)
        AS unique_customers,

    SUM(is_behavioural_purchaser)
        AS behavioural_purchasers,

    SUM(is_historical_only_purchaser)
        AS historical_only_purchasers

FROM customer_segmentation_features;


-- 2. Confirm the settled behavioural purchase-frequency definition still
-- reconciles to the enriched invoice calculations.
SELECT
    SUM(
        CASE
            WHEN purchase_frequency_12m
                 <> (
                     COALESCE(previous_3m_purchase_frequency, 0)
                     + COALESCE(recent_3m_purchase_frequency, 0)
                 )
                 AND recency_days <= 181
            THEN 1
            ELSE 0
        END
    ) AS note_not_full_12m_comparison,

    SUM(
        CASE
            WHEN is_behavioural_purchaser = 1
                 AND purchase_frequency_12m <= 0
            THEN 1
            ELSE 0
        END
    ) AS invalid_behavioural_frequency,

    SUM(
        CASE
            WHEN is_historical_only_purchaser = 1
                 AND purchase_frequency_12m <> 0
            THEN 1
            ELSE 0
        END
    ) AS invalid_historical_frequency

FROM customer_segmentation_features;


-- 3. Confirm historical-only customers now have usable observed earlier
-- purchasing information.
SELECT
    COUNT(*) AS historical_only_customers,

    SUM(
        CASE
            WHEN prior_purchase_invoices > 0
            THEN 1 ELSE 0
        END
    ) AS with_prior_purchase,

    SUM(
        CASE
            WHEN prior_observed_net_sales > 0
            THEN 1 ELSE 0
        END
    ) AS with_positive_prior_value,

    ROUND(
        SUM(prior_observed_net_sales),
        2
    ) AS total_prior_observed_net_sales,

    ROUND(
        AVG(prior_observed_net_sales),
        2
    ) AS average_prior_observed_net_sales,

    ROUND(
        AVG(prior_product_breadth),
        1
    ) AS average_prior_product_breadth

FROM customer_segmentation_features

WHERE is_historical_only_purchaser = 1;


-- 4. Reproduce the recent-activity coverage found during feature assessment
-- and attach commercially useful customer characteristics to each pattern.
SELECT
    recent_activity_pattern,
    COUNT(*) AS customer_count,

    ROUND(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        1
    ) AS behavioural_customer_share_pct,

    ROUND(
        AVG(recency_days),
        1
    ) AS average_recency_days,

    ROUND(
        AVG(purchase_frequency_12m),
        2
    ) AS average_purchase_frequency,

    ROUND(
        AVG(observed_net_sales_12m),
        2
    ) AS average_observed_net_sales,

    ROUND(
        AVG(product_breadth_12m),
        1
    ) AS average_product_breadth

FROM customer_segmentation_features

WHERE is_behavioural_purchaser = 1

GROUP BY recent_activity_pattern

ORDER BY
    CASE recent_activity_pattern
        WHEN 'both periods' THEN 1
        WHEN 'recent only' THEN 2
        WHEN 'previous only' THEN 3
        WHEN 'neither period' THEN 4
        ELSE 5
    END;


-- 5. Reconfirm the behavioural observed-net-sales total after enrichment.
--
-- This check protects against accidentally changing the validated population
-- while adding descriptive features.
SELECT
    ROUND(
        SUM(observed_net_sales_12m),
        2
    ) AS enriched_feature_observed_net_sales

FROM customer_segmentation_features;


-- 6. Inspect the difference between total observed customer value and
-- qualifying purchase-invoice value.
--
-- Large differences are expected for some customers because standalone returns
-- and financial effects belong in net customer value but not in an average
-- qualifying purchase-invoice calculation.
SELECT
    customer_id_clean,

    purchase_frequency_12m,

    ROUND(
        observed_net_sales_12m,
        2
    ) AS observed_net_sales_12m,

    ROUND(
        qualifying_purchase_invoice_value_12m,
        2
    ) AS qualifying_purchase_invoice_value_12m,

    ROUND(
        average_qualifying_purchase_invoice_value_12m,
        2
    ) AS average_qualifying_purchase_invoice_value_12m,

    ROUND(
        qualifying_purchase_invoice_value_12m
        - observed_net_sales_12m,
        2
    ) AS purchase_vs_net_value_difference

FROM customer_segmentation_features

WHERE is_behavioural_purchaser = 1

ORDER BY
    ABS(
        qualifying_purchase_invoice_value_12m
        - observed_net_sales_12m
    ) DESC

LIMIT 15;