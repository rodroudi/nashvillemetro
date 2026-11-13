#!/usr/bin/env python3
"""Pull the opening roll call (attendance) for every full council meeting since --since from Legistar.
Writes data/raw_attendance.json. Run before scripts/build_data.py."""
import json, sys, os, urllib.parse, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from refresh_data import get, SINCE
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "raw_attendance.json")
flt = urllib.parse.quote(f"EventDate ge datetime'{SINCE}' and EventBodyName eq 'Metropolitan Council'")
events = get(f"/events?$filter={flt}&$orderby=EventDate")
def one(e):
    items = get(f"/events/{e['EventId']}/eventitems?AgendaNote=0&MinutesNote=0&Attachments=0")
    rcs = [it for it in items if it.get("EventItemRollCallFlag") == 1]
    calls = []
    for it in rcs:
        r = get(f"/eventitems/{it['EventItemId']}/rollcalls")
        if r:
            calls.append({"itemId": it["EventItemId"], "title": it.get("EventItemTitle"),
                          "entries": [{"pid": x["RollCallPersonId"], "name": x["RollCallPersonName"], "value": x["RollCallValueName"]} for x in r]})
    return {"eventId": e["EventId"], "date": e["EventDate"][:10], "url": e.get("EventInSiteURL"), "rollcalls": calls}
with cf.ThreadPoolExecutor(12) as ex:
    res = list(ex.map(one, events))
json.dump(res, open(OUT, "w"))
print(len(res), "meetings;", sum(1 for r in res if r["rollcalls"]), "with a recorded roll call", file=sys.stderr)
