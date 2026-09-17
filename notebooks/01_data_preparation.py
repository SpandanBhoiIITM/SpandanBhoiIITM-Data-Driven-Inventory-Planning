import pandas as pd
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Input Excel file
excel_path = ROOT / "BDM_DataSet.xlsx"

# Output folder
data_path = ROOT / "data"
data_path.mkdir(exist_ok=True)

print("Reading:", excel_path)

# Read Sales Register
df = pd.read_excel(
    excel_path,
    sheet_name="Sales Register",
    header=3
)

# Clean column names
df.columns = [str(c).strip() for c in df.columns]

# Remove empty rows
df = df[df["Date"].notna()].copy()

# Convert data types
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")

# Clean product names
df["Product Name"] = (
    df["Product Name"]
    .astype(str)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

# Remove invalid rows
df = df.dropna(
    subset=["Date", "Product Name", "Quantity"]
)

print("\nClean sales data:")
print(df.head())

print("\nTransactions:", len(df))
print("Products:", df["Product Name"].nunique())
print(
    "Date range:",
    df["Date"].min().date(),
    "to",
    df["Date"].max().date()
)

# --------------------------------------------------
# CREATE DAILY SKU DEMAND
# --------------------------------------------------

daily = (
    df.groupby(
        ["Date", "Product Name"],
        as_index=False
    )["Quantity"]
    .sum()
)

daily = daily.rename(
    columns={"Quantity": "Demand"}
)

# Create every date
dates = pd.date_range(
    daily["Date"].min(),
    daily["Date"].max(),
    freq="D"
)

# Get all products
products = sorted(
    daily["Product Name"].unique()
)

# Create complete Date × Product grid
grid = pd.MultiIndex.from_product(
    [dates, products],
    names=["Date", "Product Name"]
).to_frame(index=False)

# Merge actual demand
daily = grid.merge(
    daily,
    on=["Date", "Product Name"],
    how="left"
)

# If product had no sale on a day → demand = 0
daily["Demand"] = daily["Demand"].fillna(0)

# Add useful date features
daily["DayOfWeek"] = daily["Date"].dt.dayofweek
daily["Month"] = daily["Date"].dt.month
daily["IsWeekend"] = (
    daily["DayOfWeek"] >= 5
).astype(int)

# Save
output_file = data_path / "daily_sku_demand.csv"

daily.to_csv(
    output_file,
    index=False
)

print("\n--------------------------------")
print("SUCCESS!")
print("--------------------------------")

print("Daily SKU rows:", len(daily))
print("SKUs:", daily["Product Name"].nunique())
print("Saved to:", output_file)

print("\nFirst 10 rows:")
print(daily.head(10))