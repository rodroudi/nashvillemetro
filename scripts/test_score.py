#!/usr/bin/env python3
"""Checks for the Dolly Servitude score. Run: python3 scripts/test_score.py"""
import datetime, json, os, sys
from decimal import Decimal
sys.path.insert(0, os.path.dirname(__file__))
import compute_score as cs

ROOT = os.path.join(os.path.dirname(__file__), "..")
TODAY = datetime.date(2026, 11, 22)
FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok", name)
    else:
        FAILS.append(name + ((" " + detail) if detail else ""))
        print("FAIL", name, detail)


def test_civility():
    terms = ["idiot", "stupid", "fuck"]
    check("clean post", cs.civility_flags("Thanks for coming to the meeting.", terms, 40, 0.7) == [])
    check("insult", "term:idiot" in cs.civility_flags("What an idiot.", terms, 40, 0.7))
    check("word boundary", cs.civility_flags("The classic vote failed.", ["ass"], 40, 0.7) == [])
    check("url ignored", cs.civility_flags("See https://example.com/idiot-guide for the agenda.", terms, 40, 0.7) == [])
    shouting = "THIS IS A LONG SHOUT ABOUT THE BUDGET AND THE VOTE TONIGHT"
    check("shouting", "shouting" in cs.civility_flags(shouting, terms, 40, 0.7))
    check("short caps not shouting", "shouting" not in cs.civility_flags("YES", terms, 40, 0.7))


def test_window_and_cap():
    check("inside window", cs.in_window(datetime.date(2026, 11, 1), TODAY, 90))
    check("outside window", not cs.in_window(datetime.date(2026, 1, 1), TODAY, 90))
    check("future ignored", not cs.in_window(datetime.date(2026, 12, 1), TODAY, 90))
    check("cap", cs.cap_points(8, 8) == Decimal(100))
    check("over cap", cs.cap_points(20, 8) == Decimal(100))
    check("half cap", cs.cap_points(4, 8) == Decimal(50))


def test_rounding():
    check("half up integer", int(cs.round_half_up("89.5", 0)) == 90)
    check("half up tenth", cs.round_half_up("94.65", 1) == Decimal("94.7"))
    check("half down not used", int(cs.round_half_up("0.5", 0)) == 1)


def test_renormalize_story():
    included = [
        {"points": 50.0, "weight": 30},
        {"points": 100.0, "weight": 10},
    ]
    score, raw, text = cs.arithmetic(included, 40)
    # 50*30 + 100*10 = 2500; /40 = 62.5 -> 63
    check("renormalize math", score == 63 and raw == 62.5, text)


def test_live_files():
    scores = json.load(open(os.path.join(ROOT, "data", "scores.json"), encoding="utf-8"))
    members = json.load(open(os.path.join(ROOT, "data", "members.json"), encoding="utf-8"))["members"]
    config = json.load(open(os.path.join(ROOT, "data", "score_config.json"), encoding="utf-8"))
    check("all members scored", len(scores["members"]) == len(members) == 41)
    weight = sum(c["weight"] for c in config["components"])
    check("weights sum to 100", weight == 100)
    by = {m["pid"]: m for m in scores["members"]}
    for m in members:
        row = by[m["pid"]]
        check(f"tile data {m['name']}", row["score"] is not None and 0 <= row["score"] <= 100, str(row["score"]))
        included = [c for c in row["components"] if c["status"] == "ok"]
        avail = sum(c["weight"] for c in included)
        check(f"coverage weight {m['name']}", avail == row["coverageWeight"])
        if included:
            again, _, _ = cs.arithmetic(included, avail)
            check(f"arithmetic {m['name']}", again == row["score"], f"{again} vs {row['score']} {row['arithmetic']}")
    terry = by[281]
    check("terry has score", isinstance(terry["score"], int))
    ids = {c["id"]: c for c in terry["components"]}
    check("terry attendance scored", ids["council_attendance"]["status"] == "ok")
    check("terry votes scored", ids["vote_presence"]["status"] == "ok")
    check("terry newsletter scored", ids["newsletter"]["status"] == "ok" and ids["newsletter"]["points"] == 100)
    check("terry posts not scored", ids["online_engagement"]["status"] == "missing")
    check("terry decency not scored", ids["decency"]["status"] == "missing")
    check("terry community missing", ids["community_meetings"]["status"] == "missing")
    check("terry replies missing", ids["constituent_replies"]["status"] == "missing")
    sean = by[209]
    sean_ids = {c["id"]: c for c in sean["components"]}
    check("sean partial posts not scored", sean_ids["online_engagement"]["status"] == "missing")
    sandra = {c["id"]: c for c in by[234]["components"]}
    check("sandra confirmed empty posts score zero", sandra["online_engagement"]["status"] == "ok" and sandra["online_engagement"]["points"] == 0)
    check("sandra decency still missing", sandra["decency"]["status"] == "missing")
    sheri = {c["id"]: c for c in by[284]["components"]}
    check("govdelivery newsletter is zero", sheri["newsletter"]["status"] == "ok" and sheri["newsletter"]["points"] == 0)
    ginny = {c["id"]: c for c in by[220]["components"]}
    check("protected account is missing not zero", ginny["online_engagement"]["status"] == "missing")
    # every member file exists and index matches
    index = json.load(open(os.path.join(ROOT, "data", "tweets", "index.json"), encoding="utf-8"))
    for m in members:
        slug = cs.slugify(m["name"])
        path = os.path.join(ROOT, "data", "tweets", slug + ".json")
        check(f"tweet file {slug}", os.path.exists(path))
        doc = json.load(open(path, encoding="utf-8"))
        check(f"schema {slug}", doc["pid"] == m["pid"] and "fetchStatus" in doc and isinstance(doc["posts"], list))
        check(f"index {slug}", index["byPid"][str(m["pid"])]["fetchStatus"] == doc["fetchStatus"])
    pop = {p["id"]: p for p in scores["population"]}
    check("attendance populated for all", pop["council_attendance"]["scoredMembers"] == 41)
    check("community populated for none", pop["community_meetings"]["scoredMembers"] == 0)
    check("replies populated for none", pop["constituent_replies"]["scoredMembers"] == 0)
    check("decency populated for none yet", pop["decency"]["scoredMembers"] == 0)


if __name__ == "__main__":
    test_civility()
    test_window_and_cap()
    test_rounding()
    test_renormalize_story()
    if os.path.exists(os.path.join(ROOT, "data", "scores.json")):
        test_live_files()
    else:
        print("skip live files (scores.json not built)")
    if FAILS:
        print("\n%d failed" % len(FAILS))
        for f in FAILS:
            print(" -", f)
        sys.exit(1)
    print("\nall checks passed")
