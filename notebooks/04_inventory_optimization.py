import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# PROJECT PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "daily_sku_demand.csv"
ABC_FILE = ROOT / "outputs" / "abc_xyz.csv"
OUTPUT_DIR = ROOT / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)


# =========================================================
# LOAD DATA
# =========================================================

df = pd.read_csv(
    DATA_FILE,
    parse_dates=["Date"]
)

abc_xyz = pd.read_csv(
    ABC_FILE
)

print("Data loaded successfully!")

print("Daily demand rows:", len(df))
print("SKUs:", df["Product Name"].nunique())


# =========================================================
# INVENTORY ASSUMPTIONS
# =========================================================

# These are simulation assumptions.
LEAD_TIME_DAYS = 7

# 95% service level
SERVICE_LEVEL_Z = 1.65

# Review inventory every 7 days
REVIEW_PERIOD = 7


# =========================================================
# CALCULATE DEMAND STATISTICS
# =========================================================

stats = (
    df.groupby("Product Name")["Demand"]
    .agg(
        Mean_Daily_Demand="mean",
        Std_Daily_Demand="std"
    )
    .reset_index()
)

stats["Std_Daily_Demand"] = (
    stats["Std_Daily_Demand"]
    .fillna(0)
)


# =========================================================
# SAFETY STOCK
# =========================================================

stats["Safety_Stock"] = (
    SERVICE_LEVEL_Z
    * stats["Std_Daily_Demand"]
    * np.sqrt(LEAD_TIME_DAYS)
)


# =========================================================
# REORDER POINT
# =========================================================

stats["Lead_Time_Demand"] = (
    stats["Mean_Daily_Demand"]
    * LEAD_TIME_DAYS
)

stats["Reorder_Point"] = (
    stats["Lead_Time_Demand"]
    + stats["Safety_Stock"]
)


# =========================================================
# ABC + XYZ
# =========================================================

stats = stats.merge(
    abc_xyz[
        [
            "Product Name",
            "ABC",
            "XYZ",
            "ABC_XYZ"
        ]
    ],
    on="Product Name",
    how="left"
)


# =========================================================
# INVENTORY POLICY
# =========================================================

def policy(row):

    # High-value and highly variable items
    if row["ABC"] == "A" and row["XYZ"] == "Z":
        return "Frequent Review"

    # High-value stable/moderate demand
    elif row["ABC"] == "A":
        return "High Priority"

    # Medium value items
    elif row["ABC"] == "B":
        return "Periodic Review"

    # Low value items
    else:
        return "Basic Review"


stats["Inventory_Policy"] = (
    stats.apply(policy, axis=1)
)


# =========================================================
# HISTORICAL INVENTORY SIMULATION
# =========================================================

print("\nRunning inventory simulation...")


def simulate_inventory(
    demand,
    reorder_point,
    safety_stock,
    lead_time=7
):

    # Starting inventory
    inventory = max(
        reorder_point + safety_stock,
        1
    )

    pipeline = []

    stockout_days = 0
    total_demand = 0
    fulfilled_demand = 0

    inventory_sum = 0

    for day_demand in demand:

        # Receive orders whose lead time has finished
        received = 0

        new_pipeline = []

        for arrival_day, quantity in pipeline:

            if arrival_day <= 0:
                received += quantity
            else:
                new_pipeline.append(
                    (arrival_day - 1, quantity)
                )

        pipeline = new_pipeline

        inventory += received

        # Customer demand
        total_demand += day_demand

        fulfilled = min(
            inventory,
            day_demand
        )

        inventory -= fulfilled

        fulfilled_demand += fulfilled

        # Stockout
        if fulfilled < day_demand:
            stockout_days += 1

        inventory_sum += inventory

        # Reorder
        if inventory <= reorder_point:

            already_on_order = sum(
                q for _, q in pipeline
            )

            target_inventory = (
                reorder_point
                + safety_stock
            )

            order_quantity = max(
                target_inventory
                - inventory
                - already_on_order,
                0
            )

            if order_quantity > 0:

                pipeline.append(
                    (
                        lead_time,
                        order_quantity
                    )
                )

    fill_rate = (
        fulfilled_demand / total_demand
        if total_demand > 0
        else 1
    )

    average_inventory = (
        inventory_sum / len(demand)
        if len(demand) > 0
        else 0
    )

    return {
        "Stockout_Days": stockout_days,
        "Total_Demand": total_demand,
        "Fulfilled_Demand": fulfilled_demand,
        "Fill_Rate": fill_rate,
        "Average_Inventory": average_inventory
    }


# =========================================================
# RUN SIMULATION FOR EVERY SKU
# =========================================================

simulation_results = []

for _, row in stats.iterrows():

    product = row["Product Name"]

    product_demand = (
        df[
            df["Product Name"] == product
        ]
        .sort_values("Date")["Demand"]
        .values
    )

    result = simulate_inventory(
        demand=product_demand,
        reorder_point=row["Reorder_Point"],
        safety_stock=row["Safety_Stock"],
        lead_time=LEAD_TIME_DAYS
    )

    result["Product Name"] = product

    simulation_results.append(result)


simulation = pd.DataFrame(
    simulation_results
)


# =========================================================
# MERGE RESULTS
# =========================================================

final = stats.merge(
    simulation,
    on="Product Name",
    how="left"
)


# =========================================================
# ROUND VALUES
# =========================================================

numeric_columns = [
    "Mean_Daily_Demand",
    "Std_Daily_Demand",
    "Safety_Stock",
    "Lead_Time_Demand",
    "Reorder_Point",
    "Fill_Rate",
    "Average_Inventory"
]

for col in numeric_columns:

    final[col] = final[col].round(2)


# =========================================================
# SAVE RECOMMENDATIONS
# =========================================================

output_file = (
    OUTPUT_DIR /
    "inventory_recommendations.csv"
)

final.to_csv(
    output_file,
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print("\n")
print("=" * 60)
print("INVENTORY OPTIMIZATION RESULTS")
print("=" * 60)

print(
    final[
        [
            "Product Name",
            "ABC",
            "XYZ",
            "Safety_Stock",
            "Reorder_Point",
            "Stockout_Days",
            "Fill_Rate"
        ]
    ]
    .head(15)
    .to_string(index=False)
)


print("\n")
print("=" * 60)
print("OVERALL RESULTS")
print("=" * 60)

print(
    "Total simulated stockout days:",
    final["Stockout_Days"].sum()
)

print(
    "Average fill rate:",
    round(
        final["Fill_Rate"].mean() * 100,
        2
    ),
    "%"
)

print(
    "Average inventory:",
    round(
        final["Average_Inventory"].mean(),
        2
    )
)


print("\n")
print("=" * 60)
print("SUCCESS!")
print("=" * 60)

print(
    "Saved to:",
    output_file
)