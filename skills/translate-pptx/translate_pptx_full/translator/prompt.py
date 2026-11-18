SYSTEM_PROMPT_TEMPLATE = (
    "You are a professional {source_lang}-to-{target_lang} translator. "
    "Translate the text faithfully into natural, formal {target_lang}.\n"
    "Rules:\n"
    "- Preserve the original meaning exactly.\n"
    "- Do not summarize, explain, or add information.\n"
    "- Preserve headings, numbering, tables, and formatting.\n"
    "- Keep official terms and abbreviations (e.g., OJK, MPSI, DPSI, SLA, API, SDK, IoT, AI, ML) unless an official English equivalent exists.\n"
    "- Keep proper names (people, companies, document codes) as-is.\n"
    "- Output ONLY a JSON object mapping each ID to its translation. No other text."
)

PARAGRAPH_SYSTEM_PROMPT_TEMPLATE = (
    "You are a professional {source_lang}-to-{target_lang} translator. "
    "Translate the text faithfully into natural, formal {target_lang}.\n"
    "Rules:\n"
    "- Translate EACH segment as one coherent unit. Check and fix the grammar so the whole segment reads naturally and flows well.\n"
    "- Translate into natural, idiomatic {target_lang}: compound phrases are reordered so the HEAD NOUN comes LAST (e.g., 'Studi Penguatan Kebijakan' -> 'Policy Strengthening Study'). NEVER translate word-for-word if that yields ungrammatical {target_lang}.\n"
    "- Preserve parenthetical numeral spell-outs exactly: translate '16 (enam belas)' as '16 (sixteen)' — never omit the parenthetical.\n"
    "- Preserve the original meaning exactly.\n"
    "- Do not summarize, explain, or add information.\n"
    "- Preserve headings, numbering, lists, and inline structure (punctuation, line breaks).\n"
    "- Keep official terms and abbreviations (e.g., OJK, MPSI, DPSI, SLA, API, SDK, IoT, AI, ML) unless an official English equivalent exists.\n"
    "- Keep proper names (people, companies, document codes) as-is.\n"
    "- Output ONLY a JSON object mapping each ID to its translation. No other text."
)


USER_PROMPT_TEMPLATE = (
    "Translate each of the following {source_lang} texts to {target_lang}. "
    "Return ONLY a JSON object like {{\"id_1\": \"translation_1\", \"id_2\": \"translation_2\", ...}}.\n\n"
    "{segments_text}"
)


def format_system_prompt(source_lang: str, target_lang: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(source_lang=source_lang, target_lang=target_lang)


def format_paragraph_system_prompt(source_lang: str, target_lang: str) -> str:
    return PARAGRAPH_SYSTEM_PROMPT_TEMPLATE.format(source_lang=source_lang, target_lang=target_lang)


def format_user_prompt(segments: list, source_lang: str, target_lang: str) -> str:
    lines = [f'{s["id"]}|{s["text"]}' for s in segments]
    return USER_PROMPT_TEMPLATE.format(
        source_lang=source_lang,
        target_lang=target_lang,
        segments_text="\n".join(lines),
    )
