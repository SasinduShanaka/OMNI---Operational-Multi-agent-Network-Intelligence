# Demand forecast data

The forecast reads `OMNI_DB.demand_history` using `MONGO_URI` from
`backend/.env`. Product choices are loaded from this collection.

Add records in MongoDB Compass with these fields:

- `sku`: product code, such as `GAR-006`.
- `product_name`: display name.
- `date`: preferably a BSON date; ISO date strings and supported Extended JSON
  date objects can also be read.
- `quantity`: nonnegative numeric demand.

Forecasting needs at least three distinct months per product. Records within
one month are summed, so avoid inserting duplicate monthly totals. Reload the
forecast page after adding products; run the forecast again after data changes.

The dashboard includes historical charts, monthly predictions, backtest metrics,
and a one-page PDF preview with download and print controls. Backtest metrics
measure historical error, not future certainty.

`seed_data.py` is a separate demonstration utility that clears and repopulates
multiple collections. It is not executed by the forecast API.

## Data quality checks

The dashboard checks the selected product automatically and provides a Check
again button after Compass edits. `GET /forecast/data-quality/{sku}` returns
counts, issues, document IDs, missing months, and forecast eligibility.
Forecast responses also include `data_quality` from the same record snapshot
used in calculations, including validation failures.

Invalid dates and nonfinite, negative, or boolean quantities are excluded.
Zero quantities and numeric strings are accepted. Missing product names use
the SKU as a fallback and generate a warning. Multiple records per month and
inconsistent names are flagged for review; no records are modified or deleted.
Fewer than three usable months or gaps between observed months block forecasts.
Three to seven usable months generate a limited-validation warning.

To demonstrate this feature, use a demo database: insert an invalid date,
repeat a monthly total, or remove an intermediate month. Check again to see
issues, correct the data in Compass, and recheck before rerunning the forecast.
Run `python -B -m unittest agents.test_forecast` for validation tests.
