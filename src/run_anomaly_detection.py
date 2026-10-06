"""Modül 3 deneyi: giriş-çıkış kayıtlarında anomali tespiti.

Kullanım: python -m src.run_anomaly_detection
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score

from .checkout_log import generate_checkout_log


def rule_based_flag(df):
    stats = df.groupby("interface")["duration_min"].agg(["mean", "std"]).rename(
        columns={"mean": "fam_mean", "std": "fam_std"})
    d = df.merge(stats, on="interface", how="left")
    long_duration = d["duration_min"] > (d["fam_mean"] + 3 * d["fam_std"])
    off_hours = (d["hour"] < 8) | (d["hour"] >= 17)
    incompatible = d["machine_compatible"] == 0
    flag = long_duration | off_hours | (d["is_weekend"] == 1) | incompatible
    return flag.astype(int).to_numpy()


def main():
    df = generate_checkout_log(n_days=45, seed=0, anomaly_rate=0.07)
    df.to_csv("results/checkout_log_sample.csv", index=False)
    true_rate = df["is_anomaly"].mean()
    print(f"Toplam kayıt: {len(df)}, gerçek anomali oranı: %{true_rate*100:.1f}")

    features = df[["duration_min", "hour", "is_weekend", "machine_compatible"]]
    iso = IsolationForest(n_estimators=300, contamination=true_rate, random_state=0)
    iso_flag = (iso.fit_predict(features) == -1).astype(int)
    rule_flag = rule_based_flag(df)

    y_true = df["is_anomaly"].to_numpy()
    rows = []
    for name, pred in [("IsolationForest", iso_flag), ("Kural tabanlı", rule_flag)]:
        rows.append({
            "method": name,
            "precision": precision_score(y_true, pred, zero_division=0),
            "recall": recall_score(y_true, pred, zero_division=0),
            "f1": f1_score(y_true, pred, zero_division=0),
            "flagged_count": int(pred.sum()),
        })
    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv("results/anomaly_detection_metrics.csv", index=False)
    print(metrics_df.to_string(index=False))

    by_type = df.assign(iso_flag=iso_flag, rule_flag=rule_flag).groupby("anomaly_type").apply(
        lambda g: pd.Series({
            "n": len(g), "iso_yakalama_%": 100 * g["iso_flag"].mean(),
            "rule_yakalama_%": 100 * g["rule_flag"].mean(),
        }), include_groups=False,
    ).reset_index()
    by_type.to_csv("results/anomaly_detection_by_type.csv", index=False)
    print()
    print(by_type.to_string(index=False))

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(metrics_df))
    width = 0.25
    for i, metric in enumerate(["precision", "recall", "f1"]):
        ax.bar(x + i * width, metrics_df[metric], width, label=metric)
    ax.set_xticks(x + width)
    ax.set_xticklabels(metrics_df["method"])
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title("Anomali tespiti: yöntem karşılaştırması")
    fig.tight_layout()
    fig.savefig("results/figures/anomaly_detection_comparison.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(by_type))
    width = 0.35
    ax.bar(x - width/2, by_type["iso_yakalama_%"], width, label="IsolationForest")
    ax.bar(x + width/2, by_type["rule_yakalama_%"], width, label="Kural tabanlı")
    ax.set_xticks(x)
    ax.set_xticklabels(by_type["anomaly_type"], rotation=20)
    ax.set_ylabel("Yakalama oranı (%)")
    ax.legend()
    ax.set_title("Anomali türüne göre tespit oranı")
    fig.tight_layout()
    fig.savefig("results/figures/anomaly_detection_by_type.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
