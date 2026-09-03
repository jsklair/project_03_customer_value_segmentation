-- Project 03: Customer Value & Retention Segmentation
-- Validate the snapshot segmentation against held-out future behaviour.
--
-- Segment assignment is fixed entirely from information available by
-- 31 May 2011. This file then measures behaviour from 1 June 2011 to
-- 30 November 2011.
--
-- The validation is descriptive/predictive rather than causal. Differences
-- between segments can demonstrate useful differentiation, but they cannot
-- show that belonging to a segment caused later purchasing behaviour.


DROP VIEW IF EXISTS customer_segment_validation;


CREATE VIEW customer_segment_validation AS

WITH validation_invoice_metrics AS (

    SELECT
        customer_id_clean,

        MIN(
            CASE
                WHEN has_qualifying_activity = 1
                THEN invoice_timestamp
            END
        ) AS first_validation_purchase_timestamp,

        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                THEN 1
                ELSE 0
            END
        ) AS validation_purchase_invoices,

        COUNT(
            DISTINCT CASE
                WHEN has_qualifying_activity = 1
                THEN strftime('%Y-%m', invoice_timestamp)
            END
        ) AS validation_active_months,

        -- Retain all signed customer-attributable financial effects when
        -- measuring future observed customer value.
        SUM(observed_invoice_value)
            AS validation_observed_net_sales,

        -- Separately retain value attached specifically to qualifying purchase
        -- invoices. This allows purchasing and later signed financial effects
        -- to be interpreted separately.
        SUM(
            CASE
                WHEN has_qualifying_activity = 1
                THEN observed_invoice_value
                ELSE 0
            END
        ) AS validation_qualifying_purchase_value

    FROM invoice_summary

    WHERE
        has_customer_id = 1
        AND analysis_period = 'validation'

    GROUP BY customer_id_clean
),

validation_product_breadth AS (

    SELECT
        customer_id_clean,

        COUNT(DISTINCT stock_code_clean)
            AS validation_product_breadth

    FROM classified_transactions

    WHERE
        has_customer_id = 1
        AND analysis_period = 'validation'
        AND counts_in_product_breadth = 1

    GROUP BY customer_id_clean
)

SELECT
    segments.*,

    invoices.first_validation_purchase_timestamp,

    COALESCE(
        invoices.validation_purchase_invoices,
        0
    ) AS validation_purchase_invoices,

    CASE
        WHEN COALESCE(
                 invoices.validation_purchase_invoices,
                 0
             ) > 0
        THEN 1
        ELSE 0
    END AS has_validation_purchase,

    COALESCE(
        invoices.validation_active_months,
        0
    ) AS validation_active_months,

    COALESCE(
        invoices.validation_observed_net_sales,
        0
    ) AS validation_observed_net_sales,

    COALESCE(
        invoices.validation_qualifying_purchase_value,
        0
    ) AS validation_qualifying_purchase_value,

    COALESCE(
        breadth.validation_product_breadth,
        0
    ) AS validation_product_breadth,

    -- Days to the first subsequent qualifying purchase gives an intuitive
    -- measure of how quickly customers return after the historical snapshot.
    CASE
        WHEN invoices.first_validation_purchase_timestamp IS NOT NULL
        THEN CAST(
            julianday(
                DATE(invoices.first_validation_purchase_timestamp)
            )
            - julianday('2011-05-31')
            AS INTEGER
        )
        ELSE NULL
    END AS days_to_next_purchase

FROM customer_segments AS segments

LEFT JOIN validation_invoice_metrics AS invoices
    ON segments.customer_id_clean = invoices.customer_id_clean

LEFT JOIN validation_product_breadth AS breadth
    ON segments.customer_id_clean = breadth.customer_id_clean;


-- 1. Ensure validation preserves the complete snapshot segment population.
SELECT
    COUNT(*) AS validation_rows,

    COUNT(DISTINCT customer_id_clean)
        AS unique_customers,

    SUM(
        CASE
            WHEN customer_segment IS NULL
            THEN 1 ELSE 0
        END
    ) AS missing_segments

FROM customer_segment_validation;


-- 2. Main held-out validation by segment.
SELECT
    customer_segment,

    COUNT(*) AS snapshot_customers,

    SUM(has_validation_purchase)
        AS future_purchasers,

    ROUND(
        100.0 * SUM(has_validation_purchase)
        / COUNT(*),
        1
    ) AS future_purchase_rate_pct,

    ROUND(
        AVG(validation_purchase_invoices),
        2
    ) AS average_future_purchase_frequency,

    ROUND(
        AVG(
            CASE
                WHEN has_validation_purchase = 1
                THEN validation_purchase_invoices
            END
        ),
        2
    ) AS average_frequency_among_future_purchasers,

    ROUND(
        AVG(
            CASE
                WHEN has_validation_purchase = 1
                THEN days_to_next_purchase
            END
        ),
        1
    ) AS average_days_to_next_purchase,

    ROUND(
        AVG(validation_observed_net_sales),
        2
    ) AS average_future_observed_net_sales,

    ROUND(
        SUM(validation_observed_net_sales),
        2
    ) AS total_future_observed_net_sales,

    ROUND(
        AVG(validation_product_breadth),
        1
    ) AS average_future_product_breadth

FROM customer_segment_validation

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


-- 3. Separate the value generated by customers who actually make a future
-- qualifying purchase from financial effects belonging to non-purchasers.
SELECT
    customer_segment,

    ROUND(
        AVG(
            CASE
                WHEN has_validation_purchase = 1
                THEN validation_observed_net_sales
            END
        ),
        2
    ) AS average_future_value_among_purchasers,

    ROUND(
        SUM(
            CASE
                WHEN has_validation_purchase = 1
                THEN validation_observed_net_sales
                ELSE 0
            END
        ),
        2
    ) AS future_value_from_purchasers,

    ROUND(
        SUM(
            CASE
                WHEN has_validation_purchase = 0
                THEN validation_observed_net_sales
                ELSE 0
            END
        ),
        2
    ) AS future_value_from_non_purchasers

FROM customer_segment_validation

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


-- 4. Specifically test whether the high-value lapsed group is a more useful
-- reactivation priority than the remainder of the historical-only population.
SELECT
    customer_segment,

    COUNT(*) AS lapsed_customers,

    SUM(has_validation_purchase)
        AS reactivated_customers,

    ROUND(
        100.0 * SUM(has_validation_purchase)
        / COUNT(*),
        1
    ) AS reactivation_rate_pct,

    ROUND(
        AVG(
            CASE
                WHEN has_validation_purchase = 1
                THEN days_to_next_purchase
            END
        ),
        1
    ) AS average_days_to_reactivation,

    ROUND(
        AVG(validation_observed_net_sales),
        2
    ) AS average_future_observed_net_sales,

    ROUND(
        SUM(validation_observed_net_sales),
        2
    ) AS total_future_observed_net_sales

FROM customer_segment_validation

WHERE customer_segment IN (
    'High-value lapsed',
    'Lapsed'
)

GROUP BY customer_segment

ORDER BY
    CASE customer_segment
        WHEN 'High-value lapsed' THEN 1
        WHEN 'Lapsed' THEN 2
    END;


-- 5. Show how much held-out positive observed value is associated with each
-- snapshot segment.
WITH positive_validation_total AS (

    SELECT
        SUM(
            CASE
                WHEN validation_observed_net_sales > 0
                THEN validation_observed_net_sales
                ELSE 0
            END
        ) AS total_positive_validation_value

    FROM customer_segment_validation
)

SELECT
    customer_segment,

    ROUND(
        SUM(
            CASE
                WHEN validation_observed_net_sales > 0
                THEN validation_observed_net_sales
                ELSE 0
            END
        ),
        2
    ) AS positive_future_observed_value,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN validation_observed_net_sales > 0
                THEN validation_observed_net_sales
                ELSE 0
            END
        )
        / MAX(
            positive_validation_total.total_positive_validation_value
        ),
        1
    ) AS positive_future_value_share_pct

FROM customer_segment_validation

CROSS JOIN positive_validation_total

GROUP BY customer_segment

ORDER BY positive_future_value_share_pct DESC;


-- 6. Validation totals across the complete snapshot population.
SELECT
    COUNT(*) AS snapshot_customers,

    SUM(has_validation_purchase)
        AS customers_with_future_purchase,

    ROUND(
        100.0 * SUM(has_validation_purchase)
        / COUNT(*),
        1
    ) AS overall_future_purchase_rate_pct,

    SUM(validation_purchase_invoices)
        AS future_purchase_invoices,

    ROUND(
        SUM(validation_observed_net_sales),
        2
    ) AS total_future_observed_net_sales,

    ROUND(
        SUM(validation_qualifying_purchase_value),
        2
    ) AS total_future_qualifying_purchase_value

FROM customer_segment_validation;