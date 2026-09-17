import numpy as np
import pandas as pd


def safety_stock(std_demand, lead_time_days, service_z=1.65):
    return service_z * std_demand * np.sqrt(max(lead_time_days, 1))


def reorder_point(mean_daily_demand, std_demand, lead_time_days=7, service_z=1.65):
    ss = safety_stock(std_demand, lead_time_days, service_z)
    return mean_daily_demand * lead_time_days + ss


def build_inventory_recommendations(daily_demand, lead_time_days=7):
    stats = daily_demand.groupby("Product Name")["Demand"].agg(
        Mean_Daily_Demand="mean",
        Std_Daily_Demand="std"
    ).reset_index()

    stats["Std_Daily_Demand"] = stats["Std_Daily_Demand"].fillna(0)
    stats["Safety_Stock"] = stats.apply(
        lambda r: safety_stock(
            r["Std_Daily_Demand"], lead_time_days
        ), axis=1
    )
    stats["Reorder_Point"] = stats.apply(
        lambda r: reorder_point(
            r["Mean_Daily_Demand"],
            r["Std_Daily_Demand"],
            lead_time_days
        ), axis=1
    )
    return stats
