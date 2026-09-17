import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent.parent

EXCEL_FILE = ROOT / "BDM_DataSet.xlsx"
OUTPUT_DIR = ROOT / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)


# =========================================================
# LOAD PURCHASE DATA
# =========================================================

df = pd.read_excel(
    EXCEL_FILE,
    sheet_name="Purchase Register",
    header=3
)

df.columns = [
    str(c).strip()
    for c in df.columns
]

print("Purchase data loaded!")

print("Rows:", len(df))

df.columns = df.columns.astype(str).str.strip()

print("Columns:", df.columns.tolist())


# =========================================================
# CLEAN DATA
# =========================================================

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)

df["Expiry Date"] = pd.to_datetime(
    df["Expiry Date"],
    errors="coerce"
)

df["Quantity"] = pd.to_numeric(
    df["Quantity"],
    errors="coerce"
)

df["Product Name"] = (
    df["Product Name"]
    .astype(str)
    .str.strip()
    .str.replace(
        r"\s+",
        " ",
        regex=True
    )
)

df = df.dropna(
    subset=[
        "Date",
        "Expiry Date",
        "Product Name",
        "Quantity"
    ]
)


# =========================================================
# REFERENCE DATE
# =========================================================

REFERENCE_DATE = df["Date"].max()

print(
    "Reference date:",
    REFERENCE_DATE.date()
)


# =========================================================
# DAYS TO EXPIRY
# =========================================================

df["Days_To_Expiry"] = (
    df["Expiry Date"]
    - REFERENCE_DATE
).dt.days


# =========================================================
# EXPIRY RISK CATEGORY
# =========================================================

def expiry_category(days):

    if days < 0:
        return "Expired"

    elif days <= 30:
        return "Critical"

    elif days <= 90:
        return "High Risk"

    elif days <= 180:
        return "Moderate Risk"

    else:
        return "Low Risk"


df["Expiry_Risk"] = (
    df["Days_To_Expiry"]
    .apply(expiry_category)
)


# =========================================================
# PRODUCT-LEVEL EXPIRY SUMMARY
# =========================================================

summary = (
    df.groupby("Product Name")
    .agg(
        Total_Stock=("Quantity", "sum"),

        Earliest_Expiry=(
            "Expiry Date",
            "min"
        ),

        Average_Days_To_Expiry=(
            "Days_To_Expiry",
            "mean"
        ),

        Minimum_Days_To_Expiry=(
            "Days_To_Expiry",
            "min"
        )
    )
    .reset_index()
)


# =========================================================
# RISK CATEGORY
# =========================================================

summary["Expiry_Risk"] = (
    summary["Minimum_Days_To_Expiry"]
    .apply(expiry_category)
)


# =========================================================
# FEFO PRIORITY
# =========================================================

# First Expiry, First Out
summary = summary.sort_values(
    "Earliest_Expiry"
).reset_index(drop=True)

summary["FEFO_Priority"] = (
    summary.index + 1
)


# =========================================================
# EXPIRY-RISK STOCK
# =========================================================

risk_stock = (
    df.groupby("Expiry_Risk")["Quantity"]
    .sum()
    .reset_index()
)

risk_stock["Percentage_of_Stock"] = (
    risk_stock["Quantity"]
    / risk_stock["Quantity"].sum()
    * 100
)


# =========================================================
# SAVE PRODUCT ANALYSIS
# =========================================================

product_file = (
    OUTPUT_DIR /
    "expiry_analysis.csv"
)

summary.to_csv(
    product_file,
    index=False
)


# =========================================================
# SAVE RISK SUMMARY
# =========================================================

risk_file = (
    OUTPUT_DIR /
    "expiry_risk_summary.csv"
)

risk_stock.to_csv(
    risk_file,
    index=False
)


# =========================================================
# DISPLAY
# =========================================================

print("\n")
print("=" * 65)
print("EXPIRY RISK ANALYSIS")
print("=" * 65)

print(
    summary[
        [
            "Product Name",
            "Total_Stock",
            "Earliest_Expiry",
            "Minimum_Days_To_Expiry",
            "Expiry_Risk"
        ]
    ]
    .head(20)
    .to_string(index=False)
)


print("\n")
print("=" * 65)
print("STOCK BY EXPIRY RISK")
print("=" * 65)

print(
    risk_stock.to_string(
        index=False
    )
)


print("\n")
print("=" * 65)
print("SUCCESS!")
print("=" * 65)

print(
    "Product analysis:",
    product_file
)

print(
    "Risk summary:",
    risk_file
)