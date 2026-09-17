import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "daily_sku_demand.csv"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

df = pd.read_csv(DATA_FILE)

df["Date"] = pd.to_datetime(df["Date"])

print("Data loaded!")
print("Rows:", len(df))
print("Products:", df["Product Name"].nunique())

# --------------------------------------------------
# PARAMETERS
# --------------------------------------------------

LEAD_TIME = 7
Z = 1.65

# --------------------------------------------------
# SKU LEVEL PARAMETERS
# --------------------------------------------------

sku_stats = (
    df.groupby("Product Name")
    .agg(
        Mean_Daily_Demand=("Demand", "mean"),
        Std_Daily_Demand=("Demand", "std")
    )
    .reset_index()
)

sku_stats["Std_Daily_Demand"] = (
    sku_stats["Std_Daily_Demand"].fillna(0)
)

# Basic policy
sku_stats["ROP_Basic"] = (
    sku_stats["Mean_Daily_Demand"] * LEAD_TIME
)

# Safety-stock policy
sku_stats["Safety_Stock"] = (
    Z
    * sku_stats["Std_Daily_Demand"]
    * np.sqrt(LEAD_TIME)
)

sku_stats["ROP_Safety"] = (
    sku_stats["Mean_Daily_Demand"] * LEAD_TIME
    + sku_stats["Safety_Stock"]
)

# --------------------------------------------------
# SIMULATION FUNCTION
# --------------------------------------------------

def simulate_policy(data, stats, rop_column):

    results = []

    for product in stats["Product Name"]:

        product_data = (
            data[data["Product Name"] == product]
            .sort_values("Date")
            .copy()
        )

        rop = stats.loc[
            stats["Product Name"] == product,
            rop_column
        ].iloc[0]

        inventory = rop

        stockout_days = 0
        total_demand = 0
        fulfilled_demand = 0
        inventory_sum = 0

        for _, row in product_data.iterrows():

            demand = row["Demand"]

            total_demand += demand

            fulfilled = min(inventory, demand)

            fulfilled_demand += fulfilled

            if inventory < demand:
                stockout_days += 1

            inventory -= demand

            # Replenishment when inventory reaches ROP
            if inventory <= rop:
                inventory += rop

            inventory_sum += inventory

        avg_inventory = (
            inventory_sum / len(product_data)
            if len(product_data) > 0
            else 0
        )

        fill_rate = (
            fulfilled_demand / total_demand
            if total_demand > 0
            else 1
        )

        results.append({
            "Product Name": product,
            "Stockout_Days": stockout_days,
            "Fill_Rate": fill_rate,
            "Average_Inventory": avg_inventory
        })

    return pd.DataFrame(results)


# --------------------------------------------------
# RUN BOTH POLICIES
# --------------------------------------------------

basic = simulate_policy(
    df,
    sku_stats,
    "ROP_Basic"
)

safety = simulate_policy(
    df,
    sku_stats,
    "ROP_Safety"
)

# --------------------------------------------------
# COMBINE RESULTS
# --------------------------------------------------

comparison = basic.merge(
    safety,
    on="Product Name",
    suffixes=("_Basic", "_Safety")
)

# --------------------------------------------------
# CALCULATE IMPROVEMENT
# --------------------------------------------------

comparison["Stockout_Reduction_%"] = np.where(
    comparison["Stockout_Days_Basic"] > 0,
    (
        (
            comparison["Stockout_Days_Basic"]
            - comparison["Stockout_Days_Safety"]
        )
        / comparison["Stockout_Days_Basic"]
    ) * 100,
    0
)

comparison["Inventory_Change_%"] = (
    (
        comparison["Average_Inventory_Safety"]
        - comparison["Average_Inventory_Basic"]
    )
    / comparison["Average_Inventory_Basic"].replace(0, np.nan)
) * 100

# --------------------------------------------------
# OVERALL SUMMARY
# --------------------------------------------------

summary = pd.DataFrame({
    "Metric": [
        "Total Stockout Days",
        "Average Fill Rate",
        "Average Inventory"
    ],

    "Basic Policy": [
        comparison["Stockout_Days_Basic"].sum(),
        comparison["Fill_Rate_Basic"].mean(),
        comparison["Average_Inventory_Basic"].mean()
    ],

    "Safety Stock Policy": [
        comparison["Stockout_Days_Safety"].sum(),
        comparison["Fill_Rate_Safety"].mean(),
        comparison["Average_Inventory_Safety"].mean()
    ]
})

basic_stockouts = comparison["Stockout_Days_Basic"].sum()
safety_stockouts = comparison["Stockout_Days_Safety"].sum()

if basic_stockouts > 0:
    stockout_reduction = (
        (basic_stockouts - safety_stockouts)
        / basic_stockouts
    ) * 100
else:
    stockout_reduction = 0

inventory_change = (
    (
        comparison["Average_Inventory_Safety"].mean()
        - comparison["Average_Inventory_Basic"].mean()
    )
    / comparison["Average_Inventory_Basic"].mean()
) * 100


# --------------------------------------------------
# SAVE OUTPUTS
# --------------------------------------------------

comparison_file = OUTPUT_DIR / "fair_policy_comparison.csv"
summary_file = OUTPUT_DIR / "fair_policy_summary.csv"

comparison.to_csv(comparison_file, index=False)
summary.to_csv(summary_file, index=False)

# --------------------------------------------------
# PRINT RESULTS
# --------------------------------------------------

print("\n")
print("=" * 70)
print("FAIR INVENTORY POLICY COMPARISON")
print("=" * 70)

print(summary.to_string(index=False))

print("\n")
print("=" * 70)
print("OVERALL RESULTS")
print("=" * 70)

print(f"Basic stockout days: {basic_stockouts}")
print(f"Safety-stock stockout days: {safety_stockouts}")

print(f"Stockout reduction: {stockout_reduction:.2f}%")

print(
    f"Basic average inventory: "
    f"{comparison['Average_Inventory_Basic'].mean():.2f}"
)

print(
    f"Safety-stock average inventory: "
    f"{comparison['Average_Inventory_Safety'].mean():.2f}"
)

print(f"Inventory change: {inventory_change:.2f}%")

print(
    f"Basic fill rate: "
    f"{comparison['Fill_Rate_Basic'].mean() * 100:.2f}%"
)

print(
    f"Safety-stock fill rate: "
    f"{comparison['Fill_Rate_Safety'].mean() * 100:.2f}%"
)

print("\nSaved:")
print(comparison_file)
print(summary_file)