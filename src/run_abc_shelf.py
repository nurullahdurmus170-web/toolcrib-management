"""Modül 2 deneyi: A/B/C sınıflandırması, talep tahmini ve raf bölgesi
kayma (drift) tespiti.

Kullanım: python -m src.run_abc_shelf
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .abc_shelf import generate_daily_usage
from .taxonomy import HOLDER_INTERFACES

FORECAST_DAYS = 14
HISTORY_DAYS = 120  # A/B/C için kullanılan "geçmiş" pencere


def classify_abc(usage_by_interface):
    """Klasik A/B/C: toplam kullanıma göre sıralı kümülatif pay.
    A: ilk %70'e kadar, B: %70-90, C: kalan (Pareto benzeri)."""
    s = usage_by_interface.sort_values(ascending=False)
    cum_share = s.cumsum() / s.sum()
    classes = pd.Series(index=s.index, dtype=object)
    classes[cum_share <= 0.70] = "A"
    classes[(cum_share > 0.70) & (cum_share <= 0.90)] = "B"
    classes[cum_share > 0.90] = "C"
    return classes


def exp_smooth_forecast_last(series, alpha=0.3):
    level = series.iloc[0]
    for v in series:
        level = alpha * v + (1 - alpha) * level
    return level


def main():
    df = generate_daily_usage(n_days=180, seed=0)
    df.to_csv("results/abc_usage_dataset_sample.csv", index=False)

    hist = df[df.date < df.date.max() - pd.Timedelta(days=FORECAST_DAYS)]
    hist_recent = hist[hist.date >= hist.date.max() - pd.Timedelta(days=HISTORY_DAYS)]
    future = df[df.date >= df.date.max() - pd.Timedelta(days=FORECAST_DAYS)]

    hist_totals = hist_recent.groupby("interface")["usage_count"].sum()
    hist_classes = classify_abc(hist_totals)

    # Tahmin: her standart için üstel düzgünleştirme ile günlük seviye,
    # FORECAST_DAYS ile çarpılarak "öngörülen" dönem toplamı kestirilir.
    forecast_levels = {}
    actual_future_totals = {}
    mae_rows = []
    for h in HOLDER_INTERFACES:
        name = h["name"]
        s = hist_recent[hist_recent.interface == name].sort_values("date")["usage_count"]
        level = exp_smooth_forecast_last(s, alpha=0.3)
        forecast_levels[name] = level
        fut = future[future.interface == name]["usage_count"]
        actual_future_totals[name] = fut.sum()
        mae = abs(level * FORECAST_DAYS - fut.sum())
        mae_rows.append({"interface": name, "forecast_period_total": round(level * FORECAST_DAYS, 1),
                          "actual_period_total": int(fut.sum()), "abs_error": round(mae, 1)})

    forecast_totals = pd.Series({k: v * FORECAST_DAYS for k, v in forecast_levels.items()})
    forecast_classes = classify_abc(forecast_totals)

    drift_df = pd.DataFrame({
        "interface": hist_classes.index,
        "historical_class": hist_classes.values,
        "forecast_class": [forecast_classes.get(i, "?") for i in hist_classes.index],
    })
    drift_df["class_changed"] = drift_df["historical_class"] != drift_df["forecast_class"]
    drift_df.to_csv("results/abc_class_drift.csv", index=False)

    mae_df = pd.DataFrame(mae_rows)
    mae_df.to_csv("results/abc_forecast_mae.csv", index=False)

    # Raf bölgesi önerisi: A->Zone1, B->Zone2, C->Zone3; kayan standartlar
    # için önerilen bölge değişikliği ayrıca işaretlenir.
    zone_map = {"A": "Zone 1 (operatöre en yakın)", "B": "Zone 2 (orta mesafe)", "C": "Zone 3 (arka/az erişilen)"}
    drift_df["current_zone"] = drift_df["historical_class"].map(zone_map)
    drift_df["suggested_zone"] = drift_df["forecast_class"].map(zone_map)
    drift_df.to_csv("results/abc_shelf_suggestions.csv", index=False)

    print("== A/B/C sınıf kayması (geçmiş vs tahmin) ==")
    print(drift_df.to_string(index=False))
    print("\n== Tahmin hatası (14 günlük dönem toplamı) ==")
    print(mae_df.to_string(index=False))

    # --- Şekil: BBT40 örneği üzerinden yükseliş trendi ---
    sub = df[df.interface == "BBT40"].sort_values("date")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(sub["date"], sub["usage_count"].rolling(7).mean(), label="7g hareketli ortalama")
    ax.axvline(df.date.max() - pd.Timedelta(days=FORECAST_DAYS), color="gray", linestyle=":")
    ax.set_title("BBT40: açıkça yükselen talep trendi (7 günlük hareketli ortalama)")
    ax.set_ylabel("Günlük kullanım (7g ort.)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig("results/figures/abc_bbt40_trend.png", dpi=150)
    plt.close(fig)

    # --- Şekil: geçmiş vs tahmin edilen dönem toplamları (A/B/C renkli) ---
    colors = {"A": "#2e7d32", "B": "#f9a825", "C": "#9e9e9e"}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(drift_df))
    ax.bar(x, mae_df.set_index("interface").loc[drift_df["interface"], "actual_period_total"],
           color=[colors[c] for c in drift_df["forecast_class"]])
    ax.set_xticks(x)
    ax.set_xticklabels(drift_df["interface"], rotation=20)
    ax.set_ylabel(f"Gerçekleşen kullanım (son {FORECAST_DAYS} gün)")
    ax.set_title("Standart başına kullanım (renk = tahmin edilen A/B/C sınıfı)")
    fig.tight_layout()
    fig.savefig("results/figures/abc_classes_forecast.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
