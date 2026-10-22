"""Generate explicitly synthetic Brasaland monthly sales for practice only."""

import argparse
import csv
from pathlib import Path
import random


SEED = 42
START_YEAR = 2016
END_YEAR = 2025
SEASONALITY = (0.88, 0.90, 0.98, 1.00, 1.05, 1.02, 1.08, 1.00, 0.94, 1.01, 1.10, 1.25)
MARKETS = (("CO", "COP", 900_000_000), ("US", "USD", 180_000))
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "examples/sales-forecasting/brasaland_sales_synthetic.csv"
)


def generate_sales(output: Path) -> int:
    random_generator = random.Random(SEED)
    output.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    with output.open("x", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=("month", "country", "currency", "sales", "is_synthetic"),
        )
        writer.writeheader()
        for year in range(START_YEAR, END_YEAR + 1):
            for month in range(1, 13):
                month_index = (year - START_YEAR) * 12 + month - 1
                growth = 1.045 ** (month_index / 12)
                for country, currency, baseline in MARKETS:
                    noise = max(0.1, 1 + random_generator.gauss(0, 0.06))
                    sales = round(baseline * growth * SEASONALITY[month - 1] * noise, 2)
                    writer.writerow(
                        {
                            "month": f"{year}-{month:02d}-01",
                            "country": country,
                            "currency": currency,
                            "sales": sales,
                            "is_synthetic": "true",
                        }
                    )
                    row_count += 1
    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    try:
        row_count = generate_sales(arguments.output)
    except FileExistsError:
        parser.error(f"Output already exists; refusing to overwrite: {arguments.output}")
    print(f"Created {row_count} SYNTHETIC rows: {arguments.output}")


if __name__ == "__main__":
    main()