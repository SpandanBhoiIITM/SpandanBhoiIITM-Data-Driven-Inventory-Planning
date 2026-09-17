import numpy as np

def wmape(y_true, y_pred):
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return np.nan
    return np.sum(np.abs(np.asarray(y_true) - np.asarray(y_pred))) / denominator


def improvement_percent(baseline_wmape, model_wmape):
    if baseline_wmape == 0:
        return np.nan
    return (baseline_wmape - model_wmape) / baseline_wmape * 100
