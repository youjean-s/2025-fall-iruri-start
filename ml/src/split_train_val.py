import pandas as pd
import numpy as np

IN_PATH = "ml/data/features/features_labeled.csv"
TRAIN_OUT = "ml/data/features/train.csv"
VAL_OUT = "ml/data/features/val.csv"

VAL_RATIO = 0.2
SEED = 42

def main():
    df = pd.read_csv(IN_PATH)

    if "user_id" not in df.columns:
        raise ValueError("Missing user_id column")
    if "label_fhi" not in df.columns:
        raise ValueError("Missing label_fhi column")

    users = df["user_id"].astype(str).unique()
    rng = np.random.default_rng(SEED)
    rng.shuffle(users)

    n_val = int(len(users) * VAL_RATIO)
    val_users = set(users[:n_val])

    val = df[df["user_id"].astype(str).isin(val_users)].copy()
    train = df[~df["user_id"].astype(str).isin(val_users)].copy()

    # leak check
    inter = set(train["user_id"].astype(str)).intersection(set(val["user_id"].astype(str)))
    assert len(inter) == 0, f"Leak detected: {len(inter)} overlapping users"

    train.to_csv(TRAIN_OUT, index=False)
    val.to_csv(VAL_OUT, index=False)

    print(f"[OK] train rows={len(train)} users={train['user_id'].nunique()} -> {TRAIN_OUT}")
    print(f"[OK] val   rows={len(val)} users={val['user_id'].nunique()} -> {VAL_OUT}")

if __name__ == "__main__":
    main()
