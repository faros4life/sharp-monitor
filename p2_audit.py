#!/usr/bin/env python3
"""Project 2 audit runner - READ-ONLY. Reads tracker/state.enc and the private registry (GET only).
No Gmail, no order endpoint, no state change, no commit. Public log = counts only. Venue reads (Nov 14 23:33, Peter "Build it"):
Novig GET /v3/portfolio/fills with the READ-ONLY key (verified read-only by novig_signed.ready), and ProphetX with the DATA key:
POST /auth/login (authentication only) then GET trades - no trading key, no order route, no odds API. The dollar / ROI report goes ONLY to Peter's
private Telegram (Peter approved Nov 14 18:06 ET), the same route as last50_report.send_telegram; nothing is written to disk.
Fails closed: unreadable registry -> nothing is reported. executor is NOT imported (see the index block)."""
import csv
import io
import json
import os
import sys

from p2_audit_core import CSV_FIELDS, build, link_index, render


def read_novig_fills():
    """(fills, note, complete). complete is False when the 40-page guard stops with a cursor still pending. READ-ONLY: novig_signed.ready() confirms with Novig that the key is read-only before any call, and
    fails closed. Both wallets (main + the bot sub-wallet, whose key ID only is passed), paginated - the same read
    clv_link_recon uses (run 43240507919). The note is a fixed label; no response text is ever printed."""
    try:
        import novig_signed as nv
        if not nv.ready():
            return [], "novig read key not ready", False
        fills, complete = [], True
        for kid in dict.fromkeys([nv._S["id"], (os.environ.get("NOVIG_TRADE_KEY_ID") or "").strip()]):
            if not kid:
                continue
            after, pages = None, 0
            while pages < 40:
                pages += 1
                prm = {"limit": 100, "keyId": kid}
                if after:
                    prm["after"] = after
                d = nv.get("/v3/portfolio/fills", prm)
                got, nxt = [], None
                for v in (d.values() if isinstance(d, dict) else [d]):
                    if isinstance(v, list):
                        got += v
                    elif isinstance(v, dict):
                        got += v.get("items") or v.get("fills") or v.get("data") or []
                        nxt = nxt or v.get("next")
                if isinstance(d, dict):
                    nxt = nxt or d.get("next")
                fills += got
                if not got or not nxt:
                    break
                after = nxt
            else:
                complete = False          # page cap reached with a cursor still pending: TRUNCATED, never "ok"
        return fills, ("ok" if complete else "TRUNCATED at the 40-page guard"), complete
    except Exception as e:
        return [], f"novig fills unreadable ({type(e).__name__})", False


def read_px_trades():
    """(trades, note, complete). ProphetX DATA key. Two calls: POST /auth/login (authentication only - no order, no state
    change) then GET /v4/mm/get_trades. No paging parameter is documented or used in this repo and every recorded read
    returned exactly 100 rows, so 100 rows or any paging marker = possibly TRUNCATED -> no ProphetX EXACT from it."""
    from p2_audit_core import px_trades_complete
    try:
        import book_check as bc
        if not bc.px_login():
            return [], "prophetx login failed", False
        d = bc.px_call("/v4/mm/get_trades") or {}
        data = d.get("data") or {}
        trades = data.get("trades") or []
        ok = px_trades_complete(trades, list(data) + list(d))
        return trades, ("ok" if ok else "POSSIBLY TRUNCATED (100-row cap or paging marker)"), ok
    except Exception as e:
        return [], f"prophetx trades unreadable ({type(e).__name__})", False


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
    # 15 Nov: the registry prunes orders after 4 days. Orders it no longer holds are restored from the
    # durable reporting ledger so older positions keep their exact lane instead of falling to UNATTRIBUTED.
    import report_sections as rs
    import reporting_ledger as rl
    import os as _os
    ledger_orders, ledger_fills = [], {}
    if _os.path.exists(rl.OUT):
        cur = rl.latest(rl.load_ledger())
        ledger_orders = [d for (k, _i), (_f, d) in cur.items() if k == "order"]
        ledger_fills = {i: d for (k, i), (_f, d) in cur.items() if k == "fill"}
    else:
        print("durable ledger ABSENT - registry window only")
    rr, ledger_extra = rs.merge_orders(rr, ledger_orders)
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

    fills, nf, nok = read_novig_fills()
    trades, nt, pok = read_px_trades()
    links = link_index(fills, trades, {"nv": nok, "px": pok})
    print(f"venue reads: novig fills {len(fills)} ({nf}) | prophetx trades {len(trades)} ({nt}) | tracker rows with a venue link "
          f"{sum(1 for r in rows if str(r.get('id') or '') in links)} of {len(rows)} | complete: novig {nok}, prophetx {pok}")
    import clv_ledger as cl
    import clv_stale as cstale
    cb = (tb.dec(json.load(open(cl.STATE))) or {}).get("bets") or {}
    stale = cstale.stale_map(cb, st.get("bets") or {})
    clv = {k: r["clv"] for k, r in cb.items()
           if r.get("clv") is not None and not r.get("fixture_doubt") and k not in stale}
    rep = build(rows, index, reg._venue, links, clv)
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
    print("FUZZY lanes are the tracker's own text-matched labels (UNVERIFIED). EXACT = venue order id or venue fill/trade link "
          "to ONE registry claim per order, one lane per position.")
    text, csv_rows = render(rep)
    fills_all = dict(ledger_fills)
    fills_all.update(reg.fills() or {})
    p1 = rs.project1(rows, clv)
    integ = rs.integrity(rr, fills_all, rows, clv, rep, pok)
    text += rs.render(p1, integ, ledger_extra)
    print(f"ledger orders restored {ledger_extra} | project1 first-seen {p1['first_seen_since_start']} graded {p1['graded']} "
          f"missing close {p1['missing_close']} | integrity: placed {integ['placed_orders_since_start']} "
          f"(fill by id {integ['fill_record_by_id']}, by play_key {integ['fill_record_by_play_key']}) without fill record {integ['placed_orders_without_fill_record']}, not-terminal fills "
          f"{integ['fill_records_not_terminal']}, settled missing CLV {integ['settled_missing_certified_clv']}, "
          f"not exact {integ['positions_without_exact_lane']}")
    return 0 if send_private(text, csv_rows) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e_:    # an exception message can carry row text: print the type only
        print(f"FATAL: {type(e_).__name__} (message withheld)", flush=True)
        sys.exit(1)
