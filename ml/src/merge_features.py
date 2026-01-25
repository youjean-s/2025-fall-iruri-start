import pandas as pd

BASIC_PATH = "ml/data/features/features_basic.csv"
CAT_PATH = "ml/data/features/features_category_mix_30d.csv"
OUT_PATH = "ml/data/features/features.csv"

def main():
    basic = pd.read_csv(BASIC_PATH)
    cat = pd.read_csv(CAT_PATH)

    # date type unify
    basic["date"] = pd.to_datetime(basic["date"], errors="coerce")
    cat["date"] = pd.to_datetime(cat["date"], errors="coerce")

    basic = basic.dropna(subset=["user_id", "date"])
    cat = cat.dropna(subset=["user_id", "date"])

    merged = basic.merge(cat, on=["user_id", "date"], how="left").fillna(0.0)

    merged.to_csv(OUT_PATH, index=False)
    print(f"[OK] merged saved -> {OUT_PATH} (rows={len(merged)}, cols={len(merged.columns)})")
    print("sample cols:", merged.columns.tolist()[:20])
    print("sample head:\n", merged.head(3))

if __name__ == "__main__":
    main()
