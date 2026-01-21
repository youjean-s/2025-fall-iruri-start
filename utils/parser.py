"""
parser.py
Input: push notification text (str)
Output: list[dict] normalized transactions with keys:
  datetime, amount, merchant, category, source, payment_method, raw_text
"""

import re
from datetime import datetime


def _detect_source(text: str) -> str:
    t = text.lower()
    if "카카오페이" in text or "kakaopay" in t:
        return "kakaopay"
    if "신한" in text:
        return "shinhan"
    if "kb" in t or "국민" in text:
        return "kb"
    if "현대" in text:
        return "hyundai"
    if "삼성" in text:
        return "samsung"
    return "unknown"


def _normalize_tx(tx: dict, raw_text: str) -> dict:
    return {
        "datetime": tx.get("datetime"),
        "amount": float(tx.get("amount", 0)),
        "merchant": tx.get("merchant") or tx.get("store") or tx.get("place"),
        "category": tx.get("category"),
        "source": tx.get("source"),
        "payment_method": tx.get("payment_method"),
        "raw_text": raw_text,
    }


def _parse_unknown(text: str) -> dict:
    # 기존 기본 파싱 로직을 unknown fallback으로 사용
    amount_pattern = r"([\d,]+)\s*원"
    amount_match = re.search(amount_pattern, text)
    amount = int(amount_match.group(1).replace(",", "")) if amount_match else 0

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    store = lines[1] if len(lines) >= 2 else "알수없음"

    datetime_pattern = r"(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})"
    dt_match = re.search(datetime_pattern, text)
    if dt_match:
        dt_str = f"{dt_match.group(1)} {dt_match.group(2)}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    else:
        dt = datetime.now()

    return {"store": store, "amount": amount, "datetime": dt}


def _parse_shinhan(text: str) -> dict:
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # 1) amount: 어디 있든 "숫자원" 패턴으로 검색 (1줄째에 붙는 경우 대응)
    amount = 0
    m = re.search(r"([\d,]+)\s*원", text)
    if m:
        amount = int(m.group(1).replace(",", ""))

    # 2) datetime: 보통 마지막 줄에 있음 (없으면 현재시간)
    dt = datetime.now()
    mdt = re.search(r"(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})", text)
    if mdt:
        dt = datetime.strptime(f"{mdt.group(1)} {mdt.group(2)}", "%Y-%m-%d %H:%M")

    # 3) store/merchant: 보통 2번째 줄이 매장명
    store = "알수없음"
    if len(lines) >= 2:
        store = lines[1]
    else:
        # fallback: 그래도 없으면 unknown 로직 사용
        fallback = _parse_unknown(text)
        store = fallback.get("store", store)

    return {
        "store": store,
        "amount": amount,
        "datetime": dt,
        "payment_method": "card",  # 신한카드 푸시는 카드 결제로 간주
    }

def _parse_kakaopay(text: str) -> dict:
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # amount
    amount = 0
    m = re.search(r"([\d,]+)\s*원", text)
    if m:
        amount = int(m.group(1).replace(",", ""))

    # datetime (있는 경우만)
    dt = datetime.now()
    mdt = re.search(r"(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})", text)
    if mdt:
        dt = datetime.strptime(f"{mdt.group(1)} {mdt.group(2)}", "%Y-%m-%d %H:%M")

    # merchant: 보통 2번째 줄
    store = "알수없음"
    if len(lines) >= 2:
        store = lines[1]

    return {
        "store": store,
        "amount": amount,
        "datetime": dt,
        "payment_method": "wallet",  # 카카오페이는 지갑/간편결제로
    }



def parse_push_notification(text: str) -> list[dict]:
    try:
        source = _detect_source(text)

        if source == "shinhan":
            tx = _parse_shinhan(text)
        elif source == "kakaopay":
            tx = _parse_kakaopay(text)
        else:
            tx = _parse_unknown(text)

        if not tx:
            return []

        tx["source"] = source
        return [_normalize_tx(tx, raw_text=text)]

    except Exception as e:
        print("[ParserError]", e)
        return []
