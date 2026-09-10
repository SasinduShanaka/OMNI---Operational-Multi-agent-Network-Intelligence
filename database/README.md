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
