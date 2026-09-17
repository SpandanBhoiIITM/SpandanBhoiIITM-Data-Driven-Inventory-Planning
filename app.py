import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

st.set_page_config(
    page_title="Pharmacy Inventory Assistant",
    page_icon="💊",
    layout="wide"
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    daily_demand = pd.read_csv(
        DATA_DIR / "daily_sku_demand.csv"
    )

    abc_xyz = pd.read_csv(
        OUTPUT_DIR / "abc_xyz.csv"
    )

    inventory = pd.read_csv(
        OUTPUT_DIR / "inventory_recommendations.csv"
    )

    expiry = pd.read_csv(
        OUTPUT_DIR / "expiry_analysis.csv"
    )

    expiry_risk = pd.read_csv(
        OUTPUT_DIR / "expiry_risk_summary.csv"
    )

    policy = pd.read_csv(
        OUTPUT_DIR / "lead_time_policy_comparison.csv"
    )

    daily_demand["Date"] = pd.to_datetime(
        daily_demand["Date"]
    )

    expiry["Earliest_Expiry"] = pd.to_datetime(
        expiry["Earliest_Expiry"]
    )

    return (
        daily_demand,
        abc_xyz,
        inventory,
        expiry,
        expiry_risk,
        policy
    )


(
    daily_demand,
    abc_xyz,
    inventory,
    expiry,
    expiry_risk,
    policy
) = load_data()


# ============================================================
# HEADER
# ============================================================

st.title("💊 Pharmacy Inventory Assistant")

st.markdown(
    """
    **Retail pharmacy decision-support dashboard**

    Monitor sales, inventory risk, expiry, and replenishment
    decisions from one place.
    """
)


# ============================================================
# TOP METRICS
# ============================================================

total_products = daily_demand["Product Name"].nunique()

total_demand = daily_demand["Demand"].sum()

expired_stock = expiry_risk.loc[
    expiry_risk["Expiry_Risk"] == "Expired",
    "Quantity"
].sum()

moderate_stock = expiry_risk.loc[
    expiry_risk["Expiry_Risk"] == "Moderate Risk",
    "Quantity"
].sum()

total_stock = expiry_risk["Quantity"].sum()

at_risk_stock = expired_stock + moderate_stock

at_risk_percentage = (
    at_risk_stock / total_stock * 100
    if total_stock > 0
    else 0
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Products",
        total_products
    )

with col2:
    st.metric(
        "Total Units Sold",
        f"{total_demand:,.0f}"
    )

with col3:
    st.metric(
        "Expiry Risk",
        f"{at_risk_percentage:.1f}%"
    )

with col4:
    st.metric(
        "Expired Units",
        f"{expired_stock:,.0f}"
    )


st.divider()


# ============================================================
# TODAY'S ACTIONS
# ============================================================

st.header("🚨 Today's Actions")

action_col1, action_col2 = st.columns(2)


# ------------------------------------------------------------
# EXPIRY ALERTS
# ------------------------------------------------------------

with action_col1:

    st.subheader("⚠️ Expiry Alerts")

    expiry_alerts = expiry[
        expiry["Expiry_Risk"].isin(
            ["Expired", "Critical", "High Risk", "Moderate Risk"]
        )
    ].copy()

    expiry_alerts = expiry_alerts.sort_values(
        "Earliest_Expiry"
    )

    if len(expiry_alerts) == 0:

        st.success("No expiry alerts.")

    else:

        for _, row in expiry_alerts.head(5).iterrows():

            product = row["Product Name"]
            risk = row["Expiry_Risk"]
            days = row["Minimum_Days_To_Expiry"]

            if risk == "Expired":

                st.error(
                    f"🔴 **{product}** — EXPIRED"
                )

            else:

                st.warning(
                    f"🟡 **{product}** — "
                    f"{days} days to earliest expiry"
                )


# ------------------------------------------------------------
# REORDER ALERTS
# ------------------------------------------------------------

with action_col2:

    st.subheader("🛒 Reorder Alerts")

    if "Current_Stock" in inventory.columns:

        reorder_items = inventory[
            inventory["Current_Stock"]
            < inventory["ROP"]
        ].copy()

    else:

        reorder_items = pd.DataFrame()

    if len(reorder_items) == 0:

        st.success(
            "No products currently below reorder point."
        )

    else:

        for _, row in reorder_items.head(5).iterrows():

            st.warning(
                f"🟠 **{row['Product Name']}** — "
                f"below reorder point"
            )


st.divider()


# ============================================================
# SALES TREND
# ============================================================

st.header("📊 Sales Overview")

sales_daily = (
    daily_demand
    .groupby("Date")["Demand"]
    .sum()
    .reset_index()
)

st.line_chart(
    sales_daily.set_index("Date")["Demand"]
)


# ============================================================
# TOP / SLOW PRODUCTS
# ============================================================

col1, col2 = st.columns(2)


with col1:

    st.subheader("🔥 Fast-Moving Products")

    top_products = (
        daily_demand
        .groupby("Product Name")["Demand"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    st.dataframe(
        top_products.rename("Units Sold"),
        use_container_width=True
    )


with col2:

    st.subheader("🐌 Slow-Moving Products")

    slow_products = (
        daily_demand
        .groupby("Product Name")["Demand"]
        .sum()
        .sort_values()
        .head(10)
    )

    st.dataframe(
        slow_products.rename("Units Sold"),
        use_container_width=True
    )


st.divider()


# ============================================================
# ABC / XYZ
# ============================================================

st.header("📦 Inventory Classification")

abc_col1, abc_col2 = st.columns(2)


with abc_col1:

    st.subheader("ABC Classification")

    if "ABC" in abc_xyz.columns:

        abc_counts = (
            abc_xyz["ABC"]
            .value_counts()
            .sort_index()
        )

        st.bar_chart(abc_counts)


with abc_col2:

    st.subheader("XYZ Classification")

    if "XYZ" in abc_xyz.columns:

        xyz_counts = (
            abc_xyz["XYZ"]
            .value_counts()
            .sort_index()
        )

        st.bar_chart(xyz_counts)


st.subheader("ABC × XYZ Matrix")

if "ABC_XYZ" in abc_xyz.columns:

    matrix = pd.crosstab(
        abc_xyz["ABC"],
        abc_xyz["XYZ"]
    )

    st.dataframe(
        matrix,
        use_container_width=True
    )


st.divider()


# ============================================================
# EXPIRY RISK
# ============================================================

st.header("🚨 Expiry Risk")

expiry_chart = expiry_risk.set_index(
    "Expiry_Risk"
)["Percentage_of_Stock"]

st.bar_chart(expiry_chart)


st.subheader("Products Requiring Expiry Attention")

expiry_display = expiry[
    [
        "Product Name",
        "Total_Stock",
        "Earliest_Expiry",
        "Minimum_Days_To_Expiry",
        "Expiry_Risk"
    ]
].copy()

expiry_display = expiry_display.sort_values(
    "Earliest_Expiry"
)

st.dataframe(
    expiry_display.head(20),
    use_container_width=True
)


st.divider()


# ============================================================
# PRODUCT LOOKUP
# ============================================================

st.header("🔎 Product Analysis")

products = sorted(
    daily_demand["Product Name"].unique()
)

selected_product = st.selectbox(
    "Select a product",
    products
)


product_demand = daily_demand[
    daily_demand["Product Name"] == selected_product
].copy()

product_expiry = expiry[
    expiry["Product Name"] == selected_product
]

product_inventory = inventory[
    inventory["Product Name"] == selected_product
]


# ------------------------------------------------------------
# PRODUCT METRICS
# ------------------------------------------------------------

p1, p2, p3 = st.columns(3)

with p1:

    avg_demand = product_demand["Demand"].mean()

    st.metric(
        "Average Daily Demand",
        f"{avg_demand:.2f}"
    )


with p2:

    total_product_demand = (
        product_demand["Demand"].sum()
    )

    st.metric(
        "Total Demand",
        f"{total_product_demand:.0f}"
    )


with p3:

    if len(product_expiry) > 0:

        risk = product_expiry.iloc[0]["Expiry_Risk"]

    else:

        risk = "Unknown"

    st.metric(
        "Expiry Risk",
        risk
    )


# ------------------------------------------------------------
# PRODUCT DEMAND CHART
# ------------------------------------------------------------

st.subheader(
    f"Demand History — {selected_product}"
)

product_chart = (
    product_demand
    .set_index("Date")["Demand"]
)

st.line_chart(product_chart)


# ------------------------------------------------------------
# PRODUCT EXPIRY INFORMATION
# ------------------------------------------------------------

if len(product_expiry) > 0:

    row = product_expiry.iloc[0]

    st.subheader("Expiry Information")

    e1, e2, e3 = st.columns(3)

    with e1:
        st.write("Earliest Expiry")
        st.write(
            row["Earliest_Expiry"].date()
        )

    with e2:
        st.write("Days Remaining")
        st.write(
            int(row["Minimum_Days_To_Expiry"])
        )

    with e3:
        st.write("Risk")
        st.write(
            row["Expiry_Risk"]
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Inventory recommendations are decision-support outputs "
    "based on historical demand and stated simulation assumptions."
)