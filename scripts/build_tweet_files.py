#!/usr/bin/env python3
"""Write data/tweets/<slug>.json from the handle check below.

The JSON files are what the site and the scorer read. This script fills a
file only when it is missing, so a later edit to a post file is kept.
Pass --force to overwrite every file from this table.

Handles were checked on 2026-11-22. A handle is listed only when a public
page ties it to that member and the X profile resolved. nashville.gov member
pages link the Council Office account (@NashvilleMCO) and not personal ones.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from compute_score import slugify, DATA

CHECKED = "2026-11-22"

# pid -> record. pid matches data/members.json.
HANDLES = {
    204: {
        "handle": None,
        "handleCheck": {
            "checked": CHECKED,
            "result": "not_found",
            "note": "A social icon in the Nashville Newsletters archive links twitter.com/zulfatsuara. That profile returned not found on this date. The nashville.gov page does not list a personal X account.",
        },
    },
    233: {
        "handle": None,
        "handleCheck": {
            "checked": CHECKED,
            "result": "not_found",
            "note": "Ballotpedia linked https://x.com/DelishiaForNash. That profile returned not found on this date.",
        },
    },
    290: {
        "handle": None,
        "handleCheck": {
            "checked": CHECKED,
            "result": "not_found",
            "note": "quinforcouncil.com lists no X account. A Bluesky account exists and is not used here, because this component is X only.",
        },
    },
    202: {
        "handle": "AllenBurkley",
        "profileName": "Council Member Burkley Allen",
        "bio": "Burkley Allen is a Metro Council Member at-Large. She formerly served as District Council Member for District 18.",
        "handleSource": {
            "title": "Public X profile",
            "url": "https://x.com/AllenBurkley",
            "checked": CHECKED,
            "note": "The profile name and bio identify her as the at-large council member.",
        },
    },
    291: {
        "handle": "Oliviafornash",
        "profileName": "Olivia Hill",
        "bio": "Metro Council At-Large | Metro Council Member at-Large, Navy Vet.",
        "handleSource": {
            "title": "voteoliviahill.com",
            "url": "https://voteoliviahill.com/",
            "checked": CHECKED,
            "note": "The campaign site links https://x.com/Oliviafornash. The profile bio says Metro Council at-large.",
        },
    },
    275: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from her nashville.gov page or newsletter archive."}},
    206: {
        "handle": "toombsfortwo",
        "profileName": "Kyonzte Toombs",
        "bio": "Councilwoman for District 2, Nashville Metro Council",
        "handleSource": {
            "title": "toombsfortwo.com",
            "url": "https://toombsfortwo.com/",
            "checked": CHECKED,
            "note": "Her campaign site links https://x.com/toombsfortwo and the bio names the District 2 seat. Ballotpedia also lists @fly_attorney, which is a second account under her name and is not the one scored.",
        },
    },
    207: {
        "handle": "JGamble4Council",
        "profileName": "Jennifer Gamble",
        "bio": "Lifelong Moderate Democrat",
        "handleSource": {
            "title": "Jennifer Gamble newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/jennifer-gamble",
            "checked": CHECKED,
            "note": "The archive repeats a social link to twitter.com/JGamble4Council. The profile name is Jennifer Gamble.",
        },
    },
    292: {
        "handle": "MikeForTennesee",
        "profileName": "Mike Cortese",
        "bio": "Father, husband, professor, Metro Councilman, and congressional candidate in TN-4.",
        "handleSource": {
            "title": "Ballotpedia page for Mike Cortese",
            "url": "https://ballotpedia.org/Mike_Cortese",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/MikeForTennesee. The handle is spelled that way on the profile. The bio says Metro Councilman.",
        },
    },
    209: {
        "handle": "SeanForFive",
        "profileName": "Sean Parker is FOR Transit",
        "bio": "Councilmember for Nashville's 5th District. Housing, safe streets, and effective services.",
        "handleSource": {
            "title": "seanforfive.com",
            "url": "https://seanforfive.com/",
            "checked": CHECKED,
            "note": "The campaign site and the newsletter archive both link @SeanForFive. The profile bio names District 5.",
        },
        "fetchStatus": "partial",
        "fetchedAt": "2026-11-22T18:40:00Z",
        "fetchNote": "One public post was verified by its status URL on the syndication payload. replyCount is that payload's conversation_count (24) and likeCount is favorite_count (16). Repost and quote counts were not in the payload and are null. The file is not a full lookback, so online engagement and decency are not scored from it.",
        "posts": [
            {
                "id": "2124211124061045000",
                "url": "https://x.com/SeanForFive/status/2124211124061045000",
                "text": "@Steve_sjfsongs Why don’t you ask grok you bluechecked dork",
                "createdAt": "2026-11-21T18:39:32.000Z",
                "replyCount": 24,
                "repostCount": None,
                "likeCount": 16,
                "quoteCount": None,
                "isReply": True,
                "isRetweet": False,
                "lang": "en",
            }
        ],
    },
    276: {
        "handle": "claycapp",
        "profileName": "Clay Capp",
        "bio": "Nashville native, raising two more. Council Member for District 6.",
        "handleSource": {
            "title": "Ballotpedia page for Clay Capp",
            "url": "https://ballotpedia.org/Clay_Capp",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/claycapp. The bio says Council Member for District 6.",
        },
    },
    211: {
        "handle": None,
        "handleCheck": {
            "checked": CHECKED,
            "result": "not_found",
            "note": "A 2020 WTVF article quoted @emilyfor7. That profile did not resolve to a public account on this date, so it is not listed.",
        },
    },
    277: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page."}},
    213: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page or newsletter archive."}},
    278: {
        "handle": "voteJFW",
        "profileName": "Jennifer Frensley Webb",
        "bio": "",
        "handleSource": {
            "title": "Ballotpedia page for Jennifer Frensley Webb",
            "url": "https://ballotpedia.org/Jennifer_Frensley_Webb",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/voteJFW. The profile name is Jennifer Frensley Webb.",
        },
    },
    293: {
        "handle": "jeff_eslick",
        "profileName": "Jeff Eslick",
        "bio": "I am running because District 11 needs a neighbor. Metro Council doesn't need another political activist.",
        "handleSource": {
            "title": "Ballotpedia page for Jeff Eslick",
            "url": "https://ballotpedia.org/Jeff_Eslick",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/jeff_eslick. The bio names District 11.",
        },
    },
    216: {
        "handle": "Erinfor12",
        "profileName": "Erin Evans",
        "bio": "Erin Evans is Metro Nashville Councilmember for District 12 (Hermitage, Tenn)",
        "handleSource": {
            "title": "Erin Evans newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/erin-evans",
            "checked": CHECKED,
            "note": "The archive uses a social icon linking to twitter.com/Erinfor12. The bio names District 12.",
        },
    },
    217: {
        "handle": "Bradford4D13",
        "profileName": "Councilman Russ Bradford",
        "bio": "Metro Council District 13.",
        "handleSource": {
            "title": "Russ Bradford newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/russ-bradford",
            "checked": CHECKED,
            "note": "The archive repeats links to twitter.com/bradford4d13. The bio says Metro Council District 13.",
        },
    },
    279: {
        "handle": "JordanHuffman",
        "profileName": "Councilman Jordan Huffman",
        "bio": "Nashville Metro Council Member (D14).",
        "handleSource": {
            "title": "Jordan Huffman newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/jordan-huffman",
            "checked": CHECKED,
            "note": "The archive links twitter.com/jordanhuffman. The bio says Nashville Metro Council Member (D14).",
        },
    },
    280: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page or newsletter archive."}},
    220: {
        "handle": "GinnyWelsch",
        "profileName": "no pass for fascism",
        "protected": True,
        "bio": "",
        "handleSource": {
            "title": "Ginny Welsch newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/ginny-welsch",
            "checked": CHECKED,
            "note": "The archive and Ballotpedia (https://ballotpedia.org/Ginny_Welsch) link @GinnyWelsch. On this date the profile display name was \"no pass for fascism\" and posts were protected, so no post text was read.",
        },
        "fetchStatus": "protected",
        "fetchedAt": "2026-11-22T00:00:00Z",
        "fetchNote": "The account is protected. Posts were not read. Online engagement and decency are left out of the score rather than treated as zero.",
    },
    281: {
        "handle": "terryvofornash",
        "profileName": "Terry Vo for Nashville",
        "bio": "Inclusion. Integrity. Kindness | District 17 Metropolitan Councilmember",
        "handleSource": {
            "title": "Terry Vo newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/terry-vo",
            "checked": CHECKED,
            "note": "The archive uses a social icon linking to twitter.com/terryvofornash. The bio says District 17 Metropolitan Councilmember.",
        },
    },
    222: {
        "handle": "CashforCouncil",
        "profileName": "TomCashforCouncil",
        "bio": "Lifelong Nashvillian, educator, and Council Member for District 18",
        "handleSource": {
            "title": "votetomcash.com",
            "url": "https://www.votetomcash.com/",
            "checked": CHECKED,
            "note": "The campaign site links https://twitter.com/CashforCouncil. The bio says Council Member for District 18.",
        },
    },
    282: {
        "handle": "JacobKupin4D19",
        "profileName": "Jacob Kupin",
        "bio": "District 19 Councilperson, Passionate Collaborator",
        "handleSource": {
            "title": "jacobkupin.com",
            "url": "https://www.jacobkupin.com/",
            "checked": CHECKED,
            "note": "The campaign site links https://twitter.com/JacobKupin4D19. The bio says District 19 Councilperson.",
        },
    },
    283: {
        "handle": "HortonRollin",
        "profileName": "Rollin Horton",
        "bio": "Nashville Metro Council Member District 20. The Nations, Charlotte Robertson, White Bridge, Hillwood.",
        "handleSource": {
            "title": "Public X profile",
            "url": "https://x.com/HortonRollin",
            "checked": CHECKED,
            "note": "The profile name and bio identify him as the District 20 council member. His newsletter is the Westside Stories Substack.",
        },
    },
    225: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page or newsletter archive."}},
    284: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified. The newsletter archive links a Metro Planning post, not her account."}},
    227: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "thomdruffel.com lists no X account."}},
    285: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "brendafornashville.com lists no X account. A Bluesky account exists and is not used here."}},
    286: {
        "handle": "JLPreptit",
        "profileName": "Jeff L Preptit, Esq.",
        "bio": "Civil Rights Attorney",
        "handleSource": {
            "title": "Jeff Preptit newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/jeff-preptit",
            "checked": CHECKED,
            "note": "The archive uses a social icon linking to twitter.com/JLPreptit. The profile name is Jeff L Preptit, Esq.",
        },
    },
    230: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "district26nashville.com lists no X account."}},
    231: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page. He is not the other public figures named Bob Nash."}},
    287: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page."}},
    294: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page or newsletter archive."}},
    234: {
        "handle": "SandraForNash",
        "profileName": "Sandra Sepulveda",
        "bio": "",
        "profilePostCount": 0,
        "handleSource": {
            "title": "sandrafornashville.com contact page",
            "url": "https://www.sandrafornashville.com/contact",
            "checked": CHECKED,
            "note": "The contact page links https://twitter.com/SandraForNash. The profile name is Sandra Sepulveda and the profile header reported 0 posts.",
        },
        "fetchStatus": "ok",
        "fetchedAt": "2026-11-22T00:00:00Z",
        "fetchNote": "The public profile header reported 0 posts on this date, so the lookback window contains no posts. Repost and like counts are not applicable.",
        "posts": [],
    },
    235: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified. He is not the Florida member of Congress who uses a similar name."}},
    236: {
        "handle": "Stylesfor32",
        "profileName": "JoyStylesforDistrict32",
        "bio": "Councilwoman for District 32. Bridge Builder. Passionate about people",
        "handleSource": {
            "title": "Ballotpedia page for Joy Styles",
            "url": "https://ballotpedia.org/Joy_Styles",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/Stylesfor32. The bio says Councilwoman for District 32.",
        },
    },
    237: {
        "handle": "MrsALee",
        "profileName": "Antoinette Lee",
        "bio": "I'm active in TN state politics, and I advocate for public school education and public education employees.",
        "handleSource": {
            "title": "Ballotpedia page for Antoinette Lee",
            "url": "https://ballotpedia.org/Antoinette_Lee",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/MrsALee. The profile name is Antoinette Lee. The bio does not itself say Metro Council.",
        },
    },
    288: {"handle": None, "handleCheck": {"checked": CHECKED, "result": "not_found", "note": "No personal X account was verified from the nashville.gov page or newsletter archive."}},
    289: {
        "handle": "JasonSpainTN",
        "profileName": "Jason Spain",
        "bio": "Nashville Metro Council Member, District 35. Executive Director, Tennessee Public Transportation Association.",
        "handleSource": {
            "title": "Jason Spain newsletter archive",
            "url": "https://www.nashvillenewsletters.org/member/jason-spain",
            "checked": CHECKED,
            "note": "The archive links twitter.com/JasonSpainTN. The bio says Nashville Metro Council Member, District 35.",
        },
    },
    238: {
        "handle": "angienashville",
        "profileName": "Angie E. Henderson",
        "bio": "Vice Mayor of Nashville. President of #MetroCouncilNash. Not a govt/official acct.",
        "handleSource": {
            "title": "Ballotpedia page for Angie Henderson",
            "url": "https://ballotpedia.org/Angie_Henderson",
            "checked": CHECKED,
            "note": "Ballotpedia links https://x.com/angienashville. Her bio says Vice Mayor and also says the account is not an official government account.",
        },
    },
}


def file_for(member):
    extra = HANDLES.get(member["pid"], {})
    handle = extra.get("handle")
    status = extra.get("fetchStatus")
    if status is None:
        status = "pending" if handle else "no_handle"
    doc = {
        "pid": member["pid"],
        "slug": slugify(member["name"]),
        "name": member["name"],
        "handle": handle,
        "profileUrl": ("https://x.com/" + handle) if handle else None,
        "profileName": extra.get("profileName"),
        "protected": bool(extra.get("protected")),
        "bio": extra.get("bio") or "",
        "handleSource": extra.get("handleSource"),
        "handleCheck": extra.get("handleCheck") or ({"checked": CHECKED, "result": "verified"} if handle else None),
        "fetchedAt": extra.get("fetchedAt"),
        "fetchStatus": status,
        "fetchNote": extra.get("fetchNote") or (
            "Handle verified. Recent posts have not been loaded into this file yet."
            if handle and status == "pending"
            else "No verified handle, so there are no posts to load."
        ),
        "truncated": False,
        "posts": extra.get("posts") or [],
    }
    if "profilePostCount" in extra:
        doc["profilePostCount"] = extra["profilePostCount"]
    return doc


def main():
    force = "--force" in sys.argv
    members = json.load(open(os.path.join(DATA, "members.json"), encoding="utf-8"))["members"]
    out_dir = os.path.join(DATA, "tweets")
    os.makedirs(out_dir, exist_ok=True)
    wrote = skipped = 0
    missing_seed = []
    for member in members:
        if member["pid"] not in HANDLES:
            missing_seed.append(member["name"])
        path = os.path.join(out_dir, slugify(member["name"]) + ".json")
        if os.path.exists(path) and not force:
            skipped += 1
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(file_for(member), f, indent=1, ensure_ascii=False)
            f.write("\n")
        wrote += 1
    if missing_seed:
        raise SystemExit("No handle row for: " + ", ".join(missing_seed))
    print(f"wrote {wrote}, left {skipped} existing files alone")


if __name__ == "__main__":
    main()
