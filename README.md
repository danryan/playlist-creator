# playlist-creator

Create Apple Music playlists from markdown files. Write your playlist as a simple markdown list, and this tool searches Apple Music for each track and adds them to a new playlist in your library.

## Markdown Format

```markdown
# My Playlist Name

Optional description text.

- Artist Name - Track Title
- Another Artist - Another Track
```

Supports bullet lists (`-`, `*`), numbered lists (`1.`), bare lines, and em/en dash separators.

## Installation

```bash
pip install .
```

## Usage

### Preview tracks (no API calls)

```bash
playlist-creator playlist.md --dry-run
```

### Create a playlist

Set the required environment variables:

```bash
export APPLE_MUSIC_TEAM_ID=your_team_id
export APPLE_MUSIC_KEY_ID=your_key_id
export APPLE_MUSIC_PRIVATE_KEY_PATH=/path/to/AuthKey_XXXXXX.p8
export APPLE_MUSIC_USER_TOKEN=your_user_token
export APPLE_MUSIC_STOREFRONT=us  # optional, defaults to us
```

Then run:

```bash
playlist-creator playlist.md -v
```

### Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Parse and display tracks without creating a playlist |
| `-n, --name` | Override the playlist name from the markdown heading |
| `-d, --description` | Override the playlist description |
| `-v, --verbose` | Show detailed search results |

## Getting Apple Music Credentials

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/)
2. Create a MusicKit key in Certificates, Identifiers & Profiles
3. Download the `.p8` private key file
4. Note your Team ID and Key ID
5. Obtain a user token via MusicKit JS or MusicKit on iOS/macOS

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
