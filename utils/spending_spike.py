from datetime import datetime, timedelta

def detect_spending_spike(transactions, detector=None) -> dict:
    if not transactions:
        return {"spike_score": 0.0, "spike_flags": []}
    if isinstance(transactions, dict):
        transactions = [transactions]
    transactions = [tx for tx in transactions if isinstance(tx, dict)]
    if not transactions:
        return {"spike_score": 0.0, "spike_flags": []}

    # 날짜 파싱
    parsed = []
    for tx in transactions:
        try:
            dt = datetime.fromisoformat(str(tx.get("datetime", "")))
            amt = int(float(tx.get("amount", 0)))
            if amt > 0:
                parsed.append((dt, amt))
        except Exception:
            continue

    if not parsed:
        return {"spike_score": 0.0, "spike_flags": []}

    asof = datetime.now()
    w7 = asof - timedelta(days=7)
    w30 = asof - timedelta(days=30)

    recent7 = [amt for dt, amt in parsed if dt >= w7]
    prev30 = [amt for dt, amt in parsed if w30 <= dt < w7]

    if not recent7 or not prev30:
        return {"spike_score": 0.0, "spike_flags": []}

    avg_recent = sum(recent7) / len(recent7)
    avg_prev = sum(prev30) / len(prev30)

    if avg_prev == 0:
        return {"spike_score": 0.0, "spike_flags": []}

    spike_ratio = round((avg_recent - avg_prev) / avg_prev, 2)

    spike_flags = []
    if spike_ratio >= 0.5:
        spike_flags.append({"reason": "spike_ratio>=0.5", "score": spike_ratio})

    return {"spike_score": spike_ratio, "spike_flags": spike_flags}