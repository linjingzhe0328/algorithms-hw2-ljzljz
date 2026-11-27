"""Compare chaining and linear-probing search costs with their estimates."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable

CAPACITY = 4093
SEED = 20261127
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
OUTPUT_DIR = Path(__file__).parent
CSV_PATH = OUTPUT_DIR / "results.csv"
SVG_PATH = OUTPUT_DIR / "results.svg"
PDF_PATH = OUTPUT_DIR / "report.pdf"


def _random_urls(prefix: str, count: int, rng: Random) -> list[str]:
    return [
        f"https://example.com/{prefix}/{index}/{rng.getrandbits(64):016x}"
        for index in range(count)
    ]


def _chain_comparisons(table: HashTable[int], key: str) -> int:
    node = table._buckets[table._bucket_index(key)]
    comparisons = 0
    while node is not None:
        comparisons += 1
        if node.key == key:
            break
        node = node.next
    return comparisons


def _measure() -> list[dict[str, float | int]]:
    rng = Random(SEED)
    maximum_entries = int(CAPACITY * LOAD_FACTORS[-1] + 0.5)
    urls = _random_urls("stored", maximum_entries, rng)
    missing_urls = _random_urls("missing", maximum_entries, rng)
    rows: list[dict[str, float | int]] = []

    for load_factor in LOAD_FACTORS:
        entry_count = int(load_factor * CAPACITY + 0.5)
        actual_load = entry_count / CAPACITY
        chaining: HashTable[int] = HashTable(
            initial_capacity=CAPACITY, max_load=None
        )
        linear: LinearProbingHashTable[int] = LinearProbingHashTable(
            initial_capacity=CAPACITY, max_load=None
        )
        for index, key in enumerate(urls[:entry_count]):
            chaining.put(key, index)
            linear.put(key, index)

        misses = missing_urls[:entry_count]
        rows.append(
            {
                "load_factor": load_factor,
                "actual_load_factor": actual_load,
                "entries": entry_count,
                "chaining_success_measured": sum(
                    _chain_comparisons(chaining, key) for key in urls[:entry_count]
                )
                / entry_count,
                "chaining_success_theory": 1 + actual_load / 2,
                "chaining_failure_measured": sum(
                    _chain_comparisons(chaining, key) for key in misses
                )
                / entry_count,
                "chaining_failure_theory": actual_load,
                "linear_success_measured": sum(
                    len(linear.probe_indices(key)) for key in urls[:entry_count]
                )
                / entry_count,
                "linear_success_theory": 0.5
                * (1 + 1 / (1 - actual_load)),
                "linear_failure_measured": sum(
                    len(linear.probe_indices(key)) for key in misses
                )
                / entry_count,
                "linear_failure_theory": 0.5
                * (1 + 1 / (1 - actual_load) ** 2),
            }
        )
    return rows


def _write_csv(rows: list[dict[str, float | int]]) -> None:
    fieldnames = list(rows[0])
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{value:.6f}" if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def _write_svg_panel(
    parts: list[str],
    rows: list[dict[str, float | int]],
    panel_x: int,
    title: str,
    prefix: str,
    y_max: float,
    y_step: float,
) -> None:
    panel_width = 580
    left, right, top, bottom = panel_x + 62, panel_x + panel_width - 20, 105, 555
    plot_width, plot_height = right - left, bottom - top

    def x_position(alpha: float) -> float:
        return left + alpha / 0.9 * plot_width

    def y_position(value: float) -> float:
        return bottom - value / y_max * plot_height

    parts.append(
        f'<text x="{panel_x + panel_width / 2}" y="78" text-anchor="middle" '
        f'font-size="18">{title}</text>'
    )
    tick_count = int(y_max / y_step)
    for tick in range(tick_count + 1):
        value = tick * y_step
        y = y_position(value)
        parts.extend(
            [
                f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>',
                f'<text x="{left - 10}" y="{y + 5:.2f}" text-anchor="end" '
                f'font-size="12">{value:g}</text>',
            ]
        )
    for tick in range(10):
        alpha = tick / 10
        if alpha > 0.9:
            continue
        x = x_position(alpha)
        parts.extend(
            [
                f'<line class="grid" x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}"/>',
                f'<text x="{x:.2f}" y="{bottom + 20}" text-anchor="middle" '
                f'font-size="12">{alpha:.1f}</text>',
            ]
        )
    x = x_position(0.9)
    parts.extend(
        [
            f'<line class="grid" x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}"/>',
            f'<text x="{x:.2f}" y="{bottom + 20}" text-anchor="middle" '
            'font-size="12">0.9</text>',
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>',
            f'<text x="{(left + right) / 2}" y="{bottom + 48}" '
            'text-anchor="middle" font-size="14">Load factor (alpha)</text>',
            f'<text x="{panel_x + 17}" y="{(top + bottom) / 2}" '
            f'transform="rotate(-90 {panel_x + 17} {(top + bottom) / 2})" '
            'text-anchor="middle" font-size="14">Average probes</text>',
        ]
    )

    panel_series = (
        (f"{prefix}_success_measured", "#1769aa", "Success measured", False),
        (f"{prefix}_success_theory", "#1769aa", "Success theory", True),
        (f"{prefix}_failure_measured", "#d1495b", "Failure measured", False),
        (f"{prefix}_failure_theory", "#d1495b", "Failure theory", True),
    )
    for field, color, label, is_theory in panel_series:
        points = " ".join(
            f'{x_position(float(row["actual_load_factor"])):.2f},'
            f'{y_position(float(row[field])):.2f}'
            for row in rows
        )
        dash = ' stroke-dasharray="7 5"' if is_theory else ""
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.5"'
            f'{dash} points="{points}"/>'
        )
        for row in rows:
            x = x_position(float(row["actual_load_factor"]))
            y = y_position(float(row[field]))
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>')

    legend = (
        ("#1769aa", False, "Success measured"),
        ("#1769aa", True, "Success theory"),
        ("#d1495b", False, "Failure measured"),
        ("#d1495b", True, "Failure theory"),
    )
    legend_x = (panel_x + 75, panel_x + 315)
    legend_y = (603, 625)
    for index, (color, is_theory, label) in enumerate(legend):
        col, row_index = index % 2, index // 2
        start_x, y = legend_x[col], legend_y[row_index]
        dash = ' stroke-dasharray="7 5"' if is_theory else ""
        parts.extend(
            [
                f'<line x1="{start_x}" y1="{y}" x2="{start_x + 25}" y2="{y}" '
                f'stroke="{color}" stroke-width="2.5"{dash}/>',
                f'<text x="{start_x + 31}" y="{y + 4}" font-size="11">{label}</text>',
            ]
        )


def _write_svg(rows: list[dict[str, float | int]]) -> None:
    width, height = 1260, 675
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<style>text{font-family:Arial,sans-serif;fill:#222}'
        '.grid{stroke:#ddd;stroke-width:1}.axis{stroke:#333;stroke-width:1.5}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="630" y="35" text-anchor="middle" font-size="22">'
        "Average hash-table search probes</text>",
    ]
    _write_svg_panel(parts, rows, 20, "Separate chaining", "chaining", 2.5, 0.5)
    _write_svg_panel(parts, rows, 640, "Linear probing", "linear", 60, 10)
    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _pdf_text(x: float, y: float, size: int, text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET"


def _pdf_panel(
    commands: list[str],
    rows: list[dict[str, float | int]],
    x_origin: float,
    title: str,
    prefix: str,
    y_max: float,
    y_step: float,
) -> None:
    plot_x, plot_y, plot_width, plot_height = x_origin + 35, 430, 225, 205

    def x_position(alpha: float) -> float:
        return plot_x + alpha / 0.9 * plot_width

    def y_position(value: float) -> float:
        return plot_y + value / y_max * plot_height

    commands.append(_pdf_text(x_origin + 30, 670, 13, title))
    for tick in range(int(y_max / y_step) + 1):
        value = tick * y_step
        y = y_position(value)
        commands.extend(
            [
                "0.85 G",
                f"{plot_x:.2f} {y:.2f} m {plot_x + plot_width:.2f} {y:.2f} l S",
                "0 G",
                _pdf_text(x_origin + 4, y - 3, 7, f"{value:g}"),
            ]
        )
    for tick in range(10):
        alpha = tick / 10
        if alpha > 0.9:
            continue
        x = x_position(alpha)
        commands.append(_pdf_text(x - 7, plot_y - 15, 7, f"{alpha:.1f}"))
    commands.append(_pdf_text(x_position(0.9) - 7, plot_y - 15, 7, "0.9"))
    commands.extend(
        [
            "0 G",
            f"{plot_x:.2f} {plot_y:.2f} m {plot_x:.2f} "
            f"{plot_y + plot_height:.2f} l S",
            f"{plot_x:.2f} {plot_y:.2f} m "
            f"{plot_x + plot_width:.2f} {plot_y:.2f} l S",
            _pdf_text(plot_x + 77, plot_y - 29, 8, "Load factor"),
            _pdf_text(x_origin + 7, plot_y + plot_height + 7, 7, "Average probes"),
        ]
    )
    series = (
        (f"{prefix}_success_measured", (0.09, 0.41, 0.67), False),
        (f"{prefix}_success_theory", (0.09, 0.41, 0.67), True),
        (f"{prefix}_failure_measured", (0.82, 0.29, 0.34), False),
        (f"{prefix}_failure_theory", (0.82, 0.29, 0.34), True),
    )
    for field, color, theory in series:
        commands.append(f"{color[0]} {color[1]} {color[2]} RG")
        commands.append("[4 3] 0 d" if theory else "[] 0 d")
        for index, row in enumerate(rows):
            x = x_position(float(row["actual_load_factor"]))
            y = y_position(float(row[field]))
            commands.append(f"{x:.2f} {y:.2f} {'m' if index == 0 else 'l'}")
        commands.append("S")
    commands.extend(["0 G", "[] 0 d"])

    legend = (
        ("Success measured", (0.09, 0.41, 0.67), False),
        ("Success theory", (0.09, 0.41, 0.67), True),
        ("Failure measured", (0.82, 0.29, 0.34), False),
        ("Failure theory", (0.82, 0.29, 0.34), True),
    )
    for index, (label, color, theory) in enumerate(legend):
        column, row_index = index % 2, index // 2
        x = x_origin + (12 if column == 0 else 145)
        y = 385 - row_index * 14
        commands.extend(
            [
                f"{color[0]} {color[1]} {color[2]} RG",
                "[4 3] 0 d" if theory else "[] 0 d",
                f"{x:.2f} {y:.2f} m {x + 20:.2f} {y:.2f} l S",
                "0 G",
                "[] 0 d",
                _pdf_text(x + 24, y - 3, 7, label),
            ]
        )


def _write_pdf_report(rows: list[dict[str, float | int]]) -> None:
    commands = [
        _pdf_text(45, 755, 19, "Linear probing and separate chaining"),
        _pdf_text(45, 738, 10, "Measured average search probes and theoretical estimates"),
    ]
    _pdf_panel(commands, rows, 35, "Separate chaining", "chaining", 2.5, 0.5)
    _pdf_panel(commands, rows, 315, "Linear probing", "linear", 55, 10)

    high_load = rows[-1]
    commands.extend(
        [
            _pdf_text(45, 345, 9, "Method: same deterministic URL keys, capacity 4,093, and load factors 0.1-0.9."),
            _pdf_text(45, 329, 9, "Chaining estimates: success 1 + alpha/2; failure alpha."),
            _pdf_text(45, 313, 9, "Linear probing estimates: success (1 + 1/(1-alpha))/2;"),
            _pdf_text(45, 299, 9, "failure (1 + 1/(1-alpha)^2)/2. Probes count inspected slots or nodes."),
            _pdf_text(
                45,
                275,
                9,
                f"At alpha=0.9, chaining success/failure: "
                f'{float(high_load["chaining_success_measured"]):.2f}/'
                f'{float(high_load["chaining_failure_measured"]):.2f}; '
                f'linear probing: {float(high_load["linear_success_measured"]):.2f}/'
                f'{float(high_load["linear_failure_measured"]):.2f}.',
            ),
            _pdf_text(45, 257, 9, "Linear probing develops primary clusters, increasing especially unsuccessful searches"),
            _pdf_text(45, 243, 9, "at high load; separate chaining remains close to its expected linear growth."),
        ]
    )

    stream = ("\n".join(commands) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode("ascii"))
        document.extend(obj)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    PDF_PATH.write_bytes(document)


def _print_table(rows: list[dict[str, float | int]]) -> None:
    print(
        "alpha entries  chain success (measured/theory)  "
        "chain failure (measured/theory)  linear success (measured/theory)  "
        "linear failure (measured/theory)"
    )
    for row in rows:
        print(
            f'{row["actual_load_factor"]:5.2f} {row["entries"]:6d}  '
            f'{row["chaining_success_measured"]:6.3f}/{row["chaining_success_theory"]:6.3f}  '
            f'{row["chaining_failure_measured"]:6.3f}/{row["chaining_failure_theory"]:6.3f}  '
            f'{row["linear_success_measured"]:6.3f}/{row["linear_success_theory"]:6.3f}  '
            f'{row["linear_failure_measured"]:6.3f}/{row["linear_failure_theory"]:6.3f}'
        )


def main() -> None:
    rows = _measure()
    _write_csv(rows)
    _write_svg(rows)
    _write_pdf_report(rows)
    _print_table(rows)
    print(f"\nWrote {CSV_PATH}, {SVG_PATH}, and {PDF_PATH}")


if __name__ == "__main__":
    main()
