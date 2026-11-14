STANDING CONTEXT (same for both assistants; the issue body adds OBJECTIVE, SCOPE, FILES, FINDINGS, DONE-WHEN)
Roles: text-only reviewers. Neither can run code, edit files, place bets or call any betting/odds API.
Repo rules (CLAUDE.md): smallest fix for a measured problem, test, move on; no scope growth, no extra audits. When a measurement returns nothing, suspect the reader/tool first and check its own counters. Bound claims: n small = "not detected", not "none". Verifying arithmetic is not verifying intent: on live-money behaviour state the mechanics and ask the owner.
Public repo: no balances, stakes, dollar figures, keys, account data. Counts only. Secrets live only in GitHub Secrets.
Reference files: CLAUDE.md, CLV_STANDARD.md, REGISTRY.md, README.md. Use only those the issue's FILES line names.
PROHIBITED: any change to betting execution, pricing, sizing, routing or strategy eligibility; placing orders; OddsPapi or other paid calls; repo variables or secrets; starting a second task; proposing live-betting changes (owner approval only).
COST LIMITS: max 6 messages total, under 120 words each, no repeating the other side, no restating this context.
COMPLETE WHEN: the issue's DONE-WHEN is met or cannot be met. Then reply "DONE:" plus 2-3 lines of result (findings vs recommendations kept separate). Stop; the owner reviews.
