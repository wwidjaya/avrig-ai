import json
import re
import time

from ..utils.logging import get_logger, ProgressBar
from ..config import Config
from .client import OllamaClient
from .prompt import (
    format_system_prompt,
    format_paragraph_system_prompt,
    format_user_prompt,
)
from ..models.manifest import TranslationManifest


def translate_all(manifest: TranslationManifest, config: Config, logger=None):
    system_prompt = format_system_prompt(config.source_lang, config.target_lang)
    _translate(manifest, config, logger, system_prompt)


def translate_paragraphs(manifest: TranslationManifest, config: Config, logger=None):
    system_prompt = format_paragraph_system_prompt(config.source_lang, config.target_lang)
    _translate(manifest, config, logger, system_prompt)


def _translate(manifest: TranslationManifest, config: Config, logger=None, system_prompt: str = ""):
    client = OllamaClient(
        url=config.ollama_url,
        model=config.model,
        temperature=config.temperature,
        timeout=config.timeout,
        max_retries=config.max_retries,
    )

    segments = manifest.segments
    total = len(segments)

    if logger:
        logger.info(f"Translating {total} segments via {config.model}")

    already = sum(1 for s in segments if s.translated_text)
    if logger and already:
        logger.info(f"  {already} already translated, skipping")

    bar = ProgressBar(total, "Translate")
    for start in range(0, total, config.batch_size):
        batch = segments[start:start + config.batch_size]

        untranslated = [s for s in batch if not s.translated_text]
        if not untranslated:
            bar.update(len(batch))
            continue

        batch_data = [{"id": s.id, "text": s.original_text} for s in untranslated]
        user_prompt = format_user_prompt(batch_data, config.source_lang, config.target_lang)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if config.dry_run:
            if logger:
                logger.info(f"  [dry-run] Would translate {len(batch_data)} segments")
            bar.update(len(batch))
            continue

        if logger:
            logger.debug(f"  Batch {start // config.batch_size}: {len(batch_data)} segments")

        try:
            reply = client.translate_batch(messages)
            translations = _parse_translations(reply)
        except RuntimeError as e:
            if logger:
                logger.error(f"  Batch failed: {e}")
            if config.mode == "strict":
                raise
            bar.update(len(batch))
            continue

        if translations:
            applied = 0
            for s in untranslated:
                if s.id in translations:
                    s.translated_text = translations[s.id]
                    manifest.set_translation(s.id, translations[s.id])
                    applied += 1
            if logger and applied < len(untranslated):
                logger.warning(f"  Got {applied}/{len(untranslated)} translations in batch")
        else:
            if logger:
                logger.warning("  Could not parse translations from response")

        if not config.dry_run:
            bar.update(len(batch))
        time.sleep(0.5)

    bar.close()
    if logger:
        tc = manifest.translated_count()
        logger.info(f"Translated {tc}/{total} segments")


def _parse_translations(text: str) -> dict:
    """Tolerant parser for LLM JSON-ish responses.

    gemma4 often emits valid JSON, but sometimes drops the quotes around
    values. Strategy: strict json.loads first; if that fails, fall back to a
    scan for `"id": value` / `id: value` pairs where the value runs until the
    next key (line-based, unquoted values allowed).
    """
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        raw = m.group()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): v for k, v in parsed.items() if isinstance(v, str)}
        except json.JSONDecodeError:
            pass

        # tolerant line-based parse: "id": value  (value may be unquoted)
        result = {}
        for line in raw.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in ("{", "}"):
                continue
            m2 = re.match(r'^"?([\w.:\-]+)"?\s*:\s*(".*"|.*)$', line, re.DOTALL)
            if m2:
                key, val = m2.group(1), m2.group(2).strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if val:
                    result[key] = val
        if result:
            return result

    # last resort: line-by-line "id|text"
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        m2 = re.match(r'(\d+|[\w]+)\|(.+)', line)
        if m2:
            result[m2.group(1)] = m2.group(2).strip()
    return result
