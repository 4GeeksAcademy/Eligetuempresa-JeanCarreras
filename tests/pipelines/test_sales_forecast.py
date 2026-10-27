from pathlib import Path

import pandas as pd
import pytest

from forecast import load_sales, split_sales


DATASET = (
    Path(__file__).resolve().parents[2]
    / "examples/sales-forecasting/brasaland_sales_synthetic.csv"
)


def test_split_has_eight_training_years_two_test_years_and_no_leakage():
    data = load_sales(DATASET).sample(frac=1, random_state=42)
    train, test = split_sales(data)
    assert set(train["month"].dt.year) == set(range(2016, 2024))
    assert set(test["month"].dt.year) == {2024, 2025}
    assert len(train) == 192
    assert len(test) == 48
    assert train["month"].nunique() == 96
    assert test["month"].nunique() == 24
    assert train["month"].max() < test["month"].min()
    assert set(train["month"]).isdisjoint(test["month"])
    assert set(zip(train["month"], train["country"])).isdisjoint(
        zip(test["month"], test["country"])
    )
    changed = data.copy()
    changed.loc[changed["month"] >= "2024-01-01", "sales"] *= 100
    changed_train, _ = split_sales(changed)
    pd.testing.assert_frame_equal(train, changed_train)


def test_split_rejects_duplicate_keys():
    data = load_sales(DATASET)
    with pytest.raises(ValueError, match="Duplicate"):
        split_sales(pd.concat([data, data.iloc[[0]]]))


def test_split_rejects_missing_month():
    data = load_sales(DATASET)
    with pytest.raises(ValueError, match="120 complete months"):
        split_sales(data.iloc[1:])


def test_split_rejects_missing_target():
    data = load_sales(DATASET)
    data.loc[0, "sales"] = float("nan")
    with pytest.raises(ValueError, match="Missing values"):
        split_sales(data)
