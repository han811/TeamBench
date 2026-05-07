# RDS27: NYC Taxi Demand Anomaly Investigation

## Background

NYC TLC yellow taxi trip data shows an anomalous demand spike on
**March 14–15, 2018** — trip counts were approximately 34%
above the baseline for comparable days in the same period.

Your task is to identify all factors that contributed to this spike
by synthesizing evidence from the trip data and three external documents.

## Dataset

- File: `data/nyc_taxi.csv`
- Rows: 2000 (subsample)
- Key columns: `tpep_pickup_datetime`, `tpep_dropoff_datetime`,
  `trip_distance`, `fare_amount`, `PULocationID`, `DOLocationID`

## Corpus Documents

Reference documents in `corpus/`:

| File | Description |
|------|-------------|
| `weather.csv` | Daily weather data (precipitation, temperature, conditions) |
| `events.csv` | Major events schedule with venue and attendance |
| `transit_disruptions.md` | MTA service advisory for affected dates |

**All three factors contribute.** Identify each one and, where possible,
quantify its contribution to the demand spike.

## Required Deliverables

### 1. `analysis.py`
- Load and explore taxi trip data
- Identify anomaly dates by computing trip volume vs baseline
- Read corpus documents and correlate with anomaly timing
- Quantify each factor's estimated contribution where data permits

### 2. `results.json`
```json
{
  "anomaly_dates": ["<date1>", ...],
  "baseline_trip_count": <float>,
  "anomaly_trip_count": <float>,
  "demand_spike_pct": <float>,
  "demand_spike_factors": ["<factor1>", "<factor2>", "<factor3>"],
  "primary_factor": "<string>"
}
```

### 3. `report.md`
400–700 words covering:
- Magnitude of the demand spike (quantified)
- Each contributing factor with supporting evidence
- Which factor had the greatest impact and why
- Operational implications for taxi/rideshare dispatching

## Grading Criteria
1. `analysis.py` runs without error
2. Weather / precipitation factor identified
3. Major event factor identified
4. Transit disruption / subway closure identified
5. `results.json` has `demand_spike_factors` with ≥ 2 entries
6. `report.md` quantifies at least one factor's contribution
7. Data loaded correctly
8. `results.json` valid JSON with required fields
