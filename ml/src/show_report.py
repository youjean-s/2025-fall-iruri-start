import json
import pandas as pd

REPORT_PATH = "ml/artifacts/reports/baseline_report.json"
FI_PATH = "ml/artifacts/reports/feature_importance.csv"

TOP_N = 15

def main():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    print("== Baseline Report ==")
    for k, v in report.items():
        print(f"{k}: {v}")

    fi = pd.read_csv(FI_PATH).sort_values("importance", ascending=False)

    print(f"\n== Top {TOP_N} Feature Importance (gain) ==")
    print(fi.head(TOP_N).to_string(index=False))

if __name__ == "__main__":
    main()
