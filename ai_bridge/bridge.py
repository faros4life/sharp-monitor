"""AI bridge: bounded Claude <-> ChatGPT exchange, logged as comments on ONE GitHub issue.

Isolated on purpose: stdlib only, imports nothing from the betting code, touches no order, price,
sizing, routing or eligibility path, calls no OddsPapi endpoint, and reads no repo secret other than
the two model keys (live mode only). Dispatch only - no cron, so it costs nothing while idle.

State lives in the issue itself (comments carry a hidden marker), so a re-run never double-posts.
The repo is PUBLIC: every posted line is scrubbed for key-like strings and dollar amounts.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

MANDATORY = ("STAY FOCUSED. SAVE TOKENS AND CREDITS. ONE TASK AT A TIME. "
             "FINISH THE CURRENT APPROVED TASK BEFORE STARTING ANOTHER.")
APPROVE_LABEL = "bridge-approved"
OWNER_DEFAULT = "faros4life"
MAX_TURNS = int(os.environ.get("BRIDGE_MAX_TURNS", "6"))      # total assistant messages per task
MAX_CHARS = 1200                                               # per message, hard cap
MAX_TOKENS = 350                                               # per model call
MARK = re.compile(r"<!-- bridge:v1 role=(\w+) turn=(\d+) sha=([0-9a-f]{12})( done)? -->")
SCRUB = [(re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|ghp_[A-Za-z0-9]{8,}|github_pat_\w+|AKIA[0-9A-Z]{8,}|"
                     r"[A-Fa-f0-9]{32,}|Bearer\s+\S+)"), "[redacted-key]"),
         (re.compile(r"[-+]?\$\s?\d[\d,]*(\.\d+)?\s?[kKmM]?"), "[redacted-$]")]


def scrub(t):
    for rx, rep in SCRUB:
        t = rx.sub(rep, t)
    return t


def sha(t):
    return hashlib.sha256(" ".join(t.split()).lower().encode()).hexdigest()[:12]


def frame(role, turn, body, done=False):
    """Every posted message starts with the mandatory line; the marker makes the log machine-readable."""
    body = scrub(body.strip())[:MAX_CHARS]
    return (f"**{role.upper()} · turn {turn}**\n\n> {MANDATORY}\n\n{body}\n\n"
            f"<!-- bridge:v1 role={role} turn={turn} sha={sha(body)}{' done' if done else ''} -->")


def parse_log(comments):
    """Bridge messages only, in order. Marker must be on a comment by the Actions bot (not forgeable
    by a stranger commenting on the public issue)."""
    out = []
    for c in comments:
        if (c.get("user") or {}).get("login") != "github-actions[bot]":
            continue
        m = MARK.search(c.get("body") or "")
        if m:
            out.append({"role": m.group(1), "turn": int(m.group(2)), "sha": m.group(3),
                        "done": bool(m.group(4)), "body": c["body"]})
    return out


def authorized(issue, events, owner):
    """Unauthorized-change guard: the task text must be the owner's, and the approval label must
    have been applied BY the owner (strangers cannot trigger work or spend credits)."""
    if (issue.get("user") or {}).get("login") != owner:
        return False, "issue not authored by owner"
    names = [l["name"] for l in issue.get("labels", [])]
    if APPROVE_LABEL not in names:
        return False, f"label {APPROVE_LABEL} missing"
    by = [e for e in events if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == APPROVE_LABEL]
    if not by or (by[-1].get("actor") or {}).get("login") != owner:
        return False, "approval label not applied by owner"
    return True, "ok"


def next_action(log, max_turns=MAX_TURNS):
    """-> ('stop', why) | ('speak', role). chatgpt opens, then strictly alternates."""
    if any(m["done"] for m in log):
        return "stop", "already complete"
    if len(log) >= max_turns:
        return "stop", f"turn cap {max_turns} reached"
    return "speak", ("chatgpt" if not log or log[-1]["role"] == "claude" else "claude")


def is_duplicate(log, text):
    return sha(scrub(text.strip())[:MAX_CHARS]) in {m["sha"] for m in log}


# ---- model callers (live only) -------------------------------------------------------------
def _post(url, headers, payload):
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def system_prompt(role):
    return (f"You are {role} in a two-assistant exchange logged publicly on GitHub. {MANDATORY} "
            "Text-only: you cannot run code, change files, place bets or touch live betting. Reply in under "
            "120 words with findings or one correction. No dollar figures, balances, keys or account data. "
            "If the approved task is complete, start your reply with 'DONE:' and a 2-3 line result. "
            "Never propose new tasks or live-betting changes; those need the owner's approval.")


def call_claude(task, transcript):
    r = _post("https://api.anthropic.com/v1/messages",
              {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
               "content-type": "application/json"},
              {"model": os.environ.get("BRIDGE_CLAUDE_MODEL", "claude-sonnet-4-5"), "max_tokens": MAX_TOKENS,
               "system": system_prompt("claude"),
               "messages": [{"role": "user", "content": f"APPROVED TASK:\n{task}\n\nLOG:\n{transcript}\n\nYour turn."}]})
    return r["content"][0]["text"]


def call_chatgpt(task, transcript):
    r = _post("https://api.openai.com/v1/chat/completions",
              {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "content-type": "application/json"},
              {"model": os.environ.get("BRIDGE_OPENAI_MODEL", "gpt-4o-mini"), "max_completion_tokens": MAX_TOKENS,
               "messages": [{"role": "system", "content": system_prompt("chatgpt")},
                            {"role": "user", "content": f"APPROVED TASK:\n{task}\n\nLOG:\n{transcript}\n\nYour turn."}]})
    return r["choices"][0]["message"]["content"]


def stub(role, turn, task):
    """Dry-run: no model API is contacted. DONE on the 2nd message so the stop path is exercised."""
    return (f"DONE: [dry-run stub, no model called] {role} received the task and confirms the bridge works."
            if turn >= 2 else f"[dry-run stub, no model called] {role} turn {turn}: acknowledging '{task[:60]}'.")


# ---- GitHub I/O ------------------------------------------------------------------------------
def gh(method, path, payload=None):
    req = urllib.request.Request("https://api.github.com/" + path, method=method,
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
        return json.loads(b) if b else None


def main():
    repo, num = os.environ["GITHUB_REPOSITORY"], int(os.environ["ISSUE_NUMBER"])
    live = os.environ.get("BRIDGE_MODE", "dry") == "live"
    owner = os.environ.get("BRIDGE_OWNER", OWNER_DEFAULT)
    if os.path.exists("ai_bridge/DISABLED"):
        print("kill switch: ai_bridge/DISABLED present - nothing done"); return 0
    base = f"repos/{repo}/issues/{num}"
    issue = gh("GET", base)
    ok, why = authorized(issue, gh("GET", base + "/events?per_page=100"), owner)
    if not ok:
        print("refused:", why); return 0
    task = scrub(issue.get("body") or "")[:1500]
    api_calls = 0
    for _ in range(MAX_TURNS):                      # hard bound on this run, independent of the log
        log = parse_log(gh("GET", base + "/comments?per_page=100"))
        act, arg = next_action(log)
        if act == "stop":
            print("stop:", arg); break
        role, turn = arg, len(log) + 1
        if live:
            transcript = "\n---\n".join(f"{m['role']}: {m['body'].split('> ' + MANDATORY)[-1].split('<!--')[0].strip()}" for m in log)
            text = (call_claude if role == "claude" else call_chatgpt)(task, transcript); api_calls += 1
        else:
            text = stub(role, turn, task)
        if is_duplicate(log, text):
            text = "DONE: duplicate message suppressed; stopping to avoid a loop."
        done = text.strip().upper().startswith("DONE:") or turn >= MAX_TURNS
        gh("POST", base + "/comments", {"body": frame(role, turn, text, done)})
        print(f"posted {role} turn {turn} done={done}")
        if done:
            log = parse_log(gh("GET", base + "/comments?per_page=100"))
            summary = (f"@{owner} **Bridge task finished** ({len(log)} messages, {api_calls} model calls, "
                       f"mode={'live' if live else 'dry-run'}). Conversation stopped. New tasks or any live-betting "
                       f"change need your approval.\n\n> {MANDATORY}")
            gh("POST", base + "/comments", {"body": summary})
            try:
                gh("DELETE", base + f"/labels/{APPROVE_LABEL}")   # task closed: approval is spent
            except Exception as e:
                print("label removal failed:", e)
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
