"""Capture a dated TSETMC daily observation without inferring eligibility or fills."""
import argparse
from datetime import date, datetime, time
from hashlib import sha256
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
LOCK = "52af7e38de7ce9a4db939c8da0a652ee3f4b81248d4846cbcbdec2151afa8fd0"
ENDPOINT = "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{}/0"
MAX_BYTES = 4_000_000


def match(raw, code, day):
    rows = json.loads(raw)["closingPriceDaily"]
    if not isinstance(rows, list):
        raise ValueError("Expected a list of daily rows")
    key = int(day.strftime("%Y%m%d"))
    matching = [r for r in rows if type(r.get("dEven")) is int and r["dEven"] == key]
    if any(str(r.get("insCode")) != code for r in matching) or len(matching) > 1:
        return "identity_or_duplicate_conflict", None
    if not matching:
        return "session_row_absent", None
    fields = ("priceFirst", "priceMax", "priceMin", "pClosing", "qTotTran5J", "qTotCap")
    row = matching[0]
    if not all(type(row.get(f)) in (float, int) and 0 < row[f] < float("inf") for f in fields):
        return "nonpositive_or_invalid_market_fields", None
    if row["qTotTran5J"] % 1:
        return "noninteger_volume", None
    if not row["priceMin"] <= row["priceFirst"] <= row["priceMax"]:
        return "invalid_first_price_range", None
    return "candidate_pending_evidence", dict(zip(
        ("first", "high", "low", "close", "volume", "value"), (row[f] for f in fields)
    ))


def capture(day, symbol, code, output):
    url = ENDPOINT.format(code)
    result = {"symbol": symbol, "ins_code": code, "session_date": day.isoformat(), "source": url}
    try:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "MarketResearchCapture/1.0"})
        with urlopen(request, timeout=12) as response:
            if response.url != url:
                raise ValueError("Unexpected source redirect")
            result["http_status"] = response.status
            raw = response.read(MAX_BYTES + 1)
        result["received_at"] = datetime.now(TEHRAN).isoformat()
        if len(raw) > MAX_BYTES:
            raise ValueError("Response above configured capture limit")
        name = f"{code}.json"
        (output / name).write_bytes(raw)
        result.update(raw_file=name, raw_sha256=sha256(raw).hexdigest())
        result["status"], result["observation"] = match(raw, code, day)
    except HTTPError as exc:
        result.update(status="http_error", http_status=exc.code)
        exc.close()
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result.update(status="capture_failed", error_type=type(exc).__name__)
    result.setdefault("received_at", datetime.now(TEHRAN).isoformat())
    return result


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=here / "PROSPECTIVE_LEAD5.json")
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.protocol.read_bytes()
    if sha256(raw).hexdigest() != LOCK:
        parser.error("Frozen protocol digest mismatch")
    spec = json.loads(raw)
    now = datetime.now(TEHRAN)
    day = args.date or now.date()
    if day != now.date() or day < date.fromisoformat(spec["first_eligible_date"]):
        parser.error("Use this collector only on the current Tehran date after the frozen start")
    if now.time() < time(15):
        parser.error("Collection opens at 15:00 Tehran; official session completion still requires evidence")
    args.output.mkdir(parents=True, exist_ok=False)
    rows = [capture(day, symbol, code, args.output) for symbol, code in spec["symbols"].items()]
    report = {
        "protocol_sha256": LOCK, "started_at": now.isoformat(), "date": day.isoformat(),
        "scope": "transport and row observation only",
        "approved_for_backtest": False,
        "pending_evidence": ["official_calendar_and_close", "symbol_state", "adjustments",
                             "effective_fees_and_settlement", "source_integrity_review"],
        "observations": rows,
    }
    (args.output / "receipt.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
