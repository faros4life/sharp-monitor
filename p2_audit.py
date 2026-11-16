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

from p2_audit_core import CSV_FIELDS, build, fills_without_tracker_row, index_from_sources, link_index, render


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


def read_px_matching(order_ids, frm_ts, to_ts, max_pages=60):
    """(matched_ids, complete, note). READ-ONLY GETs of /v2/mm/get_wager_matching_detail: the time range paged to
    the end by next_cursor, plus one call filtered to the given wager ids. complete=True ONLY when the range was
    paged to a page with no cursor and no error. Counts only are printed."""
    from p2_audit_core import px_match_records, px_next_cursor, px_matched_ids, px_has_cursor_field
    import urllib.parse as up
    try:
        import book_check as bc
        if not bc.px_login():
            return set(), False, "prophetx login failed"
        recs, cur, pages, complete = [], None, 0, False
        while pages < max_pages:
            q = {"from": int(frm_ts), "to": int(to_ts), "limit": 100}
            if cur:
                q["next_cursor"] = cur
            d = bc.px_call("/v2/mm/get_wager_matching_detail?" + up.urlencode(q)) or {}
            pages += 1
            page = px_match_records(d)
            recs += page
            cur = px_next_cursor(d)
            if not cur:
                # complete ONLY if the cursor field exists (and is empty) or the page is short: a renamed cursor
                # field must never read as "no more pages"
                complete = px_has_cursor_field(d) or len(page) < 100
                break
        by_id = 0
        if order_ids:
            try:
                d2 = bc.px_call("/v2/mm/get_wager_matching_detail?" + up.urlencode({"wager_ids": ",".join(order_ids)})) or {}
                r2 = px_match_records(d2)
                by_id = len(r2)
                recs += r2
            except Exception as e2:
                by_id = f"error {type(e2).__name__}"
        note = f"pages {pages}, records {len(recs)}, by-id records {by_id}, complete {complete}"
        return px_matched_ids(recs), complete, note
    except Exception as e:
        return set(), False, f"matching detail unreadable ({type(e).__name__})"


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
    rr_live = list(rr)
    rr, ledger_extra = rs.merge_orders(rr, ledger_orders)     # (used by the integrity / day sections, unchanged)
    # EXACT claims (Peter, 16 Nov): live registry + durable ledger, DEDUPLICATED BY IMMUTABLE ORDER / CLIENT ID. The lane is
    # registry.row_lane on the stored row (its 'source' field), never a key prefix or a game name.
    index, src_stats = index_from_sources([("registry", rr_live), ("ledger", ledger_orders)], reg.row_lane, reg._venue)
    no_lane = src_stats.get("rows_no_provable_lane", 0)
    print("claim sources (order ids, deduplicated):", {k: v for k, v in src_stats.items() if k != "rows_no_provable_lane"})

    # 16 Nov: a venue row whose order id IS a placed registry bot order is a bot fill by registry evidence, whatever
    # the tracker's own source label says. Paging the tracker's ProphetX read surfaced such a fill labelled manual.
    # Promoted rows are counted and checked against existing bot rows so one bet can never be counted twice.
    _bot_keys = {(str(b.get("game")), str(b.get("bet")), str(b.get("book"))) for b in rows}
    promoted, promo_dup = [], 0
    for b in raw.values():
        if b.get("dup_of") or (b.get("source") or "") == "bot" or str(b.get("order_ref") or "") not in index:
            continue
        if (str(b.get("game")), str(b.get("bet")), str(b.get("book"))) in _bot_keys:
            promo_dup += 1          # same bet already present as a bot row: NOT added
            continue
        promoted.append(dict(b, source="bot", source_was=b.get("source"), source_by="registry order id"))
    # 16 Nov: Polymarket US rows carry no order id, but a settled row's id embeds the venue market slug
    # ("pm|Title [slug]|outcome|settled") and the registry stores the request it sent, marketSlug included. Linked
    # ONLY when exactly one placed registry bot order and exactly one tracker row share the slug.
    import re as _re
    _d = lambda x: x if isinstance(x, dict) else {}
    # The registry keeps no copy of the Polymarket request, so the order's market slug comes from the VENUE: the
    # pmus-activity job reads each fill back and saves order id -> marketSlug (encrypted, reporting/pm_links.enc).
    pm_links = {}
    if _os.path.exists("reporting/pm_links.enc"):
        pm_links = tb.dec(json.load(open("reporting/pm_links.enc"))) or {}
    pm_orders = {}
    for o in rr:
        for lo in [_d(o.get("live_order")), _d(o.get("live_rest"))]:
            oid_ = str(lo.get("order_id") or "")
            slug = pm_links.get(oid_) or _d(lo.get("order")).get("marketSlug")
            if lo.get("status") == "placed" and slug and oid_ in index:
                pm_orders.setdefault(slug, set()).add(oid_)
    pm_rows = {}
    for b in raw.values():
        m = _re.search(r"\[([^\]]+)\]", str(b.get("id") or "")) if str(b.get("id") or "").startswith("pm|") else None
        if m and not b.get("dup_of"):
            pm_rows.setdefault(m.group(1), []).append(b)
    _pm_all = [o for o in rr for lo in [_d(o.get("live_order")), _d(o.get("live_rest"))]
               if lo.get("status") == "placed" and "polymarket" in str(lo.get("book") or o.get("fill_book") or "").lower()]
    print(f"polymarket link diag: placed PM orders {len(_pm_all)}, with marketSlug in the stored request {sum(len(v) for v in pm_orders.values())}, "
          f"tracker pm rows with a slug in the id {sum(len(v) for v in pm_rows.values())} "
          f"(pm rows total {sum(1 for b in raw.values() if str(b.get('id') or '').startswith('pm|'))}), "
          f"slugs on both sides {len(set(pm_orders) & set(pm_rows))}, "
          f"venue links on file {len(pm_links)}")
    pm_linked = pm_ambiguous = 0
    have = {str(b.get("id")) for b in rows + promoted}
    for slug, oids in pm_orders.items():
        cand = pm_rows.get(slug) or []
        if len(oids) != 1 or len(cand) != 1:
            pm_ambiguous += 1 if cand else 0
            continue
        b = cand[0]
        if str(b.get("id")) in have:
            if not b.get("order_ref"):
                for r_ in rows + promoted:
                    if str(r_.get("id")) == str(b.get("id")):
                        r_["order_ref"] = next(iter(oids))
            continue
        if (str(b.get("game")), str(b.get("bet")), str(b.get("book"))) in _bot_keys:
            promo_dup += 1          # same bet already present as a bot row: NOT added
            continue
        promoted.append(dict(b, source="bot", source_was=b.get("source"), order_ref=next(iter(oids)),
                             source_by="registry order market slug"))
        pm_linked += 1
    rows = rows + promoted
    print(f"registry-proven bot rows the tracker labelled otherwise: added {len(promoted)} "
          f"(of which Polymarket US by market slug {pm_linked}, ambiguous slugs not linked {pm_ambiguous}), "
          f"skipped as already present {promo_dup}")
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
    from bot_live_export import TRIGGERS     # Peter's 13 Nov ruled lane table (constant only; nothing is run)
    ruled = (TRIGGERS, tb.toks)
    rep = build(rows, index, reg._venue, links, clv, ruled)
    # SECTION F (Peter, 16 Nov): every bot row from 12 Nov ET, classified the same way, with its own exactly-once check.
    # 16 Nov: by the BET's own time only (placed / game start / settlement), never a discovery stamp - paging the
    # tracker's ProphetX read surfaced ~260 old trades in one run, all "first seen" today.
    _f0 = rs._t(rs.START_ET + "T05:00:00+00:00")
    since = [r for r in rows if rs._event_time(r) is not None and rs._event_time(r) >= _f0]
    print(f"section F scope: bot rows with no event time (excluded, not guessed) {sum(1 for r in rows if rs._event_time(r) is None)}")
    rep_f = build(since, index, reg._venue, links, clv, ruled)
    eof = rep_f.get("exactly_once") or {}
    print(f"section F (from {rs.START_ET} ET): bot rows {len(since)} | exactly-once {'OK' if eof.get('ok') else 'FAILED'} | "
          "buckets " + ", ".join(f"{b} {v['all']['settled']}+{v['open_or_ambiguous']} open" for b, v in rep_f["buckets"].items()))
    print("section F join:", rep_f["join"])
    print("bot fills of registry orders with NO tracker row (by venue):",
          fills_without_tracker_row(links, index, {str(r.get("id") or "") for r in rows}) or "none")
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
    print("EXACT = VERIFIED (venue order id or venue fill/trade link to ONE registry claim per order, one lane per position). "
          "RULED = Peter's 13 Nov ruled table, Oct 31 - Nov 12 (never EXACT). FUZZY = tracker text label (UNVERIFIED).")
    text, csv_rows = render(rep)
    tf, cf = render(rep_f)
    text += f"\n\nSECTION F - EVERY BOT ROW FROM {rs.START_ET} ET (settled W/L, ROI, units where verified, certified CLV availability)\n" + tf
    for r_ in cf:
        r_["bucket"] = "F|" + r_["bucket"]
    csv_rows += cf
    fills_all = dict(ledger_fills)
    fills_all.update(reg.fills() or {})
    p1 = rs.project1(rows, clv)
    integ = rs.integrity(rr, fills_all, rows, clv, rep, pok)
    text += rs.render(p1, integ, ledger_extra)
    # SECTION G (Peter, 16 Nov): every missing fill record and every missing certified CLV since 12 Nov, each with
    # the evidence-based reason. Detail is private; the public log carries category counts only.
    venue_ids_seen = {i for t, ids_l in links.items() if t != "_incomplete" for ids in ids_l for i in ids}
    fx0 = rs.fill_exceptions(rr, fills_all, venue_ids_seen, pok)
    px_ids = sorted({i for e in fx0 if "prophet" in e["venue"] for i in e.get("ids") or []})
    px_ev = None
    if px_ids:
        import time as _time
        frm = int(rs._t(rs.START_ET + "T05:00:00Z").timestamp())
        px_matched, px_full, px_note = read_px_matching(px_ids, frm, int(_time.time()))
        print(f"prophetx matching detail: {px_note} | queried orders {len(px_ids)}")
        px_ev = {"matched": px_matched, "complete": px_full}
    tracked = {str(r.get("order_ref")) for r in rows if r.get("order_ref")}
    tracked |= {i for t_, ids_l in links.items() if t_ != "_incomplete" and t_ in {str(r.get("id") or "") for r in rows}
                for ids in ids_l for i in ids}
    fx = rs.fill_exceptions(rr, fills_all, venue_ids_seen, pok, px_ev, tracked)
    raw_clv = {k: r for k, r in cb.items()}
    cx = rs.clv_exceptions(rows, raw_clv, clv, set(stale))
    text += rs.render_exceptions(fx, cx)
    for e_ in fx:   # venue + verdict only: no game, side, id or amount
        print(f"  G order exception: day {e_['day']} venue {e_['venue']} lane {e_['key'].split('|')[0]} -> "
              f"{e_['category'].split(' - ')[0]}" + ("" if e_.get("in_project2") is None else
              f" | linked to a Project 2 position: {'yes' if e_['in_project2'] else 'NO'}"))
    print(f"section G: no-fill-record orders {len(fx)} {rs.category_counts(fx)} | confirmed fills NOT in Project 2 "
          f"{sum(1 for e in fx if e.get('in_project2') is False)} | settled without certified CLV {len(cx)} "
          f"{rs.category_counts(cx)}")
    # Section E covers the previous ET day (the scheduled 04:52 ET run reports yesterday's slate);
    # REPORT_DAY overrides it for a one-off check of a specific day.
    from datetime import datetime as _dt, timedelta as _td
    day = _os.environ.get("REPORT_DAY") or (_dt.now(rs.ET) - _td(days=1)).strftime("%Y-%m-%d")
    so, sp = rs.day_selections(day, rr, fills_all, rows, clv, rep.get("row_bucket") or {})
    text += rs.render_day(day, so, sp, rep.get("exactly_once") or {})
    eo = rep.get("exactly_once") or {}
    print(f"section E {day}: bot orders {len(so)}, bot positions {len(sp)} "
          f"(settled {sum(1 for p in sp if p['result'] != 'OPEN')}, CLV missing {sum(1 for p in sp if p['clv'] == 'MISSING')}) | "
          f"exactly-once {'OK' if eo.get('ok') else 'FAILED'} rows {eo.get('rows')} in-plays {eo.get('rows_in_plays')} distinct {eo.get('distinct')}")
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
