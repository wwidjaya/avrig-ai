#!/usr/bin/env python3
"""
Reusable .docx translator (V3 - segment-based, NO LLM markers).

Translates any language pair through an Ollama LLM while preserving exact
visual styles (bold/italic/underline, fonts, tables, TOC areas).

Coverage: body paragraphs, tables, textboxes, headers/footers (incl.
first-page and even-page variants), footnotes, endnotes, and comments.

How formatting is preserved (V3):
  - Runs are grouped into SEGMENTS by their emphasis state (bold/italic/
    underline) and by whether they are lexical (words) or structural
    (punctuation/whitespace only).
  - Each lexical segment is translated SEPARATELY as one unit, with the
    whole source paragraph supplied as context. Because a bold phrase is
    translated in a single call, its translated words are trivially bold:
    no tags, no markers, no word-alignment heuristics.
  - Structural runs (pure punctuation/spaces) are kept verbatim.
  - The translated segment words are distributed back onto the segment's
    runs proportionally by original word count, preserving each run's own
    font properties and the original leading/trailing spaces.
  - A deterministic typographic polish pass fixes comma/paren spacing,
    glued words, duplicate punctuation, and applies a small built-in
    word-order repair map (e.g. "REPORT FINAL" -> "FINAL REPORT") that can
    be overridden via JSON config.
  - Table-of-contents areas are skipped and copied verbatim.
  - Headers/footers/footnotes/endnotes/comments/textboxes are translated
    with the same run-level preservation.

Usage:
    python3 translate_docx.py input.docx -o output.docx \
        --host 10.30.200.32 --port 11434 --model gemma4:latest
    python3 translate_docx.py input.docx --dry-run
"""
import argparse, json, os, re, sys, time
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from lxml import etree
import requests
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.oxml.parser import parse_xml
from docx.text.paragraph import Paragraph
from docx.text.run import Run

DEFAULT_HOST = '10.30.200.32'
DEFAULT_PORT = '11434'
DEFAULT_MODEL = 'gemma4:latest'
DEFAULT_DELAY = 0.3
DEFAULT_SOURCE_LANG = 'Indonesian'
DEFAULT_TARGET_LANG = 'English'
DEFAULT_TEMPERATURE = 0.1

# Headings that mark auto-generated TOC areas (configurable via config file).
DEFAULT_TOC_HEADINGS = (
    'DAFTAR ISI', 'TABLE OF CONTENTS',
    'DAFTAR TABEL', 'LIST OF TABLES',
    'DAFTAR GAMBAR', 'LIST OF FIGURES',
    'DAFTAR SINGKATAN', 'LIST OF ABBREVIATIONS',
    'DAFTAR LAMPIRAN', 'LIST OF APPENDICES',
)

# Deterministic safety-net word-order fixes applied AFTER translation.
# These are exact-phrase repairs on the translated text (not LLM-dependent).
# Override by passing {"word_repairs": {}} (or your own map) in a JSON config.
DEFAULT_WORD_REPAIRS = {
    'REPORT FINAL': 'FINAL REPORT',               # LAPORAN AKHIR
    'Study Strengthening MPSI': 'MPSI Strengthening Study',  # STUDI PENGUATAN MPSI
    'ISO/IEC 27032 the standard': 'the ISO/IEC 27032 standard',
    'standards ISO/IEC 27032': 'ISO/IEC 27032 standards',
    'with World Bank': 'with the World Bank',
    'Otoritas Jasa Keuangan (OJK)': 'Financial Services Authority (OJK)',
    'Otoritas Jasa Keuangan': 'Financial Services Authority',
    'RAHASIA': 'CONFIDENTIAL',                 # doc classification stamp
}

# Deterministic whole-segment term overrides (exact match, no LLM call).
# These win over any model output, so critical terms can never drift.
DEFAULT_FIXED_TERMS = {
    'RAHASIA': 'CONFIDENTIAL',            # document classification stamp
    'LAPORAN AKHIR': 'FINAL REPORT',      # cover-page report type
    'KLAUSUL KERAHASIAAN': 'CONFIDENTIALITY CLAUSE',  # section heading
}

# Common language names so callers may pass ISO codes (en, id, fr, ...).
_LANG_NAMES = {
    'en': 'English', 'id': 'Indonesian', 'ms': 'Malay', 'fr': 'French',
    'de': 'German', 'es': 'Spanish', 'pt': 'Portuguese', 'it': 'Italian',
    'nl': 'Dutch', 'ru': 'Russian', 'zh': 'Chinese', 'ja': 'Japanese',
    'ko': 'Korean', 'ar': 'Arabic', 'vi': 'Vietnamese', 'th': 'Thai',
    'tr': 'Turkish', 'pl': 'Polish', 'uk': 'Ukrainian', 'hi': 'Hindi',
}


def resolve_lang_name(value):
    """Accept ISO codes or full language names; return a full name."""
    if not value:
        return value
    key = value.strip().lower()
    return _LANG_NAMES.get(key, value.strip())


DEFAULT_CONTEXT_HINT = (
    'This is an official, formal document; use a professional register. '
    'The Indonesian word "RAHASIA" (a document-classification mark) must be '
    'translated as "CONFIDENTIAL", never "SECRET". '
    'Glossary (translate these terms exactly): '
    '"Tim Studi WB" = "World Bank Study Team"; '
    '"Tim Studi Departemen Pengelolaan Sistem Informasi OJK" = "OJK '
    'Information System Management Department Study Team"; '
    '"Studi Penguatan MPSI" = "MPSI Strengthening Study".'
)


@dataclass
class TranslatorConfig:
    """All tunable settings. Fields mirror CLI options / JSON config keys."""
    host: str = DEFAULT_HOST
    port: str = DEFAULT_PORT
    model: str = DEFAULT_MODEL
    source_lang: str = DEFAULT_SOURCE_LANG
    target_lang: str = DEFAULT_TARGET_LANG
    delay: float = DEFAULT_DELAY
    temperature: float = DEFAULT_TEMPERATURE
    skip_toc: bool = True
    toc_headings: tuple = field(
        default_factory=lambda: tuple(DEFAULT_TOC_HEADINGS))
    context_hint: str = DEFAULT_CONTEXT_HINT
    verbose: bool = False
    dry_run: bool = False
    # Typographic cleanup applied after assembly (safe, generic rules).
    fix_punct_spacing: bool = True   # "word ," -> "word,"
    fix_paren_spacing: bool = True   # "( x" -> "(x", "x )" -> "x)"
    dedupe_punct: bool = True        # ", ," -> ","
    split_glued_words: bool = True   # "forWorld" -> "for World"
    word_repairs: dict = field(default_factory=lambda: dict(DEFAULT_WORD_REPAIRS))
    fixed_terms: dict = field(default_factory=lambda: dict(DEFAULT_FIXED_TERMS))
    # whole-segment term overrides, applied BEFORE any LLM call
    sentence_split_threshold: int = 300
    # segments longer than this are split at sentence boundaries so each
    # LLM call stays short (avoids truncation / mixed-language output)
    # exact-phrase replacements applied to the TRANSLATED text after
    # assembly (e.g. {"REPORT FINAL": "FINAL REPORT"}). Built-in map above;
    # override via JSON config ({"word_repairs": {}} disables).

    @classmethod
    def from_dict(cls, data):
        known = {f.name for f in fields(cls)}
        cfg = cls()
        for key, value in (data or {}).items():
            if key in known and value is not None:
                setattr(cfg, key, value)
        cfg.source_lang = resolve_lang_name(cfg.source_lang)
        cfg.target_lang = resolve_lang_name(cfg.target_lang)
        if cfg.toc_headings:
            cfg.toc_headings = tuple(cfg.toc_headings)
        return cfg

    @classmethod
    def from_json(cls, path):
        with open(path, 'r', encoding='utf-8') as fh:
            return cls.from_dict(json.load(fh))

    def with_overrides(self, overrides):
        """Return a copy with CLI overrides applied (None values ignored)."""
        cfg = TranslatorConfig.from_dict(asdict(self))
        known = {f.name for f in fields(self.__class__)}
        for key, value in (overrides or {}).items():
            if key in known and value is not None:
                setattr(cfg, key, value)
        cfg.source_lang = resolve_lang_name(cfg.source_lang)
        cfg.target_lang = resolve_lang_name(cfg.target_lang)
        return cfg

# ---------------------------------------------------------------------------
# Ollama helper
# ---------------------------------------------------------------------------

def check_ollama(host, port):
    url = f'http://{host}:{port}/api/tags'
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return True
    except Exception as exc:
        print(f'  Cannot connect to Ollama at {host}:{port}: {exc}')
        return False


def call_ollama(text, source, target, host, port, model='gemma4:latest',
                extra_rules='', temperature=DEFAULT_TEMPERATURE,
                context_hint=DEFAULT_CONTEXT_HINT, strict=False):
    system = (
        f'You are a professional translator. Translate the following {source} text '
        f'to {target}. CRITICAL rules:\n'
        f'1. Output ONLY the translation -- no explanations, notes, or extra text.\n'
        f'2. Use FORMAL, professional language appropriate for official/government documents.\n'
        f'3. Preserve the EXACT original case when the text is in ALL CAPS.\n'
        f'4. Preserve any numbers, codes, and special characters exactly as-is.\n'
        f'5. Keep acronyms and proper names unchanged.\n'
        f'6. Match the original line breaks if any.\n'
        f'7. Keep any leading/trailing punctuation and spacing from the input.\n'
        f'8. Your ENTIRE output must be written in {target}. Never leave any\n'
        f'   source-language word untranslated; a mixed-language output is a failure.\n'
    )
    if context_hint:
        system = system + f'9. Context: {context_hint}\n'
    if strict:
        system = system + ('\nSTRICT: The text above MUST be translated in full. '
                           'Echoing it back unchanged, or leaving any part in the '
                           'source language, is a FAILURE. Transliterate if unsure.\n')
    if extra_rules:
        system = system + '\n' + extra_rules
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user',
             'content': f'Translate this {source} text to {target}:\n\n{text}'}
        ],
        'stream': False,
        'options': {'temperature': temperature}
    }
    url = f'http://{host}:{port}/api/chat'
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data['message']['content'].strip()
    except Exception as exc:
        print(f'\n  Ollama error: {exc}')
        return text

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _run_fmt(run):
    """Snapshot all font formatting from a run into a dict."""
    clr = run.font.color
    return {
        'bold': run.bold,
        'italic': run.italic,
        'underline': run.underline,
        'font_name': run.font.name,
        'font_size': run.font.size,
        'font_color_rgb': clr.rgb if clr and clr.rgb else None,
        'font_color_theme': clr.theme_color if clr else None,
        'strike': run.font.strike,
        'all_caps': run.font.all_caps,
        'small_caps': run.font.small_caps,
        'superscript': run.font.superscript,
        'subscript': run.font.subscript,
        'highlight_color': run.font.highlight_color,
    }


def _apply_fmt(run, fmt):
    """Apply a formatting dict back to a run."""
    for k, v in fmt.items():
        if v is None:
            continue
        if k == 'bold':
            run.bold = v
        elif k == 'italic':
            run.italic = v
        elif k == 'underline':
            run.underline = v
        elif k == 'font_name':
            run.font.name = v
        elif k == 'font_size':
            run.font.size = v
        elif k == 'font_color_rgb':
            run.font.color.rgb = v
        elif k == 'font_color_theme' and v is not None:
            run.font.color.theme_color = v
        elif k == 'strike':
            run.font.strike = v
        elif k == 'all_caps':
            run.font.all_caps = v
        elif k == 'small_caps':
            run.font.small_caps = v
        elif k == 'superscript':
            run.font.superscript = v
        elif k == 'subscript':
            run.font.subscript = v
        elif k == 'highlight_color':
            run.font.highlight_color = v


# ---------------------------------------------------------------------------
# Run classification
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r'\w')


def is_structural(text):
    """True if text has zero word-characters (pure punctuation/whitespace)."""
    return not bool(_WORD_RE.search(text))


def word_count(text):
    """Count whitespace-separated tokens that contain at least one word char."""
    if not text:
        return 0
    return len([t for t in text.split() if _WORD_RE.search(t)])


def _emphasis_key(fmt):
    """Sorted tuple of emphasis flags that are explicitly True."""
    return tuple(k for k in ('bold', 'italic', 'underline') if fmt.get(k) is True)


# ---------------------------------------------------------------------------
# Table-of-contents detection
# ---------------------------------------------------------------------------

def is_toc_paragraph(para, toc_headings=DEFAULT_TOC_HEADINGS):
    """True if paragraph belongs to an auto-generated TOC area.

    Detects TOC field instructions (w:instrText), TOC entry paragraphs
    (PAGEREF fields), and section headings listed in toc_headings.
    """
    xml = para._p.xml
    if 'instrText' in xml and 'TOC' in xml:
        return True
    if 'PAGEREF' in xml:
        return True
    t = para.text.strip().upper()
    if t in toc_headings:
        return True
    return False

# ---------------------------------------------------------------------------
# Typographic polish (generic, configurable)
# ---------------------------------------------------------------------------

# 'word ,' -> 'word,'
_SPACE_BEFORE_PUNCT_RE = re.compile(r'\s+([,.;:!?])')
# '( x' -> '(x'
_PUNCT_AFTER_PAREN_RE = re.compile(r'\(\s+')
# 'x )' -> 'x)'
_PAREN_BEFORE_RE = re.compile(r'\s+\)')
# ', ,' -> ','   (also '; ;', '. .', ': :')
_DUP_PUNCT_RE = re.compile(r'([,.;:!?])\s+\1')
# glued lowercase->Uppercase inside a word: "forWorld" -> "for World"
_CAMEL_GLUE_RE = re.compile(r'(?<=[a-z])(?=[A-Z])')
# closing paren glued to a word: "(UU PDP)governance" -> "(UU PDP) governance"
_PAREN_GLUE_RE = re.compile(r'\)(?=[A-Za-z])')
# sentence boundary: '. ' / '! ' / '? ' followed by an uppercase letter
# or opening quote/paren (avoids splitting abbreviations like 'No. 5')
_SENT_SEP_RE = re.compile(r'(?<=[.!?])(\s+)(?=[A-Z\u00ab\"\'(])')
# leading punctuation/space to strip before an LLM call and re-attach after
_LEAD_PUNCT_RE = re.compile(r'^[\s,;:]+')

def _apply_word_repairs(active_outputs, repairs):
    """Apply exact-phrase repairs per run AND across run boundaries.

    Per-run first (catches 'REPORT FINAL' inside one run), then boundary
    repairs: if a phrase spans two adjacent runs (e.g. bold 'ISO/IEC 27032'
    followed by ' the standard...'), the replacement is split at the same
    token position so each run keeps its own formatting.
    """
    n = len(active_outputs)
    if not repairs:
        return

    # 4a. Per-run exact-phrase replacements.
    for i in range(n):
        r, txt, fmt = active_outputs[i]
        if not txt:
            continue
        for phrase, replacement in repairs.items():
            if phrase in txt:
                txt = txt.replace(phrase, replacement)
        active_outputs[i] = (r, txt, fmt)

    # 4b. Cross-boundary replacements (phrase spans two adjacent runs).
    sep = '\x0b'  # vertical tab: regex \s (so '\s+' crosses run boundaries) and never in docx text
    for phrase, replacement in repairs.items():
        ptoks = phrase.split()
        rtoks = replacement.split()
        if len(ptoks) < 2 or len(rtoks) < 2:
            continue
        pat = re.compile(
            r'(?<![A-Za-z0-9])' +
            r'\s+'.join(re.escape(tok) for tok in ptoks) +
            r'(?![A-Za-z0-9])')
        for i in range(n - 1):
            ra, ta, fa = active_outputs[i]
            rb, tb, fb = active_outputs[i + 1]
            if not ta or not tb:
                continue
            joined = ta + sep + tb
            m = pat.search(joined)
            if not m:
                continue
            if not (m.start() <= len(ta) < m.end()):
                continue  # phrase fully inside one run (handled in 4a)
            before = m.group(0).split(sep, 1)[0]
            k = len(before.split())          # tokens of phrase before boundary
            if not (0 < k < len(rtoks)):
                continue
            head = ' '.join(rtoks[:k])
            tail = ' '.join(rtoks[k:])
            consumed = ta[m.start():]                     # ta text inside the match
            ta_new = ta[:m.start()] + head + consumed[len(consumed.rstrip()):]  # keep trailing space
            tb_start = len(ta) + 1
            tb_end = m.end() - tb_start      # exclusive index inside tb
            tb_match = tb[:tb_end]
            lead_sp = tb_match[:len(tb_match) - len(tb_match.lstrip())]
            tb_new = lead_sp + tail + tb[tb_end:]
            active_outputs[i] = (ra, ta_new, fa)
            active_outputs[i + 1] = (rb, tb_new, fb)
            break  # one boundary fix per phrase

def _apply_polish_pass(active_outputs, active, cfg):
    """Clean up assembled run texts after segment translation.

    All rules are local, generic, and safe; run objects and their styles
    are never touched, only the text assigned to each run:

      1. per-run: collapse 'word ,' -> 'word,', '( x' -> '(x', 'x )' -> 'x)',
         duplicate punctuation ', ,' -> ','; split glued words
         ('forWorld' -> 'for World', '(UU PDP)governance' -> '(UU PDP) governance');
      2. boundaries: re-insert a space where the SOURCE had one but the
         translation glued two words together; drop stray spaces before
         punctuation / inside parentheses; dedupe identical punctuation
         split across adjacent runs; fix ')' glued to a following word;
      3. strip a stray trailing comma at the very end of the paragraph;
      4. apply cfg.word_repairs (per run AND across run boundaries).

    ``active`` is the parallel list of (run, lead, core, trail, fmt, struct)
    used to build ``active_outputs``; it supplies the original spacing so
    that glue repairs only fire where the source really had a space.
    """
    if not active_outputs:
        return
    orig_spacing = [(lead, trail) for _, lead, _, trail, _, _ in active]
    n = len(active_outputs)

    # 1. Per-run punctuation + glue cleanup.
    for i in range(n):
        r, txt, fmt = active_outputs[i]
        if not txt:
            continue
        if cfg.split_glued_words:
            txt = _CAMEL_GLUE_RE.sub(' ', txt)
            txt = _PAREN_GLUE_RE.sub(') ', txt)
        if cfg.fix_punct_spacing:
            txt = _SPACE_BEFORE_PUNCT_RE.sub(r'\1', txt)
            txt = _PUNCT_AFTER_PAREN_RE.sub('(', txt)
            txt = _PAREN_BEFORE_RE.sub(')', txt)
        if cfg.dedupe_punct:
            txt = _DUP_PUNCT_RE.sub(r'\1', txt)
        active_outputs[i] = (r, txt, fmt)

    # 2. Boundary rules between adjacent runs.
    for i in range(n - 1):
        r_a, txt_a, fmt_a = active_outputs[i]
        r_b, txt_b, fmt_b = active_outputs[i + 1]
        if not txt_a or not txt_b:
            continue
        src_had_space = bool(orig_spacing[i][1]) or bool(orig_spacing[i + 1][0])
        # (a) glue: source had a space but translation merged two words.
        if (src_had_space and txt_a[-1].isalnum() and txt_b[0].isalnum()
                and not txt_a[-1].isspace() and not txt_b[0].isspace()):
            txt_a = txt_a + ' '
        # (b) 'word ,' -> 'word,': drop trailing space before punctuation.
        if txt_a.endswith(' ') and txt_b[0] in ',.;:!?':
            txt_a = txt_a.rstrip()
        # (c) '( x' -> '(x': drop leading space after an opening paren.
        if txt_a.endswith('(') and txt_b.startswith(' '):
            txt_b = txt_b.lstrip()
        # (d) 'x )' -> 'x)': drop leading space before a closing paren.
        if txt_b.startswith(' ') and txt_b.lstrip().startswith(')'):
            txt_b = txt_b.lstrip()
        # (e) dedupe identical punctuation split across the boundary.
        if txt_a and txt_b and txt_a[-1] in ',.;:!?' and txt_b[0] == txt_a[-1]:
            txt_b = txt_b[1:] if len(txt_b) > 1 else ''
        # (f) 'x)' + word: source had a space, paren glued to next word.
        if (cfg.split_glued_words and src_had_space
                and txt_a.rstrip().endswith(')') and txt_b[0].isalnum()
                and not txt_b[0].isspace()):
            txt_a = txt_a + ' '
        active_outputs[i] = (r_a, txt_a, fmt_a)
        active_outputs[i + 1] = (r_b, txt_b, fmt_b)

    # 3. Strip stray trailing comma(s) at the very end of the paragraph.
    for j in range(n - 1, -1, -1):
        r, txt, fmt = active_outputs[j]
        if txt and txt.strip():
            txt = txt.rstrip().rstrip(',')
            active_outputs[j] = (r, txt, fmt)
            break

    # 4. Exact-phrase repairs (per run + across run boundaries).
    _apply_word_repairs(active_outputs, cfg.word_repairs)

# ---------------------------------------------------------------------------
# Config loading (reusable, config-driven)
# ---------------------------------------------------------------------------

def load_config(args):
    """Build a TranslatorConfig: JSON config file -> CLI overrides.

    word_repairs ALWAYS starts from the built-in DEFAULT_WORD_REPAIRS map so
    that CLI-only runs get the same deterministic fixes as configured runs;
    a JSON "word_repairs" object merges on top (per-key override).
    """
    cfg = TranslatorConfig()
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        if isinstance(data.get('word_repairs'), dict):
            data['word_repairs'] = {
                **DEFAULT_WORD_REPAIRS, **data['word_repairs']}
        if isinstance(data.get('fixed_terms'), dict):
            data['fixed_terms'] = {
                **DEFAULT_FIXED_TERMS, **data['fixed_terms']}
        cfg = TranslatorConfig.from_dict(data)
    cfg = cfg.with_overrides({
        'source_lang': args.source_lang,
        'target_lang': args.target_lang,
        'model': args.model,
        'host': args.host,
        'port': args.port,
        'temperature': args.temperature,
        'delay': args.delay,
        'context_hint': args.context_hint,
        'verbose': True if args.verbose else None,
    })
    if args.verbose:
        print(f'  Model    : {cfg.model}  (temp={cfg.temperature})')
        print(f'  Endpoint : http://{cfg.host}:{cfg.port}')
        print(f'  Languages: {cfg.source_lang} -> {cfg.target_lang}')
        print(f'  Config   : {args.config or "(built-in defaults)"}')
        print(f'  Repairs  : {cfg.word_repairs}')
    return cfg


# ---------------------------------------------------------------------------
# Translator engine (segment-based)
# ---------------------------------------------------------------------------

class Translator:
    """Translates paragraphs & tables while preserving run-level styling.

    Approach: no marker tags. Contiguous runs sharing identical formatting
    are grouped into segments; each segment is translated in a single LLM
    call (so e.g. the whole bold phrase "LAPORAN AKHIR" becomes one
    translation unit), and the translated words are distributed back onto
    the segment's runs proportionally to the original word counts, keeping
    each run's own font properties and original leading/trailing spaces.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.translated = 0      # LLM calls made
        self.cached = 0          # reuses from exact-text cache
        self.skipped = 0         # TOC / empty / structural paragraphs
        self.failed = 0
        self.text_cache = {}     # exact source text -> translation
        self._seg_counter = 0
        self._para_counter = 0
        self.where_counts = Counter()   # location kind -> translated count

    # -- helpers ----------------------------------------------------------

    def _next_seg_id(self, para_idx):
        self._seg_counter += 1
        return f'p{para_idx}s{self._seg_counter}'

    def _translate_text(self, text, para_id=None, context_hint=None):
        """Translate ``text`` via Ollama with exact-text dedupe.

        Deterministic glossary wins over everything (fixed_terms, exact whole-
        segment match, no LLM call); long segments are split at sentence
        boundaries so each LLM call stays short and complete.
        """
        if not text.strip():
            return text
        if self.cfg.dry_run:
            self.translated += 1
            return text
        key = text.strip().upper()
        if key in self.cfg.fixed_terms:
            return self.cfg.fixed_terms[key]
        if text in self.text_cache:
            self.cached += 1
            return self.text_cache[text]
        out = self._call_translator(text, context_hint)
        if out == text:
            self.failed += 1
        else:
            self.translated += 1
            self.text_cache[text] = out
        if self.cfg.delay:
            time.sleep(self.cfg.delay)
        return out

    @staticmethod
    def _split_sentences(text):
        """Split into [sentence, separator, sentence, ..., tail] parts."""
        parts, last = [], 0
        for m in _SENT_SEP_RE.finditer(text):
            parts.append(text[last:m.start()])
            parts.append(m.group(1))
            last = m.end()
        parts.append(text[last:])
        return parts

    def _call_translator(self, text, context_hint=None):
        """One Ollama call, or several if the segment is long.

        Leading punctuation/space is stripped before the call and re-attached
        afterwards so the model never echoes a bare punctuation fragment; if
        the model returns the input unchanged, one strict retry is attempted.
        """
        m = _LEAD_PUNCT_RE.match(text)
        lead = m.group(0) if m else ''
        core = text[len(lead):] if lead else text
        if not core.strip():
            return text

        def _one(part, strict=False):
            out = call_ollama(
                part, self.cfg.source_lang, self.cfg.target_lang,
                self.cfg.host, self.cfg.port, self.cfg.model,
                temperature=self.cfg.temperature,
                context_hint=context_hint or self.cfg.context_hint,
                strict=strict)
            if out.strip() == part.strip():
                out = call_ollama(
                    part, self.cfg.source_lang, self.cfg.target_lang,
                    self.cfg.host, self.cfg.port, self.cfg.model,
                    temperature=self.cfg.temperature,
                    context_hint=context_hint or self.cfg.context_hint,
                    strict=True)      # echoed input: retry with STRICT rules
            return out

        if len(core) <= self.cfg.sentence_split_threshold:
            out = _one(core)
        else:
            parts = self._split_sentences(core)
            # group sentences into chunks of at most `threshold` characters
            groups, cur, cur_len = [], '', 0
            for idx in range(0, len(parts), 2):
                sent = parts[idx]
                sep = parts[idx + 1] if idx + 1 < len(parts) else ''
                if cur and cur_len + len(sent) + 1 > self.cfg.sentence_split_threshold:
                    groups.append(cur)
                    cur, cur_len = '', 0
                cur += sent
                cur_len += len(sent)
                if sep:
                    cur += sep
                    cur_len += len(sep)
            if cur:
                groups.append(cur)
            if len(groups) < 2:
                out = _one(core)      # split failed; fall back to whole core
            else:
                outs = [_one(g.strip()) for g in groups if g.strip()]
                out = ' '.join(outs)  # chunks joined with a single space
        if lead:
            out = lead + out.lstrip()
        return out

    def _runs_of(self, para):
        """All Run objects in a paragraph, including hyperlink-nested ones."""
        return [Run(r, para) for r in para._p.iter(qn('w:r'))]

    def _segments_of(self, active):
        """Group consecutive active entries whose FULL formatting dicts match.

        Entries with identical (bold, italic, underline, font name, size,
        color, ...) belong to one segment and are translated as one unit.
        """
        segs = []
        for entry in active:
            if segs and segs[-1][-1][4] == entry[4]:
                segs[-1].append(entry)
            else:
                segs.append([entry])
        return segs

    @staticmethod
    def _has_emphasis(active):
        return any(entry[4].get(k) is True
                   for entry in active for k in ('bold', 'italic', 'underline'))

    def _distribute(self, out_text, entries):
        """Split a translated segment across its runs proportionally.

        Returns one text piece per entry (same order). Entries whose core
        was purely structural (no words) receive an empty piece and are kept
        verbatim by the caller. Whitespace splits are plain single spaces;
        the original lead/trail spacing is re-applied by the caller.
        """
        words = out_text.split()
        counts = [word_count(e[2]) for e in entries]
        total = sum(counts)
        if total == 0 or not words:
            return [''] * len(entries)
        assigned = []
        remaining = len(words)
        for i, c in enumerate(counts):
            if i == len(counts) - 1:
                n = remaining
            else:
                n = min(round(c / total * len(words)), remaining)
            assigned.append(n)
            remaining -= n
        texts, start = [], 0
        for n in assigned:
            texts.append(' '.join(words[start:start + n]))
            start += n
        return texts

    # -- paragraph translation --------------------------------------------

    def _translate_paragraph(self, para, para_idx):
        runs = self._runs_of(para)
        if not runs:
            return False
        joined = ''.join(r.text for r in runs)
        if not joined.strip():
            return False
        if is_structural(joined):
            return False  # pure numbers / punctuation / whitespace

        # (run, lead, core, trail, fmt, is_structural) per run
        active = []
        for run in runs:
            t = run.text
            lead = t[:len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            core = t[len(lead):len(t) - len(trail)] if trail else t[len(lead):]
            # Pure-spacing runs (empty core) are not structural: they must not
            # poison the segment-level verbatim check (any(e[5]) below).
            struct = is_structural(core) if core.strip() else False
            active.append((run, lead, core, trail, _run_fmt(run), struct))

        if not self._has_emphasis(active):
            # Plain paragraph: one translation call for the whole text, kept
            # in the first run; remaining runs are blanked (styles intact).
            out = self._translate_text(joined, para_id=f'p{para_idx}')
            active_outputs = []
            assigned = False
            for (run, lead, core, trail, fmt, struct) in active:
                if assigned:
                    active_outputs.append((run, '', fmt))
                else:
                    active_outputs.append((run, lead + out + trail, fmt))
                    assigned = True
        else:
            # Emphasis paragraph: translate each segment separately with the
            # full paragraph as context; structural runs kept verbatim.
            para_hint = ('This text is a segment of the following paragraph: '
                         f'"{joined[:300]}". Translate the segment so it fits '
                         'that paragraph naturally, keeping formal official '
                         'register and preserving the segment meaning exactly.')
            active_outputs = []
            for seg in self._segments_of(active):
                if any(e[5] for e in seg) or is_structural(
                        ''.join(e[2] for e in seg)):
                    # verbatim structural segment
                    for (run, lead, core, trail, fmt, struct) in seg:
                        active_outputs.append((run, lead + core + trail, fmt))
                    continue
                seg_text = ''.join(e[2] for e in seg)
                out = self._translate_text(
                    seg_text, para_id=self._next_seg_id(para_idx),
                    context_hint=para_hint)
                pieces = self._distribute(out, seg)
                for (run, lead, core, trail, fmt, struct), piece in zip(
                        seg, pieces):
                    if struct:
                        active_outputs.append((run, lead + core + trail, fmt))
                    else:
                        active_outputs.append((run, lead + piece + trail, fmt))

        _apply_polish_pass(active_outputs, active, self.cfg)
        for (run, txt, fmt) in active_outputs:
            run.text = txt
            _apply_fmt(run, fmt)
        return True

    # -- tables ------------------------------------------------------------

    def _translate_table(self, table, table_idx):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if is_toc_paragraph(para, self.cfg.toc_headings):
                        self.skipped += 1
                        continue
                    self._translate_paragraph(para, f't{table_idx}')

    # -- container traversal ----------------------------------------------

    def _translate_para_el(self, para_el, doc, where):
        """Translate a single ``w:p`` element (or skip it) and report counts."""
        idx = self._para_counter
        self._para_counter += 1
        para = Paragraph(para_el, doc)
        if is_toc_paragraph(para, self.cfg.toc_headings):
            self.skipped += 1
            return False
        try:
            ok = self._translate_paragraph(para, idx)
        except Exception as exc:
            self.failed += 1
            print(f'  [warn] {where} paragraph {idx}: {exc}')
            return False
        if ok:
            self.where_counts[where] += 1
            if self.cfg.verbose:
                print(f'  [{idx:>3} {where}] {para.text[:70]}')
        return ok

    def _translate_container(self, container, doc, where):
        """Recursively translate paragraphs/tables/textboxes in a container.

        ``container`` is any XML element holding block content: the document
        body, a table cell, an SDT content node, a textbox (``w:txbxContent``),
        a header/footer root, a footnote/endnote node, or a comment node.
        Paragraphs containing textboxes are handled through the textbox (the
        outer paragraph itself carries no text); runs inside hyperlinks are
        translated like any other run.
        """
        for child in list(container.iterchildren()):
            tag = child.tag
            if tag == qn('w:p'):
                txbxs = child.findall('.//' + qn('w:txbxContent'))
                if txbxs:
                    for tb in txbxs:
                        self._translate_container(tb, doc, 'textbox')
                else:
                    self._translate_para_el(child, doc, where)
            elif tag == qn('w:tbl'):
                for row in child.iterchildren(qn('w:tr')):
                    for cell in row.iterchildren(qn('w:tc')):
                        self._translate_container(cell, doc, 'table_cell')
            elif tag == qn('w:sdt'):
                sdt_content = child.find(qn('w:sdtContent'))
                if sdt_content is not None:
                    self._translate_container(sdt_content, doc, where)

    # -- document ----------------------------------------------------------

    def translate_document(self, doc):
        self._para_counter = 0
        self.where_counts = Counter()

        # Body: paragraphs, tables, textboxes (incl. inside SDTs).
        self._translate_container(doc.element.body, doc, 'paragraph')

        # Headers & footers per section (linked ones are inherited: skipped).
        seen_parts = set()
        for section in doc.sections:
            for hf, kind in (
                    (section.header, 'header'),
                    (section.footer, 'footer'),
                    (section.first_page_header, 'first_page_header'),
                    (section.first_page_footer, 'first_page_footer'),
                    (section.even_page_header, 'even_page_header'),
                    (section.even_page_footer, 'even_page_footer')):
                if hf is None or hf.is_linked_to_previous:
                    continue
                part = hf.part
                if id(part) in seen_parts:
                    continue
                seen_parts.add(id(part))
                self._translate_container(part.element, doc, kind)

        # Footnotes & endnotes (auto-numbered entries have id > 0).
        # These parts may be opaque (plain Part without a live element tree),
        # so parse, translate, and re-serialize them.
        for reltype, tag, kind in (
                (RT.FOOTNOTES, 'w:footnote', 'footnote'),
                (RT.ENDNOTES, 'w:endnote', 'endnote')):
            try:
                part = doc.part.rels.part_with_reltype(reltype)
            except KeyError:
                continue
            if hasattr(part, 'element'):
                root, opaque = part.element, False
            else:
                root = parse_xml(part._blob)
                opaque = True
            for node in root.iterchildren(qn(tag)):
                try:
                    fid = int(node.get(qn('w:id')) or 0)
                except (TypeError, ValueError):
                    fid = 0
                if fid <= 0:
                    continue
                self._translate_container(node, doc, kind)
            if opaque:
                part._blob = etree.tostring(
                    root, xml_declaration=True, encoding='UTF-8', standalone=True)

        # Comments.
        try:
            cmt_part = doc.part.rels.part_with_reltype(RT.COMMENTS)
        except KeyError:
            cmt_part = None
        if cmt_part is not None:
            for node in cmt_part.element.iterchildren(qn('w:comment')):
                self._translate_container(node, doc, 'comment')

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog='translate_docx.py',
        description='Translate a .docx via an Ollama LLM, preserving visual '
                    'styles (bold/italic/underline, fonts, tables, TOC, '
                    'headers/footers, footnotes, endnotes, comments).')
    p.add_argument('input', help='Path to the input .docx file')
    p.add_argument('-o', '--output', help='Output .docx path '
                   '(default: <input>_translated.docx)')
    p.add_argument('--host', default=None, help=f'Ollama host '
                   f'(default: {DEFAULT_HOST})')
    p.add_argument('--port', default=None, help=f'Ollama port '
                   f'(default: {DEFAULT_PORT})')
    p.add_argument('--model', default=None, help=f'Model name '
                   f'(default: {DEFAULT_MODEL})')
    p.add_argument('--source', dest='source_lang', default=None,
                   help='Source language name or ISO code (default: '
                        f'{DEFAULT_SOURCE_LANG})')
    p.add_argument('--target', dest='target_lang', default=None,
                   help='Target language name or ISO code (default: '
                        f'{DEFAULT_TARGET_LANG})')
    p.add_argument('--temperature', type=float, default=None,
                   help=f'LLM temperature (default: {DEFAULT_TEMPERATURE})')
    p.add_argument('--delay', type=float, default=None,
                   help=f'Seconds to sleep between LLM calls '
                        f'(default: {DEFAULT_DELAY})')
    p.add_argument('--config', help='Optional JSON config file '
                   '(keys mirror TranslatorConfig fields)')
    p.add_argument('--context-hint', dest='context_hint', default=None,
                   help='Extra register/terminology guidance for the LLM')
    p.add_argument('--dry-run', action='store_true',
                   help='Scan the document and report what would be '
                        'translated, without calling the LLM')
    p.add_argument('-v', '--verbose', action='store_true',
                   help='Print per-paragraph progress')
    return p.parse_args(argv)


def main():
    args = parse_args()
    cfg = load_config(args)

    doc = Document(args.input)

    if args.dry_run:
        cfg = cfg.with_overrides({'dry_run': True})
        tr = Translator(cfg)
        tr.translate_document(doc)
        print(f'Input : {args.input}')
        print('Output: ' + (args.output
                            or os.path.splitext(args.input)[0]
                            + '_translated.docx'))
        print('Dry-run scan (no LLM calls):')
        print(f'  Would translate : {tr.translated} segments '
              f'(TOC/empty/structural skipped: {tr.skipped})')
        if tr.where_counts:
            kinds = ', '.join(f'{k}: {v}'
                              for k, v in tr.where_counts.most_common())
            print(f'  By location    : {kinds}')
        return

    if not check_ollama(cfg.host, cfg.port):
        print(f'  Aborting: no Ollama at http://{cfg.host}:{cfg.port}')
        sys.exit(1)

    tr = Translator(cfg)
    tr.translate_document(doc)

    out_path = args.output or (
        os.path.splitext(args.input)[0] + '_translated.docx')
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    doc.save(out_path)

    print(f'\nSaved: {out_path}')
    print(f'  LLM calls : {tr.translated}'
          + (f'  (cached: {tr.cached})' if tr.cached else ''))
    print(f'  Skipped   : {tr.skipped}  (TOC / structural / empty)')
    if tr.failed:
        print(f'  Warnings  : {tr.failed}  (paragraphs left untranslated)')


if __name__ == '__main__':
    main()
