import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor
from prophet import Prophet


# =========================================================
# PROJECT PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "daily_sku_demand.csv"
OUTPUT_DIR = ROOT / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)


# =========================================================
# LOAD DATA
# =========================================================

df = pd.read_csv(
    DATA_FILE,
    parse_dates=["Date"]
)

df = df.sort_values(
    ["Product Name", "Date"]
).reset_index(drop=True)

print("Data loaded!")
print("Rows:", len(df))
print("SKUs:", df["Product Name"].nunique())


# =========================================================
# WMAPE
# =========================================================

def wmape(actual, predicted):

    actual = np.array(actual)
    predicted = np.array(predicted)

    denominator = np.sum(np.abs(actual))

    if denominator == 0:
        return np.nan

    return (
        np.sum(np.abs(actual - predicted))
        / denominator
    )


# =========================================================
# CREATE LAG FEATURES FOR XGBOOST
# =========================================================

model_df = df.copy()

group = model_df.groupby("Product Name")["Demand"]

# Previous demand
model_df["lag_1"] = group.shift(1)
model_df["lag_7"] = group.shift(7)
model_df["lag_14"] = group.shift(14)
model_df["lag_28"] = group.shift(28)

# Rolling demand
model_df["rolling_7"] = (
    model_df
    .groupby("Product Name")["Demand"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(7)
        .mean()
    )
)

model_df["rolling_14"] = (
    model_df
    .groupby("Product Name")["Demand"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(14)
        .mean()
    )
)

model_df["rolling_28"] = (
    model_df
    .groupby("Product Name")["Demand"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(28)
        .mean()
    )
)

# Date features
model_df["day_of_week"] = (
    model_df["Date"].dt.dayofweek
)

model_df["month"] = (
    model_df["Date"].dt.month
)

model_df["day"] = (
    model_df["Date"].dt.day
)

model_df["is_weekend"] = (
    model_df["day_of_week"] >= 5
).astype(int)


# Remove rows where lag features don't exist
model_df = model_df.dropna().copy()


# =========================================================
# TIME-BASED TRAIN / TEST SPLIT
# =========================================================

# Last 28 days = test set
cutoff = (
    model_df["Date"].max()
    - pd.Timedelta(days=27)
)

train = model_df[
    model_df["Date"] < cutoff
].copy()

test = model_df[
    model_df["Date"] >= cutoff
].copy()

print("\nTrain period:")
print(train["Date"].min(), "to", train["Date"].max())

print("\nTest period:")
print(test["Date"].min(), "to", test["Date"].max())


# =========================================================
# XGBOOST
# =========================================================

features = [
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_7",
    "rolling_14",
    "rolling_28",
    "day_of_week",
    "month",
    "day",
    "is_weekend"
]

print("\nTraining XGBoost...")

xgb_model = XGBRegressor(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42
)

xgb_model.fit(
    train[features],
    train["Demand"]
)

test["XGBoost"] = (
    xgb_model
    .predict(test[features])
)

# Demand cannot be negative
test["XGBoost"] = (
    test["XGBoost"]
    .clip(lower=0)
)


# =========================================================
# NAIVE BASELINE
# =========================================================

test["Naive"] = test["lag_7"]


# =========================================================
# MOVING AVERAGE BASELINE
# =========================================================

test["Moving_Average"] = test[
    "rolling_7"
]


# =========================================================
# PROPHET
# =========================================================

print("\nTraining Prophet models...")

prophet_predictions = []

products = test["Product Name"].unique()

for i, product in enumerate(products, start=1):

    print(
        f"Prophet: {i}/{len(products)} - {product}"
    )

    product_train = train[
        train["Product Name"] == product
    ][["Date", "Demand"]].copy()

    product_test = test[
        test["Product Name"] == product
    ][["Date", "Demand"]].copy()

    # Prophet requires ds and y
    prophet_train = product_train.rename(
        columns={
            "Date": "ds",
            "Demand": "y"
        }
    )

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05
    )

    model.fit(prophet_train)

    future = pd.DataFrame({
        "ds": product_test["Date"]
    })

    forecast = model.predict(future)

    prediction = forecast[
        ["ds", "yhat"]
    ].copy()

    prediction["Product Name"] = product
    prediction = prediction.rename(
        columns={
            "ds": "Date",
            "yhat": "Prophet"
        }
    )

    prediction["Prophet"] = (
        prediction["Prophet"]
        .clip(lower=0)
    )

    prophet_predictions.append(
        prediction
    )


# Combine Prophet predictions
prophet_df = pd.concat(
    prophet_predictions,
    ignore_index=True
)


# =========================================================
# MERGE ALL PREDICTIONS
# =========================================================

test = test.merge(
    prophet_df,
    on=["Date", "Product Name"],
    how="left"
)


# =========================================================
# MODEL EVALUATION
# =========================================================

models = [
    "Naive",
    "Moving_Average",
    "XGBoost",
    "Prophet"
]

results = []

for model_name in models:

    actual = test["Demand"]
    predicted = test[model_name]

    results.append({

        "Model": model_name,

        "WMAPE": wmape(
            actual,
            predicted
        ),

        "MAE": mean_absolute_error(
            actual,
            predicted
        ),

        "RMSE": np.sqrt(
            mean_squared_error(
                actual,
                predicted
            )
        )
    })


results_df = pd.DataFrame(results)


# =========================================================
# PRINT RESULTS
# =========================================================

print("\n")
print("=" * 60)
print("FORECASTING RESULTS")
print("=" * 60)

print(
    results_df.to_string(
        index=False
    )
)


# =========================================================
# SAVE RESULTS
# =========================================================

results_df.to_csv(
    OUTPUT_DIR /
    "forecast_metrics.csv",
    index=False
)

test[
    [
        "Date",
        "Product Name",
        "Demand",
        "Naive",
        "Moving_Average",
        "XGBoost",
        "Prophet"
    ]
].to_csv(
    OUTPUT_DIR /
    "forecast_comparison.csv",
    index=False
)


print("\n")
print("=" * 60)
print("SUCCESS!")
print("=" * 60)

print(
    "Metrics saved to:",
    OUTPUT_DIR /
    "forecast_metrics.csv"
)

print(
    "Predictions saved to:",
    OUTPUT_DIR /
    "forecast_comparison.csv"
)