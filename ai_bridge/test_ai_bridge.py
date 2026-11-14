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
    # shared context: committed file fits uncut, carries every required section, is scrubbed and capped
    std = open(b.CONTEXT_FILE, encoding="utf-8").read().strip()
    assert len(std) <= b.CONTEXT_MAX, len(std)
    for key in ("PROHIBITED", "COST LIMITS", "COMPLETE WHEN", "Repo rules", "Reference files"):
        assert key in std, key
    body = "OBJECTIVE: x\nSCOPE: y\nFILES: z\nFINDINGS: w\nDONE-WHEN: v\nkey sk-abcdef123456 $900 " + "q" * 5000
    ctx = b.build_context(body)
    assert "OBJECTIVE: x" in ctx and "DONE-WHEN: v" in ctx and "PROHIBITED" in ctx
    assert "sk-abc" not in ctx and "$900" not in ctx
    assert len(ctx) <= b.CONTEXT_MAX + b.TASK_MAX + 80, len(ctx)
    # both assistants receive byte-identical context + prompt (same log -> same user message)
    assert b.user_prompt(ctx, "t") == b.user_prompt(ctx, "t") and ctx in b.user_prompt(ctx, "")
    # the mandatory line stays in the system prompt of both roles and in every framed message
    assert all(b.MANDATORY in b.system_prompt(r) for r in ("claude", "chatgpt"))
    # callers, with the network replaced: both send the same context and keep the mandatory line
    seen = []
    b._post = lambda url, h, p: (seen.append(p) or {"content": [{"text": "ok"}],
                                                     "choices": [{"message": {"content": "ok"}}]})
    os.environ["ANTHROPIC_API_KEY"] = os.environ["OPENAI_API_KEY"] = "dummy"
    b.call_claude(ctx, "log"); b.call_chatgpt(ctx, "log")
    a_user = seen[0]["messages"][0]["content"]
    o_user = seen[1]["messages"][-1]["content"]
    assert a_user == o_user and ctx in a_user
    assert b.MANDATORY in seen[0]["system"] and b.MANDATORY in seen[1]["messages"][0]["content"]
    assert seen[0]["max_tokens"] == b.MAX_TOKENS == seen[1]["max_completion_tokens"]
    # regression: premature DONE cannot end the conversation (it did on live test #3, turn 1)
    t, d = b.resolve_done("DONE: all good", [], "chatgpt", 1)
    assert d is False and not t.upper().startswith("DONE:") and "early DONE ignored" in t
    one = b.parse_log([cm("chatgpt", 1, "hello")])
    assert b.resolve_done("DONE: x", one, "chatgpt", 2)[1] is False      # same role twice is not both
    # correct alternation through a full normal run, driven by next_action + resolve_done
    comments, order = [], []
    for turn in range(1, 7):
        log = b.parse_log(comments)
        act, role = b.next_action(log)
        if act == "stop":
            break
        text, done = b.resolve_done("DONE: early" if turn == 1 else ("DONE: finished" if turn == 4 else f"msg {turn}"),
                                    log, role, turn)
        comments.append(cm(role, turn, text, done)); order.append(role)
    assert order == ["chatgpt", "claude", "chatgpt", "claude"], order          # alternates, DONE@1 ignored
    assert b.next_action(b.parse_log(comments)) == ("stop", "already complete")  # normal termination on turn 4
    # DONE from the second role right after the first speaks is allowed
    assert b.resolve_done("DONE: ok", one, "claude", 2)[1] is True
    # six-message cap still terminates without a DONE; duplicates still caught; auth unchanged
    assert b.resolve_done("msg", [], "chatgpt", b.MAX_TURNS)[1] is True
    assert b.MAX_TURNS == 6 and b.MAX_CHARS == 1200
    print("ai_bridge tests: all passed")


if __name__ == "__main__":
    test()
