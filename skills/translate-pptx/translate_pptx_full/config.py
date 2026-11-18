from dataclasses import dataclass, field


DEFAULT_OLLAMA_URL = "http://10.30.200.32:11434/api/chat"
DEFAULT_MODEL = "gemma4"
DEFAULT_BATCH_SIZE = 50
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TIMEOUT = 120
DEFAULT_MAX_RETRIES = 3


@dataclass
class Config:
    ollama_url: str = DEFAULT_OLLAMA_URL
    model: str = DEFAULT_MODEL
    batch_size: int = DEFAULT_BATCH_SIZE
    temperature: float = DEFAULT_TEMPERATURE
    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    cache_path: str = ""
    force: bool = False
    dry_run: bool = False
    mode: str = "resilient"
    output_path: str = ""
    source_lang: str = "Indonesian"
    target_lang: str = "English"
    format_mode: str = "align"          # align | positional
