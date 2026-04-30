"""CLI entry point for halref."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="halref",
    help="Detect hallucinated references in academic PDFs.",
    no_args_is_help=True,
)
console = Console()


def _fmt_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"


@app.command()
def check(
    paths: Annotated[list[Path], typer.Argument(help="PDF file(s) or directory to check")],
    outdir: Annotated[Path, typer.Option("--outdir", "-d", help="Output directory for all results")] = Path("halref_output"),
    config: Annotated[Optional[Path], typer.Option("--config", "-c", help="Config TOML file")] = None,
    ref_pages: Annotated[Optional[str], typer.Option("--ref-pages", help="Reference pages (1-indexed, e.g., '9-13')")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: terminal, json, bib, all")] = "all",
    apis: Annotated[Optional[str], typer.Option("--apis", help="Comma-separated API list (e.g., 's2,crossref,dblp')")] = None,
    llm: Annotated[bool, typer.Option("--llm", help="Enable LLM verification pass")] = False,
    llm_base_url: Annotated[Optional[str], typer.Option("--llm-base-url", help="LLM endpoint URL")] = None,
    llm_model: Annotated[Optional[str], typer.Option("--llm-model", help="LLM model name")] = None,
    threshold: Annotated[float, typer.Option("--threshold", "-t", help="Hallucination score threshold for flagging")] = 0.5,
    show_ok: Annotated[bool, typer.Option("--show-ok", help="Show all references including verified OK ones")] = False,
    risk_reports: Annotated[
        bool,
        typer.Option(
            "--risk-reports",
            help="Write risk_summary.md/csv and reports/detail_<id>.md per article",
        ),
    ] = False,
    llm_extract: Annotated[
        bool,
        typer.Option(
            "--llm-extract",
            help="Refine each extracted reference with local LLM (set [llm] model in config)",
        ),
    ] = False,
    llm_batch: Annotated[
        bool,
        typer.Option(
            "--llm-batch",
            help="One LLM call on full reference section (needs large context; overrides per-ref LLM)",
        ),
    ] = False,
) -> None:
    """Check PDF(s) for hallucinated references.

    By default, only shows medium/high-risk references. Use --show-ok to see all.

    All output goes into --outdir (default: halref_output/):
      - Per-PDF .bib files with extracted references
      - report.json with full verification results
      - report_annotated.bib with hallucination scores
      - With ``--risk-reports``: risk_summary.md, risk_summary.csv, reports/detail_<id>.md
      - Terminal report printed to stdout
    """
    from halref.config import load_config

    t_start = time.time()

    cfg = load_config(str(config) if config else None)

    # CLI overrides
    if ref_pages:
        cfg.extraction.ref_pages = ref_pages
    if llm:
        cfg.llm.enabled = True
    if llm_base_url:
        cfg.llm.base_url = llm_base_url
    if llm_model:
        cfg.llm.model = llm_model
    if llm_extract:
        cfg.extraction.llm_parse_refs = True
    if llm_batch:
        cfg.extraction.llm_batch_refs = True

    # Resolve PDF paths
    pdf_files = _resolve_paths(paths)
    if not pdf_files:
        console.print("[red]No PDF files found.[/red]")
        raise typer.Exit(1)

    # Create output directory
    outdir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]halref check[/bold] — {len(pdf_files)} PDF(s)")
    console.print(f"Output: {outdir.resolve()}", style="dim")
    console.print()

    # Step 1: Extract references from all PDFs
    from halref.extract.bib_writer import write_bib, write_bib_from_match_results
    from halref.pipeline import extract_all, run_check

    t_extract = time.time()
    extract_result = extract_all(pdf_files, cfg)
    per_file_refs = extract_result.per_file_refs
    extraction_seconds = extract_result.extraction_seconds
    total_refs = sum(len(r) for r in per_file_refs.values())
    console.print(
        f"[green]Extraction complete[/green] — "
        f"{total_refs} references from {len(pdf_files)} files "
        f"({_fmt_elapsed(time.time() - t_extract)})"
    )

    # Step 2: Write .bib files immediately (before verification)
    bib_dir = outdir / "bib"
    bib_dir.mkdir(exist_ok=True)
    for pdf_path, refs in per_file_refs.items():
        if refs:
            bib_path = bib_dir / f"{pdf_path.stem}.bib"
            write_bib(refs, bib_path)

    # Step 3: Verify against APIs (using pre-extracted refs)
    console.print()
    t_verify = time.time()
    report = asyncio.run(
        run_check(pdf_files, cfg, threshold=threshold, per_file_refs=per_file_refs)
    )
    verify_elapsed = time.time() - t_verify
    console.print(
        f"[green]Verification complete[/green] — "
        f"{report.total_flagged} flagged of {report.total_references} "
        f"({_fmt_elapsed(verify_elapsed)})"
    )

    # Re-write .bib after verification: repair + canonical API fields when confident
    for file_report in report.reports:
        if file_report.results:
            pdf_name = Path(file_report.input_file).stem
            bib_path = bib_dir / f"{pdf_name}.bib"
            write_bib_from_match_results(file_report.results, bib_path, quiet=True)

    # Step 4: Output report(s)
    from halref.output.bib_output import write_bib_report
    from halref.output.json_output import write_json_report
    from halref.output.report import print_terminal_report

    write_json = format in ("json", "all")
    write_bib_annotated = format in ("bib", "all")
    write_terminal = format in ("terminal", "all")

    if write_json:
        json_path = outdir / "report.json"
        write_json_report(report, json_path)
        console.print(f"Wrote {json_path.resolve()}", style="dim")

    if risk_reports:
        from halref.output.risk_reports import write_batch_risk_reports

        write_batch_risk_reports(report, outdir, cfg.matching.weights)
        console.print(
            f"Wrote {outdir.resolve() / 'risk_summary.md'}, "
            f"{outdir.resolve() / 'risk_summary.csv'}, "
            f"and {outdir.resolve() / 'reports' / 'detail_*.md'}",
            style="dim",
        )

    if write_bib_annotated:
        bib_report_path = outdir / "report_annotated.bib"
        write_bib_report(report, bib_report_path)
        console.print(f"Wrote {bib_report_path.resolve()}", style="dim")

    console.print()
    if write_terminal:
        print_terminal_report(report, threshold=threshold, show_ok=show_ok)

    wall_total = time.time() - t_start
    n_pdf = len(pdf_files)
    ext_list = list(extraction_seconds.values())
    ext_sum = sum(ext_list)
    ext_avg = ext_sum / n_pdf if n_pdf else 0.0
    amortized_verify = verify_elapsed / n_pdf if n_pdf else 0.0
    avg_wall_per_pdf = wall_total / n_pdf if n_pdf else 0.0

    timing_path = outdir / "timing_report.md"
    lines = [
        "# Tempos de execução (halref check)",
        "",
        f"- **PDFs processados:** {n_pdf}",
        f"- **Tempo total (parede):** {wall_total:.2f} s ({_fmt_elapsed(wall_total)})",
        f"- **Média de tempo total por PDF** (parede ÷ N): **{avg_wall_per_pdf:.2f} s**",
        "",
        "## Extração (local, por ficheiro)",
        "",
        "| PDF | Segundos | Referências |",
        "|-----|----------:|-------------:|",
    ]
    for pdf_path in sorted(pdf_files, key=lambda p: p.name):
        secs = extraction_seconds.get(pdf_path, 0.0)
        nrefs = len(per_file_refs.get(pdf_path, []))
        lines.append(f"| `{pdf_path.name}` | {secs:.2f} | {nrefs} |")
    lines.extend(
        [
            "",
            f"- **Soma extração:** {ext_sum:.2f} s",
            f"- **Média extração por PDF:** {ext_avg:.2f} s",
            "",
            "## Verificação (APIs, lote partilhado)",
            "",
            f"- **Tempo total de verificação:** {verify_elapsed:.2f} s ({_fmt_elapsed(verify_elapsed)})",
            f"- **Cota média por PDF** (verificação ÷ N, só para comparação): {amortized_verify:.2f} s",
            "",
            "A verificação corre em lote com deduplicação entre PDFs; o tempo não é independente por ficheiro.",
        ]
    )
    timing_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"Wrote {timing_path.resolve()}", style="dim")

    console.print(
        f"\n[bold]Done[/bold] in {_fmt_elapsed(wall_total)}"
    )


@app.command("check-bib")
def check_bib(
    paths: Annotated[list[Path], typer.Argument(help=".bib file(s) or directory containing .bib files")],
    outdir: Annotated[Path, typer.Option("--outdir", "-d", help="Output directory for all results")] = Path("halref_output"),
    config: Annotated[Optional[Path], typer.Option("--config", "-c", help="Config TOML file")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: terminal, json, bib, all")] = "all",
    llm: Annotated[bool, typer.Option("--llm", help="Enable LLM verification pass")] = False,
    llm_base_url: Annotated[Optional[str], typer.Option("--llm-base-url", help="LLM endpoint URL")] = None,
    llm_model: Annotated[Optional[str], typer.Option("--llm-model", help="LLM model name")] = None,
    threshold: Annotated[float, typer.Option("--threshold", "-t", help="Hallucination score threshold for flagging")] = 0.5,
    show_ok: Annotated[bool, typer.Option("--show-ok", help="Show all references including verified OK ones")] = False,
    risk_reports: Annotated[
        bool,
        typer.Option(
            "--risk-reports",
            help="Write risk_summary.md/csv and reports/detail_<id>.md per article",
        ),
    ] = False,
) -> None:
    """Check pre-existing .bib file(s) for hallucinated references.

    Skips PDF extraction — reads references directly from BibTeX files
    and verifies them against academic databases.

    All output goes into --outdir (default: halref_output/).
    """
    from halref.config import load_config
    from halref.extract.bib_reader import read_bib
    from halref.pipeline import run_check

    t_start = time.time()

    cfg = load_config(str(config) if config else None)
    if llm:
        cfg.llm.enabled = True
    if llm_base_url:
        cfg.llm.base_url = llm_base_url
    if llm_model:
        cfg.llm.model = llm_model

    # Resolve .bib paths
    bib_files = _resolve_bib_paths(paths)
    if not bib_files:
        console.print("[red]No .bib files found.[/red]")
        raise typer.Exit(1)

    outdir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]halref check-bib[/bold] — {len(bib_files)} .bib file(s)")
    console.print(f"Output: {outdir.resolve()}", style="dim")
    console.print()

    # Read references from .bib files
    per_file_refs: dict[Path, list] = {}
    total_refs = 0
    for bib_path in bib_files:
        refs = read_bib(bib_path)
        per_file_refs[bib_path] = refs
        total_refs += len(refs)
        console.print(f"  {bib_path.name}: {len(refs)} references", style="dim")

    console.print(
        f"\n[green]Loaded {total_refs} references[/green] from {len(bib_files)} file(s)"
    )

    # Verify against APIs
    console.print()
    t_verify = time.time()
    report = asyncio.run(
        run_check(
            list(per_file_refs.keys()),
            cfg,
            threshold=threshold,
            per_file_refs=per_file_refs,
        )
    )
    console.print(
        f"[green]Verification complete[/green] — "
        f"{report.total_flagged} flagged of {report.total_references} "
        f"({_fmt_elapsed(time.time() - t_verify)})"
    )

    # Output report(s)
    from halref.output.bib_output import write_bib_report
    from halref.output.json_output import write_json_report
    from halref.output.report import print_terminal_report

    write_json = format in ("json", "all")
    write_bib_annotated = format in ("bib", "all")
    write_terminal = format in ("terminal", "all")

    if write_json:
        json_path = outdir / "report.json"
        write_json_report(report, json_path)
        console.print(f"Wrote {json_path.resolve()}", style="dim")

    if risk_reports:
        from halref.output.risk_reports import write_batch_risk_reports

        write_batch_risk_reports(report, outdir, cfg.matching.weights)
        console.print(
            f"Wrote {outdir.resolve() / 'risk_summary.md'}, "
            f"{outdir.resolve() / 'risk_summary.csv'}, "
            f"and {outdir.resolve() / 'reports' / 'detail_*.md'}",
            style="dim",
        )

    if write_bib_annotated:
        bib_report_path = outdir / "report_annotated.bib"
        write_bib_report(report, bib_report_path)
        console.print(f"Wrote {bib_report_path.resolve()}", style="dim")

    console.print()
    if write_terminal:
        print_terminal_report(report, threshold=threshold, show_ok=show_ok)

    console.print(
        f"\n[bold]Done[/bold] in {_fmt_elapsed(time.time() - t_start)}"
    )


@app.command()
def extract(
    paths: Annotated[list[Path], typer.Argument(help="PDF file(s) to extract references from")],
    outdir: Annotated[Path, typer.Option("--outdir", "-d", help="Output directory for .bib files")] = Path("halref_output"),
    config: Annotated[Optional[Path], typer.Option("--config", "-c", help="Config TOML file")] = None,
    ref_pages: Annotated[Optional[str], typer.Option("--ref-pages", help="Reference pages (1-indexed, e.g., '9-13')")] = None,
    llm_extract: Annotated[
        bool,
        typer.Option(
            "--llm-extract",
            help="Refine each reference with local LLM ([llm] model in config)",
        ),
    ] = False,
    llm_batch: Annotated[
        bool,
        typer.Option(
            "--llm-batch",
            help="One LLM call on full reference section (needs large context)",
        ),
    ] = False,
) -> None:
    """Extract references from PDF(s) and output as BibTeX.

    Saves one .bib file per PDF into --outdir (default: halref_output/).
    """
    from halref.config import load_config
    from halref.extract.bib_writer import write_bib
    from halref.extract.ensemble import extract_references

    t_start = time.time()

    cfg = load_config(str(config) if config else None)
    if ref_pages:
        cfg.extraction.ref_pages = ref_pages
    if llm_extract:
        cfg.extraction.llm_parse_refs = True
    if llm_batch:
        cfg.extraction.llm_batch_refs = True

    pdf_files = _resolve_paths(paths)
    if not pdf_files:
        console.print("[red]No PDF files found.[/red]")
        raise typer.Exit(1)

    outdir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]halref extract[/bold] — {len(pdf_files)} PDF(s)")
    console.print(f"Output: {outdir.resolve()}", style="dim")
    console.print()

    total = 0
    for pdf_path in pdf_files:
        t_file = time.time()
        refs = extract_references(pdf_path, cfg)
        if refs:
            bib_path = outdir / f"{pdf_path.stem}.bib"
            write_bib(refs, bib_path)
            total += len(refs)
        elapsed = _fmt_elapsed(time.time() - t_file)
        console.print(
            f"  {pdf_path.name}: {len(refs)} refs ({elapsed})",
            style="dim" if refs else "yellow",
        )

    console.print(
        f"\n[bold]Done[/bold] — {total} references in {_fmt_elapsed(time.time() - t_start)}"
    )


def _resolve_paths(paths: list[Path]) -> list[Path]:
    """Expand directories into PDF files."""
    pdf_files = []
    for p in paths:
        if p.is_dir():
            pdf_files.extend(sorted(p.glob("*.pdf")))
        elif p.suffix.lower() == ".pdf" and p.exists():
            pdf_files.append(p)
        else:
            console.print(f"[yellow]Skipping {p} (not a PDF or doesn't exist)[/yellow]")
    return pdf_files


def _resolve_bib_paths(paths: list[Path]) -> list[Path]:
    """Expand directories into .bib files."""
    bib_files = []
    for p in paths:
        if p.is_dir():
            bib_files.extend(sorted(p.glob("*.bib")))
        elif p.suffix.lower() == ".bib" and p.exists():
            bib_files.append(p)
        else:
            console.print(f"[yellow]Skipping {p} (not a .bib file or doesn't exist)[/yellow]")
    return bib_files


if __name__ == "__main__":
    app()
