#!/usr/bin/env python3
"""
Download and prepare canonical public datasets for TeamBench DS/ML tasks.

Usage:
    python datasets/download_datasets.py --list
    python datasets/download_datasets.py --dataset adult_income
    python datasets/download_datasets.py --all [--force]

Datasets available via direct HTTP (no auth):
    adult_income, fred_macro, telco_churn

All other datasets fall back to realistic synthetic placeholders that match
the real schema and approximate statistical properties.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import random
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

DATASETS: dict[str, dict] = {
    "adult_income": {
        "description": "UCI Adult Income — predict whether income exceeds $50K/yr",
        "source": "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data",
        "license": "CC-BY 4.0",
        "rows": "48,842 (full)",
        "direct_download": True,
    },
    "fred_macro": {
        "description": "FRED macroeconomic time series: UNRATE, CPIAUCSL, FEDFUNDS, GDP",
        "source": "https://fred.stlouisfed.org/graph/fredgraph.csv",
        "license": "Public Domain",
        "rows": "time series (~780 months)",
        "direct_download": True,
    },
    "telco_churn": {
        "description": "IBM Telco Customer Churn dataset",
        "source": (
            "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d"
            "/master/data/Telco-Customer-Churn.csv"
        ),
        "license": "Public Domain",
        "rows": "7,043 (full)",
        "direct_download": True,
    },
    "lending_club": {
        "description": "Lending Club loan data (Kaggle CC0) — synthetic placeholder",
        "source": "https://www.kaggle.com/datasets/wordsforthewise/lending-club",
        "license": "CC0",
        "rows": "50,000 (subsample / placeholder)",
        "direct_download": False,
    },
    "ames_housing": {
        "description": "Ames Housing dataset (Kaggle/OpenML CC0) — synthetic placeholder",
        "source": "https://www.kaggle.com/c/house-prices-advanced-regression-techniques",
        "license": "CC0",
        "rows": "2,930 (full / placeholder)",
        "direct_download": False,
    },
    "nyc_taxi": {
        "description": "NYC TLC Yellow Taxi trip records — synthetic placeholder",
        "source": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
        "license": "Public Domain",
        "rows": "100,000 (subsample / placeholder)",
        "direct_download": False,
    },
    "online_retail": {
        "description": "UCI Online Retail transactional data — synthetic placeholder",
        "source": "https://archive.ics.uci.edu/ml/datasets/online+retail",
        "license": "CC-BY 4.0",
        "rows": "500,000 (subsample / placeholder)",
        "direct_download": False,
    },
    "credit_card_fraud": {
        "description": "ULB Credit Card Fraud Detection (Kaggle CC0) — synthetic placeholder",
        "source": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
        "license": "CC0",
        "rows": "50,000 (subsample / placeholder)",
        "direct_download": False,
    },
    "who_gho": {
        "description": "WHO Global Health Observatory country-year statistics — synthetic placeholder",
        "source": "https://www.who.int/data/gho",
        "license": "CC-BY 4.0",
        "rows": "~3,000 country-years (placeholder)",
        "direct_download": False,
    },
    "stackoverflow": {
        "description": "Stack Overflow Annual Developer Survey (ODbL) — synthetic placeholder",
        "source": "https://insights.stackoverflow.com/survey",
        "license": "ODbL",
        "rows": "50,000 (subsample / placeholder)",
        "direct_download": False,
    },
}

DATASETS_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def _write_csv(path: Path, header: list[str], rows: list[list], provenance: str) -> None:
    """Write rows to a CSV file with a provenance comment header."""
    lines = [f"# {line}" for line in provenance.strip().splitlines()]
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    size_kb = path.stat().st_size // 1024
    print(f"  Written {len(rows):,} rows -> {path.name} ({size_kb} KB)")


def _fetch_url(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "TeamBench/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# Direct downloaders
# ---------------------------------------------------------------------------

def download_adult_income(path: Path) -> None:
    """Download UCI Adult Income dataset (no auth required)."""
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
    header = [
        "age", "workclass", "fnlwgt", "education", "education_num",
        "marital_status", "occupation", "relationship", "race", "sex",
        "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
    ]
    provenance = (
        "Dataset: Adult Income (Census Income)\n"
        "Source:  https://archive.ics.uci.edu/ml/datasets/adult\n"
        "License: CC-BY 4.0\n"
        "Rows:    48,842 (full dataset)\n"
        "Task:    Binary classification — income >50K vs <=50K"
    )
    print(f"  Fetching {url} ...")
    raw = _fetch_url(url)
    text = raw.decode("utf-8", errors="replace")
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 15:
            rows.append(parts)
    _write_csv(path, header, rows, provenance)


def download_fred_macro(path: Path) -> None:
    """Download FRED macroeconomic series via CSV API."""
    # Series: UNRATE (monthly), CPIAUCSL (monthly), FEDFUNDS (monthly), GDP (quarterly)
    series = {
        "UNRATE": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE",
        "CPIAUCSL": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL",
        "FEDFUNDS": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS",
        "GDP": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP",
    }
    provenance = (
        "Dataset: FRED Macroeconomic Time Series\n"
        "Source:  https://fred.stlouisfed.org/\n"
        "License: Public Domain (Federal Reserve Bank of St. Louis)\n"
        "Series:  UNRATE (unemployment %), CPIAUCSL (CPI), FEDFUNDS (fed funds rate), GDP\n"
        "Rows:    Monthly/quarterly observations merged on date"
    )
    data: dict[str, dict] = {}
    for name, url in series.items():
        print(f"  Fetching FRED series {name} ...")
        raw = _fetch_url(url)
        reader = csv.reader(io.StringIO(raw.decode("utf-8")))
        for row in reader:
            if len(row) != 2 or row[0] == "DATE":
                continue
            d, val = row[0].strip(), row[1].strip()
            if d not in data:
                data[d] = {}
            data[d][name] = val if val != "." else ""
    header = ["date", "UNRATE", "CPIAUCSL", "FEDFUNDS", "GDP"]
    rows = sorted(
        [[d, r.get("UNRATE", ""), r.get("CPIAUCSL", ""), r.get("FEDFUNDS", ""), r.get("GDP", "")]
         for d, r in data.items()],
        key=lambda x: x[0],
    )
    _write_csv(path, header, rows, provenance)


def download_telco_churn(path: Path) -> None:
    """Download IBM Telco Churn dataset from GitHub."""
    url = (
        "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d"
        "/master/data/Telco-Customer-Churn.csv"
    )
    print(f"  Fetching {url} ...")
    raw = _fetch_url(url)
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty response from Telco Churn URL")
    provenance = (
        "Dataset: Telco Customer Churn\n"
        "Source:  https://github.com/IBM/telco-customer-churn-on-icp4d\n"
        "License: Public Domain (IBM)\n"
        "Rows:    7,043 (full dataset)\n"
        "Task:    Binary classification — predict customer churn"
    )
    # Write raw content with provenance comment prepended
    header_line = lines[0]
    header = [c.strip() for c in header_line.split(",")]
    rows = []
    reader = csv.reader(lines[1:])
    for row in reader:
        if row:
            rows.append(row)
    _write_csv(path, header, rows, provenance)


# ---------------------------------------------------------------------------
# Synthetic placeholder generators
# ---------------------------------------------------------------------------

def _placeholder_lending_club(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: Lending Club Loan Data (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://www.kaggle.com/datasets/wordsforthewise/lending-club\n"
        "License: CC0\n"
        "Note: This is a synthetic placeholder matching the real schema.\n"
        "      Download the real data from Kaggle for production use.\n"
        "Rows: 50,000 (synthetic)"
    )
    grades = ["A", "B", "C", "D", "E", "F", "G"]
    purposes = ["debt_consolidation", "credit_card", "home_improvement", "other",
                "major_purchase", "small_business", "car", "vacation", "medical"]
    home_own = ["RENT", "OWN", "MORTGAGE", "OTHER"]
    statuses = ["Fully Paid", "Charged Off", "Current", "Late (31-120 days)", "Default"]
    verification = ["Verified", "Source Verified", "Not Verified"]
    header = [
        "loan_amnt", "funded_amnt", "term", "int_rate", "installment",
        "grade", "sub_grade", "emp_length", "home_ownership", "annual_inc",
        "verification_status", "loan_status", "purpose", "dti",
        "delinq_2yrs", "fico_range_low", "fico_range_high", "open_acc",
        "pub_rec", "revol_bal", "revol_util", "total_acc", "out_prncp",
        "total_pymnt", "total_rec_prncp", "total_rec_int", "last_pymnt_amnt",
        "recoveries", "default_ind",
    ]
    rows = []
    for _ in range(50000):
        loan = rng.randint(1000, 40000)
        grade = rng.choice(grades)
        sub_grade = grade + str(rng.randint(1, 5))
        term = rng.choice(["36 months", "60 months"])
        int_rate = round(rng.uniform(5.0, 28.0), 2)
        installment = round(loan * int_rate / 100 / 12 * 1.1, 2)
        emp_len = rng.choice(["< 1 year", "1 year", "2 years", "3 years", "4 years",
                               "5 years", "6 years", "7 years", "8 years", "9 years", "10+ years"])
        annual_inc = round(rng.lognormvariate(10.8, 0.6), 2)
        fico_low = rng.randint(620, 840)
        status = rng.choice(statuses)
        default_ind = 1 if "Charged Off" in status or "Default" in status else 0
        total_pymnt = round(loan * rng.uniform(0.5, 1.3), 2)
        rows.append([
            loan, loan, term, int_rate, installment,
            grade, sub_grade, emp_len, rng.choice(home_own), annual_inc,
            rng.choice(verification), status, rng.choice(purposes),
            round(rng.uniform(0, 40), 2), rng.randint(0, 5),
            fico_low, fico_low + 4, rng.randint(2, 30), rng.randint(0, 2),
            rng.randint(0, 50000), round(rng.uniform(0, 100), 1),
            rng.randint(5, 40), round(max(0, loan - total_pymnt * 0.6), 2),
            total_pymnt, round(total_pymnt * 0.8, 2), round(total_pymnt * 0.2, 2),
            round(rng.uniform(100, 2000), 2), round(rng.uniform(0, 500), 2),
            default_ind,
        ])
    _write_csv(path, header, rows, provenance)


def _placeholder_ames_housing(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: Ames Housing (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://www.kaggle.com/c/house-prices-advanced-regression-techniques\n"
        "License: CC0\n"
        "Note: Synthetic placeholder matching the real schema.\n"
        "Rows: 2,930 (synthetic)"
    )
    neighborhoods = ["NAmes", "CollgCr", "OldTown", "Edwards", "Somerst",
                     "NridgHt", "Gilbert", "Sawyer", "NWAmes", "Mitchel"]
    conditions = range(1, 11)
    header = [
        "Id", "MSSubClass", "MSZoning", "LotFrontage", "LotArea", "Street",
        "LotShape", "LandContour", "Utilities", "LotConfig", "LandSlope",
        "Neighborhood", "Condition1", "BldgType", "HouseStyle",
        "OverallQual", "OverallCond", "YearBuilt", "YearRemodAdd",
        "RoofStyle", "ExterQual", "ExterCond", "Foundation",
        "TotalBsmtSF", "HeatingQC", "CentralAir",
        "GrLivArea", "FullBath", "HalfBath", "BedroomAbvGr",
        "KitchenAbvGr", "KitchenQual", "TotRmsAbvGrd", "Functional",
        "Fireplaces", "GarageType", "GarageCars", "GarageArea",
        "PoolArea", "MoSold", "YrSold", "SaleType", "SaleCondition",
        "SalePrice",
    ]
    rows = []
    for i in range(2930):
        qual = rng.randint(1, 10)
        yr_built = rng.randint(1880, 2010)
        gr_liv = rng.randint(700, 4000)
        sale_price = int(qual * 15000 + gr_liv * 55 + rng.gauss(0, 15000))
        sale_price = max(50000, sale_price)
        rows.append([
            i + 1, rng.choice([20, 30, 40, 50, 60, 70, 80, 90, 120, 160]),
            rng.choice(["RL", "RM", "FV", "RH", "C(all)"]),
            rng.randint(50, 130), rng.randint(5000, 20000), "Pave",
            rng.choice(["Reg", "IR1", "IR2", "IR3"]),
            rng.choice(["Lvl", "Bnk", "HLS", "Low"]),
            "AllPub", rng.choice(["Inside", "Corner", "CulDSac", "FR2"]),
            rng.choice(["Gtl", "Mod", "Sev"]),
            rng.choice(neighborhoods),
            rng.choice(["Norm", "Feedr", "Artery", "RRAn", "PosN"]),
            rng.choice(["1Fam", "2FmCon", "Duplex", "TwnhsE", "Twnhs"]),
            rng.choice(["1Story", "2Story", "1.5Fin", "SFoyer", "SLvl"]),
            qual, rng.randint(1, 9), yr_built, max(yr_built, rng.randint(yr_built, 2010)),
            rng.choice(["Gable", "Hip", "Flat", "Gambrel", "Mansard"]),
            rng.choice(["Ex", "Gd", "TA", "Fa", "Po"]),
            rng.choice(["Ex", "Gd", "TA", "Fa", "Po"]),
            rng.choice(["PConc", "CBlock", "BrkTil", "Slab", "Stone"]),
            rng.randint(0, 2500), rng.choice(["Ex", "Gd", "TA", "Fa", "Po"]),
            rng.choice(["Y", "N"]),
            gr_liv, rng.randint(0, 3), rng.randint(0, 2), rng.randint(1, 6),
            1, rng.choice(["Ex", "Gd", "TA", "Fa", "Po"]),
            rng.randint(4, 12), "Typ",
            rng.randint(0, 3), rng.choice(["Attchd", "Detchd", "BuiltIn", "CarPort", "None"]),
            rng.randint(0, 3), rng.randint(0, 1000),
            rng.randint(0, 500), rng.randint(1, 12), rng.randint(2006, 2010),
            "WD", rng.choice(["Normal", "Abnorml", "Partial", "AdjLand", "Alloca", "Family"]),
            sale_price,
        ])
    _write_csv(path, header, rows, provenance)


def _placeholder_nyc_taxi(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: NYC TLC Yellow Taxi Trip Records (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page\n"
        "License: Public Domain\n"
        "Note: Synthetic placeholder matching the real schema.\n"
        "Rows: 100,000 (synthetic)"
    )
    header = [
        "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "passenger_count", "trip_distance", "RatecodeID", "store_and_fwd_flag",
        "PULocationID", "DOLocationID", "payment_type", "fare_amount",
        "extra", "mta_tax", "tip_amount", "tolls_amount",
        "improvement_surcharge", "total_amount", "congestion_surcharge",
    ]
    base = date(2023, 1, 1)
    rows = []
    for _ in range(100000):
        day_offset = rng.randint(0, 364)
        pickup_dt = base + timedelta(days=day_offset)
        pickup_h = rng.randint(0, 23)
        pickup_m = rng.randint(0, 59)
        duration_min = rng.randint(2, 90)
        dropoff_h = pickup_h + (pickup_m + duration_min) // 60
        dropoff_m = (pickup_m + duration_min) % 60
        trip_dist = round(rng.uniform(0.1, 30.0), 2)
        fare = round(max(3.0, trip_dist * 2.5 + 3.0), 2)
        tip = round(fare * rng.uniform(0, 0.3), 2) if rng.random() > 0.3 else 0.0
        rows.append([
            rng.choice([1, 2]),
            f"{pickup_dt} {pickup_h:02d}:{pickup_m:02d}:00",
            f"{pickup_dt} {min(dropoff_h, 23):02d}:{dropoff_m:02d}:00",
            rng.randint(1, 6), trip_dist,
            rng.choice([1, 2, 3, 4, 5, 6]),
            rng.choice(["Y", "N"]),
            rng.randint(1, 263), rng.randint(1, 263),
            rng.choice([1, 2, 3, 4]),
            fare, round(rng.choice([0.0, 0.5, 1.0]), 2), 0.5,
            tip, 0.0, 0.3,
            round(fare + tip + 0.5 + 0.3 + 2.5, 2), 2.5,
        ])
    _write_csv(path, header, rows, provenance)


def _placeholder_online_retail(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: Online Retail (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://archive.ics.uci.edu/ml/datasets/online+retail\n"
        "License: CC-BY 4.0\n"
        "Note: Synthetic placeholder matching the real schema.\n"
        "Rows: 500,000 (synthetic)"
    )
    header = ["InvoiceNo", "StockCode", "Description", "Quantity",
              "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    countries = ["United Kingdom", "Germany", "France", "EIRE", "Spain",
                 "Netherlands", "Belgium", "Switzerland", "Portugal", "Australia"]
    descriptions = [
        "WHITE HANGING HEART T-LIGHT HOLDER", "WHITE METAL LANTERN",
        "CREAM CUPID HEARTS COAT HANGER", "KNITTED UNION FLAG HOT WATER BOTTLE",
        "RED WOOLLY HOTTIE WHITE HEART", "SET 7 BABUSHKA NESTING BOXES",
        "GLASS STAR FROSTED T-LIGHT HOLDER", "HAND WARMER UNION JACK",
        "HAND WARMER RED POLKA DOT", "ASSORTED COLOUR BIRD ORNAMENT",
    ]
    base = date(2010, 12, 1)
    rows = []
    for i in range(500000):
        inv_no = f"5{rng.randint(30000, 99999)}"
        stock = f"{rng.randint(10000, 99999)}"
        inv_date = base + timedelta(days=rng.randint(0, 364))
        cust_id = rng.randint(12000, 18500) if rng.random() > 0.2 else ""
        rows.append([
            inv_no, stock, rng.choice(descriptions),
            rng.randint(-5, 50),
            f"{inv_date} {rng.randint(6,20):02d}:{rng.randint(0,59):02d}:00",
            round(rng.uniform(0.1, 15.0), 2),
            cust_id, rng.choice(countries),
        ])
    _write_csv(path, header, rows, provenance)


def _placeholder_credit_card_fraud(path: Path) -> None:
    rng = _rng(42)
    import math
    provenance = (
        "Dataset: Credit Card Fraud Detection (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud\n"
        "License: CC0\n"
        "Note: Synthetic placeholder — PCA components are random Gaussians.\n"
        "      Real data has genuine PCA features from anonymised transactions.\n"
        "Rows: 50,000 (synthetic)"
    )
    header = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]
    rows = []
    fraud_rate = 0.00172  # approx real rate
    t = 0.0
    for _ in range(50000):
        t += rng.uniform(0, 10)
        is_fraud = 1 if rng.random() < fraud_rate else 0
        v_features = [round(rng.gauss(0 if not is_fraud else rng.uniform(-3, 3), 1), 6)
                      for _ in range(28)]
        amount = round(abs(rng.lognormvariate(3.0 if not is_fraud else 4.5, 1.5)), 2)
        rows.append([round(t, 0)] + v_features + [amount, is_fraud])
    _write_csv(path, header, rows, provenance)


def _placeholder_who_gho(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: WHO Global Health Observatory (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://www.who.int/data/gho\n"
        "License: CC-BY 4.0\n"
        "Note: Synthetic placeholder matching the real schema.\n"
        "Rows: ~3,000 country-years (synthetic)"
    )
    countries = [
        ("Afghanistan", "AFG", "Low income", "Eastern Mediterranean"),
        ("Brazil", "BRA", "Upper middle income", "Americas"),
        ("China", "CHN", "Upper middle income", "Western Pacific"),
        ("Germany", "DEU", "High income", "Europe"),
        ("India", "IND", "Lower middle income", "South-East Asia"),
        ("Japan", "JPN", "High income", "Western Pacific"),
        ("Kenya", "KEN", "Lower middle income", "Africa"),
        ("Mexico", "MEX", "Upper middle income", "Americas"),
        ("Nigeria", "NGA", "Lower middle income", "Africa"),
        ("South Africa", "ZAF", "Upper middle income", "Africa"),
        ("United Kingdom", "GBR", "High income", "Europe"),
        ("United States", "USA", "High income", "Americas"),
    ]
    header = [
        "country", "country_code", "year", "life_expectancy",
        "infant_mortality", "under5_mortality", "maternal_mortality",
        "hiv_prevalence", "tb_incidence", "malaria_incidence", "measles_incidence",
        "physicians_per_1000", "hospital_beds_per_1000",
        "health_expenditure_pct_gdp", "income_group", "region",
    ]
    rows = []
    for country, code, income, region in countries:
        for year in range(2000, 2022):
            base_le = {"High income": 78, "Upper middle income": 73,
                       "Lower middle income": 65, "Low income": 58}.get(income, 68)
            le = round(base_le + rng.gauss(0, 0.5) + (year - 2000) * 0.2, 1)
            rows.append([
                country, code, year,
                le,
                round(max(1, rng.gauss(30 if "Low" in income else 8, 3)), 1),
                round(max(1, rng.gauss(50 if "Low" in income else 10, 5)), 1),
                round(max(1, rng.gauss(400 if "Low" in income else 12, 30)), 0),
                round(max(0, rng.gauss(5 if "Africa" in region else 0.3, 0.5)), 2),
                round(max(0, rng.gauss(100 if "Low" in income else 10, 10)), 1),
                round(max(0, rng.gauss(200 if "Africa" in region else 0.5, 20)), 1),
                round(max(0, rng.gauss(50 if "Low" in income else 2, 5)), 1),
                round(max(0.05, rng.gauss(0.2 if "Low" in income else 3.0, 0.3)), 2),
                round(max(0.1, rng.gauss(0.5 if "Low" in income else 5.0, 0.5)), 1),
                round(max(1, rng.gauss(4 if "High" in income else 6, 0.5)), 1),
                income, region,
            ])
    _write_csv(path, header, rows, provenance)


def _placeholder_stackoverflow(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: Stack Overflow Developer Survey (SYNTHETIC PLACEHOLDER)\n"
        "Real source: https://insights.stackoverflow.com/survey\n"
        "License: ODbL\n"
        "Note: Synthetic placeholder matching the real schema.\n"
        "Rows: 50,000 (synthetic)"
    )
    header = [
        "ResponseId", "MainBranch", "Employment", "Country", "EdLevel",
        "YearsCode", "YearsCodePro", "DevType", "OrgSize", "Currency",
        "CompTotal", "CompFreq", "LanguageHaveWorkedWith",
        "LanguageWantToWorkWith", "DatabaseHaveWorkedWith",
        "PlatformHaveWorkedWith", "WebframeHaveWorkedWith",
        "Age", "Gender", "MentalHealth", "JobSat", "ConvertedCompYearly",
    ]
    countries = ["United States of America", "India", "Germany", "United Kingdom",
                 "Canada", "France", "Brazil", "Netherlands", "Australia", "Poland"]
    dev_types = ["Developer, full-stack", "Developer, back-end", "Developer, front-end",
                 "Developer, mobile", "Data scientist or machine learning specialist",
                 "DevOps specialist", "Developer, desktop or enterprise applications",
                 "Engineer, data", "Engineer, site reliability"]
    languages = ["Python;JavaScript", "JavaScript;TypeScript", "Python;SQL",
                 "Java;Kotlin", "C#;.NET", "Go;Python", "Rust;C++",
                 "PHP;JavaScript", "Ruby;Python", "Swift;Objective-C"]
    ed_levels = [
        "Bachelor\u2019s degree (B.A., B.S., B.Eng., etc.)",
        "Master\u2019s degree (M.A., M.S., M.Eng., MBA, etc.)",
        "Some college/university study without earning a degree",
        "Secondary school (e.g. American high school, German Realschule or Gymnasium, etc.)",
        "Associate degree (A.A., A.S., etc.)",
    ]
    rows = []
    for i in range(50000):
        yrs_code = rng.randint(0, 40)
        yrs_pro = min(yrs_code, rng.randint(0, 30))
        comp = round(abs(rng.lognormvariate(11.0, 0.8)), 0) if rng.random() > 0.1 else ""
        rows.append([
            i + 1,
            rng.choice(["I am a developer by profession",
                        "I am not primarily a developer, but I write code sometimes"]),
            rng.choice(["Employed, full-time", "Employed, part-time",
                        "Independent contractor, freelancer, or self-employed",
                        "Student, full-time"]),
            rng.choice(countries),
            rng.choice(ed_levels),
            yrs_code, yrs_pro,
            rng.choice(dev_types),
            rng.choice(["Just me - I am a freelancer, sole proprietor, etc.",
                        "2 to 9 employees", "10 to 19 employees", "20 to 99 employees",
                        "100 to 499 employees", "500 to 999 employees", "1,000 to 4,999 employees",
                        "5,000 to 9,999 employees", "10,000 or more employees"]),
            "USD\tUnited States dollar",
            comp, rng.choice(["Yearly", "Monthly", "Weekly"]),
            rng.choice(languages), rng.choice(languages),
            rng.choice(["MySQL;PostgreSQL", "PostgreSQL;SQLite", "MongoDB;Redis",
                        "Microsoft SQL Server;MySQL", "SQLite;MySQL"]),
            rng.choice(["AWS;Docker", "Docker;Kubernetes", "GCP;AWS",
                        "Azure;Docker", "Heroku;AWS"]),
            rng.choice(["React.js;Node.js", "Vue.js;React.js", "Angular;React.js",
                        "Django;Flask", "Express;Next.js"]),
            rng.choice(["18-24 years old", "25-34 years old", "35-44 years old",
                        "45-54 years old", "55-64 years old"]),
            rng.choice(["Man", "Woman", "Non-binary, genderqueer, or gender non-conforming",
                        "Prefer not to say"]),
            rng.choice(["None of the above", "Anxiety", "Depression",
                        "Burnout", "Anxiety;Depression"]),
            rng.choice(["Very satisfied", "Slightly satisfied", "Neither satisfied nor dissatisfied",
                        "Slightly dissatisfied", "Very dissatisfied"]),
            comp,
        ])
    _write_csv(path, header, rows, provenance)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

DOWNLOADERS: dict[str, Callable[[Path], None]] = {
    "adult_income": download_adult_income,
    "fred_macro": download_fred_macro,
    "telco_churn": download_telco_churn,
    "lending_club": _placeholder_lending_club,
    "ames_housing": _placeholder_ames_housing,
    "nyc_taxi": _placeholder_nyc_taxi,
    "online_retail": _placeholder_online_retail,
    "credit_card_fraud": _placeholder_credit_card_fraud,
    "who_gho": _placeholder_who_gho,
    "stackoverflow": _placeholder_stackoverflow,
}


def _get_path(name: str) -> Path:
    return DATASETS_DIR / f"{name}.csv"


def _download_one(name: str, force: bool = False) -> bool:
    """Download or generate one dataset. Returns True on success."""
    if name not in DATASETS:
        print(f"  ERROR: unknown dataset '{name}'", file=sys.stderr)
        return False

    path = _get_path(name)
    if path.exists() and not force:
        print(f"  {name}: already exists at {path} (use --force to re-download)")
        return True

    meta = DATASETS[name]
    direct = meta["direct_download"]
    label = "Downloading" if direct else "Generating placeholder for"
    print(f"{label} {name} ...")

    fn = DOWNLOADERS[name]
    if direct:
        try:
            fn(path)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            print(f"  WARNING: direct download failed ({exc}); falling back to placeholder")
            # Fall through to placeholder
            fallback_map = {
                "adult_income": _placeholder_adult_income_fallback,
                "fred_macro": _placeholder_fred_macro_fallback,
                "telco_churn": _placeholder_telco_churn_fallback,
            }
            fallback_fn = fallback_map.get(name)
            if fallback_fn:
                fallback_fn(path)
            return True
    else:
        fn(path)
        return True


# ---------------------------------------------------------------------------
# Fallback placeholders for direct-download datasets
# ---------------------------------------------------------------------------

def _placeholder_adult_income_fallback(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: Adult Income (SYNTHETIC PLACEHOLDER — download failed)\n"
        "Real source: https://archive.ics.uci.edu/ml/datasets/adult\n"
        "License: CC-BY 4.0\n"
        "Rows: 48,842 (synthetic)"
    )
    workclasses = ["Private", "Self-emp-not-inc", "Self-emp-inc", "Federal-gov",
                   "Local-gov", "State-gov", "Without-pay", "Never-worked"]
    educations = ["Bachelors", "Some-college", "11th", "HS-grad", "Prof-school",
                  "Assoc-acdm", "Assoc-voc", "9th", "7th-8th", "12th",
                  "Masters", "1st-4th", "10th", "Doctorate", "5th-6th", "Preschool"]
    marital = ["Married-civ-spouse", "Divorced", "Never-married", "Separated",
               "Widowed", "Married-spouse-absent", "Married-AF-spouse"]
    occupations = ["Tech-support", "Craft-repair", "Other-service", "Sales",
                   "Exec-managerial", "Prof-specialty", "Handlers-cleaners",
                   "Machine-op-inspct", "Adm-clerical", "Farming-fishing",
                   "Transport-moving", "Priv-house-serv", "Protective-serv",
                   "Armed-Forces"]
    relationships = ["Wife", "Own-child", "Husband", "Not-in-family",
                     "Other-relative", "Unmarried"]
    races = ["White", "Asian-Pac-Islander", "Amer-Indian-Eskimo", "Other", "Black"]
    countries = ["United-States", "Cuba", "Jamaica", "India", "Mexico",
                 "South", "Japan", "Greece", "China", "Canada"]
    header = [
        "age", "workclass", "fnlwgt", "education", "education_num",
        "marital_status", "occupation", "relationship", "race", "sex",
        "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
    ]
    rows = []
    for _ in range(48842):
        age = rng.randint(17, 90)
        edu = rng.choice(educations)
        edu_num = educations.index(edu) + 1
        cap_gain = rng.choice([0] * 8 + [rng.randint(1000, 99999)])
        cap_loss = rng.choice([0] * 9 + [rng.randint(100, 4000)])
        income = ">50K" if rng.random() < 0.24 else "<=50K"
        rows.append([
            age, rng.choice(workclasses), rng.randint(10000, 1000000),
            edu, edu_num, rng.choice(marital), rng.choice(occupations),
            rng.choice(relationships), rng.choice(races),
            rng.choice(["Male", "Female"]),
            cap_gain, cap_loss, rng.randint(1, 99),
            rng.choice(countries), income,
        ])
    _write_csv(path, header, rows, provenance)


def _placeholder_fred_macro_fallback(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: FRED Macroeconomic Time Series (SYNTHETIC PLACEHOLDER — download failed)\n"
        "Real source: https://fred.stlouisfed.org/\n"
        "License: Public Domain\n"
        "Rows: 780 monthly observations (synthetic)"
    )
    header = ["date", "UNRATE", "CPIAUCSL", "FEDFUNDS", "GDP"]
    rows = []
    base = date(1960, 1, 1)
    unrate = 5.5
    cpi = 29.6
    fedfunds = 3.5
    gdp = 543.3
    for m in range(780):
        current = base + timedelta(days=m * 30)
        unrate = max(2.5, min(15.0, unrate + rng.gauss(0, 0.15)))
        cpi = cpi * (1 + rng.gauss(0.003, 0.002))
        fedfunds = max(0.0, min(22.0, fedfunds + rng.gauss(0, 0.1)))
        gdp_val = gdp * (1 + rng.gauss(0.007, 0.01)) if m % 3 == 0 else ""
        if m % 3 == 0:
            gdp = float(gdp_val) if gdp_val != "" else gdp
        rows.append([
            current.strftime("%Y-%m-%d"),
            round(unrate, 1), round(cpi, 3),
            round(fedfunds, 2), round(gdp_val, 1) if gdp_val != "" else "",
        ])
    _write_csv(path, header, rows, provenance)


def _placeholder_telco_churn_fallback(path: Path) -> None:
    rng = _rng(42)
    provenance = (
        "Dataset: Telco Customer Churn (SYNTHETIC PLACEHOLDER — download failed)\n"
        "Real source: https://github.com/IBM/telco-customer-churn-on-icp4d\n"
        "License: Public Domain (IBM)\n"
        "Rows: 7,043 (synthetic)"
    )
    header = [
        "customerID", "gender", "SeniorCitizen", "Partner", "Dependents",
        "tenure", "PhoneService", "MultipleLines", "InternetService",
        "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
        "StreamingTV", "StreamingMovies", "Contract", "PaperlessBilling",
        "PaymentMethod", "MonthlyCharges", "TotalCharges", "Churn",
    ]
    internet_svcs = ["DSL", "Fiber optic", "No"]
    contracts = ["Month-to-month", "One year", "Two year"]
    payment_methods = [
        "Electronic check", "Mailed check",
        "Bank transfer (automatic)", "Credit card (automatic)",
    ]
    rows = []
    for i in range(7043):
        tenure = rng.randint(0, 72)
        monthly = round(rng.uniform(18.0, 118.0), 2)
        total = round(monthly * tenure + rng.gauss(0, 5), 2) if tenure > 0 else ""
        internet = rng.choice(internet_svcs)
        yes_no_na = ["Yes", "No", "No internet service"] if internet == "No" else ["Yes", "No"]
        churn = "Yes" if rng.random() < 0.265 else "No"
        rows.append([
            f"{rng.randint(1000,9999)}-{rng.choice('ABCDEFGHIJKLMNOP')}{rng.randint(1000,9999)}",
            rng.choice(["Male", "Female"]),
            rng.choice([0, 0, 0, 1]),
            rng.choice(["Yes", "No"]), rng.choice(["Yes", "No"]),
            tenure,
            rng.choice(["Yes", "No"]),
            rng.choice(["Yes", "No", "No phone service"]),
            internet,
            rng.choice(yes_no_na), rng.choice(yes_no_na),
            rng.choice(yes_no_na), rng.choice(yes_no_na),
            rng.choice(yes_no_na), rng.choice(yes_no_na),
            rng.choice(contracts),
            rng.choice(["Yes", "No"]),
            rng.choice(payment_methods),
            monthly, total if total != "" else 0.0, churn,
        ])
    _write_csv(path, header, rows, provenance)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_list() -> None:
    print(f"{'Name':<24} {'Direct DL':<11} {'License':<15} {'Rows'}")
    print("-" * 78)
    for name, meta in DATASETS.items():
        direct = "yes" if meta["direct_download"] else "placeholder"
        print(f"{name:<24} {direct:<11} {meta['license']:<15} {meta['rows']}")


def cmd_download(name: str, force: bool) -> None:
    ok = _download_one(name, force=force)
    if not ok:
        sys.exit(1)


def cmd_all(force: bool) -> None:
    failed = []
    for name in DATASETS:
        ok = _download_one(name, force=force)
        if not ok:
            failed.append(name)
    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)
    print(f"\nAll {len(DATASETS)} datasets ready in {DATASETS_DIR}/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and prepare TeamBench DS/ML datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all datasets")
    group.add_argument("--dataset", metavar="NAME", help="Download a single dataset by name")
    group.add_argument("--all", action="store_true", help="Download all datasets")
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if file already exists")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.dataset:
        cmd_download(args.dataset, force=args.force)
    elif args.all:
        cmd_all(force=args.force)


if __name__ == "__main__":
    main()
