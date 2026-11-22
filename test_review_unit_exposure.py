"""Deterministic offline regression cases for REVIEW-ONLY guard. No venue calls."""
import unittest
from review_unit_exposure import remaining, maximum_stake, fraction, ExposureUnknown
K="NFL|MIN @ SF|total|UNDER"

def leg(oid, stake, odds=-110, fill=None, status="open", verified=False, key=K):
    return dict(key=key, order_id=oid, asked_stake=stake,
                filled_stake=fill, american=odds, status=status,
                terminal_verified=verified)

class UnitGuardCases(unittest.TestCase):
    def test_min_sf_rest_then_take(self):
        # $44.264 at -110 = $40.24 gross to-win.
        old=leg("novig",44.264,fill=44.264,status="filled",verified=True)
        left=remaining([old],300,K)
        self.assertAlmostEqual(left*300,259.76,places=2)
        self.assertLessEqual(maximum_stake(left,-110,300)*100/110,259.761)
    def test_taker_then_open_rest_reserves(self):
        taker=leg("px",220,fill=220,status="filled",verified=True)
        rest=leg("nv",110)
        self.assertAlmostEqual(remaining([taker,rest],300,K),0)
    def test_partial_open_reserves_ask(self):
        self.assertAlmostEqual(remaining([leg("nv",220,fill=100,status="partially_filled")],300,K),1/3)
    def test_mixed_price_unit_convention(self):
        self.assertAlmostEqual(fraction(110,-110,300),1/3)
        self.assertAlmostEqual(fraction(100,150,300),1/3)
        self.assertAlmostEqual(remaining([leg("a",110,fill=110,status="filled",verified=True),
            leg("b",100,odds=150,fill=100,status="filled",verified=True)],300,K),1/3)
    def test_adjacent_lines_one_play_key(self):
        self.assertAlmostEqual(remaining([leg("a",110,fill=110,status="filled",verified=True),
            leg("b",110,fill=110,status="filled",verified=True)],300,K),1/3)
    def test_board_r1_200(self):
        for lane in ("R1","Board V4"):
            with self.subTest(lane=lane):
                self.assertAlmostEqual(remaining([leg("x",110,fill=110,status="filled",verified=True)],200,K),.5)
                self.assertEqual(maximum_stake(.5,-110,200),110)
    def test_unknown_expiry_fail_closed(self):
        self.assertEqual(remaining([leg("x",330,status="expired",fill=None)],300,K),0)
        self.assertEqual(remaining([leg("x",330,status="expired",fill=0,verified=True)],300,K),1)
    def test_duplicate_order_snapshots_max(self):
        self.assertAlmostEqual(remaining([leg("x",110),leg("x",220,fill=220,status="filled",verified=True)],300,K),1/3)
    def test_other_play_does_not_count(self):
        self.assertEqual(remaining([leg("x",330,key="different")],300,K),1)
    def test_invalid_fail_closed(self):
        for n in (float("nan"), float("inf"), -2):
            with self.assertRaises(ExposureUnknown):
                remaining([leg("x",n)],300,K)
        with self.assertRaises(ExposureUnknown):
            remaining([leg("",110)],300,K)

if __name__=="__main__":
    unittest.main()
