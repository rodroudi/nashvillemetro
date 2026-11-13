#!/usr/bin/env python3
"""Build data/votes.json and data/members.json from data/raw_votes.json + data/districts.geojson."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
from members_seed import MEMBERS, EMAILS, AT_LARGE_PAGE
D = os.path.join(os.path.dirname(__file__), "..", "data")
raw = json.load(open(os.path.join(D, "raw_votes.json")))
def skip_reason(m):
    c = (m.get("comment") or "").lower()
    if m.get("agendaStatus") == "Hidden" or "test" in c: return "test"
    if "cancel" in c: return "cancelled"
    if "state of metro" in c: return "ceremonial"
    return None
SKIP = {m["id"]: skip_reason(m) for m in raw["meta"]["meetings"] if skip_reason(m)}
raw["meta"]["meetings"] = [m for m in raw["meta"]["meetings"] if m["id"] not in SKIP]
raw["items"] = [i for i in raw["items"] if i["eventId"] not in SKIP]
geo = json.load(open(os.path.join(D, "districts.geojson")))
gis = {f["properties"]["DISTRICT"]: f["properties"] for f in geo["features"]}

CODE = {"Aye": "Y", "Yes": "Y", "Yea": "Y", "Nay": "N", "No": "N", "Abstain": "A", "Abstained": "A",
        "Absent": "X", "Excused": "X", "Not Present": "X", "Non-voting": "P", "Present": "P", "Recused": "R", "Recusal": "R"}
valcount = collections.Counter(v["value"] for it in raw["items"] for v in it["votes"])
unknown = [k for k in valcount if k not in CODE]

from bios_seed import BIOS, EMAIL_OVERRIDE
import re, unicodedata
OFFICE = "Historic Metro Courthouse, 1 Public Square, Suite 204, Nashville, TN 37201"
AL_PHONE = {1: "615-432-1341", 2: "615-432-1342", 3: "615-432-1343", 4: "615-432-1344", 5: "615-432-1345"}
def slug(n):
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
def photo(n):
    p = f"photos/{slug(n)}.jpg"
    return p if os.path.exists(os.path.join(D, "..", p)) else None
members = []
for seat, name, pid, area, roles, nl in MEMBERS:
    if seat == "At-large":
        no = int(AT_LARGE_PAGE[pid].split("-")[-1])
        key, email, phone, dist = f"AL{no}", EMAILS[pid], AL_PHONE[no], None
        page = f"https://www.nashville.gov/departments/council/districts/{AT_LARGE_PAGE[pid]}"
    else:
        no = None; g = gis[seat]; key, email, phone, dist = seat, EMAIL_OVERRIDE.get(seat, g["Email"]), g["BusinessPhone"], seat
        page = f"https://www.nashville.gov/departments/council/districts/district-{seat}"
    bio, comm = BIOS.get(key, ("", []))
    members.append({"pid": pid, "name": name, "district": dist, "seatNo": no, "area": area, "email": email, "phone": phone,
                    "office": OFFICE, "page": page, "photo": photo(name), "bio": bio, "committees": comm,
                    "newsletter": {"label": nl[0], "url": nl[1]} if nl else None})
vb, vc = BIOS["VM"]
members.append({"pid": 238, "name": "Angie Henderson", "district": None, "seatNo": None, "area": "Presides over the council",
                "email": "Angie.Henderson@nashville.gov", "phone": "615-880-3357", "office": OFFICE,
                "page": "https://www.nashville.gov/departments/council/districts/vice-mayor", "photo": photo("Angie Henderson"),
                "bio": vb, "committees": vc, "newsletter": None, "vm": True})
mby = {m["pid"]: m for m in members}

# voters: everyone who appears in any vote
names = {}
for it in raw["items"]:
    for v in it["votes"]:
        names[v["pid"]] = v["name"]
def seat_of(pid):
    m = mby.get(pid)
    if not m: return "Former member"
    if m.get("vm"): return "Vice Mayor"
    return f"D{m['district']}" if m["district"] else "At-large"
def sortkey(pid):
    m = mby.get(pid)
    if not m: return 200
    if m.get("vm"): return 100
    return m["district"] or 50
voters = sorted(({"pid": p, "name": mby[p]["name"] if p in mby else n, "seat": seat_of(p), "sort": sortkey(p)} for p, n in names.items()), key=lambda v: (v["sort"], v["name"]))
idx = {v["pid"]: i for i, v in enumerate(voters)}

items = []
dupes = 0
seen = set()
for it in sorted(raw["items"], key=lambda x: (x["date"], x["seq"] or 0, x["itemId"])):
    if it["itemId"] in seen: dupes += 1; continue
    seen.add(it["itemId"])
    vs = ["-"] * len(voters)
    for v in it["votes"]:
        vs[idx[v["pid"]]] = CODE.get(v["value"], "O")
    y, n = vs.count("Y"), vs.count("N")
    maj = "Y" if y > n else ("N" if n > y else None)
    url = f"https://nashville.legistar.com/gateway.aspx?M=L&ID={it['matterId']}" if it["matterId"] else it["meetingUrl"]
    items.append({"k": it["itemId"], "d": it["date"], "f": it["file"] or "", "t": " ".join((it["title"] or "").split()),
                  "ty": it["matterType"] or "", "a": it["action"] or "", "o": it["passed"] or "", "maj": maj,
                  "url": url, "mu": it["meetingUrl"], "vid": it["video"] or "", "v": "".join(vs)})


# ---------- attendance ----------
ATT_PRESENT = {"Present", "Late", "Arrived Late", "Present - Late", "Tardy"}
ATT_ABSENT = {"Absent", "Excused", "Absent - Excused", "Not Present"}
attraw = [m for m in json.load(open(os.path.join(D, "raw_attendance.json"))) if m["eventId"] not in SKIP]
rcvals = collections.Counter(e["value"] for m in attraw for rc in m["rollcalls"] for e in rc["entries"])
by_event_votes = collections.defaultdict(lambda: collections.defaultdict(list))
for it in raw["items"]:
    for v in it["votes"]:
        by_event_votes[it["eventId"]][v["pid"]].append(CODE.get(v["value"], "O"))
att = collections.defaultdict(lambda: {"attended": 0, "total": 0, "missed": [], "byRollCall": 0, "byVotes": 0})
undetermined = []
for mtg in sorted(attraw, key=lambda x: x["date"]):
    if mtg["date"] > raw["meta"]["fetchedAt"][:10]: continue  # future meeting
    status = {}
    if mtg["rollcalls"]:
        for e in mtg["rollcalls"][0]["entries"]:  # opening roll call
            if e["value"] in ATT_PRESENT: status[e["pid"]] = (True, "rc")
            elif e["value"] in ATT_ABSENT: status[e["pid"]] = (False, "rc")
    # members not on the roll call (or no roll call): fall back to recorded votes that night
    for pid, codes in by_event_votes.get(mtg["eventId"], {}).items():
        if pid in status:
            if not status[pid][0] and any(c in "YNAPR" for c in codes):
                status[pid] = (True, "late")  # absent at roll call, voted later
            continue
        status[pid] = (any(c in "YNAPR" for c in codes), "votes")
    if not status: undetermined.append(mtg["date"]); continue
    for pid, (present, how) in status.items():
        a = att[pid]; a["total"] += 1
        if present: a["attended"] += 1
        else: a["missed"].append({"date": mtg["date"], "url": mtg["url"]})
        if how == "rc" or how == "late": a["byRollCall"] += 1
        else: a["byVotes"] += 1
for m in members:
    m["attendance"] = att.get(m["pid"])
rc_meetings = sum(1 for m in attraw if m["rollcalls"] and m["date"] <= raw["meta"]["fetchedAt"][:10])

meets = raw["meta"]["meetings"]
with_votes = sorted({i["d"] for i in items})
mtg_with = len({it["eventId"] for it in raw["items"]})
no_votes = [m for m in meets if m["id"] not in {it["eventId"] for it in raw["items"]}]
total_votes = sum(len(i["v"]) - i["v"].count("-") for i in items)
asof = raw["meta"]["fetchedAt"].replace("T", " ") + " CT"
pre = [i for i in items if i["d"] < "2026-09-01"]; post = [i for i in items if i["d"] >= "2026-09-01"]
pre_div = sum(1 for i in pre if "N" in i["v"])
cov = (f"Through August 2026, Legistar lists individual votes for only a few items per meeting, mostly contested ones: {len(pre):,} items, {pre_div:,} of which had at least one no vote. Starting September 2026, Legistar lists individual votes for nearly every item ({len(post):,} items in {len({i['d'] for i in post})} meetings), including routine ones that passed unanimously. "
       "So for 2023 to mid-2026 this page is a strong record of divided votes but not of every routine vote, and per-member vote counts lean toward recent months. Attendance uses roll calls, so it is not affected.")
past = [m for m in meets if m["date"] <= raw["meta"]["fetchedAt"][:10]]
notes = f"""
<p><b>What is here.</b> Every agenda item at a full Metro Council meeting where Metro's official record lists how each member voted. We scanned {raw['meta']['agendaItemsScanned']:,} agenda items from {len(past)} full council meetings in Legistar dated {past[0]['date']} to {past[-1]['date']}. {len(items):,} items have an individual vote record, adding up to {total_votes:,} individual votes from {mtg_with} meetings ({with_votes[0]} to {with_votes[-1]}). Items decided by voice vote, on consent without a recorded tally, deferred, withdrawn, or referred without a vote have no individual record and are not listed. Nothing on this page is estimated or filled in.</p>
<p><b>Important coverage note.</b> {cov}</p>
<p><b>Attendance method.</b> For each full council meeting we use the opening roll call recorded in Legistar ({rc_meetings} of {len(past)} meetings have one). A member marked Present counts as attending. A member marked Absent at roll call who then cast a recorded vote that night counts as attending, since they arrived late. For meetings with no recorded roll call, a member counts as attending if they cast at least one recorded vote (yes, no, abstain, present, or recused) and as missing it if every recorded vote lists them absent. Test entries, a cancelled meeting, and State of Metro addresses are not counted. Meetings with neither a roll call nor any recorded votes are also left out of every member's total{(' (' + ', '.join(undetermined) + ')') if undetermined else ''}. Each member's total only counts meetings held while they were seated. "Absent for votes" is a separate count: a member can attend a meeting but be listed absent on some votes if they stepped out or did not vote.</p>
<p><b>Other definitions.</b> "With the majority" is the share of a member's yes and no votes that matched the side with more votes on that item. "Present, not voting" is mostly the Vice Mayor, who presides and votes only to break a tie. Former members who voted earlier in the term appear in the full roll calls as "Former member."</p>
<p><b>Known gaps.</b> Legistar has no full council meetings for September 2023, the first month of this term, so those meetings are not included. Consent agenda items are often adopted together in one vote, which the record may repeat under each item. Committee votes are not included, only full council meetings. Committee lists come from each member's nashville.gov page and may lag current assignments.</p>
<p><b>What this page cannot tell you.</b> Why anyone voted the way they did. For that, open the meeting page linked from each item for the agenda, minutes and video, watch the <a href="https://www.youtube.com/channel/UCKpWDnPeJ9IQ9Sx7AfBORhg">Metro Nashville Network</a> recordings, or read the member's newsletter.</p>
<p><b>Sources.</b> Votes and attendance: Metro's public Legistar records (<a href="https://nashville.legistar.com/">nashville.legistar.com</a>, read through the public API at webapi.legistar.com/v1/nashville). District lines: the <a href="https://maps.nashville.gov/arcgis/rest/services/Elections/PoliticalDistricts/MapServer/0">Metro GIS Council Districts layer</a>. Photos, biographies, phone numbers and committee lists: each member's page on <a href="https://www.nashville.gov/departments/council/districts">nashville.gov</a>. Newsletter links were checked by hand. Archive links go to <a href="https://www.nashvillenewsletters.org/">Nashville Newsletters</a>. To cross-check, see the <a href="https://pamphleteer.co/council">Nashville Pamphleteer council tracker</a> and <a href="https://metrominutes.org/">Metro Minutes</a>.</p>
<p><b>Refresh.</b> Run <code>python3 scripts/refresh_data.py</code>, <code>python3 scripts/refresh_attendance.py</code>, then <code>python3 scripts/build_data.py</code>.</p>
"""
out = {"asOf": asof, "since": raw["meta"]["since"], "range": [with_votes[0], with_votes[-1]], "meetingsWithVotes": mtg_with,
       "meetingsScanned": len(meets), "totalVotes": total_votes, "voters": voters, "items": items, "notesHtml": notes,
       "meetingsWithoutVotes": [m["date"] for m in no_votes],
       "attendance": {"first": meets[0]["date"], "rollCallMeetings": rc_meetings, "undetermined": undetermined, "values": dict(rcvals)}}
json.dump(out, open(os.path.join(D, "votes.json"), "w"), separators=(",", ":"))
json.dump({"members": members}, open(os.path.join(D, "members.json"), "w"), indent=1, ensure_ascii=False)
print("skipped", collections.Counter(SKIP.values()))
print("values:", dict(valcount), "unknown:", unknown, "dupes:", dupes)
print("items", len(items), "votes", total_votes, "range", with_votes[0], with_votes[-1], "meetings w/ votes", mtg_with, "of", len(meets))
print("voters", len(voters), [v["name"] for v in voters if v["seat"] == "Former member"])
print("rollcall values", dict(rcvals), "rc meetings", rc_meetings, "undetermined", undetermined)
print("meetings without votes:", [m["date"] for m in no_votes])
