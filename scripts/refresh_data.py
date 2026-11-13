#!/usr/bin/env python3
"""Refresh roll-call vote data for the Metro Nashville Council from the public Legistar API.

Usage: python3 scripts/refresh_data.py [--since 2023-09-01]
Writes data/raw_votes.json (items + individual votes). Then run scripts/build_data.py.
No API key needed. Only items with recorded individual votes are kept; voice votes have none.
"""
import json, sys, time, urllib.request, urllib.parse, concurrent.futures as cf, os, datetime

B = "https://webapi.legistar.com/v1/nashville"
SINCE = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "2023-09-01"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "raw_votes.json")

def get(path, tries=5):
    url = B + path
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))

def main():
    flt = urllib.parse.quote(f"EventDate ge datetime'{SINCE}' and EventBodyName eq 'Metropolitan Council'")
    events = get(f"/events?$filter={flt}&$orderby=EventDate")
    print(len(events), "council meetings since", SINCE, file=sys.stderr)
    with cf.ThreadPoolExecutor(24) as ex:
        itemlists = list(ex.map(lambda e: get(f"/events/{e['EventId']}/eventitems?AgendaNote=0&MinutesNote=0&Attachments=0"), events))
    pairs = [(e, it) for e, items in zip(events, itemlists) for it in items]
    print(len(pairs), "agenda items; fetching votes", file=sys.stderr)
    def fv(p):
        return p, get(f"/eventitems/{p[1]['EventItemId']}/votes")
    out = []
    done = 0
    with cf.ThreadPoolExecutor(32) as ex:
        for (e, it), votes in ex.map(fv, pairs):
            done += 1
            if done % 1000 == 0:
                print(done, file=sys.stderr)
            if not votes:
                continue
            out.append({
                "eventId": e["EventId"], "date": e["EventDate"][:10],
                "meetingUrl": e.get("EventInSiteURL"), "video": e.get("EventVideoPath"),
                "itemId": it["EventItemId"], "seq": it.get("EventItemMinutesSequence") or it.get("EventItemAgendaSequence"),
                "file": it.get("EventItemMatterFile"), "matterId": it.get("EventItemMatterId"),
                "matterType": it.get("EventItemMatterType"), "matterStatus": it.get("EventItemMatterStatus"),
                "title": (it.get("EventItemTitle") or "").strip(),
                "action": it.get("EventItemActionName"), "actionText": it.get("EventItemActionText"),
                "passed": it.get("EventItemPassedFlagName"), "tally": it.get("EventItemTally"),
                "votes": [{"pid": v["VotePersonId"], "name": v["VotePersonName"], "value": v["VoteValueName"]} for v in votes],
            })
    meta = {"fetchedAt": datetime.datetime.now().isoformat(timespec="minutes"), "since": SINCE,
            "meetings": [{"id": e["EventId"], "date": e["EventDate"][:10], "url": e.get("EventInSiteURL"),
                          "video": e.get("EventVideoPath"), "minutes": e.get("EventMinutesStatusName"),
                          "agendaStatus": e.get("EventAgendaStatusName"), "comment": e.get("EventComment"), "time": e.get("EventTime")} for e in events],
            "agendaItemsScanned": len(pairs)}
    json.dump({"meta": meta, "items": out}, open(OUT, "w"))
    print(len(out), "items with individual votes written to", OUT, file=sys.stderr)

if __name__ == "__main__":
    main()
