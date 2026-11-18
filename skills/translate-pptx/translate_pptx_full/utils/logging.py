import sys
import time
import logging


def setup_logger(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    logger = logging.getLogger("translate_pptx")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


def get_logger():
    return logging.getLogger("translate_pptx")


class ProgressBar:
    def __init__(self, total: int, desc: str = ""):
        self.total = total
        self.desc = desc
        self.current = 0
        self.start_time = time.time()

    def update(self, n: int = 1):
        self.current += n
        if self.total == 0:
            return
        pct = self.current / self.total * 100
        elapsed = time.time() - self.start_time
        bar_len = 30
        filled = int(bar_len * self.current // self.total)
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"\r{self.desc} [{bar}] {pct:.0f}% ({self.current}/{self.total}) {elapsed:.0f}s", end="", file=sys.stderr)
        if self.current >= self.total:
            print(file=sys.stderr)

    def close(self):
        if self.current < self.total:
            self.update(self.total - self.current)
