import base64
import os

import aiohttp


class Spotify:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.token = None

    async def get_token(self):
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is missing."
            )

        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "client_credentials"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://accounts.spotify.com/api/token",
                headers=headers,
                data=data,
            ) as response:
                result = await response.json()

                if response.status != 200:
                    raise RuntimeError(
                        f"Spotify authentication failed: {result}"
                    )

                self.token = result["access_token"]
                return self.token

    async def search(self, query, limit=5):
        if not self.token:
            await self.get_token()

        headers = {
            "Authorization": f"Bearer {self.token}",
        }

        params = {
            "q": query,
            "type": "track",
            "limit": limit,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params=params,
            ) as response:
                if response.status == 401:
                    await self.get_token()
                    return await self.search(query, limit)

                result = await response.json()

                if response.status != 200:
                    raise RuntimeError(
                        f"Spotify search failed: {result}"
                    )

                tracks = []

                for item in result.get("tracks", {}).get("items", []):
                    tracks.append({
                        "name": item["name"],
                        "artist": ", ".join(
                            artist["name"]
                            for artist in item["artists"]
                        ),
                        "album": item["album"]["name"],
                        "spotify_url": item["external_urls"]["spotify"],
                        "duration_ms": item["duration_ms"],
                    })

                return tracks


spotify = Spotify()
