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

df = df.sort_values(["Product Name", "Date"])

print("Data loaded!")
print("Rows:", len(df))
print("Products:", df["Product Name"].nunique())

# --------------------------------------------------
# PARAMETERS
# --------------------------------------------------

LEAD_TIME = 7
Z = 1.65

# --------------------------------------------------
# SKU STATISTICS
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

# Basic reorder point
sku_stats["ROP_Basic"] = (
    sku_stats["Mean_Daily_Demand"] * LEAD_TIME
)

# Safety stock
sku_stats["Safety_Stock"] = (
    Z
    * sku_stats["Std_Daily_Demand"]
    * np.sqrt(LEAD_TIME)
)

# Safety-stock reorder point
sku_stats["ROP_Safety"] = (
    sku_stats["ROP_Basic"]
    + sku_stats["Safety_Stock"]
)

# --------------------------------------------------
# REALISTIC SIMULATION
# --------------------------------------------------

def simulate_policy(data, stats, rop_column):

    results = []

    for product in stats["Product Name"]:

        product_data = (
            data[data["Product Name"] == product]
            .sort_values("Date")
            .reset_index(drop=True)
        )

        mean_demand = stats.loc[
            stats["Product Name"] == product,
            "Mean_Daily_Demand"
        ].iloc[0]

        rop = stats.loc[
            stats["Product Name"] == product,
            rop_column
        ].iloc[0]

        # Target inventory level
        order_up_to = (
            rop + mean_demand * LEAD_TIME
        )

        # Initial inventory
        inventory = order_up_to

        # Orders currently in transit
        outstanding_orders = []

        stockout_days = 0
        total_demand = 0
        fulfilled_demand = 0
        inventory_sum = 0

        for day in range(len(product_data)):

            demand = product_data.loc[day, "Demand"]

            # --------------------------------------------------
            # RECEIVE ORDERS AFTER LEAD TIME
            # --------------------------------------------------

            received_today = 0

            remaining_orders = []

            for arrival_day, order_qty in outstanding_orders:

                if arrival_day <= day:
                    received_today += order_qty
                else:
                    remaining_orders.append(
                        (arrival_day, order_qty)
                    )

            outstanding_orders = remaining_orders

            inventory += received_today

            # --------------------------------------------------
            # FULFILL DEMAND
            # --------------------------------------------------

            total_demand += demand

            fulfilled = min(inventory, demand)

            fulfilled_demand += fulfilled

            if fulfilled < demand:
                stockout_days += 1

            # Inventory cannot become negative
            inventory -= fulfilled

            # --------------------------------------------------
            # INVENTORY POSITION
            # --------------------------------------------------

            inventory_on_order = sum(
                qty for _, qty in outstanding_orders
            )

            inventory_position = (
                inventory + inventory_on_order
            )

            # --------------------------------------------------
            # REORDER
            # --------------------------------------------------

            if inventory_position <= rop:

                order_qty = max(
                    order_up_to - inventory_position,
                    0
                )

                if order_qty > 0:

                    arrival_day = day + LEAD_TIME

                    outstanding_orders.append(
                        (arrival_day, order_qty)
                    )

            # --------------------------------------------------
            # RECORD INVENTORY
            # --------------------------------------------------

            inventory_sum += inventory

        # --------------------------------------------------
        # METRICS
        # --------------------------------------------------

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
# RUN SIMULATIONS
# --------------------------------------------------

print("\nRunning Basic Policy...")

basic = simulate_policy(
    df,
    sku_stats,
    "ROP_Basic"
)

print("Running Safety-Stock Policy...")

safety = simulate_policy(
    df,
    sku_stats,
    "ROP_Safety"
)

# --------------------------------------------------
# COMBINE
# --------------------------------------------------

comparison = basic.merge(
    safety,
    on="Product Name",
    suffixes=("_Basic", "_Safety")
)

# --------------------------------------------------
# IMPROVEMENT METRICS
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

comparison["Inventory_Change_%"] = np.where(
    comparison["Average_Inventory_Basic"] > 0,
    (
        (
            comparison["Average_Inventory_Safety"]
            - comparison["Average_Inventory_Basic"]
        )
        / comparison["Average_Inventory_Basic"]
    ) * 100,
    0
)

# --------------------------------------------------
# OVERALL METRICS
# --------------------------------------------------

basic_stockouts = comparison["Stockout_Days_Basic"].sum()
safety_stockouts = comparison["Stockout_Days_Safety"].sum()

basic_fill = comparison["Fill_Rate_Basic"].mean()
safety_fill = comparison["Fill_Rate_Safety"].mean()

basic_inventory = comparison["Average_Inventory_Basic"].mean()
safety_inventory = comparison["Average_Inventory_Safety"].mean()

if basic_stockouts > 0:

    stockout_reduction = (
        (basic_stockouts - safety_stockouts)
        / basic_stockouts
    ) * 100

else:

    stockout_reduction = 0


inventory_change = (
    (safety_inventory - basic_inventory)
    / basic_inventory
) * 100

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

summary = pd.DataFrame({

    "Metric": [
        "Total Stockout Days",
        "Average Fill Rate",
        "Average Inventory"
    ],

    "Basic Policy": [
        basic_stockouts,
        basic_fill,
        basic_inventory
    ],

    "Safety Stock Policy": [
        safety_stockouts,
        safety_fill,
        safety_inventory
    ]
})

# --------------------------------------------------
# SAVE RESULTS
# --------------------------------------------------

comparison_file = (
    OUTPUT_DIR / "lead_time_policy_comparison.csv"
)

summary_file = (
    OUTPUT_DIR / "lead_time_policy_summary.csv"
)

comparison.to_csv(
    comparison_file,
    index=False
)

summary.to_csv(
    summary_file,
    index=False
)

# --------------------------------------------------
# PRINT RESULTS
# --------------------------------------------------

print("\n")
print("=" * 70)
print("REALISTIC LEAD-TIME INVENTORY SIMULATION")
print("=" * 70)

print(summary.to_string(index=False))

print("\n")
print("=" * 70)
print("OVERALL RESULTS")
print("=" * 70)

print(f"Lead time: {LEAD_TIME} days")
print(f"Safety factor Z: {Z}")

print()
print(f"Basic stockout days: {basic_stockouts}")
print(f"Safety-stock stockout days: {safety_stockouts}")

print(f"Stockout reduction: {stockout_reduction:.2f}%")

print()
print(f"Basic fill rate: {basic_fill * 100:.2f}%")
print(f"Safety-stock fill rate: {safety_fill * 100:.2f}%")

print()
print(f"Basic average inventory: {basic_inventory:.2f}")
print(f"Safety-stock average inventory: {safety_inventory:.2f}")

print(f"Inventory change: {inventory_change:.2f}%")

print("\n")
print("=" * 70)
print("FILES SAVED")
print("=" * 70)

print(comparison_file)
print(summary_file)