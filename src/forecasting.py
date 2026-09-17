import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor


def wmape(y_true, y_pred):
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return np.nan
    return np.sum(np.abs(np.asarray(y_true) - np.asarray(y_pred))) / denominator


def add_lag_features(df, lags=(1, 7, 14, 28), rolling_windows=(7, 14, 28)):
    out = df.sort_values(["Product Name", "Date"]).copy()
    g = out.groupby("Product Name")["Demand"]

    for lag in lags:
        out[f"lag_{lag}"] = g.shift(lag)

    for w in rolling_windows:
        out[f"roll_mean_{w}"] = (
            out.groupby("Product Name")["Demand"]
            .transform(lambda s: s.shift(1).rolling(w).mean())
        )

    out["dow"] = out["Date"].dt.dayofweek
    out["month"] = out["Date"].dt.month
    out["day"] = out["Date"].dt.day
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    return out


def train_xgboost(train, features):
    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42
    )
    model.fit(train[features], train["Demand"])
    return model


def evaluate_predictions(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "WMAPE": wmape(y_true, y_pred)
    }
