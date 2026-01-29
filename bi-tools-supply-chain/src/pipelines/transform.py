from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.quality.validations import validate_products

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # standardize columns just in case
    for col in ["sku", "name", "product_url"]:
        if col in out.columns:
            out[col] = out[col].astype(str).str.strip()

    # numeric coercion (safe)
    if "price_list" in out.columns:
        out["price_list"] = pd.to_numeric(out["price_list"], errors="coerce")
    if "price_sale" in out.columns:
        out["price_sale"] = pd.to_numeric(out["price_sale"], errors="coerce")
    if "rating" in out.columns:
        out["rating"] = pd.to_numeric(out["rating"], errors="coerce").round(1)
    if "reviews_count" in out.columns:
        out["reviews_count"] = pd.to_numeric(out["reviews_count"], errors="coerce").astype("Int64")

    return out


def dedupe_latest(df: pd.DataFrame) -> pd.DataFrame:
    """
    If scraping produces duplicates per sku, keep the last occurrence.
    """
    if "sku" not in df.columns:
        return df
    return df.drop_duplicates(subset=["sku"], keep="last").copy()


def main() -> None:
    # Find latest raw file OR set explicitly
    raw_dir = Path("data/raw")
    raw_files = sorted(raw_dir.glob("products_raw_*.csv"))
    if not raw_files:
        raise FileNotFoundError("No raw files found in data/raw (expected products_raw_YYYY-MM-DD.csv)")

    raw_path = raw_files[-1]
    logger.info("Reading raw data: %s", raw_path)

    df = pd.read_csv(raw_path)

    # add snapshot date (important for BI)
    snapshot_date = date.today().isoformat()
    df["snapshot_date"] = snapshot_date


    logger.info("Number of Rows before coerce_types: %d", len(df))
    df = coerce_types(df)
    logger.info("Number of Rows after coerce_types: %d", len(df))
    ###df = dedupe_latest(df)
    ###logger.info("Number of Rows after dedupe_latest: %d", len(df))

    valid_df, report = validate_products(df)

    logger.info("Rows total: %s | valid: %s | invalid: %s",
                report.total_rows, report.valid_rows, report.invalid_rows)
    if report.invalid_reasons:
        logger.info("Invalid reasons breakdown: %s", report.invalid_reasons)

    # Build a BI-friendly fact table (snapshot style)
    fact_cols = ["snapshot_date", "sku", "name", "price_list", "price_sale", "rating", "reviews_count", "product_url"]
    fact = valid_df[[c for c in fact_cols if c in valid_df.columns]].copy()

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"fact_product_snapshot_{snapshot_date}.csv"
    fact.to_csv(out_path, index=False)
    logger.info("Saved processed fact table: %s", out_path)


if __name__ == "__main__":
    main()
