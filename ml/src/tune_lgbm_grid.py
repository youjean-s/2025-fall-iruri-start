import os
import json
import itertools
import pandas as pd
import numpy as np

from sklearn.metrics import mean_absolute_error, mean_squared_error
import lightgbm as lgb

TRAIN_PATH = "ml/data/features/train.csv"
VAL_PATH = "ml/data/features/val.csv"

OUT_REPORT = "ml/artifacts/reports/grid_search_report.json"
OUT_BEST_MODEL = "ml/artifacts/models/lgbm_fhi_v2_grid_best.txt"
OUT_BEST_FI = "ml/artifacts/reports/grid_best_feature_importance.csv"

TARGET = "label_fhi"

def load_xy(path):
    df = pd.read_csv(path)
    for c in ["user_id", "date"]:
        if c in df.columns:
            df = df.drop(columns=[c])
    y = df[TARGET].astype(float)
    X = df.drop(columns=[TARGET])
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return X, y

def main():
    X_train, y_train = load_xy(TRAIN_PATH)
    X_val, y_val = load_xy(VAL_PATH)

    grid = {
        "num_leaves": [31, 63, 127],
        "learning_rate": [0.03, 0.05, 0.1],
        "subsample": [0.7, 0.9],
        "colsample_bytree": [0.7, 0.9],
        "min_child_samples": [20, 50],
        "n_estimators": [400, 800],
    }

    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))

    best = {"mae": 1e9, "rmse": 1e9, "params": None}

    results = []
    for i, vals in enumerate(combos, 1):
        params = dict(zip(keys, vals))
        model = lgb.LGBMRegressor(random_state=42, **params)

        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_metric="l1",
            callbacks=[lgb.log_evaluation(period=0)]  # silent
        )

        pred = model.predict(X_val)
        mae = float(mean_absolute_error(y_val, pred))
        rmse = float(np.sqrt(mean_squared_error(y_val, pred)))

        row = {"mae": mae, "rmse": rmse, **params}
        results.append(row)

        if mae < best["mae"]:
            best = {"mae": mae, "rmse": rmse, "params": params}
            # save best model snapshot
            os.makedirs(os.path.dirname(OUT_BEST_MODEL), exist_ok=True)
            model.booster_.save_model(OUT_BEST_MODEL)

            fi = pd.DataFrame({
                "feature": X_train.columns,
                "importance": model.booster_.feature_importance(importance_type="gain")
            }).sort_values("importance", ascending=False)
            os.makedirs(os.path.dirname(OUT_BEST_FI), exist_ok=True)
            fi.to_csv(OUT_BEST_FI, index=False)

        print(f"[{i}/{len(combos)}] MAE={mae:.4f} RMSE={rmse:.4f} params={params}")

    # save report
    os.makedirs(os.path.dirname(OUT_REPORT), exist_ok=True)
    report = {"best": best, "n_trials": len(combos)}
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # save full grid results
    pd.DataFrame(results).sort_values("mae").to_csv(
        "ml/artifacts/reports/grid_search_results.csv", index=False
    )

    print("\n[OK] Grid search done")
    print("best:", best)
    print("best model:", OUT_BEST_MODEL)
    print("report:", OUT_REPORT)

if __name__ == "__main__":
    main()
