# -*- coding: utf-8 -*-

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCRIPT = PROJECT_ROOT / "python" / "01_profile_source_data.py"

CLEANED_FILE = (
    PROJECT_ROOT
    / "data"
    / "cleaned"
    / "online_retail_transactions_classified.pkl"
)

CLASSIFICATION_SUMMARY_FILE = (
    PROJECT_ROOT
    / "reports"
    / "transaction_classification_summary.csv"
)

UNRESOLVED_SUMMARY_FILE = (
    PROJECT_ROOT
    / "reports"
    / "unresolved_transaction_classifications.csv"
)

EXPECTED_SOURCE_ROWS = 1_044_848

EXPECTED_SOURCE_COLUMNS = (
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
)

CLEANING_VERSION = 1

# These boundaries implement the settled historical snapshot design.
# Segmentation features will use only behavioural information available
# by 31 May 2011. Later activity is retained separately for validation.
BEHAVIOURAL_START = pd.Timestamp("2010-06-01")
VALIDATION_START = pd.Timestamp("2011-06-01")
VALIDATION_END = pd.Timestamp("2011-12-01")


# ---------------------------------------------------------------------
# Transaction-code definitions
# ---------------------------------------------------------------------

# These codes were investigated during source profiling and classified
# according to their business meaning. They should not contribute to
# customer purchasing activity, observed customer value or product breadth.
HARD_EXCLUSION_CLASSES = {
    "B": "bad_debt_adjustment",
    "BANK CHARGES": "bank_charge",
    "AMAZONFEE": "amazon_platform_fee",
    "CRUK": "commission",
    "ADJUST": "administrative_adjustment",
    "ADJUST2": "administrative_adjustment",
    "TEST001": "test_record",
    "TEST002": "test_record",
    "S": "sample",
}

POSTAGE_CODES = {
    "POST",
    "DOT",
    "C2",
}

DISCOUNT_CODES = {
    "D",
}

MANUAL_CODES = {
    "M",
}

GIFT_VOUCHER_PREFIXES = (
    "GIFT_0001_",
)

# Most genuine merchandise follows the source's documented five-digit
# StockCode pattern, sometimes with one or two trailing letters.
#
# Failing this pattern is NOT treated as proof that a row is invalid.
# Unfamiliar non-standard codes are surfaced for investigation instead.
STANDARD_PRODUCT_PATTERN = r"\d{5}[A-Z]{0,2}"

# Add a code here only after profiling has established that an unusual
# non-standard StockCode represents genuine merchandise.
#
# Keeping this explicit prevents unfamiliar codes from being silently
# treated as customer purchases simply because they are inconvenient
# to classify.

# These non-standard StockCodes were reviewed after the first cleaning run.
# Their descriptions represent physical merchandise rather than accounting
# or operational concepts. They are therefore eligible for merchandise
# treatment despite not matching the usual numeric StockCode pattern.
KNOWN_GENUINE_MERCHANDISE_CODES = {
    "DCGS0003",
    "DCGS0004",
    "DCGS0037",
    "DCGS0041",
    "DCGS0044",
    "DCGS0058",
    "DCGS0062",
    "DCGS0066N",
    "DCGS0068",
    "DCGS0069",
    "DCGS0070",
    "DCGS0072",
    "DCGS0075",
    "DCGS0076",
    "DCGSSBOY",
    "DCGSSGIRL",
    "PADS",
    "SP1002",
}

# A small number of source rows use a genuine product StockCode but contain
# an explicit administrative description rather than a customer transaction.
ADMINISTRATIVE_DESCRIPTION_VALUES = {
    "UPDATE",
}

# These classes contribute their signed line value to the commercial
# transaction measure before customer-identification eligibility is applied.
FINANCIAL_TRANSACTION_CLASSES = {
    "customer_cancellation_return",
    "manual",
    "postage_carriage",
    "discount",
    "gift_voucher",
    "merchandise",
}


# ---------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------


def print_section(title):
    """Print a consistent heading for cleaning output."""
    print(f"\n--- {title} ---")


def clean_text(series, uppercase=False):
    """Trim text consistently while preserving missing values."""
    cleaned = series.astype("string").str.strip()

    if uppercase:
        cleaned = cleaned.str.upper()

    return cleaned


# ---------------------------------------------------------------------
# Corrected source loading
# ---------------------------------------------------------------------


def load_profile_module():
    """
    Load the profiling module so source-construction logic has one owner.

    Script 01 already contains the validated logic for removing the proven
    cross-sheet overlap while retaining within-sheet duplicates. Reusing that
    loader avoids creating a second implementation of the same source rule.
    """
    if not PROFILE_SCRIPT.exists():
        raise FileNotFoundError(
            f"Profiling script not found: {PROFILE_SCRIPT}"
        )

    spec = spec_from_file_location(
        "project03_profile_source_data",
        PROFILE_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load profiling script: {PROFILE_SCRIPT}"
        )

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def load_corrected_source():
    """
    Load the overlap-corrected transaction source created by script 01.

    The returned DataFrame is copied before cleaning so the cached profiling
    dataset remains unchanged.
    """
    profile_module = load_profile_module()

    if not hasattr(profile_module, "load_transactions"):
        raise AttributeError(
            "01_profile_source_data.py does not expose "
            "load_transactions()."
        )

    transactions, overlap_summary = (
        profile_module.load_transactions()
    )

    validate_corrected_source(
        transactions,
        overlap_summary,
    )

    return transactions.copy()


def validate_corrected_source(
    transactions,
    overlap_summary,
):
    """
    Confirm that cleaning starts from the agreed corrected source dataset.

    These checks protect the cleaning pipeline from silently running against
    the original naïve worksheet concatenation or a stale cached dataset.
    """
    missing_columns = [
        column
        for column in EXPECTED_SOURCE_COLUMNS
        if column not in transactions.columns
    ]

    if missing_columns:
        raise ValueError(
            "Corrected source is missing columns: "
            f"{missing_columns}"
        )

    if len(transactions) != EXPECTED_SOURCE_ROWS:
        raise ValueError(
            "Corrected source row count does not match the "
            "profiling decision: "
            f"expected {EXPECTED_SOURCE_ROWS:,}, "
            f"found {len(transactions):,}."
        )

    removed_overlap = overlap_summary.get(
        "removed_later_overlap_rows"
    )

    if removed_overlap != 22_523:
        raise ValueError(
            "Source-overlap evidence does not match the agreed "
            "profiling result: expected 22,523 removed rows, "
            f"found {removed_overlap}."
        )

    required_non_missing = [
        "Invoice",
        "StockCode",
        "Quantity",
        "InvoiceDate",
        "Price",
    ]

    missing_required = (
        transactions[required_non_missing]
        .isna()
        .sum()
    )

    if (missing_required > 0).any():
        raise ValueError(
            "Unexpected missing values in required transaction "
            "fields:\n"
            f"{missing_required[missing_required > 0].to_string()}"
        )


# ---------------------------------------------------------------------
# Normalised analytical fields
# ---------------------------------------------------------------------


def build_customer_id(raw_customer_id):
    """
    Create a nullable integer customer identifier.

    Customer ID is represented numerically in the workbook, usually as
    floating-point values because missing values are present. Converting to
    pandas Int64 gives analytically cleaner identifiers while still allowing
    missing values.

    Unexpected non-numeric or fractional identifiers are treated as data
    quality failures rather than being silently converted to missing.
    """
    numeric_id = pd.to_numeric(
        raw_customer_id,
        errors="coerce",
    )

    conversion_failed = (
        raw_customer_id.notna()
        & numeric_id.isna()
    )

    if conversion_failed.any():
        examples = (
            raw_customer_id
            .loc[conversion_failed]
            .head(10)
            .tolist()
        )

        raise ValueError(
            "Unexpected non-numeric Customer ID values: "
            f"{examples}"
        )

    non_missing = numeric_id.dropna()

    fractional = non_missing.mod(1).ne(0)

    if fractional.any():
        examples = (
            non_missing
            .loc[fractional]
            .head(10)
            .tolist()
        )

        raise ValueError(
            "Unexpected non-integer Customer ID values: "
            f"{examples}"
        )

    return numeric_id.astype("Int64")


def assign_analysis_period(invoice_date):
    """
    Label each row without deleting data outside the core analysis windows.

    Keeping the complete corrected source makes the timing rules auditable.
    Downstream customer features can then filter the behavioural period
    explicitly rather than relying on rows having been removed earlier.
    """
    period = pd.Series(
        "outside_analysis",
        index=invoice_date.index,
        dtype="string",
    )

    period.loc[
        invoice_date < BEHAVIOURAL_START
    ] = "pre_behavioural"

    period.loc[
        invoice_date.ge(BEHAVIOURAL_START)
        & invoice_date.lt(VALIDATION_START)
    ] = "behavioural"

    period.loc[
        invoice_date.ge(VALIDATION_START)
        & invoice_date.lt(VALIDATION_END)
    ] = "validation"

    return period.astype("category")


def add_normalised_fields(transactions):
    """
    Preserve source fields and add cleaned analytical versions beside them.

    The original fields remain untouched wherever practical so later analysis
    can be reconciled directly with the source.
    """
    cleaned = transactions.copy()

    # This is an analytical row reference, not a claim that the source has a
    # genuine transaction-line identifier. It simply preserves the corrected
    # source ordering for later reconciliation and investigation.
    cleaned.insert(
        0,
        "source_row_id",
        pd.RangeIndex(
            1,
            len(cleaned) + 1,
        ),
    )

    cleaned["invoice_clean"] = clean_text(
        cleaned["Invoice"],
        uppercase=True,
    )

    cleaned["stock_code_clean"] = clean_text(
        cleaned["StockCode"],
        uppercase=True,
    )

    cleaned["description_clean"] = (
        clean_text(cleaned["Description"])
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )

    cleaned["country_clean"] = (
        clean_text(cleaned["Country"])
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )

    cleaned["customer_id_clean"] = build_customer_id(
        cleaned["Customer ID"]
    )

    cleaned["InvoiceDate"] = pd.to_datetime(
        cleaned["InvoiceDate"]
    )

    cleaned["analysis_period"] = assign_analysis_period(
        cleaned["InvoiceDate"]
    )

    # These diagnostics preserve characteristics that may overlap with the
    # primary transaction class. For example, a manual row can also be a
    # cancellation, and that evidence should remain visible after classification.
    cleaned["has_customer_id"] = (
        cleaned["customer_id_clean"].notna()
    )

    cleaned["is_cancellation"] = (
        cleaned["invoice_clean"]
        .str.startswith(
            "C",
            na=False,
        )
    )

    cleaned["is_manual"] = (
        cleaned["stock_code_clean"]
        .isin(MANUAL_CODES)
    )

    cleaned["is_zero_price"] = (
        cleaned["Price"].eq(0)
    )

    cleaned["is_negative_price"] = (
        cleaned["Price"].lt(0)
    )

    cleaned["is_zero_quantity"] = (
        cleaned["Quantity"].eq(0)
    )

    cleaned["is_negative_quantity"] = (
        cleaned["Quantity"].lt(0)
    )

    cleaned["is_standard_product_code"] = (
        cleaned["stock_code_clean"]
        .str.fullmatch(
            STANDARD_PRODUCT_PATTERN,
            na=False,
        )
    )

    cleaned["is_known_genuine_unusual_code"] = (
        cleaned["stock_code_clean"]
        .isin(
            KNOWN_GENUINE_MERCHANDISE_CODES
        )
    )

    # Preserve the mechanical source value independently of whether the line
    # is later considered relevant to customer value.
    cleaned["raw_line_value"] = (
        cleaned["Quantity"]
        * cleaned["Price"]
    )

    return cleaned


# ---------------------------------------------------------------------
# Transaction classification
# ---------------------------------------------------------------------


def classify_transactions(cleaned):
    """
    Assign one primary transaction class using the agreed precedence.

    Specific known business meanings take precedence over the generic
    cancellation label. Supporting diagnostic flags such as is_cancellation
    preserve overlapping characteristics separately from the primary class.
    """
    transaction_class = pd.Series(
        pd.NA,
        index=cleaned.index,
        dtype="string",
    )

    stock_code = cleaned["stock_code_clean"]

    def assign(mask, class_name):
        """
        Assign a class only where a higher-precedence rule has not already won.
        """
        available = transaction_class.isna()

        transaction_class.loc[
            available & mask
        ] = class_name

    # -----------------------------------------------------------------
    # 1. Known hard exclusions
    # -----------------------------------------------------------------
    #
    # Accounting, platform, administrative, test and sample records have
    # explicit business meanings that override other row characteristics.
    for code, class_name in HARD_EXCLUSION_CLASSES.items():
        assign(
            stock_code.eq(code),
            class_name,
        )

    # Some product-coded rows are explicitly administrative rather than sales.
    # The first classification run identified two zero-price, unidentified
    # records described simply as "update". Their administrative meaning takes
    # precedence over the otherwise genuine merchandise StockCode.
    administrative_description = (
        cleaned["description_clean"]
        .str.upper()
        .isin(ADMINISTRATIVE_DESCRIPTION_VALUES)
        & ~cleaned["has_customer_id"]
        & cleaned["is_zero_price"]
    )

    assign(
        administrative_description,
        "administrative_adjustment",
    )

    # -----------------------------------------------------------------
    # 2. Operational non-customer stock adjustments
    # -----------------------------------------------------------------
    #
    # Profiling established that these non-cancellation negative rows are
    # zero-price, unidentified stock movements rather than customer returns.
    operational_adjustment = (
        cleaned["is_negative_quantity"]
        & ~cleaned["is_cancellation"]
        & ~cleaned["has_customer_id"]
        & cleaned["is_zero_price"]
    )

    assign(
        operational_adjustment,
        "operational_stock_adjustment",
    )

    # -----------------------------------------------------------------
    # 3. Manual transactions
    # -----------------------------------------------------------------
    #
    # Manual entries showed substantial reversal/correction behaviour during
    # profiling. Their explicit manual meaning is more informative than a
    # generic cancellation label, while is_cancellation remains available
    # separately where the invoice also begins with C.
    assign(
        cleaned["is_manual"],
        "manual",
    )

    # -----------------------------------------------------------------
    # 4. Recognised non-product customer financial lines
    # -----------------------------------------------------------------
    #
    # These StockCodes identify a more specific business concept than the
    # generic C-invoice cancellation flag. Signed values therefore retain
    # charges, discounts, refunds and reversals appropriately while the
    # diagnostic is_cancellation flag preserves cancellation status.
    assign(
        stock_code.isin(POSTAGE_CODES),
        "postage_carriage",
    )

    assign(
        stock_code.isin(DISCOUNT_CODES),
        "discount",
    )

    gift_voucher = pd.Series(
        False,
        index=cleaned.index,
    )

    for prefix in GIFT_VOUCHER_PREFIXES:
        gift_voucher = (
            gift_voucher
            | stock_code.str.startswith(
                prefix,
                na=False,
            )
        )

    assign(
        gift_voucher,
        "gift_voucher",
    )

    # -----------------------------------------------------------------
    # 5. Customer cancellations / returns
    # -----------------------------------------------------------------
    #
    # Remaining C-prefixed invoices represent customer cancellations or
    # returns without a more specific special-code meaning. Their signed value
    # reduces observed customer value where Customer ID is available, but they
    # do not create recency, frequency or product breadth.
    assign(
        cleaned["is_cancellation"],
        "customer_cancellation_return",
    )

    # -----------------------------------------------------------------
    # 6. Genuine merchandise
    # -----------------------------------------------------------------
    #
    # Positive quantity and non-negative price are required. Non-standard
    # product codes are accepted only after explicit review and addition to
    # KNOWN_GENUINE_MERCHANDISE_CODES.
    merchandise_code = (
        cleaned["is_standard_product_code"]
        | cleaned[
            "is_known_genuine_unusual_code"
        ]
    )

    merchandise = (
        merchandise_code
        & cleaned["Quantity"].gt(0)
        & cleaned["Price"].ge(0)
    )

    assign(
        merchandise,
        "merchandise",
    )

    # -----------------------------------------------------------------
    # 7. Unresolved records
    # -----------------------------------------------------------------
    #
    # An unfamiliar row is surfaced for investigation rather than silently
    # defaulting to merchandise.
    transaction_class = (
        transaction_class
        .fillna("unresolved")
        .astype("category")
    )

    cleaned["transaction_class"] = transaction_class

    return cleaned


# ---------------------------------------------------------------------
# Analytical treatment fields
# ---------------------------------------------------------------------


def add_treatment_fields(cleaned):
    """
    Translate transaction classes into customer-analysis treatment measures.

    The class-level financial measure is kept separately from final customer
    eligibility. This allows the project to quantify otherwise relevant value
    that cannot be assigned to a customer because Customer ID is missing.
    """
    class_name = (
        cleaned["transaction_class"]
        .astype("string")
    )

    # This records whether the transaction's business class contributes to
    # observed commercial value before customer-identification eligibility.
    cleaned["class_counts_in_net_sales"] = (
        class_name.isin(
            FINANCIAL_TRANSACTION_CLASSES
        )
    )

    cleaned["classified_net_sales"] = (
        cleaned["raw_line_value"]
        .where(
            cleaned[
                "class_counts_in_net_sales"
            ],
            0.0,
        )
    )

    # Customer activity is deliberately narrower than merely having a
    # Customer ID. Only genuine merchandise purchases and positive voucher
    # sales represent fresh purchasing activity.
    positive_purchase = (
        cleaned["Quantity"].gt(0)
    )

    activity_class = (
        class_name.isin(
            {
                "merchandise",
                "gift_voucher",
            }
        )
    )

    cleaned["counts_as_activity"] = (
        cleaned["has_customer_id"]
        & activity_class
        & positive_purchase
    )

    # Missing-ID transactions stay in the classified dataset but cannot
    # contribute to customer-level observed value.
    cleaned["counts_in_net_sales"] = (
        cleaned["has_customer_id"]
        & cleaned[
            "class_counts_in_net_sales"
        ]
    )

    # Only genuine positive merchandise can add to product breadth.
    # Postage, discounts, vouchers, returns and manual corrections must not
    # create artificial product variety.
    cleaned["counts_in_product_breadth"] = (
        cleaned["has_customer_id"]
        & class_name.eq("merchandise")
        & positive_purchase
    )

    cleaned["observed_net_sales"] = (
        cleaned["raw_line_value"]
        .where(
            cleaned[
                "counts_in_net_sales"
            ],
            0.0,
        )
    )

    return cleaned


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def validate_cleaned_transactions(cleaned):
    """
    Fail on contradictions between documented rules and generated data.

    Unresolved classifications are reported separately rather than causing
    this first investigative cleaning run to fail automatically.
    """
    if len(cleaned) != EXPECTED_SOURCE_ROWS:
        raise AssertionError(
            "Cleaning changed the corrected source row count."
        )

    if not cleaned["source_row_id"].is_unique:
        raise AssertionError(
            "source_row_id is not unique."
        )

    if cleaned["transaction_class"].isna().any():
        raise AssertionError(
            "At least one row has no transaction classification."
        )

    if cleaned["analysis_period"].isna().any():
        raise AssertionError(
            "At least one row has no analytical-period label."
        )

    if cleaned["raw_line_value"].isna().any():
        raise AssertionError(
            "raw_line_value contains missing values."
        )

    # -------------------------------------------------------------
    # Missing Customer ID
    # -------------------------------------------------------------
    #
    # Missing-ID rows must remain available for reconciliation but cannot
    # enter any final customer-level behavioural/value measure.
    missing_customer = (
        ~cleaned["has_customer_id"]
    )

    if cleaned.loc[
        missing_customer,
        "counts_as_activity",
    ].any():
        raise AssertionError(
            "Missing-ID rows contribute to customer activity."
        )

    if cleaned.loc[
        missing_customer,
        "counts_in_net_sales",
    ].any():
        raise AssertionError(
            "Missing-ID rows contribute to customer net sales."
        )

    if cleaned.loc[
        missing_customer,
        "counts_in_product_breadth",
    ].any():
        raise AssertionError(
            "Missing-ID rows contribute to product breadth."
        )

    # -------------------------------------------------------------
    # Cancellations and returns
    # -------------------------------------------------------------

    cancellations = (
        cleaned["transaction_class"]
        .astype("string")
        .eq(
            "customer_cancellation_return"
        )
    )

    if cleaned.loc[
        cancellations,
        "counts_as_activity",
    ].any():
        raise AssertionError(
            "Cancellation rows contribute to customer activity."
        )

    if cleaned.loc[
        cancellations,
        "counts_in_product_breadth",
    ].any():
        raise AssertionError(
            "Cancellation rows contribute to product breadth."
        )

    # -------------------------------------------------------------
    # Product breadth
    # -------------------------------------------------------------
    #
    # Product breadth is narrower than general activity. Only merchandise
    # can contribute a product code.
    breadth_rows = (
        cleaned[
            "counts_in_product_breadth"
        ]
    )

    breadth_classes = (
        cleaned.loc[
            breadth_rows,
            "transaction_class",
        ]
        .astype("string")
    )

    if not breadth_classes.eq(
        "merchandise"
    ).all():
        raise AssertionError(
            "Non-merchandise rows contribute to product breadth."
        )

    # -------------------------------------------------------------
    # Hard exclusions
    # -------------------------------------------------------------

    hard_exclusion_names = set(
        HARD_EXCLUSION_CLASSES.values()
    )

    hard_exclusion = (
        cleaned["transaction_class"]
        .astype("string")
        .isin(hard_exclusion_names)
    )

    contribution_columns = [
        "counts_as_activity",
        "counts_in_net_sales",
        "counts_in_product_breadth",
    ]

    if cleaned.loc[
        hard_exclusion,
        contribution_columns,
    ].any().any():
        raise AssertionError(
            "A hard-exclusion class contributes to customer measures."
        )

    # -------------------------------------------------------------
    # Monetary reconciliation
    # -------------------------------------------------------------
    #
    # These tests ensure classification changes cannot accidentally change
    # value signs or create monetary values inconsistent with the treatment
    # flags.
    expected_classified = (
        cleaned["raw_line_value"]
        .where(
            cleaned[
                "class_counts_in_net_sales"
            ],
            0.0,
        )
    )

    if not cleaned[
        "classified_net_sales"
    ].equals(expected_classified):
        raise AssertionError(
            "classified_net_sales does not reconcile "
            "to treatment flags."
        )

    expected_observed = (
        cleaned["raw_line_value"]
        .where(
            cleaned[
                "counts_in_net_sales"
            ],
            0.0,
        )
    )

    if not cleaned[
        "observed_net_sales"
    ].equals(expected_observed):
        raise AssertionError(
            "observed_net_sales does not reconcile "
            "to treatment flags."
        )


# ---------------------------------------------------------------------
# QA summaries
# ---------------------------------------------------------------------


def build_classification_summary(cleaned):
    """
    Create a compact public QA table describing transaction treatment.

    This report is intentionally aggregated: it documents the effect of the
    rules without exposing unnecessary customer-level detail.
    """
    summary = (
        cleaned
        .groupby(
            "transaction_class",
            observed=True,
            dropna=False,
        )
        .agg(
            rows=(
                "source_row_id",
                "size",
            ),
            identifiable_rows=(
                "has_customer_id",
                "sum",
            ),
            invoices=(
                "invoice_clean",
                "nunique",
            ),
            customers=(
                "customer_id_clean",
                "nunique",
            ),
            activity_rows=(
                "counts_as_activity",
                "sum",
            ),
            breadth_rows=(
                "counts_in_product_breadth",
                "sum",
            ),
            raw_line_value=(
                "raw_line_value",
                "sum",
            ),
            classified_net_sales=(
                "classified_net_sales",
                "sum",
            ),
            observed_net_sales=(
                "observed_net_sales",
                "sum",
            ),
        )
        .reset_index()
        .sort_values(
            [
                "rows",
                "transaction_class",
            ],
            ascending=[
                False,
                True,
            ],
        )
    )

    money_columns = [
        "raw_line_value",
        "classified_net_sales",
        "observed_net_sales",
    ]

    summary[money_columns] = (
        summary[money_columns]
        .round(2)
    )

    return summary


def build_unresolved_summary(cleaned):
    """
    Summarise unresolved records without exposing customer-level detail.

    The first cleaning run is allowed to discover unresolved classes. These
    rows then become an explicit investigation list rather than being hidden
    by a catch-all merchandise rule.
    """
    unresolved = cleaned.loc[
        cleaned[
            "transaction_class"
        ]
        .astype("string")
        .eq("unresolved")
    ].copy()

    if unresolved.empty:
        return pd.DataFrame(
            columns=[
                "stock_code_clean",
                "description_clean",
                "rows",
                "invoices",
                "customers",
                "min_quantity",
                "max_quantity",
                "min_price",
                "max_price",
                "raw_line_value",
            ]
        )

    summary = (
        unresolved
        .groupby(
            [
                "stock_code_clean",
                "description_clean",
            ],
            dropna=False,
        )
        .agg(
            rows=(
                "source_row_id",
                "size",
            ),
            invoices=(
                "invoice_clean",
                "nunique",
            ),
            customers=(
                "customer_id_clean",
                "nunique",
            ),
            min_quantity=(
                "Quantity",
                "min",
            ),
            max_quantity=(
                "Quantity",
                "max",
            ),
            min_price=(
                "Price",
                "min",
            ),
            max_price=(
                "Price",
                "max",
            ),
            raw_line_value=(
                "raw_line_value",
                "sum",
            ),
        )
        .reset_index()
        .sort_values(
            [
                "rows",
                "stock_code_clean",
            ],
            ascending=[
                False,
                True,
            ],
        )
    )

    summary["raw_line_value"] = (
        summary["raw_line_value"]
        .round(2)
    )

    return summary


def print_headline_qa(
    cleaned,
    classification_summary,
    unresolved_summary,
):
    """
    Print the checks needed before accepting the cleaned transaction layer.
    """
    print_section(
        "Cleaning result"
    )

    print(
        "Corrected source rows retained: "
        f"{len(cleaned):,}"
    )

    print(
        "Columns in classified layer: "
        f"{cleaned.shape[1]:,}"
    )

    print(
        "Date range retained: "
        f"{cleaned['InvoiceDate'].min()} "
        f"to {cleaned['InvoiceDate'].max()}"
    )

    print(
        "\nRows by analytical period:"
    )

    period_counts = (
        cleaned["analysis_period"]
        .value_counts(
            sort=False
        )
    )

    print(
        period_counts.to_string()
    )

    print_section(
        "Transaction classification summary"
    )

    print(
        classification_summary.to_string(
            index=False
        )
    )

    # Recalculate the missing-ID commercial limitation after applying the
    # transaction-treatment rules. Positive classified value is used so the
    # result remains comparable in spirit with the earlier raw-positive-value
    # profiling metric.
    positive_classified = (
        cleaned[
            "classified_net_sales"
        ].gt(0)
    )

    positive_value = (
        cleaned.loc[
            positive_classified,
            "classified_net_sales",
        ]
        .sum()
    )

    missing_positive_value = (
        cleaned.loc[
            (
                positive_classified
                & ~cleaned[
                    "has_customer_id"
                ]
            ),
            "classified_net_sales",
        ]
        .sum()
    )

    if positive_value:
        missing_share = (
            missing_positive_value
            / positive_value
        )
    else:
        missing_share = float("nan")

    print_section(
        "Post-cleaning missing Customer ID impact"
    )

    print(
        "Positive classified transaction value: "
        f"£{positive_value:,.2f}"
    )

    print(
        "Positive classified value without Customer ID: "
        f"£{missing_positive_value:,.2f}"
    )

    print(
        "Share excluded from customer attribution: "
        f"{missing_share:.1%}"
    )

    unresolved_rows = int(
        cleaned[
            "transaction_class"
        ]
        .astype("string")
        .eq("unresolved")
        .sum()
    )

    print_section(
        "Unresolved classification gate"
    )

    print(
        f"Unresolved rows: {unresolved_rows:,}"
    )

    print(
        "Unresolved StockCodes: "
        f"{unresolved_summary['stock_code_clean'].nunique():,}"
    )

    if unresolved_rows:
        print(
            "REVIEW REQUIRED: unresolved records remain. "
            "Inspect the generated unresolved summary before "
            "treating the customer-feature layer as ready."
        )

        print(
            "\nLargest unresolved groups:"
        )

        print(
            unresolved_summary
            .head(30)
            .to_string(index=False)
        )

    else:
        print(
            "PASS: no unresolved transaction "
            "classifications remain."
        )


# ---------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------


def write_outputs(
    cleaned,
    classification_summary,
    unresolved_summary,
):
    """
    Write the local cleaned layer and compact review artefacts.

    The full classified transaction dataset is generated locally rather than
    intended for GitHub. Compact QA summaries can be tracked publicly.
    """
    CLEANED_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CLASSIFICATION_SUMMARY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # DataFrame attrs are retained by pickle, allowing the local generated
    # artefact to carry useful provenance without adding repeated metadata
    # values to more than one million transaction rows.
    cleaned.attrs.update(
        {
            "cleaning_version": CLEANING_VERSION,
            "source_rows": EXPECTED_SOURCE_ROWS,
            "behavioural_start": str(
                BEHAVIOURAL_START.date()
            ),
            "snapshot_date": "2011-05-31",
            "validation_start": str(
                VALIDATION_START.date()
            ),
            "validation_end_exclusive": str(
                VALIDATION_END.date()
            ),
        }
    )

    cleaned.to_pickle(
        CLEANED_FILE
    )

    classification_summary.to_csv(
        CLASSIFICATION_SUMMARY_FILE,
        index=False,
    )

    if unresolved_summary.empty:
        # Prevent an old generated unresolved report from surviving a later
        # successful run and falsely suggesting that classification issues
        # still remain.
        if UNRESOLVED_SUMMARY_FILE.exists():
            UNRESOLVED_SUMMARY_FILE.unlink()

    else:
        unresolved_summary.to_csv(
            UNRESOLVED_SUMMARY_FILE,
            index=False,
        )

    print_section(
        "Generated outputs"
    )

    print(
        "Local classified transactions: "
        f"{CLEANED_FILE}"
    )

    print(
        "Classification summary: "
        f"{CLASSIFICATION_SUMMARY_FILE}"
    )

    if unresolved_summary.empty:
        print(
            "Unresolved summary: not created "
            "(no unresolved rows)"
        )

    else:
        print(
            "Unresolved summary: "
            f"{UNRESOLVED_SUMMARY_FILE}"
        )


# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------


def main():
    """
    Run the reproducible transaction-cleaning and classification pipeline.
    """
    print(
        "Loading corrected Project 03 transaction source..."
    )

    transactions = (
        load_corrected_source()
    )

    print(
        "Normalising fields and creating diagnostic measures..."
    )

    cleaned = add_normalised_fields(
        transactions
    )

    print(
        "Applying transaction classification precedence..."
    )

    cleaned = classify_transactions(
        cleaned
    )

    cleaned = add_treatment_fields(
        cleaned
    )

    print(
        "Validating cleaned transaction layer..."
    )

    validate_cleaned_transactions(
        cleaned
    )

    classification_summary = (
        build_classification_summary(
            cleaned
        )
    )

    unresolved_summary = (
        build_unresolved_summary(
            cleaned
        )
    )

    print_headline_qa(
        cleaned,
        classification_summary,
        unresolved_summary,
    )

    write_outputs(
        cleaned,
        classification_summary,
        unresolved_summary,
    )

    print(
        "\nCleaning pipeline completed successfully."
    )


if __name__ == "__main__":
    main()