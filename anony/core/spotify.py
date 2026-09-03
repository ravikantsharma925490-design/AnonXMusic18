# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.

import base64
import os

import aiohttp
from pyrogram import filters, types

from anony import app


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
            "Authorization": f"Bearer {self.token}"
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
                    self.token = None
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
                        "duration_ms": item["duration_ms"],
                        "spotify_url": item["external_urls"]["spotify"],
                    })

                return tracks


spotify = Spotify()


@app.on_message(
    filters.command("spotify")
    & filters.group
    & ~app.bl_users
)
async def spotify_handler(_, m: types.Message):

    if len(m.command) < 2:
        return await m.reply_text(
            "🎵 Usage:\n\n"
            "`/spotify song name`\n\n"
            "Example:\n"
            "`/spotify Kesariya`"
        )

    query = " ".join(m.command[1:]).strip()

    msg = await m.reply_text(
        f"🔎 Searching Spotify for `{query}`..."
    )

    try:
        tracks = await spotify.search(query, limit=5)

    except Exception as e:
        return await msg.edit_text(
            f"❌ Spotify search failed.\n\n`{e}`"
        )

    if not tracks:
        return await msg.edit_text(
            "❌ No Spotify tracks found."
        )

    text = "🎵 **Spotify Results**\n\n"

    for i, track in enumerate(tracks, 1):
        duration = track["duration_ms"] // 1000
        minutes = duration // 60
        seconds = duration % 60

        text += (
            f"**{i}. {track['name']}**\n"
            f"👤 {track['artist']}\n"
            f"💿 {track['album']}\n"
            f"⏱ {minutes}:{seconds:02d}\n"
            f"🔗 [Spotify]({track['spotify_url']})\n\n"
        )

    await msg.edit_text(
        text,
        disable_web_page_preview=True
    )
