# Apple Music MCP Server — Spec

## Overview

A Python MCP server that lets Claude search the Apple Music catalog and manage playlists via the Apple Music REST API. Single codebase — no Swift, no Node.js.

Builds on the existing `playlist-creator` CLI ([PR #1](https://github.com/danryan/playlist-creator/pull/1)) which already handles markdown parsing, JWT generation, catalog search, and playlist creation.

---

## Architecture

```
Claude Desktop / Claude Code
  └─ MCP (stdio)
       └─ playlist-creator MCP server (Python)
            └─ Apple Music REST API
                 ├─ Developer Token (JWT, signed from .p8 key)
                 └─ Music User Token (obtained via MusicKit JS)
```

Single process. No shelling out, no child processes, no compiled binaries.

---

## Authentication

### Developer token (JWT)

Already implemented in `playlist_creator.apple_music.AppleMusicClient`.

Requires env vars:

| Var | Description |
|---|---|
| `APPLE_MUSIC_TEAM_ID` | Apple Developer Team ID |
| `APPLE_MUSIC_KEY_ID` | MusicKit key identifier |
| `APPLE_MUSIC_PRIVATE_KEY_PATH` | Path to `.p8` private key file |

JWT is signed with ES256 (P-256 curve), valid for 6 months max. Library: `PyJWT` with `cryptography` backend.

### Music user token

Required for write operations (create playlist, add to library). Cannot be obtained programmatically via REST — requires interactive Apple ID sign-in.

Obtained via `get_user_token.html`:

1. Generate developer JWT using existing Python code
2. Open `get_user_token.html` in Safari (or localhost)
3. Paste developer JWT, click Authorize
4. Sign in with Apple ID when prompted
5. Copy the resulting user token

Token lifetime: ~6 months. Store as:

```bash
export APPLE_MUSIC_USER_TOKEN=<token>
```

When token expires, API returns 401 — repeat the flow.

| Var | Description |
|---|---|
| `APPLE_MUSIC_USER_TOKEN` | Music User Token from MusicKit JS |
| `APPLE_MUSIC_STOREFRONT` | Country code, defaults to `us` |

---

## Existing code (PR #1)

The `playlist-creator` CLI already provides:

- **Markdown parser** — bullet lists, numbered lists, bare lines, bold/italic, em/en dash separators
- **`AppleMusicClient`** — JWT generation, catalog search, playlist creation, add tracks
- **CLI interface** — `playlist-creator <file.md> [--dry-run] [-v] [-n name] [-d desc]`
- **15 unit tests** — parser + API client

The MCP server wraps `AppleMusicClient` directly — no subprocess, no reimplementation.

---

## MCP Server

### Dependencies

- `mcp` — Python MCP SDK (Anthropic)
- `pyjwt[crypto]` — JWT signing (already a dep)
- `httpx` or `requests` — API calls (already a dep)

### Transport

stdio (stdin/stdout JSON-RPC). Compatible with Claude Desktop and Claude Code.

### Environment

All existing env vars, plus optional:

| Var | Description | Default |
|---|---|---|
| `APPLE_MUSIC_SEARCH_LIMIT` | Default search result count | `10` |

### Tool definitions

#### `search_catalog`

Search the Apple Music catalog for songs.

| Param | Type | Required | Default |
|---|---|---|---|
| `query` | string | yes | — |
| `limit` | integer | no | 10 |
| `types` | string | no | `"songs"` |

Calls: `GET /v1/catalog/{storefront}/search?term={query}&types={types}&limit={limit}`

Returns:

```json
{
  "results": [
    {
      "id": "1440345678",
      "title": "Rhubarb",
      "artist": "Aphex Twin",
      "album": "Selected Ambient Works Volume II",
      "duration_ms": 312000,
      "genres": ["Electronic"],
      "release_date": "1994-11-07",
      "url": "https://music.apple.com/us/album/..."
    }
  ]
}
```

#### `create_playlist`

Create a new playlist in the user's library.

| Param | Type | Required | Default |
|---|---|---|---|
| `name` | string | yes | — |
| `description` | string | no | `""` |

Calls: `POST /v1/me/library/playlists`

Returns:

```json
{
  "id": "p.Nk1wRjM2",
  "name": "Deep Focus Ambient"
}
```

#### `add_to_playlist`

Add songs to an existing playlist by catalog IDs.

| Param | Type | Required | Default |
|---|---|---|---|
| `playlist_id` | string | yes | — |
| `song_ids` | string[] | yes | — |

Calls: `POST /v1/me/library/playlists/{id}/tracks`

Returns:

```json
{
  "added": 5,
  "failed": []
}
```

#### `list_playlists`

List the user's library playlists.

No params.

Calls: `GET /v1/me/library/playlists`

Returns:

```json
{
  "playlists": [
    {
      "id": "p.QmV0aGVz",
      "name": "Late Night Ambient",
      "track_count": 24
    }
  ]
}
```

#### `create_playlist_from_markdown`

Parse a markdown string and create a playlist from it. Reuses existing markdown parser.

| Param | Type | Required | Default |
|---|---|---|---|
| `markdown` | string | yes | — |
| `name` | string | no | parsed from `# heading` |
| `description` | string | no | parsed from body text |
| `dry_run` | boolean | no | `false` |

Flow:
1. Parse markdown into track list (artist, title pairs)
2. Search catalog for each track
3. Create playlist
4. Add found tracks
5. Return summary with matched/unmatched tracks

Returns:

```json
{
  "playlist_id": "p.Nk1wRjM2",
  "playlist_name": "Thrash Drumming Study",
  "matched": [
    {"artist": "Havok", "title": "Afterburner", "catalog_id": "1440345678"}
  ],
  "not_found": [
    {"artist": "Obscure Band", "title": "Rare Track"}
  ]
}
```

### Error handling

| Condition | MCP response |
|---|---|
| 401 from API | `ToolError`: "User token expired. Re-run get_user_token.html to obtain a new token." |
| 403 from API | `ToolError`: "Forbidden. Check Apple Music subscription status." |
| 429 from API | `ToolError`: "Rate limited. Retry in {n} seconds." |
| Missing env vars | `ToolError`: "Missing required env var: {var}" |
| No search results | Return empty results array (not an error) |

---

## File structure

```
playlist-creator/
  README.md
  pyproject.toml               # already exists
  get_user_token.html          # MusicKit JS token page (new)
  examples/
    road_trip.md               # example markdown playlist
  src/
    playlist_creator/
      __init__.py
      __main__.py              # CLI entry point (existing)
      parser.py                # Markdown parser (existing)
      apple_music.py           # AppleMusicClient (existing)
      mcp_server.py            # MCP server (new)
  tests/
    test_parser.py             # existing
    test_apple_music.py        # existing
    test_mcp_server.py         # new
```

### New files

| File | Purpose |
|---|---|
| `src/playlist_creator/mcp_server.py` | MCP tool definitions, handlers, stdio transport setup |
| `tests/test_mcp_server.py` | Unit tests for MCP tool handlers |
| `get_user_token.html` | MusicKit JS page for user token acquisition |

### Files to modify

| File | Change |
|---|---|
| `pyproject.toml` | Add `mcp` dependency, add `playlist-creator-mcp` entry point |
| `README.md` | Add MCP server setup docs |

---

## Claude Desktop integration

### `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "apple-music": {
      "command": "python",
      "args": ["-m", "playlist_creator.mcp_server"],
      "env": {
        "APPLE_MUSIC_TEAM_ID": "XXXXXXXXXX",
        "APPLE_MUSIC_KEY_ID": "XXXXXXXXXX",
        "APPLE_MUSIC_PRIVATE_KEY_PATH": "/path/to/AuthKey.p8",
        "APPLE_MUSIC_USER_TOKEN": "your-user-token"
      }
    }
  }
}
```

Or if installed as a package with entry point:

```json
{
  "mcpServers": {
    "apple-music": {
      "command": "playlist-creator-mcp"
    }
  }
}
```

(env vars loaded from shell environment or `.env` file)

---

## Setup sequence

1. Clone repo: `git clone https://github.com/danryan/playlist-creator`
2. Install: `pip install -e ".[dev]"`
3. Set env vars: `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID`, `APPLE_MUSIC_PRIVATE_KEY_PATH`
4. Get user token: open `get_user_token.html`, authorize, set `APPLE_MUSIC_USER_TOKEN`
5. Test CLI: `playlist-creator examples/road_trip.md --dry-run`
6. Test MCP: `python -m playlist_creator.mcp_server` (should start listening on stdio)
7. Add to `claude_desktop_config.json`
8. Restart Claude Desktop

---

## Example interaction

> "Make me a 90-minute ambient playlist for deep focus"

Claude would:

1. `search_catalog` "ambient electronic focus" (+ variations: "Brian Eno ambient", "Stars of the Lid", etc.)
2. Collect results, curate ~20 tracks totaling ~90 min using `duration_ms`
3. `create_playlist` "Deep Focus Ambient"
4. `add_to_playlist` with collected catalog IDs
5. Return the playlist summary with track listing

> "Here's my markdown playlist, create it" (pastes markdown)

Claude would:

1. `create_playlist_from_markdown` with the pasted content
2. Return matched/unmatched report

---

## Limitations

- **Apple Music subscription required** — catalog search works without, but add-to-library and playlist creation fail
- **User token expires** — ~6 months, requires manual re-auth via browser
- **No playlist deletion** — Apple Music API doesn't support deleting playlists
- **No smart playlists** — API only creates standard playlists
- **Rate limits** — Apple Music API allows ~20 requests/minute (undocumented, varies); batch song additions
- **Search quality** — catalog search can return unexpected results for ambiguous queries; combining artist + title improves accuracy
- **No playback control** — REST API cannot control playback on devices
- **Platform agnostic** — runs anywhere Python runs (not macOS-only like the Swift/MusicKit approach)

---

## Future extensions

| Feature | Approach |
|---|---|
| Get song details by ID | `GET /v1/catalog/{storefront}/songs/{id}` |
| Search albums/artists | Add `types` param: `albums`, `artists` |
| Get playlist tracks | `GET /v1/me/library/playlists/{id}/tracks` |
| Artwork URLs | Already in catalog search response, surface in results |
| Library search | `GET /v1/me/library/search` — separate tool or flag on `search_catalog` |
| Token refresh helper | CLI command `playlist-creator get-token` — generates JWT, opens browser |
| Batch import | Accept CSV, JSON, or plain text in addition to markdown |
| Duplicate detection | Check if song already in playlist before adding |
