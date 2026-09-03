-- Project 03: Customer Value & Retention Segmentation
-- Build and validate the invoice-level analytical layer.
--
-- This layer reduces classified transaction lines to one row per invoice
-- while preserving customer attribution, analytical-period separation,
-- purchasing-activity eligibility and signed observed value.
--
-- The presence of qualifying activity is recorded here, but the final
-- customer purchase-frequency definition is deliberately deferred to the
-- customer-feature stage.


-- 1. Confirm that each invoice can be treated as one analytical unit.
-- An invoice should not be linked to more than one identified customer.
SELECT
    COUNT(*) AS invoices_with_multiple_customers
FROM (
    SELECT
        invoice_clean
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT customer_id_clean) > 1
);


-- 2. Check whether any invoice mixes identified and unidentified rows.
-- Profiling found none; reconfirm this independently in SQLite.
SELECT
    COUNT(*) AS invoices_with_mixed_customer_status
FROM (
    SELECT
        invoice_clean
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING MIN(has_customer_id) <> MAX(has_customer_id)
);


-- 3. Check whether any invoice crosses analytical periods.
-- This protects the snapshot/held-out validation separation.
SELECT
    COUNT(*) AS invoices_spanning_multiple_periods
FROM (
    SELECT
        invoice_clean
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT analysis_period) > 1
);


-- 4. Identify invoices represented by more than one transaction timestamp.
-- A separate investigation found 83 such invoices: all timestamps remain
-- within the same calendar date, 82 span no more than five minutes and the
-- maximum span is nine minutes. The first timestamp is therefore used as
-- the invoice timestamp without affecting period assignment or meaningful
-- day-level recency analysis.
SELECT
    COUNT(*) AS invoices_with_multiple_timestamps
FROM (
    SELECT
        invoice_clean
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT InvoiceDate) > 1
);


DROP TABLE IF EXISTS invoice_summary;


-- 5. Build one row per invoice.
--
-- Materialise this stable analytical grain because several downstream
-- customer calculations reuse it. Keeping it as a view would repeatedly
-- recompute the million-row transaction aggregation.
CREATE TABLE invoice_summary AS
SELECT
    invoice_clean,

    -- Earlier checks establish that an invoice belongs to no more than
    -- one identified customer, so MAX safely retains that identifier.
    MAX(customer_id_clean) AS customer_id_clean,
    MAX(has_customer_id) AS has_customer_id,

    -- Retain timing explicitly so later customer features can respect
    -- the 31 May 2011 historical snapshot.
    -- A small number of invoices contain line timestamps a few minutes apart.
    -- Investigation confirmed all remain within one calendar date, so the first
    -- recorded timestamp provides a consistent invoice-level timestamp.
    MIN(InvoiceDate) AS invoice_timestamp,
    MAX(analysis_period) AS analysis_period,

    COUNT(*) AS transaction_line_count,

    -- Record whether the invoice contains genuine purchasing activity.
    -- This does not yet define customer purchase frequency.
    MAX(counts_as_activity) AS has_qualifying_activity,
    SUM(counts_as_activity) AS qualifying_activity_line_count,

    -- Returns affect observed customer value but do not independently
    -- create purchasing activity under the agreed methodology.
    MAX(is_cancellation) AS contains_cancellation,
    SUM(is_cancellation) AS cancellation_line_count,

    MAX(is_manual) AS contains_manual,
    SUM(is_manual) AS manual_line_count,

    -- Product breadth uses distinct eligible product codes rather than
    -- raw transaction-line counts.
    COUNT(
        DISTINCT CASE
            WHEN counts_in_product_breadth = 1
            THEN stock_code_clean
        END
    ) AS distinct_products,

    -- Preserve the monetary layers without rounding at this stage.
    -- Avoiding per-invoice rounding prevents small cumulative differences
    -- when invoice totals are reconciled back to transaction-level values.
    SUM(raw_line_value) AS raw_invoice_value,
    SUM(classified_net_sales) AS classified_invoice_value,
    SUM(observed_net_sales) AS observed_invoice_value

FROM classified_transactions
GROUP BY invoice_clean;


-- Support repeated customer- and period-level lookups downstream.
CREATE UNIQUE INDEX idx_invoice_summary_invoice
    ON invoice_summary (invoice_clean);

CREATE INDEX idx_invoice_summary_customer_period
    ON invoice_summary (customer_id_clean, analysis_period);

CREATE INDEX idx_invoice_summary_period_activity
    ON invoice_summary (analysis_period, has_qualifying_activity);


-- 6. Reconcile invoice grain.
SELECT
    COUNT(*) AS invoice_summary_rows,
    (
        SELECT COUNT(DISTINCT invoice_clean)
        FROM classified_transactions
    ) AS distinct_source_invoices
FROM invoice_summary;


-- 7. Reconcile invoice counts by analytical period.
SELECT
    analysis_period,
    COUNT(*) AS invoice_count
FROM invoice_summary
GROUP BY analysis_period
ORDER BY analysis_period;


-- 8. Inspect customer identification at invoice level.
SELECT
    CASE
        WHEN has_customer_id = 1 THEN 'identified_customer'
        ELSE 'missing_customer_id'
    END AS customer_status,
    COUNT(*) AS invoice_count
FROM invoice_summary
GROUP BY customer_status
ORDER BY customer_status;


-- 9. Inspect the potential purchasing-activity population.
-- This is diagnostic only and does not yet define customer frequency.
SELECT
    analysis_period,
    COUNT(*) AS all_invoices,
    SUM(has_qualifying_activity) AS invoices_with_qualifying_activity
FROM invoice_summary
GROUP BY analysis_period
ORDER BY analysis_period;


-- 10. Reconcile invoice-level observed value to the transaction layer.
SELECT
    ROUND(
        (
            SELECT SUM(observed_net_sales)
            FROM classified_transactions
        ),
        2
    ) AS transaction_observed_value,

    ROUND(
        SUM(observed_invoice_value),
        2
    ) AS invoice_observed_value
FROM invoice_summary;