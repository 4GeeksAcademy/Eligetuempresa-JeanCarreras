"""Sales forecasting on explicitly synthetic Brasaland data, never financial advice."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parent
SEED = 42
COVERAGE = 0.90
COUNTRIES = {"CO": "COP", "US": "USD"}
COLUMNS = {"month", "country", "currency", "sales", "is_synthetic"}


def load_sales(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    if set(data.columns) != COLUMNS:
        raise ValueError(f"Expected columns: {sorted(COLUMNS)}")
    if data.isna().any().any():
        raise ValueError("Missing values: correct the source; do not invent target sales.")
    data["month"] = pd.to_datetime(data["month"], format="%Y-%m-%d", errors="raise")
    data["sales"] = pd.to_numeric(data["sales"], errors="raise")
    if not np.isfinite(data["sales"]).all() or (data["sales"] <= 0).any():
        raise ValueError("Sales must be finite and positive.")
    if not data["is_synthetic"].astype(str).str.lower().eq("true").all():
        raise ValueError("This experiment accepts explicitly synthetic data only.")
    return data


def split_sales(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if data.isna().any().any():
        raise ValueError("Missing values must be resolved before splitting.")
    if data.duplicated(["month", "country"]).any():
        raise ValueError("Duplicate month/country keys.")
    expected = set(pd.date_range("2016-01-01", "2025-12-01", freq="MS"))
    if set(data["country"]) != set(COUNTRIES):
        raise ValueError("Expected the CO and US markets.")
    for country, currency in COUNTRIES.items():
        market = data.loc[data["country"].eq(country)]
        if set(market["month"]) != expected or not market["currency"].eq(currency).all():
            raise ValueError("Expected 120 complete months per market in its native currency.")
    ordered = data.sort_values(["month", "country"]).reset_index(drop=True)
    train = ordered.loc[ordered["month"] < "2024-01-01"].copy()
    test = ordered.loc[ordered["month"] >= "2024-01-01"].copy()
    return train, test


def month_index(dates: pd.Series) -> np.ndarray:
    return ((dates.dt.year - 2016) * 12 + dates.dt.month - 1).to_numpy(dtype=float)


def calendar_features(dates: pd.Series) -> np.ndarray:
    month = dates.dt.month.to_numpy(dtype=float)
    return np.column_stack((month, np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)))


@dataclass
class SalesModel:
    intercept: float
    slope: float
    forest: RandomForestRegressor

    def predict(self, dates: pd.Series) -> np.ndarray:
        trend = self.intercept + self.slope * month_index(dates)
        return np.exp(trend + self.forest.predict(calendar_features(dates)))


def fit_model(train: pd.DataFrame) -> SalesModel:
    dates = train["month"]
    calendar = pd.get_dummies(dates.dt.month, drop_first=True, dtype=float).to_numpy()
    design = np.column_stack((np.ones(len(train)), month_index(dates), calendar))
    log_sales = np.log(train["sales"].to_numpy())
    coefficients = np.linalg.lstsq(design, log_sales, rcond=None)[0]
    trend = coefficients[0] + coefficients[1] * month_index(dates)
    forest = RandomForestRegressor(
        n_estimators=200, min_samples_leaf=2, max_features=1.0,
        random_state=SEED, n_jobs=1,
    )
    forest.fit(calendar_features(dates), log_sales - trend)
    return SalesModel(float(coefficients[0]), float(coefficients[1]), forest)


def calibration_radius(train: pd.DataFrame) -> tuple[float, int]:
    residuals = []
    for year in (2022, 2023):
        fit = train.loc[train["month"].dt.year < year]
        validation = train.loc[train["month"].dt.year == year]
        prediction = fit_model(fit).predict(validation["month"])
        residuals.extend(np.abs(np.log(validation["sales"].to_numpy() / prediction)))
    scores = np.sort(residuals)
    rank = min(len(scores), int(np.ceil((len(scores) + 1) * COVERAGE)))
    return float(scores[rank - 1]), len(scores)


def population_stability_index(reference: np.ndarray, observed: np.ndarray) -> float:
    interior = np.unique(np.quantile(reference, np.linspace(0, 1, 6)))[1:-1]
    bins = np.concatenate(([-np.inf], interior, [np.inf]))
    expected = np.histogram(reference, bins=bins)[0].astype(float)
    actual = np.histogram(observed, bins=bins)[0].astype(float)
    expected = (expected + 0.5) / (expected.sum() + 0.5 * len(expected))
    actual = (actual + 0.5) / (actual.sum() + 0.5 * len(actual))
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def normalized_gini(actual: np.ndarray, prediction: np.ndarray) -> float | None:
    def concentration(scores: np.ndarray) -> float:
        order = np.argsort(-scores, kind="stable")
        cumulative = np.cumsum(actual[order]) / actual.sum()
        return float(cumulative.mean() - (len(actual) + 1) / (2 * len(actual)))

    perfect = concentration(actual)
    return concentration(prediction) / perfect if abs(perfect) > 1e-12 else None


def evaluate(actual: np.ndarray, prediction: np.ndarray) -> dict:
    return {
        "mse": float(mean_squared_error(actual, prediction)),
        "mae": float(mean_absolute_error(actual, prediction)),
        "r2": float(r2_score(actual, prediction)),
        "k2_score_assumed_r2": float(r2_score(actual, prediction)),
        "normalized_gini": normalized_gini(actual, prediction),
    }


def run(input_path: Path, output: Path) -> dict:
    train, test = split_sales(load_sales(input_path))
    output.mkdir(parents=True, exist_ok=True)
    results = {
        "synthetic": True,
        "seed": SEED,
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "train_period": ["2016-01", "2023-12"],
        "test_period": ["2024-01", "2025-12"],
        "k2_note": "K2 is undefined in the assignment; R2 is a provisional interpretation, not an established equivalence.",
        "interval_note": "Approximate pointwise 90% rolling-origin residual band; no guaranteed time-series coverage.",
        "markets": {},
    }
    predictions = []
    future_predictions = []
    models = {}
    figure, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    for axis, (country, currency) in zip(axes, COUNTRIES.items()):
        market_train = train.loc[train["country"].eq(country)]
        market_test = test.loc[test["country"].eq(country)].copy()
        radius, calibration_count = calibration_radius(market_train)
        model = fit_model(market_train)
        prediction = model.predict(market_test["month"])
        lower, upper = prediction * np.exp(-radius), prediction * np.exp(radius)
        actual = market_test["sales"].to_numpy()
        last_year = market_train.loc[market_train["month"].dt.year.eq(2023)]
        seasonal_lookup = dict(zip(last_year["month"].dt.month, last_year["sales"]))
        baseline = market_test["month"].dt.month.map(seasonal_lookup).to_numpy()
        metrics = evaluate(actual, prediction)
        baseline_metrics = evaluate(actual, baseline)
        metrics.update({
            "currency": currency,
            "train_rows": len(market_train),
            "test_rows": len(market_test),
            "calibration_rows": calibration_count,
            "prediction_psi_train_vs_test": population_stability_index(
                model.predict(market_train["month"]), prediction,
            ),
            "interval_nominal_coverage": COVERAGE,
            "interval_test_coverage": float(np.mean((actual >= lower) & (actual <= upper))),
            "interval_mean_width": float(np.mean(upper - lower)),
            "seasonal_baseline": baseline_metrics,
            "mae_improvement_vs_baseline_percent": float(100 * (1 - metrics["mae"] / baseline_metrics["mae"])),
        })
        results["markets"][country] = metrics
        market_test["prediction"] = prediction
        market_test["lower_90"] = lower
        market_test["upper_90"] = upper
        market_test["seasonal_baseline"] = baseline
        predictions.append(market_test)
        future = pd.DataFrame({"month": pd.date_range("2026-01-01", periods=6, freq="MS")})
        future["country"] = country
        future["currency"] = currency
        future["is_synthetic"] = True
        future["prediction"] = model.predict(future["month"])
        future["lower_90"] = future["prediction"] * np.exp(-radius)
        future["upper_90"] = future["prediction"] * np.exp(radius)
        future_predictions.append(future)
        models[country] = {
            "forest": model.forest,
            "intercept": model.intercept,
            "slope": model.slope,
            "log_interval_radius": radius,
            "currency": currency,
        }
        axis.fill_between(market_test["month"], lower, upper, color="#247d69", alpha=0.2, label="Rango aproximado 90%")
        axis.plot(market_test["month"], actual, color="#202020", marker="o", markersize=3, label="Real sintetico")
        axis.plot(market_test["month"], prediction, color="#247d69", label="Tendencia + Random Forest")
        axis.plot(market_test["month"], baseline, color="#ba6035", linestyle="--", label="Referencia estacional fija")
        axis.set_title(f"{country} | {currency} | cobertura observada: {metrics['interval_test_coverage']:.0%}")
        axis.set_ylabel(f"Ventas mensuales ({currency})")
        axis.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8, loc="upper left")
    figure.suptitle("BRASALAND | DATOS SINTETICOS | prueba 2024-2025", fontsize=14)
    figure.savefig(output / "forecast_test.png", dpi=160)
    plt.close(figure)
    pd.concat(predictions).to_csv(output / "predictions_test.csv", index=False, date_format="%Y-%m-%d")
    pd.concat(future_predictions).to_csv(output / "forecast_2026.csv", index=False, date_format="%Y-%m-%d")
    joblib.dump({"synthetic": True, "seed": SEED, "models": models}, output / "models.joblib")
    (output / "metrics.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = [
        "# Resultado del experimento sintetico", "",
        "No representa ventas reales ni demuestra viabilidad financiera.", "",
        "Entrenamiento: 2016-2023. Prueba intacta: 2024-2025.", "",
        "K2 Score se interpreta provisionalmente como R2; requiere confirmacion del docente.", "",
        "| Mercado | MAE (moneda nativa) | MSE (moneda al cuadrado) | R2 / K2 supuesto | Gini normalizado | PSI | Cobertura | Mejora MAE vs referencia |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for country, metrics in results["markets"].items():
        summary.append(
            f"| {country} ({metrics['currency']}) | {metrics['mae']:,.2f} | {metrics['mse']:.6g} | "
            f"{metrics['r2']:.4f} | {metrics['normalized_gini']:.4f} | "
            f"{metrics['prediction_psi_train_vs_test']:.4f} | {metrics['interval_test_coverage']:.1%} | "
            f"{metrics['mae_improvement_vs_baseline_percent']:.1f}% |"
        )
    summary.extend(["", "Intervalo nominal aproximado: 90%; la cobertura observada no esta garantizada.",
                    "Pronostico exploratorio enero-junio 2026: forecast_2026.csv, sin observaciones para evaluarlo.",
                    "Los modelos permanecen ajustados solo hasta diciembre de 2023; no se reentrena con la prueba."])
    (output / "REPORT.es.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "brasaland_sales_synthetic.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    arguments = parser.parse_args()
    results = run(arguments.input, arguments.output)
    for country, metrics in results["markets"].items():
        print(f"{country}: MAE={metrics['mae']:,.2f} {metrics['currency']}; "
              f"R2={metrics['r2']:.4f}; coverage={metrics['interval_test_coverage']:.1%}")
    print(f"SYNTHETIC experiment artifacts: {arguments.output}")


if __name__ == "__main__":
    main()