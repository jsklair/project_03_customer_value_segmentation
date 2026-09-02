-- Project 03: Customer Value & Retention Segmentation
-- Investigate invoices represented by more than one transaction timestamp.
--
-- The invoice layer requires one timestamp per invoice for later recency,
-- tenure and purchase-frequency calculations. Before choosing the first or
-- last timestamp, quantify how material the within-invoice variation is.


-- 1. Overall scale and timing range of affected invoices.
WITH timestamp_profile AS (
    SELECT
        invoice_clean,
        MAX(customer_id_clean) AS customer_id_clean,
        MAX(has_customer_id) AS has_customer_id,
        MAX(analysis_period) AS analysis_period,
        COUNT(*) AS transaction_line_count,
        COUNT(DISTINCT InvoiceDate) AS distinct_timestamps,
        MIN(InvoiceDate) AS first_timestamp,
        MAX(InvoiceDate) AS last_timestamp,
        (
            julianday(MAX(InvoiceDate))
            - julianday(MIN(InvoiceDate))
        ) * 24 * 60 AS span_minutes,
        MAX(counts_as_activity) AS has_qualifying_activity,
        MAX(is_cancellation) AS contains_cancellation,
        SUM(observed_net_sales) AS observed_invoice_value
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT InvoiceDate) > 1
)
SELECT
    COUNT(*) AS affected_invoices,
    SUM(has_customer_id) AS identified_invoices,
    SUM(has_qualifying_activity) AS qualifying_activity_invoices,
    SUM(contains_cancellation) AS cancellation_invoices,
    ROUND(MIN(span_minutes), 1) AS minimum_span_minutes,
    ROUND(AVG(span_minutes), 1) AS average_span_minutes,
    ROUND(MAX(span_minutes), 1) AS maximum_span_minutes
FROM timestamp_profile;


-- 2. Categorise the timestamp differences.
-- Short differences may simply reflect transaction-line entry timing,
-- whereas multi-day differences would raise a stronger invoice-grain concern.
WITH timestamp_profile AS (
    SELECT
        invoice_clean,
        (
            julianday(MAX(InvoiceDate))
            - julianday(MIN(InvoiceDate))
        ) * 24 * 60 AS span_minutes
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT InvoiceDate) > 1
)
SELECT
    CASE
        WHEN span_minutes <= 5 THEN '01: <= 5 minutes'
        WHEN span_minutes <= 60 THEN '02: > 5 to 60 minutes'
        WHEN span_minutes <= 1440 THEN '03: > 1 hour to 1 day'
        ELSE '04: > 1 day'
    END AS span_band,
    COUNT(*) AS invoice_count
FROM timestamp_profile
GROUP BY span_band
ORDER BY span_band;


-- 3. Check whether the affected invoices remain on a single calendar date.
WITH timestamp_profile AS (
    SELECT
        invoice_clean,
        MIN(InvoiceDate) AS first_timestamp,
        MAX(InvoiceDate) AS last_timestamp
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT InvoiceDate) > 1
)
SELECT
    CASE
        WHEN DATE(first_timestamp) = DATE(last_timestamp)
            THEN 'same_calendar_date'
        ELSE 'different_calendar_dates'
    END AS date_status,
    COUNT(*) AS invoice_count
FROM timestamp_profile
GROUP BY date_status
ORDER BY date_status;


-- 4. Inspect the invoices with the largest timestamp spans.
WITH timestamp_profile AS (
    SELECT
        invoice_clean,
        MAX(customer_id_clean) AS customer_id_clean,
        MAX(analysis_period) AS analysis_period,
        COUNT(*) AS transaction_line_count,
        COUNT(DISTINCT InvoiceDate) AS distinct_timestamps,
        MIN(InvoiceDate) AS first_timestamp,
        MAX(InvoiceDate) AS last_timestamp,
        (
            julianday(MAX(InvoiceDate))
            - julianday(MIN(InvoiceDate))
        ) * 24 * 60 AS span_minutes,
        MAX(counts_as_activity) AS has_qualifying_activity,
        MAX(is_cancellation) AS contains_cancellation,
        SUM(observed_net_sales) AS observed_invoice_value
    FROM classified_transactions
    GROUP BY invoice_clean
    HAVING COUNT(DISTINCT InvoiceDate) > 1
)
SELECT
    invoice_clean,
    customer_id_clean,
    analysis_period,
    transaction_line_count,
    distinct_timestamps,
    first_timestamp,
    last_timestamp,
    ROUND(span_minutes, 1) AS span_minutes,
    has_qualifying_activity,
    contains_cancellation,
    ROUND(observed_invoice_value, 2) AS observed_invoice_value
FROM timestamp_profile
ORDER BY span_minutes DESC, invoice_clean
LIMIT 20;