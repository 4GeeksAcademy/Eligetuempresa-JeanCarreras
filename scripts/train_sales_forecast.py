"""Entrenamiento reproducible del pronostico mensual consolidado de Brasaland."""

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

matplotlib.use("Agg")


ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "lag_1", "lag_3", "lag_12", "rolling_mean_3", "rolling_mean_12",
    "month_sin", "month_cos", "trend_month",
]
CANDIDATES = [
    {"max_depth": depth, "min_samples_leaf": leaf}
    for depth, leaf in [(3, 3), (5, 2), (None, 1)]
]


def load_sales(path):
    frame = pd.read_csv(path)
    required = {"month", "revenue_usd", "covers_served", "avg_ticket_usd", "market"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Faltan columnas del briefing: {sorted(required - set(frame.columns))}")
    selected = frame.loc[frame["market"] == "consolidated"].copy()
    selected["month"] = pd.to_datetime(selected["month"], format="%Y-%m-%d", errors="raise")
    selected = selected.sort_values("month").set_index("month")
    expected = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
    if not selected.index.equals(expected):
        raise ValueError("Se requieren exactamente 120 meses unicos consecutivos: 2016-2025.")
    revenue = pd.to_numeric(selected["revenue_usd"], errors="raise").astype(float)
    if not np.isfinite(revenue).all() or not (revenue > 0).all():
        raise ValueError("revenue_usd debe contener valores finitos positivos en USD.")
    return revenue


def split_sales(revenue):
    training = revenue.loc["2016-01-01":"2023-12-01"]
    holdout = revenue.loc["2024-01-01":"2025-12-01"]
    if len(training) != 96 or len(holdout) != 24:
        raise ValueError("El split debe contener 96 meses de entrenamiento y 24 de prueba.")
    if training.index.max() >= holdout.index.min():
        raise ValueError("El entrenamiento debe ser anterior a la prueba.")
    return training, holdout


def temporal_folds(revenue):
    if not revenue.index.is_monotonic_increasing or revenue.index.has_duplicates:
        raise ValueError("Los meses deben ser unicos y estar ordenados cronologicamente.")
    if not revenue.index.equals(pd.date_range(revenue.index[0], periods=len(revenue), freq="MS")):
        raise ValueError("No se admiten meses faltantes ni fechas distintas del inicio de mes.")
    if len(revenue) < 84:
        raise ValueError("Se necesitan al menos 84 meses para cinco bloques anuales.")
    for train_indices, validation_indices in TimeSeriesSplit(n_splits=5, test_size=12).split(revenue):
        if train_indices[-1] >= validation_indices[0]:
            raise ValueError("Fuga temporal entre entrenamiento y validacion.")
        yield train_indices, validation_indices


def feature_row(history, month):
    if len(history) < 12 or history.index[-1] >= month:
        raise ValueError("Cada prediccion necesita 12 meses estrictamente anteriores.")
    values = [
        history.iloc[-1], history.iloc[-3], history.iloc[-12],
        history.iloc[-3:].mean(), history.iloc[-12:].mean(),
        np.sin(2 * np.pi * month.month / 12),
        np.cos(2 * np.pi * month.month / 12),
        (month.year - 2016) * 12 + month.month - 1,
    ]
    return pd.DataFrame([values], columns=FEATURES, index=[month])


def training_features(revenue):
    rows = [feature_row(revenue.iloc[:position], revenue.index[position])
            for position in range(12, len(revenue))]
    if not rows:
        raise ValueError("Se necesitan mas de 12 meses para entrenar.")
    return pd.concat(rows), revenue.iloc[12:]


def fit_model(revenue, parameters):
    features, target = training_features(revenue)
    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=1, **parameters)
    model.fit(features, target)
    return model


def forecast(model, history, months):
    history = history.copy()
    predictions = []
    for month in months:
        prediction = float(model.predict(feature_row(history, month))[0])
        predictions.append(prediction)
        history.loc[month] = prediction
    return np.asarray(predictions)


def metrics(actual, predicted):
    mse = float(mean_squared_error(actual, predicted))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(actual, predicted))
    mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)
    return {
        "mse_usd2": mse,
        "rmse_usd": rmse,
        "mae_usd": mae,
        "mape_pct": round(mape, 2),
    }


def gini_coefficient(y_true, y_pred):
    """Normalized Gini coefficient (0 = random, 1 = perfect rank ordering).
    Mide que tan bien el modelo separa meses 'buenos' de 'malos'."""
    sorted_idx = np.argsort(y_pred)
    y_sorted = y_true[sorted_idx]
    n = len(y_true)
    if n < 2 or np.sum(y_sorted) == 0:
        return 0.0
    gini = (2 * np.sum(np.arange(1, n + 1) * y_sorted) / (n * np.sum(y_sorted))) - (n + 1) / n
    return float(min(max(gini, 0.0), 1.0))


def population_stability_index(train_preds, holdout_preds, n_bins=10):
    """PSI: Population Stability Index. Mide cambio distribucional entre
    entrenamiento y prueba.
    < 0.1 = sin cambio significativo; 0.1–0.25 = cambio moderado;
    > 0.25 = cambio estructural (reentrenar)."""
    if np.std(train_preds) == 0:
        return 0.0
    bins = np.percentile(train_preds, np.linspace(0, 100, n_bins + 1))
    bins[-1] = np.inf
    train_pct = np.histogram(train_preds, bins=bins)[0] / len(train_preds)
    holdout_pct = np.histogram(holdout_preds, bins=bins)[0] / len(holdout_preds)
    eps = 1e-6
    train_pct = np.clip(train_pct, eps, 1 - eps)
    holdout_pct = np.clip(holdout_pct, eps, 1 - eps)
    return float(np.sum((train_pct - holdout_pct) * np.log(train_pct / holdout_pct)))


def kolmogorov_smirnov_score(actual, predicted):
    """K2 Score: KS D statistic al cuadrado sobre los residuos.
    Mide sesgo sistematico en la distribucion del error.
    Valores cercanos a 0 indican residuos centrados sin sesgo."""
    residuals = actual - predicted
    if np.std(residuals) == 0:
        return 0.0
    d_stat, _ = ks_2samp(residuals, np.zeros_like(residuals))
    return float(d_stat ** 2)


def plot_forecast(actual, predicted, train_residuals_std, save_path):
    """Grafica ventas reales vs predichas con banda de variabilidad IC 95%."""
    fig, ax = plt.subplots(figsize=(12, 5))
    months = actual.index.strftime("%Y-%m")
    x = np.arange(len(actual))
    ax.plot(x, actual.values, "o-", label="Real", color="#1f77b4", linewidth=2)
    ax.plot(x, predicted, "s--", label="Predicho", color="#ff7f0e", linewidth=2)
    ax.fill_between(
        x,
        predicted - 1.96 * train_residuals_std,
        predicted + 1.96 * train_residuals_std,
        alpha=0.15, color="#ff7f0e", label=r"IC 95% ($\pm$1.96$\sigma$ residual)",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=45, ha="right")
    ax.set_ylabel("Ingresos (USD)")
    ax.set_title("Pronóstico de Ventas — Brasaland (Validación 2024–2025)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def select_parameters(training):
    results = []
    folds = list(temporal_folds(training))
    for parameters in CANDIDATES:
        scores = []
        for train_indices, validation_indices in folds:
            history = training.iloc[train_indices]
            validation = training.iloc[validation_indices]
            model = fit_model(history, parameters)
            predictions = forecast(model, history, validation.index)
            scores.append(metrics(validation, predictions))
        mae_means = [s["mae_usd"] for s in scores]
        results.append({
            "parameters": parameters,
            "folds": scores,
            "mae_mean_usd": float(np.mean(mae_means)),
            "mae_std_usd": float(np.std(mae_means, ddof=1)),
        })
    best = min(results, key=lambda r: r["mae_mean_usd"])
    return best["parameters"], results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/raw/brasaland_sales.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/models/brasaland-sales")
    args = parser.parse_args()
    revenue = load_sales(args.data)
    training, holdout = split_sales(revenue)
    parameters, search = select_parameters(training)
    model = fit_model(training, parameters)
    features, target = training_features(training)
    train_preds = model.predict(features)
    holdout_preds = forecast(model, training, holdout.index)
    train_metrics = metrics(target, train_preds)
    test_metrics = metrics(holdout, holdout_preds)
    test_metrics.update({
        "mse_translated_pct_err": test_metrics["mape_pct"],
        "gini": gini_coefficient(holdout.values, holdout_preds),
        "psi": population_stability_index(train_preds, holdout_preds),
        "k2_score": kolmogorov_smirnov_score(holdout.values, holdout_preds),
    })
    train_residuals_std = float(np.std(target - train_preds, ddof=1))
    args.output.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output / "model.joblib")
    pd.DataFrame({
        "month": holdout.index, "revenue_usd": holdout.values,
        "predicted_revenue_usd": holdout_preds,
    }).to_csv(args.output / "holdout.csv", index=False)
    plot_forecast(holdout, holdout_preds, train_residuals_std,
                  args.output / "forecast_validation.png")
    psi_note = ""
    if test_metrics["psi"] > 0.25:
        psi_note = (
            "ATENCION: PSI > 0.25 indica un cambio estructural significativo "
            "entre entrenamiento y prueba. Se recomienda reentrenar el modelo "
            "con los datos mas recientes."
        )
    elif test_metrics["psi"] > 0.1:
        psi_note = (
            "PRECAUCION: PSI entre 0.1 y 0.25 sugiere un cambio distribucional "
            "moderado. Monitorear en el proximo ciclo."
        )
    metadata = {
        "provenance": "Modelo nuevo; no se encontro un artefacto del proyecto anterior.",
        "target": "revenue_usd", "market": "consolidated", "features": FEATURES,
        "forecast_protocol": "Recursivo: no usa ventas reales del bloque de validacion.",
        "training_period": [str(training.index.min().date()), str(training.index.max().date())],
        "holdout_period": [str(holdout.index.min().date()), str(holdout.index.max().date())],
        "parameters": parameters, "search_results": search,
        "training_metrics": train_metrics,
        "holdout_metrics": test_metrics,
        "train_residuals_std_usd": train_residuals_std,
        "psi_interpretation": psi_note,
        "gini_interpretation": (
            "Bajo (<0.3): el modelo no discrimina bien meses buenos de malos."
            if test_metrics["gini"] < 0.3 else
            "Aceptable (>=0.3): el modelo puede ordenar meses por desempeno."
        ),
        "warning": "Los folds usados para seleccionar parametros no son una evaluacion independiente.",
    }
    (args.output / "training_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Modelo y metadatos guardados en {args.output}")
    print(f"  MSE: {test_metrics['mse_usd2']:.0f} USD²  "
          f"(error promedio ~{test_metrics['mape_pct']:.1f}%)")
    print(f"  Gini: {test_metrics['gini']:.3f}")
    print(f"  PSI: {test_metrics['psi']:.4f}")
    print(f"  K2 Score: {test_metrics['k2_score']:.6f}")


if __name__ == "__main__":
    main()