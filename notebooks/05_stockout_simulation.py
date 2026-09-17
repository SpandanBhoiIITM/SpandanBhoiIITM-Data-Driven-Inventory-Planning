import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# PATHS
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

print("Data loaded!")
print("SKUs:", df["Product Name"].nunique())


# =========================================================
# SIMULATION ASSUMPTIONS
# =========================================================

LEAD_TIME = 7
Z = 1.65


# =========================================================
# DEMAND STATISTICS
# =========================================================

stats = (
    df.groupby("Product Name")["Demand"]
    .agg(
        Mean_Demand="mean",
        Std_Demand="std"
    )
    .reset_index()
)

stats["Std_Demand"] = (
    stats["Std_Demand"]
    .fillna(0)
)


# =========================================================
# OPTIMIZED POLICY
# =========================================================

stats["Safety_Stock"] = (
    Z
    * stats["Std_Demand"]
    * np.sqrt(LEAD_TIME)
)

stats["Optimized_ROP"] = (
    stats["Mean_Demand"] * LEAD_TIME
    + stats["Safety_Stock"]
)


# =========================================================
# BASELINE POLICY
# =========================================================

# Baseline represents a simple inventory rule:
# keep approximately 3 days of average demand as
# the reorder threshold.

stats["Baseline_ROP"] = (
    stats["Mean_Demand"] * 3
)


# =========================================================
# INVENTORY SIMULATION FUNCTION
# =========================================================

def simulate(
    demand,
    reorder_point,
    lead_time=7
):

    # Initial inventory
    inventory = max(
        reorder_point,
        1
    )

    orders = []

    stockout_days = 0

    total_demand = 0
    fulfilled_demand = 0

    inventory_total = 0

    for daily_demand in demand:

        # -----------------------------------------
        # RECEIVE ORDERS
        # -----------------------------------------

        received = 0

        new_orders = []

        for arrival, quantity in orders:

            if arrival <= 0:

                received += quantity

            else:

                new_orders.append(
                    (
                        arrival - 1,
                        quantity
                    )
                )

        orders = new_orders

        inventory += received


        # -----------------------------------------
        # DEMAND
        # -----------------------------------------

        total_demand += daily_demand

        fulfilled = min(
            inventory,
            daily_demand
        )

        inventory -= fulfilled

        fulfilled_demand += fulfilled


        # -----------------------------------------
        # STOCKOUT
        # -----------------------------------------

        if fulfilled < daily_demand:

            stockout_days += 1


        inventory_total += inventory


        # -----------------------------------------
        # REORDER
        # -----------------------------------------

        if inventory <= reorder_point:

            # Order enough to restore inventory
            # to approximately one lead-time cycle.

            order_quantity = (
                reorder_point
                - inventory
            )

            if order_quantity > 0:

                orders.append(
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
        inventory_total / len(demand)
    )

    return {
        "Stockout_Days": stockout_days,
        "Total_Demand": total_demand,
        "Fulfilled_Demand": fulfilled_demand,
        "Fill_Rate": fill_rate,
        "Average_Inventory": average_inventory
    }


# =========================================================
# RUN BOTH POLICIES
# =========================================================

results = []

for _, row in stats.iterrows():

    product = row["Product Name"]

    demand = (
        df[
            df["Product Name"] == product
        ]
        .sort_values("Date")["Demand"]
        .values
    )


    # -----------------------------------------
    # BASELINE
    # -----------------------------------------

    baseline = simulate(
        demand=demand,
        reorder_point=row["Baseline_ROP"],
        lead_time=LEAD_TIME
    )


    # -----------------------------------------
    # OPTIMIZED
    # -----------------------------------------

    optimized = simulate(
        demand=demand,
        reorder_point=row["Optimized_ROP"],
        lead_time=LEAD_TIME
    )


    results.append({

        "Product Name": product,

        "Baseline_ROP":
            row["Baseline_ROP"],

        "Optimized_ROP":
            row["Optimized_ROP"],

        "Baseline_Stockout_Days":
            baseline["Stockout_Days"],

        "Optimized_Stockout_Days":
            optimized["Stockout_Days"],

        "Baseline_Fill_Rate":
            baseline["Fill_Rate"],

        "Optimized_Fill_Rate":
            optimized["Fill_Rate"],

        "Baseline_Average_Inventory":
            baseline["Average_Inventory"],

        "Optimized_Average_Inventory":
            optimized["Average_Inventory"]
    })


results = pd.DataFrame(results)


# =========================================================
# STOCKOUT REDUCTION
# =========================================================

baseline_total = (
    results["Baseline_Stockout_Days"].sum()
)

optimized_total = (
    results["Optimized_Stockout_Days"].sum()
)

if baseline_total > 0:

    stockout_reduction = (
        (baseline_total - optimized_total)
        / baseline_total
        * 100
    )

else:

    stockout_reduction = 0


# =========================================================
# INVENTORY CHANGE
# =========================================================

baseline_inventory = (
    results["Baseline_Average_Inventory"].mean()
)

optimized_inventory = (
    results["Optimized_Average_Inventory"].mean()
)

inventory_change = (
    (optimized_inventory - baseline_inventory)
    / baseline_inventory
    * 100
)


# =========================================================
# SAVE DETAILED RESULTS
# =========================================================

results_file = (
    OUTPUT_DIR /
    "stockout_simulation.csv"
)

results.to_csv(
    results_file,
    index=False
)


# =========================================================
# SAVE SUMMARY
# =========================================================

summary = pd.DataFrame({

    "Metric": [

        "Baseline Stockout Days",

        "Optimized Stockout Days",

        "Stockout Reduction (%)",

        "Baseline Average Inventory",

        "Optimized Average Inventory",

        "Inventory Change (%)",

        "Baseline Average Fill Rate",

        "Optimized Average Fill Rate"
    ],

    "Value": [

        baseline_total,

        optimized_total,

        round(stockout_reduction, 2),

        round(baseline_inventory, 2),

        round(optimized_inventory, 2),

        round(inventory_change, 2),

        round(
            results["Baseline_Fill_Rate"].mean()
            * 100,
            2
        ),

        round(
            results["Optimized_Fill_Rate"].mean()
            * 100,
            2
        )
    ]
})


summary_file = (
    OUTPUT_DIR /
    "stockout_summary.csv"
)

summary.to_csv(
    summary_file,
    index=False
)


# =========================================================
# PRINT RESULTS
# =========================================================

print("\n")
print("=" * 65)
print("STOCKOUT SIMULATION")
print("=" * 65)

print(
    "\nBaseline stockout days:",
    baseline_total
)

print(
    "Optimized stockout days:",
    optimized_total
)

print(
    "Stockout reduction:",
    round(
        stockout_reduction,
        2
    ),
    "%"
)

print(
    "\nBaseline average inventory:",
    round(
        baseline_inventory,
        2
    )
)

print(
    "Optimized average inventory:",
    round(
        optimized_inventory,
        2
    )
)

print(
    "Inventory change:",
    round(
        inventory_change,
        2
    ),
    "%"
)

print(
    "\nBaseline fill rate:",
    round(
        results["Baseline_Fill_Rate"].mean()
        * 100,
        2
    ),
    "%"
)

print(
    "Optimized fill rate:",
    round(
        results["Optimized_Fill_Rate"].mean()
        * 100,
        2
    ),
    "%"
)


print("\n")
print("=" * 65)
print("FILES CREATED")
print("=" * 65)

print(
    results_file
)

print(
    summary_file
)