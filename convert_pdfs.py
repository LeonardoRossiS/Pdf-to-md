from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MIN_TEXT_LENGTH_FOR_OCR = 40


def convert_pdf(
    source: Path,
    destination: Path,
    *,
    use_ocr: bool,
    ocr_language: str,
) -> None:
    import pymupdf
    import pymupdf4llm

    with pymupdf.open(source) as document:
        page_chunks = pymupdf4llm.to_markdown(
            document,
            page_chunks=True,
            show_progress=False,
        )
        markdown_pages = []

        for page_number, chunk in enumerate(page_chunks):
            page_markdown = chunk["text"].strip()

            has_little_selectable_text = (
                len(document[page_number].get_text().strip()) < MIN_TEXT_LENGTH_FOR_OCR
            )
            if use_ocr and has_little_selectable_text:
                page = document[page_number]
                text_page = page.get_textpage_ocr(
                    language=ocr_language,
                    dpi=200,
                    full=True,
                )
                ocr_text = page.get_text("text", textpage=text_page).strip()
                if ocr_text:
                    page_markdown = ocr_text

            if page_markdown:
                markdown_pages.append(page_markdown)

    markdown = "\n\n".join(markdown_pages).strip()
    if not markdown:
        raise ValueError("nenhum texto foi extraido; tente novamente com --ocr")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"{markdown}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte em lote PDFs de uma pasta para arquivos Markdown."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "pdfs",
        help="Pasta de entrada dos PDFs (padrao: ./pdfs).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "mds",
        help="Pasta de saida dos arquivos Markdown (padrao: ./mds).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui arquivos Markdown que ja existam.",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Aplica OCR somente em paginas com pouco texto selecionavel.",
    )
    parser.add_argument(
        "--ocr-language",
        default="por+eng",
        help="Idiomas do Tesseract usados pelo OCR (padrao: por+eng).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.is_dir():
        print(f"Erro: pasta de entrada nao encontrada: {input_dir}", file=sys.stderr)
        return 1

    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em: {input_dir}", file=sys.stderr)
        return 1

    converted = 0
    skipped = 0
    failed = 0

    for source in pdfs:
        destination = output_dir / f"{source.stem}.md"
        if destination.exists() and not args.overwrite:
            print(f"Ignorado (ja existe): {destination.name}")
            skipped += 1
            continue

        try:
            convert_pdf(
                source,
                destination,
                use_ocr=args.ocr,
                ocr_language=args.ocr_language,
            )
        except Exception as error:
            print(f"Falha em {source.name}: {error}", file=sys.stderr)
            failed += 1
            continue

        print(f"Convertido: {source.name} -> {destination.name}")
        converted += 1

    print(f"\nConcluido: {converted} convertido(s), {skipped} ignorado(s), {failed} falha(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
