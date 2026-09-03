-- Project 03: Customer Value & Retention Segmentation
-- Sensitivity checks for the final customer segmentation.
--
-- The primary analysis deliberately retains exact within-sheet source
-- duplicates because there is no transaction-line identifier proving that
-- identical rows are erroneous.
--
-- Manual transactions are also retained in observed customer value because
-- profiling showed that they contain real signed customer-attributable
-- financial effects, despite not representing fresh purchasing activity.
--
-- This file asks whether either decision materially changes final segment
-- membership or held-out conclusions.
--
-- A third check removes the highest 1% of behavioural snapshot-value
-- customers from validation summaries to test whether extreme customers alone
-- drive the main future-behaviour story.
--
-- These are sensitivity analyses only. They do not replace the documented
-- primary treatment unless a material instability is found.


DROP TABLE IF EXISTS temp.deduplicated_transactions;


-- Reproduce the alternative blanket exact-deduplication scenario that was
-- deliberately rejected as the primary cleaning rule.
--
-- Exact duplicates are defined using the eight original workbook fields.
-- source_row_id is excluded because it was added analytically after loading.
CREATE TEMP TABLE deduplicated_transactions AS

WITH ranked_source_rows AS (

    SELECT
        transactions.*,

        ROW_NUMBER() OVER (
            PARTITION BY
                "Invoice",
                "StockCode",
                "Description",
                Quantity,
                InvoiceDate,
                Price,
                "Customer ID",
                Country
            ORDER BY source_row_id
        ) AS exact_duplicate_row_number

    FROM classified_transactions AS transactions
)

SELECT *
FROM ranked_source_rows
WHERE exact_duplicate_row_number = 1;


-- Aggregate alternative customer monetary values.
--
-- Frequency, recency and breadth do not need to be redefined here:
--
-- * removing an exact duplicate transaction line still leaves the same
--   qualifying invoice/product occurrence represented once;
-- * Manual transactions do not count as purchasing activity or product
--   breadth in the primary methodology.
--
-- The main potential segment effect is therefore through customer value and
-- the resulting top-20% value ranks.
DROP TABLE IF EXISTS temp.sensitivity_customer_values;


CREATE TEMP TABLE sensitivity_customer_values AS

WITH no_manual_values AS (

    SELECT
        segments.customer_id_clean,

        SUM(
            CASE
                WHEN transactions.analysis_period = 'behavioural'
                     AND transactions.transaction_class <> 'manual'
                THEN transactions.observed_net_sales
                ELSE 0
            END
        ) AS no_manual_behavioural_value,

        SUM(
            CASE
                WHEN transactions.analysis_period = 'pre_behavioural'
                     AND transactions.transaction_class <> 'manual'
                THEN transactions.observed_net_sales
                ELSE 0
            END
        ) AS no_manual_prior_value

    FROM customer_segments AS segments

    LEFT JOIN classified_transactions AS transactions
        ON segments.customer_id_clean
           = transactions.customer_id_clean

    GROUP BY segments.customer_id_clean
),

deduplicated_values AS (

    SELECT
        segments.customer_id_clean,

        SUM(
            CASE
                WHEN transactions.analysis_period = 'behavioural'
                THEN transactions.observed_net_sales
                ELSE 0
            END
        ) AS deduplicated_behavioural_value,

        SUM(
            CASE
                WHEN transactions.analysis_period = 'pre_behavioural'
                THEN transactions.observed_net_sales
                ELSE 0
            END
        ) AS deduplicated_prior_value

    FROM customer_segments AS segments

    LEFT JOIN deduplicated_transactions AS transactions
        ON segments.customer_id_clean
           = transactions.customer_id_clean

    GROUP BY segments.customer_id_clean
)

SELECT
    segments.customer_id_clean,
    segments.customer_segment,

    segments.is_behavioural_purchaser,
    segments.is_historical_only_purchaser,

    segments.recency_days,
    segments.purchase_frequency_12m,

    segments.observed_net_sales_12m
        AS primary_behavioural_value,

    segments.prior_observed_net_sales
        AS primary_prior_value,

    COALESCE(
        no_manual.no_manual_behavioural_value,
        0
    ) AS no_manual_behavioural_value,

    COALESCE(
        no_manual.no_manual_prior_value,
        0
    ) AS no_manual_prior_value,

    COALESCE(
        deduplicated.deduplicated_behavioural_value,
        0
    ) AS deduplicated_behavioural_value,

    COALESCE(
        deduplicated.deduplicated_prior_value,
        0
    ) AS deduplicated_prior_value

FROM customer_segments AS segments

LEFT JOIN no_manual_values AS no_manual
    ON segments.customer_id_clean
       = no_manual.customer_id_clean

LEFT JOIN deduplicated_values AS deduplicated
    ON segments.customer_id_clean
       = deduplicated.customer_id_clean;


-- Reapply the exact final segmentation logic using the alternative monetary
-- measures. Only the value ranks can change; all snapshot timing and purchase
-- behaviour remains fixed.
DROP TABLE IF EXISTS temp.sensitivity_segments;


CREATE TEMP TABLE sensitivity_segments AS

WITH no_manual_behavioural_rank AS (

    SELECT
        customer_id_clean,

        NTILE(5) OVER (
            ORDER BY
                no_manual_behavioural_value DESC,
                customer_id_clean
        ) AS value_fifth

    FROM sensitivity_customer_values

    WHERE is_behavioural_purchaser = 1
),

no_manual_historical_rank AS (

    SELECT
        customer_id_clean,

        NTILE(5) OVER (
            ORDER BY
                no_manual_prior_value DESC,
                customer_id_clean
        ) AS value_fifth

    FROM sensitivity_customer_values

    WHERE is_historical_only_purchaser = 1
),

deduplicated_behavioural_rank AS (

    SELECT
        customer_id_clean,

        NTILE(5) OVER (
            ORDER BY
                deduplicated_behavioural_value DESC,
                customer_id_clean
        ) AS value_fifth

    FROM sensitivity_customer_values

    WHERE is_behavioural_purchaser = 1
),

deduplicated_historical_rank AS (

    SELECT
        customer_id_clean,

        NTILE(5) OVER (
            ORDER BY
                deduplicated_prior_value DESC,
                customer_id_clean
        ) AS value_fifth

    FROM sensitivity_customer_values

    WHERE is_historical_only_purchaser = 1
),

ranked AS (

    SELECT
        customer_values.*,

        no_manual_behavioural.value_fifth
            AS no_manual_behavioural_fifth,

        no_manual_historical.value_fifth
            AS no_manual_historical_fifth,

        deduplicated_behavioural.value_fifth
            AS deduplicated_behavioural_fifth,

        deduplicated_historical.value_fifth
            AS deduplicated_historical_fifth

    FROM sensitivity_customer_values AS customer_values

    LEFT JOIN no_manual_behavioural_rank AS no_manual_behavioural
        ON customer_values.customer_id_clean
           = no_manual_behavioural.customer_id_clean

    LEFT JOIN no_manual_historical_rank AS no_manual_historical
        ON customer_values.customer_id_clean
           = no_manual_historical.customer_id_clean

    LEFT JOIN deduplicated_behavioural_rank AS deduplicated_behavioural
        ON customer_values.customer_id_clean
           = deduplicated_behavioural.customer_id_clean

    LEFT JOIN deduplicated_historical_rank AS deduplicated_historical
        ON customer_values.customer_id_clean
           = deduplicated_historical.customer_id_clean
)

SELECT
    ranked.*,

    CASE
        WHEN is_historical_only_purchaser = 1
             AND no_manual_historical_fifth = 1
            THEN 'High-value lapsed'

        WHEN is_historical_only_purchaser = 1
            THEN 'Lapsed'

        WHEN no_manual_behavioural_fifth = 1
             AND recency_days <= 180
            THEN 'High-value active'

        WHEN no_manual_behavioural_fifth = 1
            THEN 'High-value at risk'

        WHEN purchase_frequency_12m >= 5
             AND recency_days <= 180
            THEN 'Core repeat'

        WHEN recency_days <= 90
            THEN 'Recent low-frequency'

        WHEN recency_days <= 180
            THEN 'Cooling low-frequency'

        ELSE 'Drifting'
    END AS no_manual_segment,

    CASE
        WHEN is_historical_only_purchaser = 1
             AND deduplicated_historical_fifth = 1
            THEN 'High-value lapsed'

        WHEN is_historical_only_purchaser = 1
            THEN 'Lapsed'

        WHEN deduplicated_behavioural_fifth = 1
             AND recency_days <= 180
            THEN 'High-value active'

        WHEN deduplicated_behavioural_fifth = 1
            THEN 'High-value at risk'

        WHEN purchase_frequency_12m >= 5
             AND recency_days <= 180
            THEN 'Core repeat'

        WHEN recency_days <= 90
            THEN 'Recent low-frequency'

        WHEN recency_days <= 180
            THEN 'Cooling low-frequency'

        ELSE 'Drifting'
    END AS deduplicated_segment

FROM ranked;


-- 1. Confirm that the alternative duplicate treatment removes exactly the
-- previously profiled excess duplicate rows.
SELECT
    (
        SELECT COUNT(*)
        FROM classified_transactions
    ) AS primary_rows,

    (
        SELECT COUNT(*)
        FROM deduplicated_transactions
    ) AS deduplicated_rows,

    (
        SELECT COUNT(*)
        FROM classified_transactions
    )
    -
    (
        SELECT COUNT(*)
        FROM deduplicated_transactions
    ) AS removed_exact_duplicate_rows;


-- 2. Quantify the monetary effect of both sensitivity scenarios.
SELECT
    ROUND(
        SUM(primary_behavioural_value),
        2
    ) AS primary_behavioural_value,

    ROUND(
        SUM(no_manual_behavioural_value),
        2
    ) AS no_manual_behavioural_value,

    ROUND(
        SUM(deduplicated_behavioural_value),
        2
    ) AS deduplicated_behavioural_value,

    ROUND(
        100.0
        * (
            SUM(no_manual_behavioural_value)
            - SUM(primary_behavioural_value)
        )
        / SUM(primary_behavioural_value),
        2
    ) AS no_manual_change_pct,

    ROUND(
        100.0
        * (
            SUM(deduplicated_behavioural_value)
            - SUM(primary_behavioural_value)
        )
        / SUM(primary_behavioural_value),
        2
    ) AS deduplicated_change_pct

FROM sensitivity_customer_values;


-- 3. Test whether either treatment decision materially changes final customer
-- segment membership.
SELECT
    'exclude Manual value' AS sensitivity_scenario,

    SUM(
        CASE
            WHEN customer_segment <> no_manual_segment
            THEN 1 ELSE 0
        END
    ) AS changed_customers,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_segment <> no_manual_segment
                THEN 1 ELSE 0
            END
        )
        / COUNT(*),
        2
    ) AS changed_customer_pct

FROM sensitivity_segments

UNION ALL

SELECT
    'remove exact duplicates',

    SUM(
        CASE
            WHEN customer_segment <> deduplicated_segment
            THEN 1 ELSE 0
        END
    ),

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN customer_segment <> deduplicated_segment
                THEN 1 ELSE 0
            END
        )
        / COUNT(*),
        2
    )

FROM sensitivity_segments;


-- 4. Show exactly which segment transitions occur under the alternatives.
SELECT
    'exclude Manual value' AS sensitivity_scenario,
    customer_segment AS primary_segment,
    no_manual_segment AS sensitivity_segment,
    COUNT(*) AS customer_count

FROM sensitivity_segments

WHERE customer_segment <> no_manual_segment

GROUP BY
    customer_segment,
    no_manual_segment

UNION ALL

SELECT
    'remove exact duplicates',
    customer_segment,
    deduplicated_segment,
    COUNT(*)

FROM sensitivity_segments

WHERE customer_segment <> deduplicated_segment

GROUP BY
    customer_segment,
    deduplicated_segment

ORDER BY
    sensitivity_scenario,
    primary_segment,
    sensitivity_segment;


-- 5. Compare the high-value monetary boundaries under each treatment.
WITH scenario_boundaries AS (

    SELECT
        'primary' AS scenario,

        MIN(
            CASE
                WHEN is_behavioural_purchaser = 1
                     AND (
                         customer_segment = 'High-value active'
                         OR customer_segment = 'High-value at risk'
                     )
                THEN primary_behavioural_value
            END
        ) AS behavioural_high_value_boundary,

        MIN(
            CASE
                WHEN customer_segment = 'High-value lapsed'
                THEN primary_prior_value
            END
        ) AS historical_high_value_boundary

    FROM sensitivity_segments

    UNION ALL

    SELECT
        'exclude Manual value',

        MIN(
            CASE
                WHEN is_behavioural_purchaser = 1
                     AND (
                         no_manual_segment = 'High-value active'
                         OR no_manual_segment = 'High-value at risk'
                     )
                THEN no_manual_behavioural_value
            END
        ),

        MIN(
            CASE
                WHEN no_manual_segment = 'High-value lapsed'
                THEN no_manual_prior_value
            END
        )

    FROM sensitivity_segments

    UNION ALL

    SELECT
        'remove exact duplicates',

        MIN(
            CASE
                WHEN is_behavioural_purchaser = 1
                     AND (
                         deduplicated_segment = 'High-value active'
                         OR deduplicated_segment = 'High-value at risk'
                     )
                THEN deduplicated_behavioural_value
            END
        ),

        MIN(
            CASE
                WHEN deduplicated_segment = 'High-value lapsed'
                THEN deduplicated_prior_value
            END
        )

    FROM sensitivity_segments
)

SELECT
    scenario,

    ROUND(
        behavioural_high_value_boundary,
        2
    ) AS behavioural_high_value_boundary,

    ROUND(
        historical_high_value_boundary,
        2
    ) AS historical_high_value_boundary

FROM scenario_boundaries;


-- 6. Test the held-out validation after excluding the highest 1% of
-- behavioural customers by snapshot observed net sales.
--
-- If the broad future-purchase ordering remains, the validation story is not
-- dependent on a handful of wholesale-scale customers.
WITH behavioural_snapshot_rank AS (

    SELECT
        customer_id_clean,

        NTILE(100) OVER (
            ORDER BY
                observed_net_sales_12m DESC,
                customer_id_clean
        ) AS snapshot_value_percentile

    FROM customer_segments

    WHERE is_behavioural_purchaser = 1
),

robust_validation AS (

    SELECT
        validation.*

    FROM customer_segment_validation AS validation

    INNER JOIN behavioural_snapshot_rank AS ranks
        ON validation.customer_id_clean
           = ranks.customer_id_clean

    WHERE ranks.snapshot_value_percentile > 1
),

positive_future_total AS (

    SELECT
        SUM(
            CASE
                WHEN validation_observed_net_sales > 0
                THEN validation_observed_net_sales
                ELSE 0
            END
        ) AS positive_future_value

    FROM robust_validation
)

SELECT
    customer_segment,

    COUNT(*) AS customers_after_top_1pct_exclusion,

    ROUND(
        100.0 * SUM(has_validation_purchase)
        / COUNT(*),
        1
    ) AS future_purchase_rate_pct,

    ROUND(
        AVG(validation_observed_net_sales),
        2
    ) AS average_future_observed_net_sales,

    ROUND(
        100.0
        * SUM(
            CASE
                WHEN validation_observed_net_sales > 0
                THEN validation_observed_net_sales
                ELSE 0
            END
        )
        / MAX(positive_future_total.positive_future_value),
        1
    ) AS positive_future_value_share_pct

FROM robust_validation

CROSS JOIN positive_future_total

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


-- 7. Test whether Manual removal or exact deduplication materially changes
-- held-out observed value by the FINAL primary segment.
--
-- Segment labels remain fixed here. This isolates sensitivity of the future
-- monetary outcome itself rather than mixing outcome changes with alternative
-- segment membership.
WITH no_manual_validation AS (

    SELECT
        segments.customer_id_clean,

        SUM(
            CASE
                WHEN transactions.analysis_period = 'validation'
                     AND transactions.transaction_class <> 'manual'
                THEN transactions.observed_net_sales
                ELSE 0
            END
        ) AS validation_value

    FROM customer_segments AS segments

    LEFT JOIN classified_transactions AS transactions
        ON segments.customer_id_clean
           = transactions.customer_id_clean

    GROUP BY segments.customer_id_clean
),

deduplicated_validation AS (

    SELECT
        segments.customer_id_clean,

        SUM(
            CASE
                WHEN transactions.analysis_period = 'validation'
                THEN transactions.observed_net_sales
                ELSE 0
            END
        ) AS validation_value

    FROM customer_segments AS segments

    LEFT JOIN deduplicated_transactions AS transactions
        ON segments.customer_id_clean
           = transactions.customer_id_clean

    GROUP BY segments.customer_id_clean
)

SELECT
    segments.customer_segment,

    ROUND(
        SUM(validation.validation_observed_net_sales),
        2
    ) AS primary_future_value,

    ROUND(
        SUM(no_manual.validation_value),
        2
    ) AS no_manual_future_value,

    ROUND(
        SUM(deduplicated.validation_value),
        2
    ) AS deduplicated_future_value,

    ROUND(
        100.0
        * (
            SUM(no_manual.validation_value)
            - SUM(validation.validation_observed_net_sales)
        )
        / NULLIF(
            SUM(validation.validation_observed_net_sales),
            0
        ),
        1
    ) AS no_manual_change_pct,

    ROUND(
        100.0
        * (
            SUM(deduplicated.validation_value)
            - SUM(validation.validation_observed_net_sales)
        )
        / NULLIF(
            SUM(validation.validation_observed_net_sales),
            0
        ),
        1
    ) AS deduplicated_change_pct

FROM customer_segments AS segments

INNER JOIN customer_segment_validation AS validation
    ON segments.customer_id_clean
       = validation.customer_id_clean

INNER JOIN no_manual_validation AS no_manual
    ON segments.customer_id_clean
       = no_manual.customer_id_clean

INNER JOIN deduplicated_validation AS deduplicated
    ON segments.customer_id_clean
       = deduplicated.customer_id_clean

GROUP BY segments.customer_segment

ORDER BY
    CASE segments.customer_segment
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