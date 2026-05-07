"""ETL pipeline — read CSV batches and produce unified output."""
import pandas as pd
import os
import glob

# Column rename mapping: non-canonical -> canonical
RENAME_MAP = {
    'full_name': 'name',
    'record_id': 'id',
    'amount': 'value',
}

CANONICAL_COLS = ['id', 'name', 'value', 'category']

def load_and_normalize(filepath):
    df = pd.read_csv(filepath, dtype=str)
    # Rename columns to canonical names
    df = df.rename(columns=RENAME_MAP)
    # Add missing canonical columns
    for col in CANONICAL_COLS:
        if col not in df.columns:
            df[col] = None
    # Keep only canonical columns
    df = df[CANONICAL_COLS]
    return df

def main():
    os.makedirs('data/output', exist_ok=True)

    files = sorted(glob.glob('data/input/*.csv'))
    frames = [load_and_normalize(f) for f in files]
    df = pd.concat(frames, ignore_index=True)

    # Fill missing category with 'unknown'
    df['category'] = df['category'].fillna('unknown')
    df['category'] = df['category'].replace('', 'unknown')

    # Clean value: convert to numeric, replace non-numeric/negative with 0
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df['value'] = df['value'].fillna(0)
    df['value'] = df['value'].clip(lower=0)

    # Convert id to numeric for proper dedup and sort
    df['id'] = pd.to_numeric(df['id'], errors='coerce')

    # Deduplicate: keep row with highest value; ties -> keep last occurrence
    # Add original order tracker
    df = df.reset_index(drop=True)
    df['_order'] = df.index

    # Sort by id, then value ascending, then original order ascending
    # drop_duplicates keep='last' will keep highest value; for ties, last original occurrence
    df = df.sort_values(by=['id', 'value', '_order'], ascending=[True, True, True])
    df = df.drop_duplicates(subset=['id'], keep='last')
    df = df.drop(columns=['_order'])

    # Fill missing category again (safety)
    df['category'] = df['category'].fillna('unknown')

    # Sort output: category ascending, then id ascending (numeric)
    df['id'] = df['id'].astype(int)
    df['value'] = df['value'].astype(int)
    df = df.sort_values(by=['category', 'id'], ascending=[True, True])

    # Enforce canonical column order
    df = df[CANONICAL_COLS]
    df = df.reset_index(drop=True)

    df.to_csv('data/output/result.csv', index=False)
    print(f"Done. Wrote {len(df)} rows to data/output/result.csv")
    print(df.to_string())

if __name__ == '__main__':
    main()
