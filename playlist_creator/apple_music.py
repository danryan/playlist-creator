"""Apple Music API client for searching tracks and creating playlists."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import jwt
import requests

APPLE_MUSIC_API = "https://api.music.apple.com/v1"


@dataclass
class AppleMusicConfig:
    team_id: str
    key_id: str
    private_key: str  # PEM-encoded private key contents
    storefront: str = "us"


class AppleMusicClient:
    """Client for Apple Music API operations."""

    def __init__(self, config: AppleMusicConfig, user_token: str) -> None:
        self.config = config
        self.user_token = user_token
        self._developer_token: str | None = None
        self._token_expiry: float = 0

    @property
    def developer_token(self) -> str:
        now = time.time()
        if self._developer_token and now < self._token_expiry:
            return self._developer_token

        expiry = now + 3600  # 1 hour
        payload = {
            "iss": self.config.team_id,
            "iat": int(now),
            "exp": int(expiry),
        }
        token = jwt.encode(
            payload,
            self.config.private_key,
            algorithm="ES256",
            headers={"kid": self.config.key_id},
        )
        self._developer_token = token
        self._token_expiry = expiry - 60  # refresh 1 min early
        return token

    def _headers(self, *, include_user_token: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.developer_token}",
            "Content-Type": "application/json",
        }
        if include_user_token:
            headers["Music-User-Token"] = self.user_token
        return headers

    def search_track(self, query: str) -> dict | None:
        """Search for a song and return the first match, or None."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.config.storefront}/search"
        params = {"term": query, "types": "songs", "limit": 1}
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        songs = data.get("results", {}).get("songs", {}).get("data", [])
        if songs:
            return songs[0]
        return None

    def create_playlist(
        self, name: str, description: str = ""
    ) -> str:
        """Create a new library playlist. Returns the playlist ID."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists"
        body: dict = {
            "attributes": {
                "name": name,
                "description": description,
            },
        }
        resp = requests.post(
            url,
            headers=self._headers(include_user_token=True),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        playlist_data = resp.json()["data"][0]
        return playlist_data["id"]

    def search_catalog(
        self, query: str, limit: int = 10, types: str = "songs"
    ) -> list[dict[str, Any]]:
        """Search the Apple Music catalog. Returns a list of result dicts."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.config.storefront}/search"
        params = {"term": query, "types": types, "limit": limit}
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        results = []
        for type_key in types.split(","):
            type_key = type_key.strip()
            items = data.get("results", {}).get(type_key, {}).get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                results.append({
                    "id": item["id"],
                    "title": attrs.get("name", ""),
                    "artist": attrs.get("artistName", ""),
                    "album": attrs.get("albumName", ""),
                    "duration_ms": attrs.get("durationInMillis", 0),
                    "genres": attrs.get("genreNames", []),
                    "release_date": attrs.get("releaseDate", ""),
                    "url": attrs.get("url", ""),
                })
        return results

    def list_playlists(self) -> list[dict[str, Any]]:
        """List the user's library playlists."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists"
        resp = requests.get(
            url,
            headers=self._headers(include_user_token=True),
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        playlists = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            playlists.append({
                "id": item["id"],
                "name": attrs.get("name", ""),
                "track_count": attrs.get("playParams", {}).get("trackCount", 0),
            })
        return playlists

    def add_tracks_to_playlist(
        self, playlist_id: str, track_ids: list[dict[str, str]]
    ) -> None:
        """Add tracks to a library playlist.

        track_ids: list of {"id": "<catalog-id>", "type": "songs"} dicts.
        """
        url = f"{APPLE_MUSIC_API}/me/library/playlists/{playlist_id}/tracks"
        body = {"data": track_ids}
        resp = requests.post(
            url,
            headers=self._headers(include_user_token=True),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
