"""Compare separate-chaining probe counts with the topic 08 estimates."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hash_table import HashTable

CAPACITY = 4093
SEED = 20261120
ALPHA_STEPS = 16
OUTPUT_DIR = Path(__file__).parent
CSV_PATH = OUTPUT_DIR / "results.csv"
SVG_PATH = OUTPUT_DIR / "results.svg"


def _random_urls(prefix: str, count: int, rng: Random) -> list[str]:
    return [
        f"https://example.com/{prefix}/{index}/{rng.getrandbits(64):016x}"
        for index in range(count)
    ]


def _count_node_comparisons(table: HashTable[int], key: str) -> int:
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
    maximum_entries = CAPACITY * 4
    urls = _random_urls("stored", maximum_entries, rng)
    rows: list[dict[str, float | int]] = []

    for step in range(1, ALPHA_STEPS + 1):
        target_alpha = step / 4
        entry_count = int(target_alpha * CAPACITY + 0.5)
        actual_alpha = entry_count / CAPACITY
        table: HashTable[int] = HashTable(
            initial_capacity=CAPACITY, max_load=None
        )
        for index, url in enumerate(urls[:entry_count]):
            table.put(url, index)

        successful_comparisons = sum(
            _count_node_comparisons(table, url) for url in urls[:entry_count]
        )
        missing_urls = _random_urls("missing", entry_count, rng)
        unsuccessful_comparisons = sum(
            _count_node_comparisons(table, url) for url in missing_urls
        )
        rows.append(
            {
                "target_alpha": target_alpha,
                "actual_alpha": actual_alpha,
                "entries": entry_count,
                "successful_average": successful_comparisons / entry_count,
                "successful_theory": 1 + actual_alpha / 2,
                "unsuccessful_average": unsuccessful_comparisons / entry_count,
                "unsuccessful_theory": actual_alpha,
            }
        )

    return rows


def _write_csv(rows: list[dict[str, float | int]]) -> None:
    fieldnames = [
        "target_alpha",
        "actual_alpha",
        "entries",
        "successful_average",
        "successful_theory",
        "unsuccessful_average",
        "unsuccessful_theory",
    ]
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


def _write_svg(rows: list[dict[str, float | int]]) -> None:
    width, height = 1000, 620
    left, right, top, bottom = 90, 40, 70, 90
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_min, x_max, y_max = 0.0, 4.0, 4.5

    def x_position(alpha: float) -> float:
        return left + (alpha - x_min) / (x_max - x_min) * plot_width

    def y_position(value: float) -> float:
        return top + plot_height - value / y_max * plot_height

    series = [
        ("successful_average", "#1769aa", "Successful: measured"),
        ("successful_theory", "#1769aa", "Successful: theory"),
        ("unsuccessful_average", "#d1495b", "Unsuccessful: measured"),
        ("unsuccessful_theory", "#d1495b", "Unsuccessful: theory"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<style>text{font-family:Arial,sans-serif;fill:#222}'
        '.grid{stroke:#ddd;stroke-width:1}.axis{stroke:#333;stroke-width:1.5}'
        '.theory{stroke-dasharray:7 5}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="500" y="34" text-anchor="middle" font-size="21">'
        "Average hash-chain node comparisons</text>",
    ]

    for tick in range(5):
        y_value = tick
        y = y_position(y_value)
        parts.extend(
            [
                f'<line class="grid" x1="{left}" y1="{y:.2f}" '
                f'x2="{width - right}" y2="{y:.2f}"/>',
                f'<text x="{left - 14}" y="{y + 5:.2f}" text-anchor="end" '
                f'font-size="13">{y_value}</text>',
            ]
        )
    for tick in range(0, 5):
        x_value = float(tick)
        x = x_position(x_value)
        parts.extend(
            [
                f'<line class="grid" x1="{x:.2f}" y1="{top}" '
                f'x2="{x:.2f}" y2="{height - bottom}"/>',
                f'<text x="{x:.2f}" y="{height - bottom + 24}" '
                f'text-anchor="middle" font-size="13">{tick}</text>',
            ]
        )

    parts.extend(
        [
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{height - bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{height - bottom}" '
            f'x2="{width - right}" y2="{height - bottom}"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 28}" '
            'text-anchor="middle" font-size="15">Load factor (alpha)</text>',
            f'<text x="22" y="{top + plot_height / 2}" '
            f'transform="rotate(-90 22 {top + plot_height / 2})" '
            'text-anchor="middle" font-size="15">Average node comparisons</text>',
        ]
    )

    for key, color, label in series:
        points = " ".join(
            f'{x_position(float(row["actual_alpha"])):.2f},'
            f'{y_position(float(row[key])):.2f}'
            for row in rows
        )
        dash = ' class="theory"' if key.endswith("_theory") else ""
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.5"'
            f'{dash} points="{points}"/>'
        )
        for row in rows:
            x = x_position(float(row["actual_alpha"]))
            y = y_position(float(row[key]))
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{color}"/>'
            )

    legend_x, legend_y = 600, 55
    for index, (key, color, label) in enumerate(series):
        y = legend_y + index * 20
        dash = ' stroke-dasharray="7 5"' if key.endswith("_theory") else ""
        parts.extend(
            [
                f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 30}" '
                f'y2="{y}" stroke="{color}" stroke-width="2.5"{dash}/>',
                f'<text x="{legend_x + 38}" y="{y + 5}" font-size="13">'
                f"{label}</text>",
            ]
        )
    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _print_table(rows: list[dict[str, float | int]]) -> None:
    print(
        "alpha    n      success measured/theory    "
        "failure measured/theory"
    )
    for row in rows:
        print(
            f'{row["actual_alpha"]:5.2f}  {row["entries"]:5d}  '
            f'{row["successful_average"]:8.3f} / '
            f'{row["successful_theory"]:6.3f}           '
            f'{row["unsuccessful_average"]:8.3f} / '
            f'{row["unsuccessful_theory"]:6.3f}'
        )


def main() -> None:
    rows = _measure()
    _write_csv(rows)
    _write_svg(rows)
    _print_table(rows)
    print(f"\nWrote {CSV_PATH} and {SVG_PATH}")


if __name__ == "__main__":
    main()
