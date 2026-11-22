#!/usr/bin/env python3
"""Compute the Dolly Servitude score from the config and the data files.

Reads:
  data/score_config.json
  data/members.json
  data/votes.json
  data/tweets/<slug>.json
  data/newsletters/<slug>.json          (optional)
  data/community_meetings/<slug>.json   (optional)
  data/constituent_replies/<slug>.json  (optional)

Writes:
  data/scores.json
  data/tweets/index.json

The window for any "last N days" rule ends on the UTC date of this run.
Run from the repo root: python3 scripts/compute_score.py
"""
import datetime, json, os, re, unicodedata
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
TOKEN = re.compile(r"[a-z0-9']+")
URL = re.compile(r"https?://\S+")


def round_half_up(value, places):
    quant = Decimal("1") if places == 0 else Decimal("0.1") ** places
    return Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)


def slugify(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_day(value):
    if not value:
        return None
    text = str(value)[:10]
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def in_window(day, today, days):
    if day is None:
        return False
    return (today - day).days <= days and (today - day).days >= 0


def cap_points(count, full):
    if full <= 0:
        return Decimal(0)
    return min(Decimal(100), Decimal(100) * Decimal(count) / Decimal(full))


def civility_flags(text, terms, min_letters, caps_ratio):
    """Return a list of short reasons. Empty list means the post is unflagged."""
    if not text or not str(text).strip():
        return ["empty"]
    raw = URL.sub(" ", str(text))
    tokens = set(TOKEN.findall(raw.lower()))
    hits = sorted(tokens & set(terms))
    reasons = [f"term:{t}" for t in hits]
    letters = [c for c in raw if c.isalpha()]
    if len(letters) >= min_letters:
        upper = sum(1 for c in letters if c.isupper())
        if upper / len(letters) >= caps_ratio:
            reasons.append("shouting")
    return reasons


def component(cid, name, weight, status, points=None, raw_input="", detail="", sources=None, as_of=None):
    return {
        "id": cid,
        "name": name,
        "weight": weight,
        "status": status,
        "points": float(points) if points is not None else None,
        "input": raw_input,
        "detail": detail,
        "asOf": as_of,
        "sources": sources or [],
    }


def weight_of(config, cid):
    for c in config["components"]:
        if c["id"] == cid:
            return c["weight"], c["name"], c.get("sources") or []
    raise KeyError(cid)


def src(config, cid, extra=None):
    _, _, sources = weight_of(config, cid)
    out = [dict(s) for s in sources if s.get("url") or s.get("title")]
    if extra:
        out.extend(extra)
    return out


def score_attendance(member, config, as_of):
    weight, name, _ = weight_of(config, "council_attendance")
    att = member.get("attendance") or {}
    total = att.get("total") or 0
    attended = att.get("attended") or 0
    if total <= 0:
        return component("council_attendance", name, weight, "missing",
                         raw_input="no meetings on file",
                         detail="No meetings were counted for this member, so attendance is left out rather than scored as zero.",
                         sources=src(config, "council_attendance"), as_of=as_of)
    points = round_half_up(Decimal(100) * Decimal(attended) / Decimal(total), 1)
    return component("council_attendance", name, weight, "ok", points,
                     raw_input=f"{attended} of {total} meetings",
                     detail="Present at the opening roll call, or absent then but recorded on a vote later that night.",
                     sources=src(config, "council_attendance"), as_of=as_of)


def score_votes(member, config, votes, as_of):
    weight, name, _ = weight_of(config, "vote_presence")
    idx = {v["pid"]: i for i, v in enumerate(votes["voters"])}
    i = idx.get(member["pid"])
    if i is None:
        return component("vote_presence", name, weight, "missing",
                         raw_input="no recorded votes",
                         detail="This member is not in the roll-call file.",
                         sources=src(config, "vote_presence"), as_of=as_of)
    n = absent = 0
    for it in votes["items"]:
        code = it["v"][i]
        if code == "-":
            continue
        n += 1
        if code == "X":
            absent += 1
    if n == 0:
        return component("vote_presence", name, weight, "missing",
                         raw_input="no recorded votes",
                         detail="No recorded roll-call vote lists this member as seated.",
                         sources=src(config, "vote_presence"), as_of=as_of)
    points = round_half_up(Decimal(100) * Decimal(n - absent) / Decimal(n), 1)
    return component("vote_presence", name, weight, "ok", points,
                     raw_input=f"{n - absent} present out of {n} recorded votes; {absent} marked absent",
                     detail="Yes, no, abstain, present-not-voting, and recusal count as present. Absent is the only miss. Not-seated items are ignored.",
                     sources=src(config, "vote_presence"), as_of=votes.get("range", ["", ""])[1] or as_of)


def score_newsletter(member, config, today, slug):
    weight, name, _ = weight_of(config, "newsletter")
    params = config["parameters"]
    path = os.path.join(DATA, "newsletters", slug + ".json")
    base_sources = src(config, "newsletter")
    if os.path.exists(path):
        doc = load(path)
        issues = doc.get("issues") or []
        window = params["newsletterLookbackDays"]
        counted = []
        for issue in issues:
            day = parse_day(issue.get("date"))
            if in_window(day, today, window):
                counted.append(issue)
        points = round_half_up(cap_points(len(counted), params["newsletterFullCredit"]), 1)
        link = None
        if counted and counted[0].get("url"):
            link = [{"title": counted[0].get("title") or "Latest issue in the window", "url": counted[0]["url"]}]
        return component("newsletter", name, weight, "ok", points,
                         raw_input=f"{len(counted)} issues in the last {window} days",
                         detail="Counted from data/newsletters/%s.json. Full credit is %s issues in the window." % (slug, params["newsletterFullCredit"]),
                         sources=base_sources + (link or []), as_of=doc.get("asOf"))
    nl = member.get("newsletter") or {}
    url = (nl.get("url") or "").strip()
    label = nl.get("label") or ""
    excluded = any(url.startswith(p) for p in params["newsletterExcludeUrlPrefixes"])
    if url and not excluded:
        return component("newsletter", name, weight, "ok", Decimal("100.0"),
                         raw_input=f"member newsletter on file: {label or url}",
                         detail="Presence only. How often it is sent is not in this file. A data/newsletters/%s.json issue list would replace this binary score." % slug,
                         sources=base_sources + [{"title": label or "Newsletter", "url": url}],
                         as_of=config.get("checked"))
    if url and excluded:
        return component("newsletter", name, weight, "ok", Decimal("0.0"),
                         raw_input="link on file is the county-wide Metro GovDelivery form, not a member newsletter",
                         detail="That URL is excluded by newsletterExcludeUrlPrefixes.",
                         sources=base_sources + [{"title": label or "Shared Metro signup", "url": url}],
                         as_of=config.get("checked"))
    return component("newsletter", name, weight, "ok", Decimal("0.0"),
                     raw_input="no member newsletter link on file",
                     detail="The hand check recorded no newsletter. That is a zero, not a missing component.",
                     sources=base_sources, as_of=config.get("checked"))


def load_tweets(slug):
    path = os.path.join(DATA, "tweets", slug + ".json")
    if not os.path.exists(path):
        return None, path
    return load(path), path


def posts_in_window(doc, today, days):
    kept = []
    undated = 0
    for post in doc.get("posts") or []:
        day = parse_day(post.get("createdAt"))
        if day is None:
            undated += 1
            continue
        if in_window(day, today, days):
            kept.append(post)
    return kept, undated


def score_online(doc, config, today):
    weight, name, _ = weight_of(config, "online_engagement")
    params = config["parameters"]
    window = params["onlineLookbackDays"]
    full = params["onlineFullCreditPosts"]
    sources = src(config, "online_engagement")
    if doc and doc.get("profileUrl"):
        sources = sources + [{"title": "@" + (doc.get("handle") or ""), "url": doc["profileUrl"]}]
    if not doc:
        return component("online_engagement", name, weight, "missing",
                         raw_input="no post file",
                         detail="data/tweets/<slug>.json is missing.",
                         sources=sources)
    status = doc.get("fetchStatus")
    handle = doc.get("handle")
    if not handle or status == "no_handle":
        note = (doc.get("handleCheck") or {}).get("note") or "No verified public X account is on file."
        return component("online_engagement", name, weight, "missing",
                         raw_input="no verified handle",
                         detail=note, sources=sources, as_of=(doc.get("handleCheck") or {}).get("checked"))
    if status == "protected":
        return component("online_engagement", name, weight, "missing",
                         raw_input=f"@{handle} is protected",
                         detail="Posts cannot be read, so engagement is left out rather than scored as zero.",
                         sources=sources, as_of=doc.get("fetchedAt"))
    if status != "ok":
        return component("online_engagement", name, weight, "missing",
                         raw_input=f"@{handle}: fetchStatus is {status or 'unset'}",
                         detail=doc.get("fetchNote") or "Posts are not a complete lookback, so they are shown on the card but not scored.",
                         sources=sources, as_of=doc.get("fetchedAt"))
    kept, undated = posts_in_window(doc, today, window)
    truncated = bool(doc.get("truncated"))
    if truncated and len(kept) < full:
        return component("online_engagement", name, weight, "missing",
                         raw_input=f"at least {len(kept)} posts in {window} days, timeline truncated",
                         detail="The file does not cover the whole window and the count is still under full credit, so scoring it would undercount.",
                         sources=sources, as_of=doc.get("fetchedAt"))
    points = round_half_up(cap_points(len(kept), full), 1)
    detail = f"Full credit is {full} posts in {window} days, counting replies and reposts."
    if truncated:
        detail += " The timeline was truncated, but the count already reaches full credit."
    if undated:
        detail += f" {undated} posts had no date and were not counted."
    return component("online_engagement", name, weight, "ok", points,
                     raw_input=f"{len(kept)} posts in the last {window} days",
                     detail=detail, sources=sources, as_of=doc.get("fetchedAt"))


def score_decency(doc, config, today):
    weight, name, _ = weight_of(config, "decency")
    params = config["parameters"]
    terms = [t.lower() for t in config.get("civilityTerms") or []]
    window = params["onlineLookbackDays"]
    minimum = params["decencyMinPosts"]
    sources = src(config, "decency")
    if doc and doc.get("profileUrl"):
        sources = sources + [{"title": "@" + (doc.get("handle") or ""), "url": doc["profileUrl"]}]
    if not doc or not doc.get("handle") or doc.get("fetchStatus") in (None, "no_handle", "pending", "partial", "protected", "error"):
        state = (doc or {}).get("fetchStatus") or "no file"
        return component("decency", name, weight, "missing",
                         raw_input=f"no complete post text ({state})",
                         detail="Tone is scored only from a complete post file (fetchStatus ok), using the member's own words.",
                         sources=sources, as_of=(doc or {}).get("fetchedAt"))
    kept, _ = posts_in_window(doc, today, window)
    own = [p for p in kept if not p.get("isRetweet") and str(p.get("text") or "").strip()]
    if len(own) < minimum:
        return component("decency", name, weight, "missing",
                         raw_input=f"{len(own)} of the member's posts with text in the window (need {minimum})",
                         detail="Too little text to score tone. The component is left out, not scored as perfect or as zero.",
                         sources=sources, as_of=doc.get("fetchedAt"))
    flagged = []
    for post in own:
        reasons = civility_flags(post.get("text"), terms, params["shoutingMinLetters"], params["shoutingCapsRatio"])
        reasons = [r for r in reasons if r != "empty"]
        if reasons:
            flagged.append({"url": post.get("url"), "reasons": reasons})
    clean = len(own) - len(flagged)
    points = round_half_up(Decimal(100) * Decimal(clean) / Decimal(len(own)), 1)
    detail = f"{clean} of {len(own)} posts had no list match and were not shouting."
    if doc.get("truncated"):
        detail += " The file may not hold the whole window; this is the posts it does hold."
    if flagged:
        detail += " Flagged: " + "; ".join(
            (f.get("url") or "post") + " (" + ", ".join(f["reasons"]) + ")" for f in flagged[:5]
        )
    return component("decency", name, weight, "ok", points,
                     raw_input=f"{clean} unflagged of {len(own)} scored posts",
                     detail=detail, sources=sources, as_of=doc.get("fetchedAt"))


def score_counted_file(cid, folder, list_key, date_key, full_key, window_key, noun, config, today, slug):
    weight, name, _ = weight_of(config, cid)
    params = config["parameters"]
    path = os.path.join(DATA, folder, slug + ".json")
    if not os.path.exists(path):
        return component(cid, name, weight, "missing",
                         raw_input="no data file",
                         detail=f"{folder}/<slug>.json is not in the repo, so this component is left out.",
                         sources=src(config, cid))
    doc = load(path)
    rows = doc.get(list_key) or []
    window = params[window_key]
    counted = 0
    for row in rows:
        if list_key == "meetings" and row.get("attended") is False:
            continue
        if in_window(parse_day(row.get(date_key)), today, window):
            counted += 1
    points = round_half_up(cap_points(counted, params[full_key]), 1)
    return component(cid, name, weight, "ok", points,
                     raw_input=f"{counted} {noun} in the last {window} days",
                     detail=f"Full credit is {params[full_key]} in the window. Read from {folder}/{slug}.json.",
                     sources=src(config, cid), as_of=doc.get("asOf"))


def arithmetic(included, available):
    parts = [f"{c['points']:.1f}×{c['weight']}" for c in included]
    total = sum(Decimal(str(c["points"])) * Decimal(c["weight"]) for c in included)
    raw = total / Decimal(available)
    score = int(round_half_up(raw, 0))
    shown = " + ".join(parts) + f" = {total}"
    shown += f"; ÷ {available} = {raw.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}; rounds to {score}"
    return score, float(raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), shown


def score_member(member, config, votes, today, vote_asof):
    slug = slugify(member["name"])
    doc, _ = load_tweets(slug)
    parts = [
        score_attendance(member, config, vote_asof),
        score_votes(member, config, votes, vote_asof),
        score_newsletter(member, config, today, slug),
        score_online(doc, config, today),
        score_decency(doc, config, today),
        score_counted_file("community_meetings", "community_meetings", "meetings", "date",
                           "communityFullCredit", "communityLookbackDays", "meetings attended",
                           config, today, slug),
        score_counted_file("constituent_replies", "constituent_replies", "replies", "date",
                           "repliesFullCredit", "repliesLookbackDays", "replies",
                           config, today, slug),
    ]
    total_weight = sum(c["weight"] for c in config["components"])
    included = [c for c in parts if c["status"] == "ok" and c["points"] is not None]
    available = sum(c["weight"] for c in included)
    if available <= 0:
        score = None
        raw = None
        text = "No component had data, so there is no score."
    else:
        score, raw, text = arithmetic(included, available)
        score = max(0, min(100, score))
    coverage_weight = available
    return {
        "pid": member["pid"],
        "slug": slug,
        "name": member["name"],
        "seat": "Vice Mayor" if member.get("vm") else ("At-large" if not member.get("district") else f"District {member['district']}"),
        "score": score,
        "raw": raw,
        "coverageWeight": coverage_weight,
        "totalWeight": total_weight,
        "coverage": float((Decimal(coverage_weight) / Decimal(total_weight)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)) if total_weight else 0,
        "arithmetic": text,
        "handle": (doc or {}).get("handle"),
        "components": parts,
    }


def population(scored, config):
    out = []
    for comp in config["components"]:
        rows = [c for m in scored for c in m["components"] if c["id"] == comp["id"]]
        ok = sum(1 for c in rows if c["status"] == "ok")
        out.append({
            "id": comp["id"],
            "name": comp["name"],
            "weight": comp["weight"],
            "scoredMembers": ok,
            "missingMembers": len(rows) - ok,
        })
    return out


def main():
    config = load(os.path.join(DATA, "score_config.json"))
    members = load(os.path.join(DATA, "members.json"))["members"]
    votes = load(os.path.join(DATA, "votes.json"))
    today = datetime.datetime.now(datetime.timezone.utc).date()
    vote_asof = votes.get("asOf")
    scored = [score_member(m, config, votes, today, vote_asof) for m in members]
    index = {"byPid": {}}
    for m in members:
        slug = slugify(m["name"])
        doc, path = load_tweets(slug)
        if doc:
            index["byPid"][str(m["pid"])] = doc
    out = {
        "version": config["version"],
        "name": config["name"],
        "computedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "windowEnds": today.isoformat(),
        "inputsAsOf": {"votes": vote_asof, "handlesChecked": config.get("checked")},
        "parameters": config["parameters"],
        "rounding": config["rounding"],
        "missingData": config["missingData"],
        "population": population(scored, config),
        "members": scored,
    }
    with open(os.path.join(DATA, "scores.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.makedirs(os.path.join(DATA, "tweets"), exist_ok=True)
    with open(os.path.join(DATA, "tweets", "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"scored {len(scored)} members, window ends {today.isoformat()}")
    for row in sorted(scored, key=lambda r: (-1 if r["score"] is None else -r["score"], r["name"])):
        print(f"{row['score'] if row['score'] is not None else 'NA':>4}  cov {row['coverage']:.0%}  {row['name']}")


if __name__ == "__main__":
    main()
