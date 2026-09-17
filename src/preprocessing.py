import pandas as pd

def load_sales_register(path):
    df = pd.read_excel(path, sheet_name="Sales Register", header=3)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df["Date"].notna()].copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Amount (₹)"] = pd.to_numeric(df["Amount (₹)"], errors="coerce")
    df["MRP (₹)"] = pd.to_numeric(df["MRP (₹)"], errors="coerce")

    df["Product Name"] = (
        df["Product Name"].astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    return df.dropna(subset=["Date", "Product Name", "Quantity"])


def make_daily_sku_demand(df):
    daily = (
        df.groupby(["Date", "Product Name"], as_index=False)["Quantity"]
        .sum()
        .rename(columns={"Quantity": "Demand"})
    )

    dates = pd.date_range(daily["Date"].min(), daily["Date"].max(), freq="D")
    products = sorted(daily["Product Name"].unique())

    grid = pd.MultiIndex.from_product(
        [dates, products], names=["Date", "Product Name"]
    ).to_frame(index=False)

    result = grid.merge(daily, on=["Date", "Product Name"], how="left")
    result["Demand"] = result["Demand"].fillna(0)
    return result
