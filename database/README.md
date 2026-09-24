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
Run `python -B -m unittest tests.agents.test_forecast` for validation tests.

## Report Agent and saved management briefs

Open **Factory reports** to select inventory, demand forecast, production, and/or
supply chain sections. Generate a report to save its executive summary, findings,
recommendations, source timestamps, and original evidence. Open any report in
history to preview it and download its PDF without rerunning the agents.

Ask Omni also accepts **Create a combined management report**, or **Create an
inventory and production report**. **Show saved reports** and **Schedule monthly
reports** provide a link to the report controls. Existing **download that report**
requests still export the previous conversation result; those simple exports are
not added to management report history.

The agent uses evidence-based rules to calculate findings and compose the executive
summary; no additional LLM key is required. It preserves failed forecasts and
unavailable sources as visible issues. Sources are captured sequentially, so this
is not a transactionally consistent snapshot across databases. Production order
flags follow the existing Production Agent's completion rule, not a due-date check.

Storage uses `MONGO_URI` and `MONGO_DB_NAME` (default `OMNI_DB`):

- `reports`: immutable report snapshots, including the original source evidence.
- `report_schedules`: scope, frequency, next run, last outcome, and worker lease.

Supply chain sections read the existing `mock-erp.db` and `mock-tms.db` SQLite
databases in read-only mode. They never seed data, approve orders, or book shipments.
Missing databases are reported as unavailable sources.

### Schedules

Create daily or monthly schedules from the report page. Times use **Asia/Colombo
(UTC+05:30)**; monthly schedules support days 1–28 to avoid nonexistent dates.
Pause/resume controls affect future runs; a run already underway may finish.
To change the scope or time, pause the old schedule and create a replacement.

The FastAPI lifespan starts a background worker that checks for due schedules
approximately every 30 seconds. Keep the backend running for automatic generation.
Schedules survive restarts in MongoDB. If the backend was offline, one current
snapshot is created for the overdue occurrence and the next run moves into the
future. These are recurring current-state reports, **not daily/monthly historical
totals**. Files are downloaded on request from history, not automatically to a device.

Workers use atomic five-minute leases and a stable report ID per occurrence to
avoid duplicate saved reports. Storage failures retain the occurrence for retry;
source failures save a partial/error report that can be inspected in history.
Reports are shared through the application's existing access model, not per-user
private storage.

API endpoints:

- `POST /reports/generate`: report scope (`title`, `domains`, optional `skus`, `periods`).
- `GET /reports?limit=20&skip=0`: paginated history.
- `GET /reports/{report_id}`: saved report sections and summary.
- `GET /reports/schedules`: saved schedules and last outcomes.
- `POST /reports/schedules`: `scope`, `frequency`, `time`, `day_of_month`.
- `PATCH /reports/schedules/{schedule_id}`: `{ "enabled": false }` to pause.

Run `python -B -m unittest tests.agents.test_report_agent backend.test_reports` for
agent, API, and scheduling tests using mocked storage (no live database changes).
Run `node --test src/components/chatReports.test.js` from `frontend` for PDF tests.
