# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

from config import Config

config = Config()
config.check()

from .logging import logger

from anony.core.dir import dirr
from anony.core.git import git
from anony.misc import dbb, heroku, sudo
from anony.core.bot import Bot
from anony.core.userbot import Userbot

dirr()
git()
dbb()
heroku()
sudo()

app = Bot()
userbot = Userbot()
