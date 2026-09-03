# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

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
    search_query = None

    # Telegram replied media
    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    # Authorized M3U8/source
    elif m3u8:
        file = await tg.process_m3u8(
            url,
            sent.id,
            video
        )

    # URL / playlist
    elif url:
        search_query = url

        if "playlist" in url.lower():
            await sent.edit_text(m.lang["playlist_fetch"])

            try:
                tracks = await yt.playlist(
                    config.PLAYLIST_LIMIT,
                    mention,
                    url,
                    video
                )

                if tracks:
                    file = tracks[0]
                    tracks.remove(file)
                    file.message_id = sent.id

            except Exception:
                file = None

        else:
            try:
                # Metadata/search only.
                # No automatic downloading/ripping.
                file = await yt.search(
                    url,
                    sent.id,
                    video=video
                )
            except Exception:
                file = None

    # Song/search text
    elif len(m.command) >= 2:
        query = " ".join(m.command[1:]).strip()
        search_query = query

        try:
            # Search/metadata only.
            file = await yt.search(
                query,
                sent.id,
                video=video
            )
        except Exception:
            file = None

    # Nothing playable
    if not file:
        return await sent.edit_text(
            "❌ No playable authorized media found.\n\n"
            "Reply to a Telegram audio/video file or provide an "
            "authorized playable source."
        )

    # Duration check
    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(
                config.DURATION_LIMIT // 60
            )
        )

    # Logger
    if await db.is_logger():
        await utils.play_log(
            m,
            sent.link,
            file.title,
            file.duration
        )

    file.user = mention

    # Queue
    if force:
        queue.force_add(m.chat.id, file)

    else:
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id,
                    file.id,
                    m.lang["play_now"]
                ),
            )
            return

    # Direct playback only.
    # No yt.download()
    # No spotdl
    # No background downloader
    try:
        await anon.play_media(
            chat_id=m.chat.id,
            message=sent,
            media=file
        )

    except Exception:
        await sent.edit_text(
            "❌ Playback connection failed."
        )
        return

    # Playlist queue
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
        ) + added
    )
