#!/usr/bin/env python3
"""Every workflow file must parse the way GitHub Actions parses it.

Nov 23: an edit added a second `env:` block to a step that already had one. PyYAML's SafeLoader
keeps the LAST duplicate key and returns a dict, so a check that "the YAML parses" passed - and
Actions refused the file with "'env' is already defined". The x2-tag workflow is on a schedule, so
it was broken for every run until it was noticed. A loader that tolerates what the real parser
rejects is not a check.
"""
import glob

import yaml

P, F = [], []
def ok(label, cond, got=""):
    (P if cond else F).append(label)
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond else f"   got: {got}"))


class Strict(yaml.SafeLoader):
    pass


def no_dupes(loader, node, deep=False):
    seen = set()
    for k, _v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            raise ValueError(f"duplicate key {key!r} on line {k.start_mark.line + 1}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_dupes)

files = sorted(glob.glob(".github/workflows/*.yml") + glob.glob(".github/workflows/*.yaml"))
ok("there are workflow files to check", len(files) > 0, str(len(files)))
for f in files:
    try:
        d = yaml.load(open(f, encoding="utf-8"), Strict)
        bad = ""
    except Exception as e:
        d, bad = None, str(e)[:120]
    ok(f"{f.split('/')[-1]} parses with no duplicate key", bad == "", bad)
    if d:
        ok(f"{f.split('/')[-1]} has a trigger and at least one job",
           bool(d.get("on") or d.get(True)) and bool(d.get("jobs")))

def _catch(text):
    try:
        yaml.load(text, Strict)
        return None
    except Exception as e:
        return str(e)


ok("the loader catches a duplicate key that SafeLoader would swallow",
   _catch("a:\n  b: 1\n  b: 2\n") is not None
   and yaml.safe_load("a:\n  b: 1\n  b: 2\n") == {"a": {"b": 2}})

print(f"\n{len(P)} passed, {len(F)} failed")
raise SystemExit(1 if F else 0)
