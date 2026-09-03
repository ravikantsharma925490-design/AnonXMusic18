# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import shutil
import glob
from pathlib import Path
import asyncio

from pyrogram import filters, types

from anony import anon, app, config, db, lang, queue, tg, yt
from anony.helpers import buttons, utils
from anony.helpers._play import checkUB


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"

    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"

    text = text[:1948] + "</blockquote>"
    return text


# Render special: Parallel background task to handle high-quality audio file transmission 
async def background_file_downloader(query: str, chat_id: int, user_id: int, message_id: int, mention: str):
    # Unique isolated directory structure for parallel concurrency downloads
    download_dir = f"/tmp/spotdl_play_{user_id}_{message_id}"
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # Executes spotDL processing layer silently in background
        command = f'spotdl download "{query}" --output "{download_dir}/%(title)s.%(ext)s" --format mp3'
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # Scans for compiled audio files
        audio_files = glob.glob(os.path.join(download_dir, "*.mp3"))
        if audio_files:
            for file_path in audio_files:
                file_name = os.path.basename(file_path)
                # Dispatch real Telegram audio item alongside inline mention parameters
                await app.send_audio(
                    chat_id=chat_id,
                    audio=file_path,
                    title=file_name.replace(".mp3", ""),
                    caption=f"🎵 **Audio file extracted successfully for:** {mention}"
                )
    except Exception as e:
        print(f"[BACKGROUND MP3 DOWNLOAD ERROR]: {str(e)}")
    finally:
        # Avoid disk leak failure rules on cloud environment
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)


@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:

    sent = await m.reply_text(m.lang["play_searching"])

    file = None
    mention = m.from_user.mention
    media = (
        tg.get_media(m.reply_to_message)
        if m.reply_to_message
        else None
    )

    tracks = []
    search_query = None # Background processing query parameter

    # ---------------------------------
    # REPLY MEDIA
    # ---------------------------------
    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    # ---------------------------------
    # M3U8
    # ---------------------------------
    elif m3u8:
        file = await tg.process_m3u8(
            url,
            sent.id,
            video
        )

    # ---------------------------------
    # URL / PLAYLIST
    # ---------------------------------
    elif url:
        search_query = url # Maps target URL string directly
        if "playlist" in url.lower():

            await sent.edit_text(
                m.lang["playlist_fetch"]
            )

            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT,
                mention,
                url,
                video
            )

            if not tracks:
                return await sent.edit_text(
                    m.lang["playlist_error"]
                )

            file = tracks[0]
            tracks.remove(file)

            file.message_id = sent.id

        else:

            file = await yt.search(
                url,
                sent.id,
                video=video
            )

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(
                    config.SUPPORT_CHAT
                )
            )

    # ---------------------------------
    # SONG NAME SEARCH
    # /play Kesariya
    # ---------------------------------
    elif len(m.command) >= 2:

        query = " ".join(m.command[1:]).strip()
        search_query = query # Maps query string values directly

        if not query:
            return await sent.edit_text(
                m.lang["play_usage"]
            )

        file = await yt.search(
            query,
            sent.id,
            video=video
        )

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(
                    config.SUPPORT_CHAT
                )
            )

    # ---------------------------------
    # NO INPUT
    # ---------------------------------
    if not file:
        return await sent.edit_text(
            m.lang["play_usage"]
        )

    # ---------------------------------
    # DURATION LIMIT
    # ---------------------------------
    if file.duration_sec > config.DURATION_LIMIT:

        return await sent.edit_text(
            m.lang["play_duration_limit"].format(
                config.DURATION_LIMIT // 60
            )
        )

    # ---------------------------------
    # LOGGER
    # ---------------------------------
    if await db.is_logger():

        await utils.play_log(
            m,
            sent.link,
            file.title,
            file.duration
        )

    file.user = mention

    # ---------------------------------
    # QUEUE
    # ---------------------------------
    if force:

        queue.force_add(
            m.chat.id,
            file
        )

    else:

        position = queue.add(
            m.chat.id,
            file
        )

        # Song already playing
        if position != 0 or await db.get_call(m.chat.id):

            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id,
                    file.id,
                    m.lang["play_now"]
                ),
            )

            # Fire off background media fetcher even if track is placed in playback pipeline queue
            if search_query:
                asyncio.create_task(
                    background_file_downloader(
                        search_query, m.chat.id, m.from_user.id, m.id, mention
                    )
                )

            # Add playlist tracks
            if tracks:

                added = playlist_to_queue(
                    m.chat.id,
                    tracks
                )

                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(
                        len(tracks)
                    ) + added,
                )

            return

    # ---------------------------------
    # DOWNLOAD / CACHE (Voice Chat Audio Layer Engine)
    # ---------------------------------
    if not file.file_path:

        extension = "mp4" if video else "webm"

        fname = (
            f"downloads/{file.id}.{extension}"
        )

        # Existing cached file
        if Path(fname).exists():

            file.file_path = fname

        else:

            await sent.edit_text(
                m.lang["play_downloading"]
            )

            try:

                file.file_path = await yt.download(
                    file.id,
                    video=video
                )

            except Exception as e:

                print(
                    f"[PLAY DOWNLOAD ERROR] {type(e).__name__}: {e}"
                )

                return await sent.edit_text(
                    "❌ Download failed.\n\n"
                    "YouTube media could not be obtained. "
                    "Check the server logs/cookies."
                )

    # ---------------------------------
    # PLAY IN VOICE CHAT
    # ---------------------------------
    try:

        await anon.play_media(
            chat_id=m.chat.id,
            message=sent,
            media=file
        )
        
        # Fire off non-blocking async background thread downoader immediately after voice link initialization
        if search_query:
            asyncio.create_task(
                background_file_downloader(
                    search_query, m.chat.id, m.from_user.id, m.id, mention
                )
            )

    except Exception as e:

        print(
            f"[PLAY VOICE ERROR] {type(e).__name__}: {e}"
        )

        return await sent.edit_text(
            "❌ Voice chat playback failed.\n\n"
            "Please check the assistant and PyTgCalls logs."
        )

    # ---------------------------------
    # PLAYLIST QUEUE
    # ---------------------------------
    if not tracks:
        return

    added = playlist_to_queue(
        m.chat.id,
        tracks
    )

    await app.send_message(
        chat_id=m.chat.id,
        text=m.lang["playlist_queued"].format(
            len(tracks)
        ) + added,
    )
