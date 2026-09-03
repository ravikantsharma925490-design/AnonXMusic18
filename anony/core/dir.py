# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import shutil
from pathlib import Path

from anony import logger


def dirr():
    """
    Ensure that the necessary directories exist.
    """

    if not shutil.which("deno") or not shutil.which("ffmpeg"):
        raise RuntimeError(
            "Deno and FFmpeg must be installed and accessible "
            "in the system PATH."
        )

    for directory in ["cache", "downloads"]:
        Path(directory).mkdir(parents=True, exist_ok=True)

    logger.info("Cache directories updated.")
