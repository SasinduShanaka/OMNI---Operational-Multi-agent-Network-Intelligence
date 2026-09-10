"""MongoDB-backed Demand Forecast Agent for OMNI."""

import math
import os
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) if MONGO_URI else None
db = mongo_client["OMNI_DB"] if mongo_client else None
demand_collection = db["demand_history"] if db is not None else None
activity_collection = db["agent_activity"] if db is not None else None

SKU_PATTERN = re.compile(r"^GAR-\d{3}$", re.IGNORECASE)
MIN_HISTORY_POINTS = 3
MAX_FORECAST_PERIODS = 12


def get_forecast_products():
    """Return the distinct products available in MongoDB demand history."""
    if demand_collection is None:
        raise RuntimeError("MONGO_URI is not configured.")
    products = {}
    for row in demand_collection.find({}, {"_id": 0, "sku": 1, "product_name": 1}):
        sku = _normalize_sku(row.get("sku"))
        if sku:
            products[sku] = {"sku": sku, "product_name": row.get("product_name") or sku}
    return [products[sku] for sku in sorted(products)]


def get_demand_history(sku: str) -> list[dict[str, Any]]:
    """Clean, aggregate, and chronologically sort one SKU's monthly demand."""
    normalized_sku = _normalize_sku(sku)
    if not normalized_sku or demand_collection is None:
        return []
    records = demand_collection.find(
        {"sku": normalized_sku},
        {"_id": 0, "date": 1, "quantity": 1, "product_name": 1, "sku": 1},
    )
    totals: dict[date, float] = defaultdict(float)
    names: dict[date, str] = {}
    for record in records:
        try:
            quantity = float(record["quantity"])
            observed_at = _parse_date(record["date"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(quantity) or quantity < 0:
            continue
        month = date(observed_at.year, observed_at.month, 1)
        totals[month] += quantity
        if record.get("product_name"):
            names[month] = str(record["product_name"])
    return [{
        "sku": normalized_sku,
        "product_name": names.get(month, normalized_sku),
        "date": month,
        "quantity": round(totals[month], 2),
    } for month in sorted(totals)]


def forecast_demand(sku: str, periods: int = 1, save_audit: bool = True) -> dict[str, Any]:
    """Forecast 1-12 upcoming monthly periods and return model accuracy."""
    normalized_sku = _normalize_sku(sku)
    if not normalized_sku:
        return _error("invalid_sku", "Provide a valid SKU such as GAR-003.")
    if not isinstance(periods, int) or isinstance(periods, bool) or not 1 <= periods <= MAX_FORECAST_PERIODS:
        return _error("invalid_periods", f"periods must be between 1 and {MAX_FORECAST_PERIODS}.", normalized_sku)
    if demand_collection is None:
        return _error("configuration_error", "Demand data is unavailable because MONGO_URI is not configured.", normalized_sku)
    try:
        history = get_demand_history(normalized_sku)
    except Exception as error:
        return _error("data_access_error", f"Unable to retrieve demand history: {error}", normalized_sku)
    if not history:
        return _error("not_found", f"No demand history was found for {normalized_sku}.", normalized_sku)
    if len(history) < MIN_HISTORY_POINTS:
        return _error("insufficient_history", f"At least {MIN_HISTORY_POINTS} demand periods are needed; only {len(history)} are available.", normalized_sku, len(history))

    quantities = [record["quantity"] for record in history]
    level, slope, alpha, beta = _fit_holt(quantities)
    predictions = [{
        "date": _add_months(history[-1]["date"], offset).isoformat(),
        "quantity": max(0, round(level + slope * offset, 2)),
    } for offset in range(1, periods + 1)]
    average = sum(quantities) / len(quantities)
    trend = _trend_label(slope, average)
    result = {
        "status": "success",
        "agent": "Demand Forecast Agent",
        "sku": normalized_sku,
        "product_name": history[-1].get("product_name", normalized_sku),
        "forecast": predictions[0]["quantity"],
        "forecast_period": predictions[0]["date"],
        "forecast_horizon_months": periods,
        "predictions": predictions,
        "trend": trend,
        "trend_per_period": round(slope, 2),
        "average_historical_demand": round(average, 2),
        "history_points": len(history),
        "history_start": history[0]["date"].isoformat(),
        "history_end": history[-1]["date"].isoformat(),
        "history": [{"date": row["date"].isoformat(), "quantity": row["quantity"]} for row in history],
        "model": "Holt's Linear Trend",
        "smoothing_parameters": {
            "alpha": alpha,
            "beta": beta,
        },
        "model_components": {
            "level": round(level, 2),
            "trend": round(slope, 2),
        },
        "accuracy": _backtest_accuracy(quantities),
        "recommendation": _recommendation(trend, predictions[0]["quantity"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    result["audit_saved"] = _save_audit(result) if save_audit else False
    return result


def forecast_all_demand(periods: int = 1, save_audit: bool = True) -> list[dict[str, Any]]:
    if demand_collection is None:
        return []
    try:
        skus = sorted(value for value in demand_collection.distinct("sku") if _normalize_sku(value))
    except AttributeError:
        skus = sorted({row.get("sku") for row in demand_collection.find({}, {"sku": 1}) if row.get("sku")})
    except Exception:
        return []
    return [result for sku in skus if (result := forecast_demand(sku, periods, save_audit))["status"] == "success"]


def _backtest_accuracy(values: list[float]) -> dict[str, float | int | str]:
    """Expanding-window one-step backtest; positive bias means overforecasting."""
    actuals, predictions = [], []
    for index in range(2, len(values)):
        level, trend, _, _ = _fit_holt(values[:index])
        actuals.append(values[index])
        predictions.append(max(0, level + trend))
    errors = [prediction - actual for prediction, actual in zip(predictions, actuals)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error ** 2 for error in errors) / len(errors))
    percentage_errors = [abs(error / actual) for error, actual in zip(errors, actuals) if actual]
    mape = 100 * sum(percentage_errors) / len(percentage_errors) if percentage_errors else 0.0
    return {
        "method": "rolling one-step backtest",
        "test_points": len(actuals),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape_percent": round(mape, 2),
        "accuracy_percent": round(max(0.0, 100.0 - mape), 2),
        "bias": round(sum(errors) / len(errors), 2),
    }


def _save_audit(result: dict[str, Any]) -> bool:
    if activity_collection is None:
        return False
    try:
        activity_collection.insert_one({
            "agent": "Demand Forecast Agent", "action": "Demand forecast generated",
            "message_type": "PREDICTION", "sku": result["sku"], "forecast": result["forecast"],
            "forecast_period": result["forecast_period"], "trend": result["trend"],
            "model": result["model"], "smoothing_parameters": result["smoothing_parameters"],
            "accuracy": result["accuracy"],
            "timestamp": datetime.now(timezone.utc),
        })
        return True
    except Exception:
        return False


def _fit_holt(values: list[float]) -> tuple[float, float, float, float]:
    """Fit Holt's additive linear-trend model with a small grid search.

    Alpha controls how quickly the estimated demand level reacts to new data,
    while beta controls how quickly the trend reacts. The pair with the lowest
    one-step in-sample squared error is selected deterministically.
    """
    candidates = [round(step / 20, 2) for step in range(1, 20)]
    best: tuple[float, float, float, float] | None = None
    best_error = math.inf

    for alpha in candidates:
        for beta in candidates:
            level, trend, squared_error = _holt_state(values, alpha, beta)
            if squared_error < best_error:
                best_error = squared_error
                best = (level, trend, alpha, beta)

    if best is None:  # Defensive fallback; validated calls always have 2+ values.
        return values[-1], 0.0, 0.5, 0.5
    return best


def _holt_state(values: list[float], alpha: float, beta: float) -> tuple[float, float, float]:
    """Return final level, trend, and one-step squared fitting error."""
    level = values[0]
    trend = values[1] - values[0] if len(values) > 1 else 0.0
    squared_error = 0.0

    for actual in values[1:]:
        one_step_forecast = level + trend
        squared_error += (actual - one_step_forecast) ** 2
        previous_level = level
        level = alpha * actual + (1 - alpha) * one_step_forecast
        trend = beta * (level - previous_level) + (1 - beta) * trend

    return level, trend, squared_error


def _trend_label(slope: float, average: float) -> str:
    tolerance = max(1.0, average * 0.02)
    return "Increasing" if slope > tolerance else "Decreasing" if slope < -tolerance else "Stable"


def _recommendation(trend: str, forecast: float) -> str:
    if trend == "Increasing":
        return f"Plan capacity and material availability for approximately {forecast:,.0f} units next month."
    if trend == "Decreasing":
        return "Review the production plan before committing additional material purchases."
    return "Maintain the current production plan and monitor demand for changes."


def _normalize_sku(sku: str | None) -> str | None:
    value = sku.strip().upper() if isinstance(sku, str) else ""
    return value if SKU_PATTERN.fullmatch(value) else None


def _parse_date(value: Any) -> datetime:
    # Some manually pasted records retain Extended JSON as a nested object.
    if isinstance(value, dict) and set(value) == {"$date"}:
        value = value["$date"]
        if isinstance(value, dict) and set(value) == {"$numberLong"}:
            return datetime.fromtimestamp(int(value["$numberLong"]) / 1000, tz=timezone.utc)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("date must be a date, datetime, or ISO date string")


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _error(code: str, message: str, sku: str | None = None, history_points: int = 0) -> dict[str, Any]:
    result = {"status": "error", "agent": "Demand Forecast Agent", "error_code": code, "message": message, "history_points": history_points}
    if sku:
        result["sku"] = sku
    return result
