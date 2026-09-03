# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import logging
from pyrogram import Client
from .core.bot import Bot
from .core.dir import dirr
from .core.git import git
from .core.userbot import Userbot
from .misc import dbb, heroku, sudo

# 1. Initialize Loggers
logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("anony")

# 2. Directory and Environment configurations 
dirr()
git()
dbb()
heroku()
sudo()

# 3. Structural class declarations
app = Bot()
userbot = Userbot()

# Explicit global class object linking to avoid client spec errors
from .core.custom import Anon
anon = Anon()

__all__ = ["app", "userbot", "anon", "logger"]
