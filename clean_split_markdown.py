from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
PAGE_MARKER_RE = re.compile(r"^\s*\*\*1d\+\s*\d+\*\*\s*$")
INLINE_MARKUP_RE = re.compile(r"[*_`]")
INDEX_LINK_RE = re.compile(r"^- \[(.+)]\(\./([^)]+)\)$")

BOOK_TITLES = {
    "3dt-alpha-tormenta-alpha": "Tormenta Alpha",
    "3dt-alpha-mega-city": "Mega City",
    "3dt-alpha-mega-city-manual-do-aventureiro": "Manual do Aventureiro de Mega City",
    "3dt-alpha-manual-revisado-biblioteca-elfica": "Manual 3D&T Alpha - Edição Revisada",
    "3dt-alpha-manual-dos-monstros": "Manual dos Monstros",
    "3dt-alpha-manual-do-defensor": "Manual do Defensor",
    "3dt-alpha-manual-do-aventureiro-alpha": "Manual do Aventureiro",
}


@dataclass(frozen=True)
class Chapter:
    label: str
    heading_text: str
    line_index: int


def clean_heading_text(text: str) -> str:
    return " ".join(INLINE_MARKUP_RE.sub("", text).split())


def normalize_heading(text: str) -> str:
    return clean_heading_text(text).casefold()


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "capitulo"


def parse_chapter(value: str) -> tuple[str, str]:
    label, separator, heading_text = value.partition("=")
    if not separator or not label.strip() or not heading_text.strip():
        raise argparse.ArgumentTypeError(
            "use o formato ROTULO=TEXTO_DO_TITULO, por exemplo "
            "'Introdução=3D&T TORMENTA'"
        )
    return label.strip(), heading_text.strip()


def find_chapters(lines: list[str], requested: list[tuple[str, str]]) -> list[Chapter]:
    chapters: list[Chapter] = []
    previous_line = -1

    for label, heading_text in requested:
        expected = normalize_heading(heading_text)
        matches = []
        for line_index, line in enumerate(lines):
            match = HEADING_RE.match(line)
            if match and normalize_heading(match.group(2)) == expected:
                matches.append((line_index, match.group(2), len(match.group(1))))

        if matches:
            best_level = min(level for _, _, level in matches)
            matches = [match for match in matches if match[2] == best_level]

        if len(matches) != 1:
            raise ValueError(
                f"o título {heading_text!r} teve {len(matches)} correspondência(s); "
                "cada título informado deve corresponder a um único cabeçalho do nível mais alto"
            )

        line_index, matched_text, _ = matches[0]
        if line_index <= previous_line:
            raise ValueError("informe os capítulos na mesma ordem em que aparecem no arquivo")

        chapters.append(Chapter(label, matched_text, line_index))
        previous_line = line_index

    return chapters


def find_book_title(
    lines: list[str],
    source: Path,
    title_override: str | None = None,
) -> str:
    if title_override:
        return title_override
    if source.stem in BOOK_TITLES:
        return BOOK_TITLES[source.stem]
    for line in lines:
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return clean_heading_text(match.group(2))
    return source.stem.replace("-", " ").strip().title()


def write_book_index(
    index_path: Path,
    title: str,
    chapter_links: list[tuple[str, str]] | None = None,
    source_link: str | None = None,
) -> None:
    index_lines = [f"# {title}", ""]
    if chapter_links:
        index_lines.extend(["## Capitulos", ""])
        index_lines.extend(f"- [{label}]({link})" for label, link in chapter_links)
    else:
        index_lines.extend(
            [
                "A divisao em capitulos precisa de revisao manual: "
                "a estrutura extraida nao permite separar o conteudo com confianca.",
                "",
            ]
        )
        if source_link:
            index_lines.extend([f"Markdown original: [abrir]({source_link})", ""])
    index_path.write_text("\n".join(index_lines).rstrip() + "\n", encoding="utf-8")


def refresh_master_index(output_root: Path, source_dir: Path) -> None:
    book_indexes: list[tuple[str, Path, list[tuple[str, str]]]] = []
    for source in sorted(source_dir.glob("*.md")):
        book_dir = output_root / source.stem
        index_path = book_dir / "index.md"
        title = find_book_title(
            source.read_text(encoding="utf-8-sig").splitlines(),
            source,
        )

        if not index_path.exists():
            book_dir.mkdir(parents=True, exist_ok=True)
            source_link = Path("..") / ".." / source_dir.name / source.name
            write_book_index(index_path, title, source_link=source_link.as_posix())

        chapter_links = []
        index_lines = index_path.read_text(encoding="utf-8-sig").splitlines()
        for line in index_lines:
            title_match = HEADING_RE.match(line)
            if title_match and len(title_match.group(1)) == 1:
                title = clean_heading_text(title_match.group(2))
            link_match = INDEX_LINK_RE.match(line)
            if link_match:
                chapter_links.append((link_match.group(1), link_match.group(2)))
        book_indexes.append((title, index_path, chapter_links))

    master_lines = ["# Indice geral dos manuais", ""]
    for title, index_path, chapter_links in book_indexes:
        book_relative = Path(".") / index_path.parent.name / index_path.name
        master_lines.extend([f"## [{title}]({book_relative.as_posix()})", ""])
        if chapter_links:
            for label, link in chapter_links:
                chapter_link = Path(".") / index_path.parent.name / link
                master_lines.append(f"- [{label}]({chapter_link.as_posix()})")
            master_lines.append("")
        else:
            master_lines.extend(["- Divisao em capitulos pendente de revisao.", ""])

    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "index.md").write_text(
        "\n".join(master_lines).rstrip() + "\n",
        encoding="utf-8",
    )


def clean_section(lines: list[str], chapter: Chapter) -> str:
    section_lines = lines[:]
    original_heading = section_lines[0]
    match = HEADING_RE.match(original_heading)
    if match is None:
        raise ValueError(f"cabeçalho inválido para o capítulo {chapter.label!r}")

    if normalize_heading(match.group(2)) == normalize_heading(chapter.label):
        section_lines[0] = f"# {chapter.label}"
        cleaned_lines = section_lines
    else:
        cleaned_lines = [f"# {chapter.label}", "", *section_lines]

    cleaned_lines = [line for line in cleaned_lines if not PAGE_MARKER_RE.fullmatch(line)]
    return "\n".join(cleaned_lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove marcadores de pagina reconhecidos e divide um Markdown "
            "pelos titulos de capitulo informados."
        )
    )
    parser.add_argument("source", type=Path, help="Arquivo Markdown original.")
    parser.add_argument(
        "--chapter",
        action="append",
        type=parse_chapter,
        required=True,
        metavar="ROTULO=TITULO",
        help=(
            "Capitulo e texto exato de um titulo Markdown. Repita na ordem do livro. "
            "Ex.: --chapter 'Introducao=3D&T e TORMENTA...'"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "mds_limpos",
        help="Pasta de saida (padrao: ./mds_limpos/<nome-do-livro>).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui arquivos de saida que ja existam.",
    )
    parser.add_argument(
        "--book-title",
        help="Define o titulo do manual no indice, substituindo a deteccao automatica.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra os titulos encontrados sem criar arquivos.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    if not source.is_file():
        print(f"Erro: arquivo nao encontrado: {source}", file=sys.stderr)
        return 1
    if source.suffix.lower() != ".md":
        print("Erro: o arquivo de entrada precisa ter extensao .md.", file=sys.stderr)
        return 1

    try:
        lines = source.read_text(encoding="utf-8-sig").splitlines()
        chapters = find_chapters(lines, args.chapter)
        output_dir = args.output_dir.resolve() / source.stem
        outputs = [
            output_dir / f"{index:02d}-{slugify(chapter.label)}.md"
            for index, chapter in enumerate(chapters, start=1)
        ]
        index_path = output_dir / "index.md"

        if args.dry_run:
            print(f"Origem: {source}")
            print(f"Destino: {output_dir}")
            for chapter, output in zip(chapters, outputs):
                print(f"Linha {chapter.line_index + 1}: {chapter.label} -> {output.name}")
            print(
                "O texto anterior ao primeiro capitulo sera omitido; "
                "marcadores de pagina **1d+ N** serao removidos."
            )
            return 0

        existing = [path for path in [*outputs, index_path] if path.exists()]
        if existing and not args.overwrite:
            names = ", ".join(path.name for path in existing)
            raise FileExistsError(
                f"arquivos de saida ja existem ({names}); use --overwrite para substitui-los"
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        for index, chapter in enumerate(chapters):
            end = chapters[index + 1].line_index if index + 1 < len(chapters) else len(lines)
            section = lines[chapter.line_index:end]
            outputs[index].write_text(clean_section(section, chapter), encoding="utf-8")

        book_title = find_book_title(lines, source, args.book_title)
        write_book_index(
            index_path,
            book_title,
            [
                (chapter.label, f"./{output.name}")
                for chapter, output in zip(chapters, outputs)
            ],
        )
        refresh_master_index(args.output_dir.resolve(), ROOT / "mds")
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    print(f"Concluido: {len(chapters)} capitulos salvos em {output_dir}")
    print(f"Indice geral atualizado: {args.output_dir.resolve() / 'index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
