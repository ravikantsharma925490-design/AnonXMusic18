# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils


class DummyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class YouTube:
    def __init__(self):
        self.base = "https://youtube.com"
        self.cookies = []
        self.checked = False
        self.cookie_dir = os.path.join(os.getcwd(), "anony", "cookies")
        self.cookie_file_path = os.path.join(self.cookie_dir, "cookies.txt")
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def get_cookies(self):
        if not self.checked:
            env_cookies = os.getenv("YT_DLP_COOKIES")
            if env_cookies:
                try:
                    os.makedirs(self.cookie_dir, exist_ok=True)
                    
                    lines = env_cookies.splitlines()
                    clean_lines = ["# Netscape HTTP Cookie File", "# http://haxx.se", ""]
                    seen_tokens = set()

                    for line in lines:
                        line_str = line.strip()
                        if not line_str or line_str.startswith("#"):
                            continue
                        
                        parts = re.split(r'\t|\s+', line_str)
                        if len(parts) >= 7:
                            cookie_name = parts[5]
                            
                            if cookie_name in ["__Secure-ROLLOUT_TOKEN", "__Secure-YNID", "VISITOR_INFO1_LIVE"]:
                                if cookie_name in seen_tokens:
                                    continue
                                seen_tokens.add(cookie_name)
                                
                            clean_line = "\t".join(parts[:7])
                            clean_lines.append(clean_line)

                    with open(self.cookie_file_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write("\n".join(clean_lines) + "\n")
                        
                    if self.cookie_file_path not in self.cookies:
                        self.cookies.append(self.cookie_file_path)
                    logger.info("Cookies filtered, corruptions removed, and saved successfully!")
                except Exception as e:
                    logger.error(f"Failed to filter and save cookies from Env: {e}")
            
            if not self.cookies and os.path.exists(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        full_path = os.path.join(self.cookie_dir, file)
                        if full_path not in self.cookies:
                            self.cookies.append(full_path)
            self.checked = True

        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        os.makedirs(self.cookie_dir, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(os.path.join(self.cookie_dir, f"{name}.txt"), "wb") as fw:
                        fw.write(await resp.read())
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        url = self.base + "/watch?v=" + video_id if not video_id.startswith("http") else video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        cookie = self.get_cookies()
               base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "logger": DummyLogger(),
            "nocheckcertificate": True,
            "cookiefile": cookie,
            
            # 🔥 CRITICAL 2026 BYPASS: FORCE MOBILE WEB TO SKIPP PO-TOKEN ENFORCEMENT
            "extractor_args": {
                "youtube": {
                    "player_client": ["mweb", "ios"], # Strictly use mobile web endpoints
                    "player_skip": ["configs", "webpage"],
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        }


        if video:
            ydl_opts = {
                **base_opts,
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)",
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                "format": "bestaudio[ext=webm][acodec=opus]",
            }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as err:
                    logger.error(f"Download Error Trace: {err}")
                    return None
                except Exception as ex:
                    logger.warning("Download failed: %s", ex)
                    return None
            return filename

        return await asyncio.to_thread(_download)
