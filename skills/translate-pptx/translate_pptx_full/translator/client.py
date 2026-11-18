import json
import time
import urllib.request
import urllib.error

from ..utils.logging import get_logger


class OllamaClient:
    def __init__(self, url: str, model: str, temperature: float = 0.1,
                 timeout: int = 120, max_retries: int = 3):
        self.url = url
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

    def translate_batch(self, messages: list[dict]) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": 8192},
        }).encode("utf-8")

        req = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
        )

        last_error = None
        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["message"]["content"]
            except (urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    get_logger().warning(f"  Ollama attempt {attempt + 1} failed: {e}, retrying in {wait}s")
                    time.sleep(wait)

        raise RuntimeError(f"Ollama request failed after {self.max_retries} attempts: {last_error}")
