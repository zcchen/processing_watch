#!/usr/bin/env python
# -*-   encoding : utf8   -*-

import sys

if sys.version_info.major != 3:
    raise ImportError("Python 3.4+ is need")
elif sys.version_info.major == 3 and not sys.version_info.minor >= 4:
    raise ImportError("Python 3.4+ is need")

import multiprocessing
import concurrent
import asyncio

__all__ = ["process"]

from processing_watch._base import (_watch_dog_interval,
                                    __base_process,
                                   )
from processing_watch.process import process
