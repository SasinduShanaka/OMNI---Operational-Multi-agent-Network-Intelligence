"""Compare saved forecasts, or clearly labeled backtests trained before the target."""
from datetime import datetime, timezone, timedelta
import math


def compare_product(sku, demand, audits, now=None):
    from agents.forecast.forecast_agent import analyze_demand_records
    now = now or datetime.now(timezone.utc)
    end = now.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = (end - timedelta(days=1)).replace(day=1)
    period = start.date().isoformat()
    result = {'sku': sku, 'period': period, 'actual': None, 'predicted': None, 'error': None, 'absolute_error': None, 'percentage_error': None, 'status': 'unavailable'}
    history, quality = analyze_demand_records(sku, list(demand.find({'sku': sku})))
    point = next((item for item in history if item['date'] == start.date()), None)
    bad_months = {issue['month'] for issue in quality['issues'] if issue['code'] in ('multiple_records_per_month', 'invalid_quantity') and issue.get('month')}
    warning = (' Records with invalid dates or quantities were excluded; review data quality for completeness.' if quality['invalid_records'] else '')
    result['data_quality_warnings'] = [issue['message'] for issue in quality['issues'] if issue['code'] in ('invalid_date', 'invalid_quantity', 'multiple_records_per_month')]
    if point is None or period[:7] in bad_months:
        return {**result, 'note': f'Actual demand for {period[:7]} is missing or has invalid/duplicate monthly records; correct that month before comparing.' + warning}
    result.update(actual=point['quantity'], product_name=point['product_name'])
    # Only use forecasts issued before the evaluated month, latest eligible first.
    records = audits.find({'agent': 'Demand Forecast Agent', 'message_type': 'PREDICTION', 'sku': sku, 'timestamp': {'$lt': start}}).sort('timestamp', -1)
    for audit in records:
        predicted = next((p.get('quantity') for p in audit.get('predictions', []) if p.get('date', '')[:7] == period[:7]), None)
        if predicted is None and str(audit.get('forecast_period', ''))[:7] == period[:7]:
            predicted = audit.get('forecast')
        if isinstance(predicted, bool) or not isinstance(predicted, (int, float)) or not math.isfinite(predicted) or predicted < 0:
            continue
        error = predicted - result['actual']
        return {**result, 'predicted': predicted, 'error': round(error, 2), 'absolute_error': round(abs(error), 2),
                'percentage_error': round(abs(error) / result['actual'] * 100, 2) if result['actual'] else None,
                'status': 'success', 'prediction_source': 'Saved forecast', 'note': 'Latest saved forecast issued before the evaluated month. Positive error means overforecasting.' + warning}
    # Walk backward from the immediately preceding month, stopping at the first
    # gap or bad month. Older gaps cannot invalidate the usable recent suffix.
    month_index = lambda value: value.year * 12 + value.month
    by_month = {month_index(row['date']): row for row in history if row['date'] < start.date()}
    cursor = month_index(start) - 1
    training = []
    while cursor in by_month and by_month[cursor]['date'].strftime('%Y-%m') not in bad_months:
        training.append(by_month[cursor])
        cursor -= 1
    training.reverse()
    boundary = f'{(cursor - 1) // 12:04d}-{(cursor - 1) % 12 + 1:02d}'
    if len(training) < 3:
        reason = 'invalid or duplicate records' if boundary in bad_months else 'missing demand'
        return {**result, 'training_months': len(training), 'note': f'No eligible saved forecast. Found {len(training)} consecutive valid training months before {period[:7]}; at least 3 are required. The sequence stops at {boundary}: {reason}. Add or correct verified monthly totals.' + warning}
    from agents.forecast.forecast_agent import _fit_holt
    level, trend, _, _ = _fit_holt([row['quantity'] for row in training])
    predicted = max(0, round(level + trend, 2))
    error = predicted - result['actual']
    return {**result, 'status': 'success', 'prediction_source': 'Historical backtest estimate',
            'predicted': predicted, 'error': round(error, 2), 'absolute_error': round(abs(error), 2),
            'percentage_error': round(abs(error) / result['actual'] * 100, 2) if result['actual'] else None,
            'training_months': len(training), 'training_end': training[-1]['date'].isoformat(),
            'training_start': training[0]['date'].isoformat(),
            'note': f"Historical backtest estimate calculated now using {len(training)} consecutive valid months from {training[0]['date']:%Y-%m} through {training[-1]['date']:%Y-%m}. Earlier disconnected history, the evaluated month, and later records were excluded from training. This is not a forecast saved at that time. Positive error means overforecasting." + warning}


def compare_last_month(skus):
    from agents.forecast.forecast_agent import demand_collection, activity_collection
    if demand_collection is None or activity_collection is None:
        raise RuntimeError('Demand and forecast audit storage must be configured.')
    return [compare_product(sku, demand_collection, activity_collection) for sku in skus]
