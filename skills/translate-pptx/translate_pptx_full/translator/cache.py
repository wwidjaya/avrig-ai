import json
import hashlib

from ..utils.logging import get_logger


class TranslationCache:
    def __init__(self, cache_path: str = ""):
        self.cache_path = cache_path
        self._cache: dict[str, str] = {}
        if cache_path:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                get_logger().info(f"Loaded {len(self._cache)} cached translations from {cache_path}")
            except (FileNotFoundError, json.JSONDecodeError):
                pass

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> str | None:
        return self._cache.get(self._key(text))

    def set(self, text: str, translation: str):
        self._cache[self._key(text)] = translation

    def save(self):
        if self.cache_path:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
