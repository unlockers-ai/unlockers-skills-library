---
name: teams-local-messages
status: prototype
description: "[PROTOTYPE] Read and recap Microsoft Teams conversations from the local Teams cache/database on macOS (new Teams client, WebView2 IndexedDB). Use when the user asks to access, search, list or summarise local Teams messages, channels or chats (e.g. a recap of the last week in Back-end and General) without using the Graph API."
---

# Teams local messages (macOS, new Teams)

> **Prototype.** Built from a single exploratory session on one machine; the IndexedDB
> layout is an undocumented Teams internal and may change with any Teams update. Expect
> rough edges, and verify results against the Teams UI before relying on them.

## Where the data is

New Teams (`com.microsoft.teams2`) keeps messages in a Chromium IndexedDB (LevelDB):

```
~/Library/Containers/com.microsoft.teams2/Data/Library/Application Support/Microsoft/MSTeams/
  EBWebView/WV2Profile_tfw/IndexedDB/https_teams.microsoft.com_0.indexeddb.{leveldb,blob}
```

Dead ends: `Library/Caches/Microsoft/.../Cache` is only HTTP cache; `WebKit/WebsiteData/IndexedDB` is empty; `Cache.db` has no messages.

Relevant databases (one per account, named `Teams:<manager>:react-web-client:<id>:...`):
- `conversation-manager` / `conversations`: id → topic (channel or chat name)
- `replychain-manager` / `replychains`, `replychains-2`: records with `messageMap` of messages
  (`imDisplayName`, `originalArrivalTime` in ms, `content` as bytes of HTML, `messageType`, `conversationId`)

## Setup (once)

```
pip install "git+https://github.com/cclgroupltd/ccl_chromium_reader.git" python-snappy
```
(PyPI has no usable release.)

## Usage

Script: `scripts/teams_messages.py` (copies the DB to a temp dir, so Teams can stay open and is never modified).

```
python3 scripts/teams_messages.py topics --days 7                      # active conversations
python3 scripts/teams_messages.py show --topic back-end --topic general --days 7
python3 scripts/teams_messages.py export --out /tmp/teams/messages.jsonl
```

`--topic` is a case-insensitive substring match on the conversation name.

## Recap workflow

1. Run `topics` to confirm the exact names the user means (a name like "Application" may not exist; say so and propose the closest ones).
2. Run `show` for those topics with the requested `--days`.
3. Summarise per conversation: decisions, PRs/work items (with ids), open questions, who asked what. Drop greetings and system noise.
4. Mention gaps honestly (missing topics, only automatic meeting notices, etc.).

## Caveats

- Only what Teams has cached locally: older history and unopened chats may be missing.
- 1:1/group chats often have no topic; they show as an empty topic or a thread id.
- Messages with no sender are system events (calls, pins, meeting notices); the script hides them.
- The cache is private data: keep exports in `/tmp` or delete them afterwards; never share them externally.
- macOS only; Windows uses a different path.
