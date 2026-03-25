"""Apple Music API client for searching tracks and creating playlists."""

from __future__ import annotations

import time
from dataclasses import dataclass

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

    def add_tracks_to_playlist(
        self, playlist_id: str, track_ids: list[dict]
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
