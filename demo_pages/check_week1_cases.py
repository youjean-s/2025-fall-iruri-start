import os
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from utils.parser import parse_push_notification
from utils.category_rules import categorize_store
from utils.fhi_calculator import calculate_fhi_from_transactions


CASES = [
    {
        "name": "shinhan_basic",
        "text": "[신한카드 승인] 5,800원\nGS25 이대점\n일시불 승인\n2024-11-21 23:10",
        "expect_source": "shinhan",
        "expect_payment": "card",
        "expect_category": "편의점",
    },
    {
        "name": "kakaopay_basic",
        "text": "카카오페이\n스타벅스\n2025-01-01 12:30\n5,000원",
        "expect_source": "kakaopay",
        "expect_payment": "wallet",
        "expect_category": "카페",
    },
    {
        "name": "unknown_fallback",
        "text": "승인\n무신사\n2025-01-02 18:10\n32,000원",
        "expect_source": "unknown",
        "expect_category": "쇼핑",
    },
]


def run():
    ok = 0
    fail = 0

    for case in CASES:
        name = case["name"]
        text = case["text"]

        txs = parse_push_notification(text)
        if not txs:
            print(f"[FAIL] {name}: parse returned empty")
            fail += 1
            continue

        tx = txs[0]
        source = tx.get("source")
        pay = tx.get("payment_method")
        merchant = tx.get("merchant")
        amount = tx.get("amount")
        dt = tx.get("datetime")

        category = categorize_store(merchant or "")
        result = calculate_fhi_from_transactions(txs)

        # shape checks
        if "fhi" not in result or "impulsive" not in result or "spike" not in result:
            print(f"[FAIL] {name}: bad result shape => {result}")
            fail += 1
            continue

        # expectation checks
        exp_source = case.get("expect_source")
        if exp_source and source != exp_source:
            print(f"[FAIL] {name}: source {source} != {exp_source}")
            fail += 1
            continue

        exp_pay = case.get("expect_payment")
        if exp_pay and pay != exp_pay:
            print(f"[FAIL] {name}: payment {pay} != {exp_pay}")
            fail += 1
            continue

        exp_cat = case.get("expect_category")
        if exp_cat and category != exp_cat:
            print(f"[FAIL] {name}: category {category} != {exp_cat} (merchant={merchant})")
            fail += 1
            continue

        print(f"[OK] {name} | {source} | {pay} | {merchant} | {amount} | {category} | fhi={result['fhi']}")
        ok += 1

    print("\n===== WEEK1 TEST SUMMARY =====")
    print(f"OK: {ok}")
    print(f"FAIL: {fail}")


if __name__ == "__main__":
    run()
