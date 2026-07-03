import os
import zipfile
import pandas as pd
import numpy as np

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def compute_velocities(df):
    df = df.sort_values("TransactionDT").reset_index(drop=True)
    v1h = np.ones(len(df), dtype=int)
    v6h = np.ones(len(df), dtype=int)
    v24h = np.ones(len(df), dtype=int)
    
    # Group by card1 for rapid processing
    for card, group in df.groupby("card1"):
        indices = group.index.values
        times = group["TransactionDT"].values
        for i in range(len(times)):
            t = times[i]
            c1 = 0
            c6 = 0
            c24 = 0
            for j in range(i - 1, -1, -1):
                dt = t - times[j]
                if dt > 86400:
                    break
                if dt <= 3600:
                    c1 += 1
                if dt <= 21600:
                    c6 += 1
                if dt <= 86400:
                    c24 += 1
            v1h[indices[i]] = c1 + 1
            v6h[indices[i]] = c6 + 1
            v24h[indices[i]] = c24 + 1
            
    df["velocity_1h"] = v1h
    df["velocity_6h"] = v6h
    df["velocity_24h"] = v24h
    return df

# Check if real transaction data already exists locally, otherwise attempt download from Kaggle
downloaded = os.path.exists("data/train_transaction.csv")

if not downloaded:
    try:
        import kaggle
        print("Kaggle API found. Authenticating and downloading ieee-fraud-detection...")
        kaggle.api.authenticate()
        kaggle.api.competition_download_files("ieee-fraud-detection", path="data")
        print("Download completed. Extracting files...")
        zip_path = "data/ieee-fraud-detection.zip"
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("data")
            downloaded = True
        else:
            for f in ["train_transaction.csv.zip", "test_transaction.csv.zip"]:
                p = os.path.join("data", f)
                if os.path.exists(p):
                    with zipfile.ZipFile(p, 'r') as zip_ref:
                        zip_ref.extractall("data")
            downloaded = True
    except Exception as e:
        print(f"Kaggle API download failed/not configured: {e}")
        print("Proceeding with realistic simulated dataset fallback...")

if downloaded:
    print("Loading train_transaction.csv...")
    df = pd.read_csv("data/train_transaction.csv")
    cols = ["TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "card1", "addr1", "P_emaildomain", "R_emaildomain", "DeviceType"]
    
    identity_path = "data/train_identity.csv"
    if os.path.exists(identity_path):
        print("Merging with identity info for DeviceType...")
        df_id = pd.read_csv(identity_path)
        df = df.merge(df_id[["TransactionID", "DeviceType"]], on="TransactionID", how="left")
    else:
        df["DeviceType"] = "desktop"
        
    df = df[[c for c in cols if c in df.columns]]
    df["addr1"] = df["addr1"].fillna(150.0)
    df["P_emaildomain"] = df["P_emaildomain"].fillna("gmail.com")
    df["R_emaildomain"] = df["R_emaildomain"].fillna("gmail.com")
    df["DeviceType"] = df["DeviceType"].fillna("desktop")
    
    # Sample 15000 rows to ensure fast local training and memory durability
    df = df.sort_values("TransactionDT").head(15000).copy()
else:
    print("Generating simulated IEEE-CIS dataset...")
    np.random.seed(2026)
    n_rows = 15000
    times = np.sort(np.random.randint(0, 86400 * 30, size=n_rows))
    frequent_cards = np.random.randint(1000, 5000, size=20)
    other_cards = np.random.randint(5000, 20000, size=200)
    p_vals = np.concatenate([np.ones(20) * 0.02, np.ones(200) * 0.003])
    p_vals /= p_vals.sum()
    cards = np.random.choice(np.concatenate([frequent_cards, other_cards]), size=n_rows, p=p_vals)
    
    df = pd.DataFrame({
        "TransactionID": range(2987000, 2987000 + n_rows),
        "isFraud": np.random.choice([0, 1], size=n_rows, p=[0.96, 0.04]),
        "TransactionDT": times,
        "TransactionAmt": np.round(np.random.exponential(scale=120.0, size=n_rows) + 5.0, 2),
        "card1": cards,
        "addr1": np.random.choice([150.0, 200.0, 300.0, 450.0], size=n_rows, p=[0.6, 0.2, 0.1, 0.1]),
        "P_emaildomain": np.random.choice(["gmail.com", "yahoo.com", "anonymous.com", "hotmail.com"], size=n_rows, p=[0.7, 0.15, 0.1, 0.05]),
        "R_emaildomain": np.random.choice(["gmail.com", "yahoo.com", "anonymous.com", "hotmail.com"], size=n_rows, p=[0.75, 0.1, 0.1, 0.05]),
        "DeviceType": np.random.choice(["desktop", "mobile"], size=n_rows, p=[0.6, 0.4])
    })

print("Computing rolling velocity features...")
df = compute_velocities(df)

# Export baseline dataset of 5,000 normal transactions
baseline_df = df[df["isFraud"] == 0].head(5000)[
    ['TransactionAmt', 'card1', 'addr1', 'P_emaildomain', 'R_emaildomain', 'DeviceType', 'velocity_1h', 'velocity_6h', 'velocity_24h']
]
baseline_df.to_csv("data/baseline_transactions.csv", index=False)
print(f"Saved baseline of {len(baseline_df)} normal rows to data/baseline_transactions.csv")

# Split temporally at 80% mark
df = df.sort_values("TransactionDT").reset_index(drop=True)
split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx]
test_df = df.iloc[split_idx:]

train_df.to_csv("data/train_split.csv", index=False)
test_df.to_csv("data/test_split.csv", index=False)
print(f"Saved train_split.csv ({len(train_df)} rows) and test_split.csv ({len(test_df)} rows). Data setup complete.")
