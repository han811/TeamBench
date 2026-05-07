# TeamBench Datasets

This directory contains canonical public datasets used by TeamBench DS/ML tasks.
Each dataset is either downloaded from its primary source or represented by a
realistic synthetic placeholder when the original requires authentication.

## Canonical Dataset Catalogue

| Name | Source | License | Rows (subsample) | File |
|------|--------|---------|-------------------|------|
| lending_club | Kaggle | CC0 | 50,000 | `lending_club.csv` |
| adult_income | UCI ML Repo | CC-BY 4.0 | 48,842 (full) | `adult_income.csv` |
| ames_housing | Kaggle/OpenML | CC0 | 2,930 (full) | `ames_housing.csv` |
| nyc_taxi | NYC TLC | Public Domain | 100,000 | `nyc_taxi.csv` |
| online_retail | UCI ML Repo | CC-BY 4.0 | 500,000 | `online_retail.csv` |
| telco_churn | Kaggle/IBM | Public Domain | 7,043 (full) | `telco_churn.csv` |
| credit_card_fraud | Kaggle/ULB | CC0 | 50,000 | `credit_card_fraud.csv` |
| fred_macro | FRED (St. Louis Fed) | Public Domain | time series | `fred_macro.csv` |
| who_gho | WHO GHO | CC-BY 4.0 | ~3,000 country-years | `who_gho.csv` |
| stackoverflow | Stack Overflow Survey | ODbL | 50,000 | `stackoverflow.csv` |

## Usage

### List available datasets
```bash
python datasets/download_datasets.py --list
```

### Download a single dataset
```bash
python datasets/download_datasets.py --dataset adult_income
python datasets/download_datasets.py --dataset fred_macro
python datasets/download_datasets.py --dataset telco_churn
```

### Download all datasets
```bash
python datasets/download_datasets.py --all
```

Datasets that can be fetched via direct HTTP (no authentication required):
- `adult_income` — UCI ML Repository
- `fred_macro` — FRED CSV API (UNRATE, CPIAUCSL, FEDFUNDS, GDP series)
- `telco_churn` — IBM GitHub raw CSV

Datasets that require Kaggle credentials or are otherwise gated will fall back
to a **synthetic placeholder** that matches the real schema and statistical
properties well enough for benchmark tasks. To use real data, download the
files manually and place them in this directory with the filenames shown above.

## Regenerating All Datasets

```bash
# From the repo root
python datasets/download_datasets.py --all

# Force re-download even if files already exist
python datasets/download_datasets.py --all --force
```

## Schema Notes

### lending_club
Columns: `loan_amnt`, `funded_amnt`, `term`, `int_rate`, `installment`,
`grade`, `sub_grade`, `emp_length`, `home_ownership`, `annual_inc`,
`verification_status`, `loan_status`, `purpose`, `dti`, `delinq_2yrs`,
`fico_range_low`, `fico_range_high`, `open_acc`, `pub_rec`, `revol_bal`,
`revol_util`, `total_acc`, `out_prncp`, `total_pymnt`, `total_rec_prncp`,
`total_rec_int`, `last_pymnt_amnt`, `recoveries`, `default_ind`

### adult_income
Columns: `age`, `workclass`, `fnlwgt`, `education`, `education_num`,
`marital_status`, `occupation`, `relationship`, `race`, `sex`,
`capital_gain`, `capital_loss`, `hours_per_week`, `native_country`, `income`

### ames_housing
Columns: 80 features including `LotArea`, `OverallQual`, `OverallCond`,
`YearBuilt`, `YearRemodAdd`, `TotalBsmtSF`, `GrLivArea`, `FullBath`,
`HalfBath`, `BedroomAbvGr`, `GarageCars`, `GarageArea`, `PoolArea`,
`MoSold`, `YrSold`, `SalePrice`

### nyc_taxi
Columns: `VendorID`, `tpep_pickup_datetime`, `tpep_dropoff_datetime`,
`passenger_count`, `trip_distance`, `RatecodeID`, `store_and_fwd_flag`,
`PULocationID`, `DOLocationID`, `payment_type`, `fare_amount`, `extra`,
`mta_tax`, `tip_amount`, `tolls_amount`, `improvement_surcharge`,
`total_amount`, `congestion_surcharge`

### online_retail
Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`,
`UnitPrice`, `CustomerID`, `Country`

### telco_churn
Columns: `customerID`, `gender`, `SeniorCitizen`, `Partner`, `Dependents`,
`tenure`, `PhoneService`, `MultipleLines`, `InternetService`,
`OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`,
`StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`,
`PaymentMethod`, `MonthlyCharges`, `TotalCharges`, `Churn`

### credit_card_fraud
Columns: `Time`, `V1`–`V28` (PCA-transformed), `Amount`, `Class`

### fred_macro
Columns: `date`, `UNRATE` (unemployment rate), `CPIAUCSL` (CPI),
`FEDFUNDS` (federal funds rate), `GDP` (quarterly GDP)

### who_gho
Columns: `country`, `country_code`, `year`, `life_expectancy`,
`infant_mortality`, `under5_mortality`, `maternal_mortality`,
`hiv_prevalence`, `tb_incidence`, `malaria_incidence`, `measles_incidence`,
`physicians_per_1000`, `hospital_beds_per_1000`, `health_expenditure_pct_gdp`,
`income_group`, `region`

### stackoverflow
Columns: `ResponseId`, `MainBranch`, `Employment`, `Country`, `EdLevel`,
`YearsCode`, `YearsCodePro`, `DevType`, `OrgSize`, `Currency`,
`CompTotal`, `CompFreq`, `LanguageHaveWorkedWith`, `LanguageWantToWorkWith`,
`DatabaseHaveWorkedWith`, `PlatformHaveWorkedWith`, `WebframeHaveWorkedWith`,
`Age`, `Gender`, `MentalHealth`, `JobSat`, `ConvertedCompYearly`

## License Notes

- **CC0**: No rights reserved; free to use for any purpose.
- **CC-BY 4.0**: Attribution required.
- **ODbL**: Open Database License; derived works must use same license.
- **Public Domain**: No restrictions.

Synthetic placeholder files generated by this toolkit are released under CC0.
