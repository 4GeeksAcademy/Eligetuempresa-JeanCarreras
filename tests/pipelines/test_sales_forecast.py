"""Pruebas sinteticas; no sustituyen la evaluacion de las ventas reales."""

import numpy as np
import pandas as pd
import pytest

from scripts.train_sales_forecast import (
    feature_row,
    forecast,
    split_sales,
    temporal_folds,
    training_features,
)


def sales():
    return pd.Series(np.arange(120, dtype=float) + 1000,
                     index=pd.date_range("2016-01-01", periods=120, freq="MS"))


def test_split_has_eight_training_years_and_two_holdout_years():
    training, holdout = split_sales(sales())
    assert len(training) == 96
    assert len(holdout) == 24
    assert training.index[-1] == pd.Timestamp("2023-12-01")
    assert holdout.index[0] == pd.Timestamp("2024-01-01")


def test_temporal_folds_preserve_chronological_order():
    training, _ = split_sales(sales())
    folds = list(temporal_folds(training))
    assert len(folds) == 5
    previous_validation_end = -1
    for train_indices, validation_indices in folds:
        np.testing.assert_array_equal(train_indices, np.arange(validation_indices[0]))
        np.testing.assert_array_equal(validation_indices,
                                      np.arange(validation_indices[0], validation_indices[-1] + 1))
        assert train_indices[-1] < validation_indices[0]
        assert previous_validation_end < validation_indices[0]
        assert training.index[train_indices[-1]] < training.index[validation_indices[0]]
        assert len(validation_indices) == 12
        previous_validation_end = validation_indices[-1]


def test_temporal_folds_reject_shuffled_months():
    with pytest.raises(ValueError, match="ordenados"):
        list(temporal_folds(sales().iloc[::-1]))


def test_features_do_not_use_current_or_future_revenue():
    revenue = sales()
    original, _ = training_features(revenue)
    changed = revenue.copy()
    changed.iloc[48:] = 99999999
    updated, _ = training_features(changed)
    pd.testing.assert_frame_equal(original.loc[:revenue.index[48]],
                                  updated.loc[:revenue.index[48]])
    row = feature_row(revenue.iloc[:48], revenue.index[48])
    assert row["lag_1"].iloc[0] == revenue.iloc[47]
    assert row["lag_12"].iloc[0] == revenue.iloc[36]
    assert row["rolling_mean_3"].iloc[0] == revenue.iloc[45:48].mean()


def test_recursive_forecast_uses_predictions_not_validation_targets():
    class LastMonthModel:
        def predict(self, features):
            return features["lag_1"].to_numpy() + 1

    training, holdout = split_sales(sales())
    predicted = forecast(LastMonthModel(), training, holdout.index)
    np.testing.assert_array_equal(predicted, training.iloc[-1] + np.arange(1, 25))
    assert len(training) == 96