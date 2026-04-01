from __future__ import annotations
import time
from contextlib import contextmanager

@contextmanager
def timed():
    start = time.perf_counter()
    payload = {}
    yield payload
    payload["elapsed_s"] = time.perf_counter() - start
