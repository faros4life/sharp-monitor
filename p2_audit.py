#!/usr/bin/env python3
"""Project 2 audit runner - READ-ONLY. Reads tracker/state.enc and the private registry (GET only).
No Gmail, no order endpoint, no state change, no commit. Public log = counts only. The dollar / ROI report goes ONLY to Peter's
private Telegram (Peter approved Nov 14 18:06 ET), the same route as last50_report.send_telegram; nothing is written to disk.
Fails closed: unreadable registry -> nothing is reported. executor is NOT imported (see the index block)."""
import csv
import io
import json
import os
import sys

from p2_audit_core import CSV_FIELDS, build, render


def send_private(text, rows):
    """PRIVATE Telegram delivery - the route last50_report.send_telegram already uses (secrets TELEGRAM_BOT_TOKEN /
    TELEGRAM_CHAT_ID). The public log gets only 'delivered: N message(s) + CSV' or the exception TYPE. Returns True/False."""
    import urllib.request
    tok = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not tok or not chat:
        print("telegram not configured - report NOT delivered")
        return False
    base = f"https://api.telegram.org/bot{tok}/"
    chunks, cur = [], ""
    for ln in text.split("\n"):
        if len(cur) + len(ln) + 1 > 3900:
            chunks.append(cur)
            cur = ""
        cur += ln + "\n"
    chunks.append(cur)
    try:
        for c in chunks:
            req = urllib.request.Request(base + "sendMessage", json.dumps({"chat_id": chat, "text": c}).encode(),
                                         {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=30).read()
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(CSV_FIELDS), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        bd = "----p2audit"
        parts = [f'--{bd}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat}\r\n',
                 f'--{bd}\r\nContent-Disposition: form-data; name="document"; filename="p2_lane_audit.csv"\r\n'
                 f'Content-Type: text/csv\r\n\r\n{buf.getvalue()}\r\n--{bd}--\r\n']
        req = urllib.request.Request(base + "sendDocument", "".join(parts).encode(),
                                     {"Content-Type": f"multipart/form-data; boundary={bd}"})
        urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        print(f"telegram send failed ({type(e).__name__})")
        return False
    print(f"telegram delivered: {len(chunks)} message(s) + CSV")
    return True


def main():
    import copy
    import json
    import sys

    import tracker_build as tb
    import registry as reg
    from p2_audit_core import build

    st = tb.dec(json.load(open(tb.STATE)))
    raw = copy.deepcopy(st.get("bets") or {})
    tb.mark_manual_dups(raw)
    # RAW rows, NOT tb.group_fills(): group_fills merges on a ProphetX strike id (a market id), which can span orders and lanes.
    rows = [b for b in raw.values() if not b.get("dup_of") and (b.get("source") or "") == "bot"]

    rr = reg.rows()
    if rr is None:
        sys.exit("registry unreadable - lane identity cannot be proven; nothing reported")
    # Lane comes from the registry row itself (registry.row_lane: 'source' = rules|board|r1|lane2, or a lane prefix on the key).
    # executor is NOT imported: executor.lane_of reads row['live'] as a dict, but ledger rows store 'live' as a BOOL, so it would
    # label every order PHASE 1; and importing executor pulls in every venue module. An unknown source proves nothing.
    d = lambda x: x if isinstance(x, dict) else {}
    index, no_lane = {}, 0
    for row in rr:
        key = row.get("key")
        more = row.get("live_more")
        los = [d(row.get("live_order")), d(row.get("live_rest"))] + [d(x) for x in (more if isinstance(more, list) else [])]
        placed = [lo for lo in los if lo.get("status") == "placed" and lo.get("order_id") and not lo.get("intent") and not lo.get("voided")
                  and not str(lo.get("order_id")).startswith("intent-")]
        if not key or not placed:
            continue
        lane = reg.row_lane(row)
        if not lane:
            no_lane += 1
            continue
        for lo in placed:
            index.setdefault(str(lo["order_id"]), []).append((reg._venue(lo.get("book") or row.get("fill_book")), str(key), lane))

    rep = build(rows, index, reg._venue)
    print("bot rows:", len(rows), "| with a venue order id (order_ref):", sum(1 for r in rows if r.get("order_ref")),
          "| registry order ids:", len(index), "| registry rows with no provable lane:", no_lane, "| join:", rep["join"])
    td = {}
    for v in rep["buckets"].values():
        for f_, d_ in v["time_diag"].items():
            t_ = td.setdefault(f_, [0, 0, 0])
            t_[0] += d_["present"]; t_[1] += d_["after_run"]; t_[2] += d_["midnight_utc"]
    print("time fields over all buckets (present / after run / exactly 00:00 UTC):",
          ", ".join(f"{f_} {a_}/{b_}/{c_}" for f_, (a_, b_, c_) in td.items()))
    for b, v in rep["buckets"].items():
        a = v["all"]
        print(f"{b}: settled {a['settled']} (verified money {a['verified_money']}), open/ambiguous {v['open_or_ambiguous']}, "
              f"no-time {v['settled_no_time']}, mixed time basis {v['MIXED_TIME_BASIS']}")
    print("FUZZY lanes are the tracker's own labels and UNVERIFIED (tracker_build KEY_LANE uses executor.lane_of on rows whose "
          "'live' is a bool).")
    text, csv_rows = render(rep)
    return 0 if send_private(text, csv_rows) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e_:    # an exception message can carry row text: print the type only
        print(f"FATAL: {type(e_).__name__} (message withheld)", flush=True)
        sys.exit(1)
