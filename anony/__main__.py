# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import signal
import importlib
import os

from aiohttp import web

from anony import (
    anon,
    app,
    config,
    db,
    logger,
    stop,
    thumb,
    userbot,
    yt,
)
from anony.plugins import all_modules


async def health(request):
    return web.Response(text="AnonXMusic is running!")


async def start_web_server():
    port = int(os.environ.get("PORT", 10000))

    web_app = web.Application()
    web_app.router.add_get("/", health)

    runner = web.AppRunner(web_app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()

    logger.info(f"Health server started on port {port}")


async def idle():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

    except NotImplementedError:

        def handler(sig, frame):
            loop.call_soon_threadsafe(stop_event.set)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    await stop_event.wait()


async def main():

    # Render Web Service health server
    await start_web_server()

    await db.connect()
    await app.boot()
    await userbot.boot()
    await anon.boot()
    await thumb.start()

    for module in all_modules:
        importlib.import_module(
            f"anony.plugins.{module}"
        )

    logger.info(
        f"Loaded {len(all_modules)} modules."
    )

    if config.COOKIES_URL:
        await yt.save_cookies(
            config.COOKIES_URL
        )

    sudoers = await db.get_sudoers()

    app.sudoers.update(sudoers)

    app.bl_users.update(
        await db.get_blacklisted()
    )

    logger.info(
        f"Loaded {len(app.sudoers)} sudo users."
    )

    await idle()
    await stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass

    except Exception as ex:
        raise SystemExit(ex)
