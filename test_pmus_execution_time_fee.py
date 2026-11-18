#!/usr/bin/env python3
"""Grade a fill on the fee that applied WHEN IT EXECUTED (Peter, Nov 18).

The discrepancy this closes: the live lanes now price Polymarket US at the Nov 14 schedule (0.095),
while the CLV ledger is deliberately pinned to the legacy basis so it cannot restate history. Without
a recorded fee, a fill taken at 0.095 would be GRADED at 0.06 - flattering every future PMUS fill by
about 1.6 points of CLV at -110.

The four cases Peter named, and what each must do:
  legacy fill            fee_coef 0.06  recorded -> graded at 0.06 even if the grader's default moves
  schedule-model fill    fee_coef 0.095 recorded -> graded at 0.095 even though the ledger runs legacy
  maker order            the maker coefficient and the maker side both recorded and honoured
  missing fee metadata   fee_coef absent -> the VENUE MODEL, which is how every historical fill keeps
                         its original treatment. Absent must never be read as zero fee.

Certification rules are NOT touched anywhere here: still a verified same-line or exact-moneyline
Pinnacle close. Only the economics that close is netted at can come off the order row.
"""
import clv_scorecard as sc
import clv_std as cs
import executor as ex
import pmus_fee as pf

FAILED = []
TOTAL = 0


def ok(name, cond, extra=""):
    global TOTAL
    TOTAL += 1
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


CP = 0.5726          # a certified Pinnacle no-vig close
AM = -110
D = 1 + 100 / 110

# ---------------------------------------------------------------- 1. the override reaches the maths
ok("legacy coefficient grades at the legacy price",
   abs(sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.06)
       - 100 * (CP * cs.net_dec("polymarket_us", D, coef=0.06) - 1)) < 1e-9)
ok("schedule coefficient grades at the schedule price",
   abs(sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.095)
       - 100 * (CP * cs.net_dec("polymarket_us", D, coef=0.095) - 1)) < 1e-9)
a = sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.06)
b = sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.095)
ok("the two models give materially different CLV", a - b > 1.0, (a, b, a - b))
ok("the schedule fill grades WORSE, never better", b < a, (a, b))

# ---------------------------------------------------------------- 2. missing metadata -> venue model
ok("fee_coef=None falls back to the venue model",
   sc.std_clv(CP, AM, "polymarket_us", fee_coef=None)
   == sc.std_clv(CP, AM, "polymarket_us"))
ok("absent metadata is NOT treated as a zero fee",
   sc.std_clv(CP, AM, "polymarket_us", fee_coef=None)
   != sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.0),
   "a zero-fee grade would flatter every historical fill")
ok("the venue-model fallback equals today's active model",
   abs(sc.std_clv(CP, AM, "polymarket_us", fee_coef=None)
       - sc.std_clv(CP, AM, "polymarket_us", fee_coef=pf.taker())) < 1e-9)

# ---------------------------------------------------------------- 3. maker orders
mk = sc.std_clv(CP, AM, "polymarket_us", fee_coef=-0.0125, maker=True)
tk = sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.06)
ok("a legacy maker fill grades better than a legacy taker fill", mk > tk, (mk, tk))
mk0 = sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.0, maker=True)
ok("a schedule maker fill grades at the raw price (free, no rebate)",
   abs(mk0 - 100 * (CP * D - 1)) < 1e-9, (mk0, 100 * (CP * D - 1)))
ok("the maker flag alone cannot grant a rebate that was not recorded",
   sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.095, maker=True)
   == sc.std_clv(CP, AM, "polymarket_us", fee_coef=0.095, maker=False),
   "the recorded coefficient governs; `maker` only selects the venue table when no coef is recorded")

# ---------------------------------------------------------------- 4. ProphetX: not a coefficient fee
ok("a coefficient is IGNORED for ProphetX, whose fee is 2% of gains",
   sc.std_clv(CP, AM, "prophetx", fee_coef=0.5) == sc.std_clv(CP, AM, "prophetx"),
   "applying a taker coefficient to a win-fee venue would be a silent mis-grade")
ok("ProphetX records no coefficient at all", ex.fee_meta("prophetx")["fee_coef"] is None)
ok("ProphetX records its model by name", ex.fee_meta("prophetx")["fee_model"] == "px_win_fee")

# ---------------------------------------------------------------- 5. what gets RECORDED
m = ex.fee_meta("polymarket_us")
ok("PMUS records the active model's taker coefficient", m["fee_coef"] == pf.taker(), m)
ok("PMUS records WHICH model produced it", m["fee_model"] == pf.MODEL, m)
ok("PMUS maker records the maker coefficient",
   ex.fee_meta("polymarket_us", maker=True)["fee_coef"] == pf.maker())
ok("PMUS maker records the side", ex.fee_meta("polymarket_us", maker=True)["fee_maker"] is True)
ok("Kalshi records its taker coefficient", ex.fee_meta("kalshi")["fee_coef"] == 0.07)
ok("a Kalshi RESTING fill records no coefficient, because its maker rate is unverified",
   ex.fee_meta("kalshi", maker=True)["fee_coef"] is None
   and ex.fee_meta("kalshi", maker=True)["fee_model"] == "maker_unverified")
ok("an unknown venue records no coefficient", ex.fee_meta("mystery")["fee_coef"] is None)
ok("every fee_meta carries all three keys",
   all(set(ex.fee_meta(b)) == {"fee_model", "fee_coef", "fee_maker"}
       for b in ("polymarket_us", "kalshi", "novig", "prophetx", "", None)))

# ---------------------------------------------------------------- 6. the projections must CARRY it
src = open("executor.py").read()
for proj in ("live_order", "live_rest", "live_more"):
    i = src.index(f'"{proj}": ')
    ok(f"the end-of-run ledger projection carries fee_meta into {proj}",
       "fee_meta(" in src[i:i + 700],
       "these are FIXED key lists - CLAUDE.md records this projection dropping a field twice")
ok("journal_order stamps the execution-time fee too",
   "fee_meta(book, maker=" in src,
   "an order placed mid-run and killed before the end-of-run email is registered only by the journal")

ll = open("live_ledger.py").read()
ok("the leg carries fee_coef off the registry row", '"fee_coef": lo.get("fee_coef")' in ll)
ok("fill-implied CLV grades on the recorded fee", 'fee_coef=l.get("fee_coef")' in ll)
ok("certified CLV grades on the recorded fee", "fees=fee_by_book(filled)" in ll)
ok("the certification guard itself is untouched",
   ll.count('how in ("own line", "moneyline")') >= 1,
   "same-line / exact-moneyline only; the fee change must not widen what certifies")

print(("FAILED: " + ", ".join(FAILED)) if FAILED else "ALL PASS")
print(f"{TOTAL - len(FAILED)} passed, {len(FAILED)} failed")
raise SystemExit(1 if FAILED else 0)
