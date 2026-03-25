"""Tests for markdown playlist parser."""

from playlist_creator.parser import Track, parse_markdown_text


def test_basic_playlist():
    md = """# My Playlist

- Artist One - Song One
- Artist Two - Song Two
"""
    playlist = parse_markdown_text(md)
    assert playlist.name == "My Playlist"
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0] == Track(artist="Artist One", title="Song One")
    assert playlist.tracks[1] == Track(artist="Artist Two", title="Song Two")


def test_numbered_list():
    md = """# Numbered

1. The Beatles - Hey Jude
2. Queen - Bohemian Rhapsody
"""
    playlist = parse_markdown_text(md)
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0].artist == "The Beatles"
    assert playlist.tracks[1].title == "Bohemian Rhapsody"


def test_description_extracted():
    md = """# Chill Vibes

A relaxing playlist for the evening.

- Norah Jones - Come Away with Me
"""
    playlist = parse_markdown_text(md)
    assert playlist.description == "A relaxing playlist for the evening."
    assert len(playlist.tracks) == 1


def test_em_dash_separator():
    md = """# Dashes

- Artist — Title With Em Dash
- Artist – Title With En Dash
"""
    playlist = parse_markdown_text(md)
    assert len(playlist.tracks) == 2


def test_bold_italic_stripped():
    md = """# Formatted

- **Bold Artist** - *Italic Song*
"""
    playlist = parse_markdown_text(md)
    assert playlist.tracks[0].artist == "Bold Artist"
    assert playlist.tracks[0].title == "Italic Song"


def test_bare_lines():
    md = """# Bare

Tom Petty - Free Fallin'
Eagles - Hotel California
"""
    playlist = parse_markdown_text(md)
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0].title == "Free Fallin'"


def test_no_heading_defaults_name():
    md = """- Artist - Song"""
    playlist = parse_markdown_text(md)
    assert playlist.name == "Untitled Playlist"


def test_search_query():
    track = Track(artist="Fleetwood Mac", title="The Chain")
    assert track.search_query() == "Fleetwood Mac The Chain"


def test_asterisk_list_marker():
    md = """# Stars

* Pink Floyd - Comfortably Numb
* Led Zeppelin - Stairway to Heaven
"""
    playlist = parse_markdown_text(md)
    assert len(playlist.tracks) == 2
