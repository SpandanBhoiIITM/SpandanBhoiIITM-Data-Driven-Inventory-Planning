import pandas as pd
from pathlib import Path

# Find project root automatically
ROOT = Path(__file__).resolve().parent.parent

# Read daily demand
file_path = ROOT / "data" / "daily_sku_demand.csv"

df = pd.read_csv(
    file_path,
    parse_dates=["Date"]
)

print("Data loaded successfully!")
print("Rows:", len(df))
print("SKUs:", df["Product Name"].nunique())


# ==========================================
# ABC ANALYSIS
# ==========================================

abc = (
    df.groupby("Product Name")
    .agg(
        Total_Demand=("Demand", "sum")
    )
    .reset_index()
)

# Calculate sales value using original sales data
sales_file = ROOT / "BDM_DataSet.xlsx"

sales = pd.read_excel(
    sales_file,
    sheet_name="Sales Register",
    header=3
)

sales.columns = [
    str(c).strip()
    for c in sales.columns
]

sales = sales[sales["Date"].notna()].copy()

sales["Amount (₹)"] = pd.to_numeric(
    sales["Amount (₹)"],
    errors="coerce"
)

sales["Product Name"] = (
    sales["Product Name"]
    .astype(str)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

sales_value = (
    sales.groupby("Product Name")["Amount (₹)"]
    .sum()
    .reset_index()
    .rename(columns={"Amount (₹)": "Sales_Value"})
)

abc = abc.merge(
    sales_value,
    on="Product Name",
    how="left"
)

abc["Sales_Value"] = abc["Sales_Value"].fillna(0)

# Sort by sales value
abc = abc.sort_values(
    "Sales_Value",
    ascending=False
).reset_index(drop=True)

# Calculate percentage contribution
total_value = abc["Sales_Value"].sum()

abc["Value_Share"] = (
    abc["Sales_Value"] / total_value
)

abc["Cumulative_Value_Share"] = (
    abc["Value_Share"].cumsum()
)

# ABC classification
def classify_abc(x):

    if x <= 0.80:
        return "A"

    elif x <= 0.95:
        return "B"

    else:
        return "C"


abc["ABC"] = (
    abc["Cumulative_Value_Share"]
    .apply(classify_abc)
)


# ==========================================
# XYZ ANALYSIS
# ==========================================

# Convert daily demand into weekly demand
df["Week"] = (
    df["Date"]
    .dt.to_period("W")
    .dt.start_time
)

weekly = (
    df.groupby(
        ["Product Name", "Week"]
    )["Demand"]
    .sum()
    .reset_index()
)

# Calculate weekly mean and standard deviation
xyz = (
    weekly.groupby("Product Name")["Demand"]
    .agg(
        Mean_Demand="mean",
        Std_Demand="std"
    )
    .reset_index()
)

xyz["Std_Demand"] = (
    xyz["Std_Demand"]
    .fillna(0)
)

# Coefficient of Variation
xyz["CV"] = (
    xyz["Std_Demand"] /
    xyz["Mean_Demand"].replace(0, pd.NA)
)

xyz["CV"] = xyz["CV"].fillna(0)


# XYZ classification
def classify_xyz(cv):

    if cv <= 0.75:
        return "X"

    elif cv <= 1.00:
        return "Y"

    else:
        return "Z"


xyz["XYZ"] = (
    xyz["CV"]
    .apply(classify_xyz)
)

# ==========================================
# COMBINE ABC + XYZ
# ==========================================

result = abc.merge(
    xyz,
    on="Product Name",
    how="left"
)

result["ABC_XYZ"] = (
    result["ABC"] + result["XYZ"]
)


# ==========================================
# SAVE RESULT
# ==========================================

output_file = (
    ROOT /
    "outputs" /
    "abc_xyz.csv"
)

output_file.parent.mkdir(
    exist_ok=True
)

result.to_csv(
    output_file,
    index=False
)


# ==========================================
# DISPLAY RESULTS
# ==========================================

print("\n================================")
print("ABC ANALYSIS")
print("================================")

print(
    result["ABC"]
    .value_counts()
    .sort_index()
)


print("\n================================")
print("XYZ ANALYSIS")
print("================================")

print(
    result["XYZ"]
    .value_counts()
    .sort_index()
)


print("\n================================")
print("ABC + XYZ")
print("================================")

print(
    result["ABC_XYZ"]
    .value_counts()
    .sort_index()
)


print("\n================================")
print("SUCCESS!")
print("================================")

print(
    "Saved to:",
    output_file
)