#!/usr/bin/env python3
"""Read Microsoft Teams (new client, macOS) messages from the local IndexedDB.

Usage:
  teams_messages.py topics [--days N]
  teams_messages.py show --topic "Back-end" [--topic General ...] [--days 7] [--max-chars 400]
  teams_messages.py export --out /tmp/teams/messages.jsonl

The live database is never touched: it is copied to a temp dir first.
Requires: pip install "git+https://github.com/cclgroupltd/ccl_chromium_reader.git" python-snappy
"""
import argparse, collections, datetime, html, json, os, re, shutil, sys, tempfile, time
from pathlib import Path

IDB = Path.home() / ("Library/Containers/com.microsoft.teams2/Data/Library/Application Support/"
                     "Microsoft/MSTeams/EBWebView/WV2Profile_tfw/IndexedDB")
ORIGIN = "https_teams.microsoft.com_0.indexeddb"


def snapshot():
    tmp = Path(tempfile.mkdtemp(prefix="teams_idb_"))
    shutil.copytree(IDB / f"{ORIGIN}.leveldb", tmp / "ldb")
    shutil.copytree(IDB / f"{ORIGIN}.blob", tmp / "blob")
    (tmp / "ldb" / "LOCK").unlink(missing_ok=True)
    return tmp


def S(x):
    if isinstance(x, bytes):
        return x.decode("utf-8", "replace")
    return x if isinstance(x, (str, int, float)) else None


def load():
    from ccl_chromium_reader import ccl_chromium_indexeddb as idb
    tmp = snapshot()
    try:
        w = idb.WrappedIndexDB(str(tmp / "ldb"), str(tmp / "blob"))
        convs, msgs = {}, []
        for db in w.database_ids:
            d = w[db.dbid_no]
            if db.name.startswith("Teams:conversation-manager"):
                for r in d["conversations"].iterate_records():
                    v = r.value
                    if isinstance(v, dict):
                        tp = v.get("threadProperties")
                        t = tp.get("topic") if isinstance(tp, dict) else None
                        t = t or v.get("title") or ""
                        convs[v.get("id")] = t if isinstance(t, str) else ""
            elif db.name.startswith("Teams:replychain-manager"):
                for store in ("replychains", "replychains-2"):
                    for r in d[store].iterate_records():
                        v = r.value
                        if not isinstance(v, dict):
                            continue
                        for m in (v.get("messageMap") or {}).values():
                            raw = S(m.get("content")) or ""
                            txt = html.unescape(re.sub(r"<[^>]+>", " ", raw))
                            msgs.append({
                                "conversationId": S(m.get("conversationId")),
                                "time": S(m.get("originalArrivalTime")),
                                "from": S(m.get("imDisplayName") or m.get("fromDisplayNameInToken")),
                                "type": S(m.get("messageType")),
                                "text": re.sub(r"\s+", " ", txt).strip(),
                            })
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for m in msgs:
        m["topic"] = convs.get(m["conversationId"], "")
    msgs.sort(key=lambda m: m["time"] or 0)
    return msgs


def real(m):
    # system events (calls, pins, meeting notices) have no sender and no real text
    return bool(m["from"] and m["text"] and m["time"])


def recent(msgs, days):
    cut = (time.time() - days * 86400) * 1000 if days else 0
    return [m for m in msgs if m["time"] and m["time"] >= cut]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("topics"); t.add_argument("--days", type=int, default=0)
    s = sub.add_parser("show")
    s.add_argument("--topic", action="append", required=True, help="substring, case-insensitive")
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--max-chars", type=int, default=400)
    e = sub.add_parser("export"); e.add_argument("--out", required=True)
    a = ap.parse_args()

    msgs = load()
    if a.cmd == "export":
        with open(a.out, "w", encoding="utf-8") as f:
            for m in msgs:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        print(f"{len(msgs)} messages -> {a.out}")
    elif a.cmd == "topics":
        c = collections.Counter(m["topic"] or m["conversationId"] for m in recent(msgs, a.days) if real(m))
        for name, n in c.most_common():
            print(n, name)
    else:
        wanted = [x.lower() for x in a.topic]
        for topic in sorted({m["topic"] for m in msgs if any(w in m["topic"].lower() for w in wanted)}):
            print(f"\n===== {topic}")
            seen = set()
            for m in recent(msgs, a.days):
                if m["topic"] != topic or not real(m) or (m["time"], m["text"]) in seen:
                    continue
                seen.add((m["time"], m["text"]))
                ts = datetime.datetime.fromtimestamp(m["time"] / 1000).strftime("%d/%m %H:%M")
                print(f"{ts} {m['from']}: {m['text'][:a.max_chars]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
