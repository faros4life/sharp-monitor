"""REVIEW ONLY. The shared exposure ledger, on the store that ALREADY exists.

NOT WIRED TO ANYTHING. No production path imports this. It writes nothing unless a caller
explicitly drives it, and no caller does.

THE SHARED-STORE QUESTION IS ALREADY ANSWERED. Nothing new has to be built or chosen:

    registry.py  REPO = faros4life/novig-runner   PATH = registry/bot_registry.json

- It is durable, and it is 645 KB of live data today.
- Its writes use the GitHub blob SHA as an OPTIMISTIC LOCK (`registry._commit`, "two overlapping
  passes cannot both win the same token"). That is a genuine compare-and-swap.
- sharp-monitor reaches it over the contents API with REGISTRY_TOKEN.
- It physically LIVES in the novig-runner repository, so the home runner already has it.

So the two systems share the store by LOCATION. What they do not share is USE: the runner's
`novig_live_order.py` contains no reference to `registry.` at all, and the only mention of
bot_registry.json anywhere in that repo is a path list in a test. Closing the gap is wiring, not
procurement - which is a much smaller problem than "choose a store", and worth saying plainly.

WHY THIS DOES NOT USE registry._commit(). _commit(merge) is a read-merge-write that RETRIES, and on
retry it re-applies the merge to whatever is in the file now. That is exactly right for additive
bookkeeping, which is what it was built for. It is WRONG for a reservation: re-applying a
reservation merge against newer state would write the reservation without re-asking whether the
budget still allows it, which is the race the whole design exists to lose. So this adapter does an
explicit fetch, then a single conditional PUT with the sha it read, and reports failure rather than
retrying. review_unit_reservation decides what to do with a lost race - and what it does is refuse.

The registry module is INJECTED so this can be exercised without network, credentials or a live
store. Nothing here holds a token; it calls the registry module's own helpers, which hold it.
"""
import copy

LEDGER_KEY = "unit_reservations"


class RegistryStore:
    """Presents the shared registry file as the read()/write() contract the protocol needs.

        read()                -> (state, version)   version is the blob sha; (None, None) unreadable
        write(state, version) -> True on a confirmed write, False when the sha has moved

    State lives under ONE key inside the existing file rather than in a new file, so both systems
    read one object under one lock. A second file would reintroduce the split this is fixing."""

    def __init__(self, registry_module, key=LEDGER_KEY):
        self._r = registry_module
        self._key = key

    def read(self):
        """(state, sha). (None, None) when the store cannot be read - NEVER ({}, None).

        That distinction is load-bearing: an unreadable store must block, and a store that reads as
        empty must not. registry._fetch() already draws it the same way."""
        try:
            data, sha = self._r._fetch()
        except Exception:
            return (None, None)
        if data is None:
            return (None, None)
        return (copy.deepcopy(data.get(self._key) or {"legs": []}), sha)

    def write(self, state, version):
        """Single conditional PUT with the sha that was read. No retry - see the module docstring.

        Returns False on a lost race so the caller refuses. It never re-reads and re-applies,
        because re-applying a reservation is how one reservation becomes two."""
        try:
            data, sha = self._r._fetch()
        except Exception:
            return False
        if data is None or sha != version:
            return False                      # someone else wrote first: lost the compare-and-swap
        merged = dict(data)
        merged[self._key] = state
        try:
            return bool(self._r._put_with_sha(merged, sha))
        except AttributeError:
            # registry.py has no single-shot conditional PUT today - only _commit, whose retry
            # semantics are unsafe here. Adding one is a PRODUCTION change to the registry module
            # and is deliberately not made from this review branch. Until it exists this adapter
            # reports failure, which fails closed.
            return False
        except Exception:
            return False


def wiring_gap():
    """The call sites that must consult this store before an order is sent. NONE do today.

    Listed so the remaining work is explicit rather than implied, and so a reviewer can check it
    against the source rather than taking it on trust."""
    return [
        ("sharp-monitor", "executor.live_order()", "shared taker path for every lane"),
        ("sharp-monitor", "executor.live_remainder()", "additional venues in the same run"),
        ("sharp-monitor", "executor.rest_bid()", "resting path - has a stake-dollar check today"),
        ("novig-runner", "novig_live_order.place()", "no registry reference at all"),
    ]
