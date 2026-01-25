import os
import json
from xml.parsers.expat import model
import pandas as pd
import numpy as np

from sklearn.metrics import mean_absolute_error, mean_squared_error
import lightgbm as lgb

TRAIN_PATH = "ml/data/features/train.csv"
VAL_PATH = "ml/data/features/val.csv"

MODEL_OUT = "ml/artifacts/models/lgbm_fhi_v2_baseline.txt"
REPORT_OUT = "ml/artifacts/reports/baseline_report.json"
FI_OUT = "ml/artifacts/reports/feature_importance.csv"

TARGET = "label_fhi"

def main():
    train = pd.read_csv(TRAIN_PATH)
    val = pd.read_csv(VAL_PATH)

    # drop non-features
    for c in ["user_id", "date"]:
        if c in train.columns:
            train = train.drop(columns=[c])
        if c in val.columns:
            val = val.drop(columns=[c])

    if TARGET not in train.columns or TARGET not in val.columns:
        raise ValueError("Missing label_fhi in train/val")

    y_train = train[TARGET].astype(float)
    X_train = train.drop(columns=[TARGET])

    y_val = val[TARGET].astype(float)
    X_val = val.drop(columns=[TARGET])

    X_train = X_train.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    X_val = X_val.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    model = lgb.LGBMRegressor(
        n_estimators=600,
        learning_rate=0.05,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )

    model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    eval_metric="l1",
    callbacks=[lgb.log_evaluation(period=50)]
)


    pred = model.predict(X_val)
    mae = float(mean_absolute_error(y_val, pred))
    rmse = float(np.sqrt(mean_squared_error(y_val, pred)))

    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_OUT), exist_ok=True)

    model.booster_.save_model(MODEL_OUT)

    fi = pd.DataFrame({
        "feature": X_train.columns,
        "importance": model.booster_.feature_importance(importance_type="gain")
    }).sort_values("importance", ascending=False)
    fi.to_csv(FI_OUT, index=False)

    report = {
        "mae": mae,
        "rmse": rmse,
        "n_train_rows": int(len(X_train)),
        "n_val_rows": int(len(X_val)),
        "n_features": int(X_train.shape[1]),
        "model_out": MODEL_OUT,
        "fi_out": FI_OUT
    }
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("[OK] baseline trained")
    print("MAE:", mae)
    print("RMSE:", rmse)
    print("model:", MODEL_OUT)
    print("report:", REPORT_OUT)
    print("feature importance:", FI_OUT)

if __name__ == "__main__":
    main()
