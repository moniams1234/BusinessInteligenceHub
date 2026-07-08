import numpy as np
import pandas as pd

_EMPTY_COLS = ["month_name", "sales_pln", "trend_forecast", "stl_forecast", "is_forecast"]


def compute_forecast(monthly_df: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    df = monthly_df[["month_name", "sales_pln"]].copy().sort_values("month_name").reset_index(drop=True)

    if len(df) < 3 or df["sales_pln"].sum() == 0:
        return pd.DataFrame(columns=_EMPTY_COLS)

    y = df["sales_pln"].values.astype(float)
    x = np.arange(len(df), dtype=float)

    # --- Linear trend ---
    slope, intercept = np.polyfit(x, y, deg=1)
    future_x = np.arange(len(df), len(df) + horizon, dtype=float)
    trend_values = (slope * future_x + intercept).tolist()

    # --- Future month labels ---
    last_period = pd.Period(df["month_name"].iloc[-1], freq="M")
    future_months = [(last_period + i + 1).strftime("%Y-%m") for i in range(horizon)]

    # --- STL ---
    stl_values = [float("nan")] * horizon
    if len(df) >= 24:
        try:
            from statsmodels.tsa.seasonal import STL

            series = pd.Series(y, dtype=float)
            stl_result = STL(series, period=12).fit()
            trend_comp = stl_result.trend
            seasonal_comp = stl_result.seasonal

            recent = trend_comp.iloc[-3:]
            trend_slope = (recent.iloc[-1] - recent.iloc[0]) / max(len(recent) - 1, 1)

            for i in range(horizon):
                seasonal_idx = len(df) - 12 + i
                seasonal_val = seasonal_comp.iloc[seasonal_idx] if 0 <= seasonal_idx < len(seasonal_comp) else 0.0
                trend_val = trend_comp.iloc[-1] + trend_slope * (i + 1)
                stl_values[i] = trend_val + seasonal_val
        except Exception:
            stl_values = [float("nan")] * horizon

    # --- Assemble output ---
    history = df.copy()
    history["trend_forecast"] = float("nan")
    history["stl_forecast"] = float("nan")
    history["is_forecast"] = False

    forecast_rows = pd.DataFrame({
        "month_name": future_months,
        "sales_pln": float("nan"),
        "trend_forecast": trend_values,
        "stl_forecast": stl_values,
        "is_forecast": True,
    })

    return pd.concat([history, forecast_rows], ignore_index=True)
