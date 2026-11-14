"""Offline tests for ai_bridge/bridge.py: no network, no secrets. Run: python3 ai_bridge/test_ai_bridge.py"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bridge as b

BOT = {"login": "github-actions[bot]"}


def cm(role, turn, text, done=False, user=BOT):
    return {"user": user, "body": b.frame(role, turn, text, done)}


def test():
    # mandatory line in every message
    assert b.MANDATORY in b.frame("claude", 1, "hi")
    # scrub: keys and dollar amounts never reach the public log
    t = b.scrub("key sk-abcdef123456 and $1,250 and +$300 and " + "a" * 40)
    assert "sk-abc" not in t and "1,250" not in t and "$300" not in t and "a" * 40 not in t
    # alternation, chatgpt opens
    assert b.next_action([]) == ("speak", "chatgpt")
    log = b.parse_log([cm("chatgpt", 1, "x")])
    assert b.next_action(log) == ("speak", "claude")
    # turn cap and done both stop
    full = b.parse_log([cm("chatgpt" if i % 2 == 0 else "claude", i + 1, f"m{i}") for i in range(6)])
    assert b.next_action(full)[0] == "stop"
    assert b.next_action(b.parse_log([cm("chatgpt", 1, "DONE: ok", done=True)]))[0] == "stop"
    # forged marker from a non-bot user is ignored
    assert b.parse_log([cm("claude", 1, "x", user={"login": "stranger"})]) == []
    # duplicate detection
    assert b.is_duplicate(log, "x") and not b.is_duplicate(log, "something new")
    # authorization: owner-authored issue + label applied by owner only
    issue = {"user": {"login": "faros4life"}, "labels": [{"name": b.APPROVE_LABEL}]}
    ev = [{"event": "labeled", "label": {"name": b.APPROVE_LABEL}, "actor": {"login": "faros4life"}}]
    assert b.authorized(issue, ev, "faros4life")[0]
    assert not b.authorized(issue, [{**ev[0], "actor": {"login": "stranger"}}], "faros4life")[0]
    assert not b.authorized({**issue, "user": {"login": "stranger"}}, ev, "faros4life")[0]
    assert not b.authorized({**issue, "labels": []}, ev, "faros4life")[0]
    # message length cap
    assert len(b.frame("claude", 1, "z" * 5000)) < b.MAX_CHARS + 600
    print("ai_bridge tests: all passed")


if __name__ == "__main__":
    test()
