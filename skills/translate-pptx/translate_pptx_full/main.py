#!/usr/bin/env python3
"""translate_pptx_full.py — Full PPTX translation pipeline (ID → EN via Ollama).

Usage:
    python translate_pptx_full.py input.pptx
    python translate_pptx_full.py input.pptx -o output.pptx
    python translate_pptx_full.py input.pptx --phase extract
    python translate_pptx_full.py input.pptx --phase translate --resume
    python translate_pptx_full.py input.pptx --phase apply
    python translate_pptx_full.py input.pptx --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .utils.logging import setup_logger
from .models.manifest import TranslationManifest
from .extractor.engine import extract_all
from .extractor.paragraph_engine import extract_paragraphs
from .translator.batcher import translate_all, translate_paragraphs
from .applier.engine import apply_all
from .applier.paragraph_engine import apply_paragraphs


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Translate PPTX files (Indonesian to English) via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pptx                           # full pipeline (paragraph mode)
  %(prog)s input.pptx --unit run                # run-level mode (per-run translation)
  %(prog)s input.pptx -o translated.pptx        # custom output
  %(prog)s input.pptx --phase extract           # extract only
  %(prog)s input.pptx --phase translate         # translate existing JSON
  %(prog)s input.pptx --phase apply             # apply existing translations
  %(prog)s input.pptx --dry-run                 # stats only, no API calls
        """,
    )
    parser.add_argument("input", help="Path to input .pptx file")
    parser.add_argument("-o", "--output", help="Output .pptx path (default: input.en.pptx)")
    parser.add_argument("--unit", choices=["paragraph", "run"], default="paragraph",
                        help="Translation unit: paragraph (grammar-coherent, run-split) or run (default: paragraph)")
    parser.add_argument("--format-mode", choices=["align", "positional"], default="align",
                        help="How formatting is preserved for paragraph mode: "
                             "align (LLM word-alignment, style follows original word, default), "
                             "positional (proportional split)")
    parser.add_argument("--phase", choices=["all", "extract", "translate", "apply"],
                        default="all", help="Pipeline phase to run (default: all)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing segments.json (skip already-translated)")

    parser.add_argument("--ollama-url", default=Config.ollama_url,
                        help=f"Ollama API URL (default: {Config.ollama_url})")
    parser.add_argument("--model", default=Config.model,
                        help=f"Ollama model (default: {Config.model})")
    parser.add_argument("--temperature", type=float, default=Config.temperature,
                        help=f"LLM temperature (default: {Config.temperature})")
    parser.add_argument("--batch-size", type=int, default=Config.batch_size,
                        help=f"Batch size (default: {Config.batch_size})")
    parser.add_argument("--timeout", type=int, default=Config.timeout,
                        help=f"Ollama timeout in seconds (default: {Config.timeout})")
    parser.add_argument("--max-retries", type=int, default=Config.max_retries,
                        help=f"Max retries per batch (default: {Config.max_retries})")

    parser.add_argument("--cache", default="", help="Translation cache file path")
    parser.add_argument("--force", action="store_true", help="Force re-translation (ignore cache)")
    parser.add_argument("--dry-run", action="store_true", help="Extract + estimate only, no API calls")
    parser.add_argument("--mode", choices=["strict", "resilient"], default="resilient",
                        help="Error handling mode (default: resilient)")
    parser.add_argument("--source-lang", default=Config.source_lang,
                        help=f"Source language (default: {Config.source_lang})")
    parser.add_argument("--target-lang", default=Config.target_lang,
                        help=f"Target language (default: {Config.target_lang})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    logger = setup_logger(args.verbose)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    config = Config(
        ollama_url=args.ollama_url,
        model=args.model,
        batch_size=args.batch_size,
        temperature=args.temperature,
        timeout=args.timeout,
        max_retries=args.max_retries,
        cache_path=args.cache,
        force=args.force,
        dry_run=args.dry_run,
        mode=args.mode,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        format_mode=args.format_mode,
    )

    segments_path = input_path.parent / f"{input_path.stem}.segments.json"

    if args.output:
        output_path = args.output
    else:
        output_path = str(input_path.parent / f"{input_path.stem}.en.pptx")

    manifest = TranslationManifest(source_path=str(input_path), unit=args.unit)

    # ── Phase 1: Extract ──
    if args.phase in ("all", "extract"):
        logger.info(f"Phase 1: Extracting text from {input_path} ({args.unit} mode)")
        if args.unit == "paragraph":
            segs = extract_paragraphs(str(input_path), logger)
        else:
            segs = extract_all(str(input_path), logger)
        for s in segs:
            manifest.add_segment(s)
        with open(segments_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(segs)} segments to {segments_path}")

        if args.dry_run:
            logger.info(f"[dry-run] Extraction complete. Would translate {len(segs)} segments.")
            return

        if args.phase == "extract":
            logger.info("Extract phase complete. Run with --phase translate to continue.")
            return

    # ── Phase 2: Translate ──
    if args.phase in ("all", "translate"):
        if args.resume or args.phase == "translate":
            if segments_path.exists():
                with open(segments_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                manifest = TranslationManifest.from_dict(data)
                logger.info(f"Loaded {len(manifest.segments)} segments from {segments_path}")
            else:
                logger.error(f"No segments file found at {segments_path}. Run extract phase first.")
                sys.exit(1)

        logger.info(f"Phase 2: Translating {len(manifest.segments)} segments via {config.model}")
        if args.unit == "paragraph":
            translate_paragraphs(manifest, config, logger)
        else:
            translate_all(manifest, config, logger)

        with open(segments_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved translations to {segments_path}")

        if args.phase == "translate":
            logger.info("Translate phase complete. Run with --phase apply to generate PPTX.")
            return

    # ── Phase 3: Apply ──
    if args.phase in ("all", "apply"):
        if args.phase == "apply":
            if segments_path.exists():
                with open(segments_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                manifest = TranslationManifest.from_dict(data)
                logger.info(f"Loaded {len(manifest.segments)} segments from {segments_path}")
            else:
                logger.error(f"No segments file found at {segments_path}. Run extract+translate first.")
                sys.exit(1)

        logger.info(f"Phase 3: Applying translations to {output_path}")
        if args.unit == "paragraph":
            apply_paragraphs(manifest, output_path, config, logger)
        else:
            apply_all(manifest, output_path, logger)

        tc = manifest.translated_count()
        sc = manifest.skipped_count()
        logger.info(f"Done. {tc} translated, {sc} skipped.")

        # Generate sidecar report
        report_path = input_path.parent / f"{input_path.stem}.report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Translation Report: {input_path.name}\n\n")
            f.write(f"**Source:** {config.source_lang} → {config.target_lang}\n")
            f.write(f"**Model:** {config.model}\n")
            f.write(f"**Unit:** {manifest.unit}\n\n")
            f.write(f"| Metric | Count |\n|---|---|\n")
            f.write(f"| Total segments | {len(manifest.segments)} |\n")
            f.write(f"| Translated | {tc} |\n")
            f.write(f"| Skipped | {sc} |\n\n")
            skipped = [s for s in manifest.segments if s.skip]
            if skipped:
                f.write("## Items Requiring Manual Review\n\n")
                for s in skipped:
                    f.write(f"- Slide {s.slide_idx + 1}, Shape {s.shape_id}: {s.element_type.name}\n")
            f.write("\n---\n")
            f.write("*Generated by translate_pptx_full.py*\n")
        logger.info(f"Saved report to {report_path}")


if __name__ == "__main__":
    main()
