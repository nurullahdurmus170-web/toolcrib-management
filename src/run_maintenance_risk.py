"""Modül 1 deneyi: öğrenilen risk modeli vs sabit eşik kuralı.

Kullanım: python -m src.run_maintenance_risk
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                              recall_score, confusion_matrix)
from .cost_analysis import plot_cost_comparison
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from .maintenance_risk import generate_dataset, fixed_threshold_rule, FIXED_THRESHOLD

NUMERIC = ["usage_count", "age_days"]
CATEGORICAL = ["interface", "type", "length_category", "system"]


SEEDS = [0, 1, 2, 3, 4]


def _run_one_seed(seed):
    """Bir veri/tohum için çok sınıflı ve ikili karşılaştırma metriklerini
    döndürür. Çağıran taraf bunu SEEDS üzerinde ortalar."""
    df = generate_dataset(n_samples=2500, seed=seed)
    X = df[CATEGORICAL + NUMERIC]
    y_multi = df["risk_class"]
    y_bin = df["needs_maintenance_soon"]

    idx_train, idx_test = train_test_split(
        df.index, test_size=0.25, random_state=seed, stratify=y_multi
    )
    X_train, X_test = X.loc[idx_train], X.loc[idx_test]

    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
                             remainder="passthrough")

    clf_multi = Pipeline([("pre", pre), ("model", RandomForestClassifier(
        n_estimators=300, random_state=seed, class_weight="balanced"))])
    clf_multi.fit(X_train, y_multi.loc[idx_train])
    pred_multi = clf_multi.predict(X_test)

    dummy_multi = DummyClassifier(strategy="most_frequent")
    dummy_multi.fit(X_train[NUMERIC], y_multi.loc[idx_train])
    pred_multi_dummy = dummy_multi.predict(X_test[NUMERIC])

    multi = {
        "rf_accuracy": accuracy_score(y_multi.loc[idx_test], pred_multi),
        "rf_macro_f1": f1_score(y_multi.loc[idx_test], pred_multi, average="macro"),
        "dummy_accuracy": accuracy_score(y_multi.loc[idx_test], pred_multi_dummy),
        "dummy_macro_f1": f1_score(y_multi.loc[idx_test], pred_multi_dummy, average="macro"),
    }

    clf_bin = Pipeline([("pre", pre), ("model", RandomForestClassifier(
        n_estimators=300, random_state=seed, class_weight="balanced"))])
    clf_bin.fit(X_train, y_bin.loc[idx_train])
    pred_bin_model = clf_bin.predict(X_test)
    pred_bin_rule = fixed_threshold_rule(df.loc[idx_test])
    y_test_bin = y_bin.loc[idx_test]

    def _confusion_counts(y_true, y_pred):
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}

    binary = {
        "model_precision": precision_score(y_test_bin, pred_bin_model, zero_division=0),
        "model_recall": recall_score(y_test_bin, pred_bin_model, zero_division=0),
        "model_f1": f1_score(y_test_bin, pred_bin_model, zero_division=0),
        "rule_precision": precision_score(y_test_bin, pred_bin_rule, zero_division=0),
        "rule_recall": recall_score(y_test_bin, pred_bin_rule, zero_division=0),
        "rule_f1": f1_score(y_test_bin, pred_bin_rule, zero_division=0),
        "n_test": len(y_test_bin),
    }
    model_cm = _confusion_counts(y_test_bin, pred_bin_model)
    rule_cm = _confusion_counts(y_test_bin, pred_bin_rule)
    for k, v in model_cm.items():
        binary[f"model_{k}"] = v
    for k, v in rule_cm.items():
        binary[f"rule_{k}"] = v

    test_df = df.loc[idx_test].copy()
    test_df["rule_pred"] = pred_bin_rule
    by_type = test_df.groupby("type").apply(
        lambda g: pd.Series({
            "true_rate_%": 100 * g["needs_maintenance_soon"].mean(),
            "rule_flagged_%": 100 * g["rule_pred"].mean(),
        }), include_groups=False
    )
    return multi, binary, by_type


def main():
    # Son seed'in ham veri örneğini (demo/inceleme amaçlı) sakla
    generate_dataset(n_samples=2500, seed=SEEDS[-1]).to_csv(
        "results/maintenance_dataset_sample.csv", index=False)

    multi_list, binary_list, by_type_list = [], [], []
    for seed in SEEDS:
        multi, binary, by_type = _run_one_seed(seed)
        multi_list.append(multi)
        binary_list.append(binary)
        by_type_list.append(by_type)

    multi_df = pd.DataFrame(multi_list)
    multi_summary = pd.DataFrame([
        {"model": "Random Forest", "accuracy_mean": multi_df.rf_accuracy.mean(),
         "accuracy_std": multi_df.rf_accuracy.std(), "macro_f1_mean": multi_df.rf_macro_f1.mean(),
         "macro_f1_std": multi_df.rf_macro_f1.std()},
        {"model": "Dummy (en sık sınıf)", "accuracy_mean": multi_df.dummy_accuracy.mean(),
         "accuracy_std": multi_df.dummy_accuracy.std(), "macro_f1_mean": multi_df.dummy_macro_f1.mean(),
         "macro_f1_std": multi_df.dummy_macro_f1.std()},
    ])
    multi_summary.to_csv("results/maintenance_classification_metrics.csv", index=False)

    binary_df = pd.DataFrame(binary_list)
    compare_df = pd.DataFrame([
        {"method": "Öğrenilen model (RF)",
         "precision_mean": binary_df.model_precision.mean(), "precision_std": binary_df.model_precision.std(),
         "recall_mean": binary_df.model_recall.mean(), "recall_std": binary_df.model_recall.std(),
         "f1_mean": binary_df.model_f1.mean(), "f1_std": binary_df.model_f1.std()},
        {"method": f"Sabit eşik (usage_count ≥ {FIXED_THRESHOLD})",
         "precision_mean": binary_df.rule_precision.mean(), "precision_std": binary_df.rule_precision.std(),
         "recall_mean": binary_df.rule_recall.mean(), "recall_std": binary_df.rule_recall.std(),
         "f1_mean": binary_df.rule_f1.mean(), "f1_std": binary_df.rule_f1.std()},
    ])
    compare_df.to_csv("results/maintenance_vs_fixed_threshold.csv", index=False)

    by_type = pd.concat(by_type_list).groupby(level=0).agg(["mean", "std"])
    by_type.columns = ["_".join(c) for c in by_type.columns]
    by_type = by_type.reset_index().rename(columns={"index": "type"})
    by_type.to_csv("results/maintenance_rule_bias_by_type.csv", index=False)

    print(f"== Çok sınıflı risk sınıflandırması ({len(SEEDS)} seed ortalaması) ==")
    print(multi_summary.to_string(index=False))
    print(f"\n== Öğrenilen model vs sabit eşik ({len(SEEDS)} seed ortalaması) ==")
    print(compare_df.to_string(index=False))
    print("\n== Sabit eşiğin tip bazında sapması ==")
    print(by_type.to_string(index=False))

    # Grafikler son seed'in tek-örnek sonuçlarından üretilir (görsel amaçlı);
    # metin/tablo metrikleri yukarıdaki seed-ortalamalarından gelir.
    compare_df_single = pd.DataFrame([
        {"method": "Öğrenilen model (RF)", "precision": binary_list[-1]["model_precision"],
         "recall": binary_list[-1]["model_recall"], "f1": binary_list[-1]["model_f1"]},
        {"method": f"Sabit eşik (usage_count ≥ {FIXED_THRESHOLD})", "precision": binary_list[-1]["rule_precision"],
         "recall": binary_list[-1]["rule_recall"], "f1": binary_list[-1]["rule_f1"]},
    ])
    by_type_single = by_type_list[-1].reset_index().rename(columns={"index": "type"})

    # --- Şekil: yöntem karşılaştırması (tek-seed örnek, metinler seed ortalamasından) ---
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(compare_df_single))
    width = 0.25
    for i, metric in enumerate(["precision", "recall", "f1"]):
        ax.bar(x + i * width, compare_df_single[metric], width, label=metric)
    ax.set_xticks(x + width)
    ax.set_xticklabels(compare_df_single["method"], fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title("Bakım riski: öğrenilen model vs sabit eşik kuralı")
    fig.tight_layout()
    fig.savefig("results/figures/maintenance_vs_fixed_threshold.png", dpi=150)
    plt.close(fig)

    # --- Şekil: tip bazında sabit eşiğin yanlış kalibrasyonu ---
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(by_type_single))
    width = 0.35
    ax.bar(x - width/2, by_type_single["true_rate_%"], width, label="Gerçek bakım ihtiyacı %")
    ax.bar(x + width/2, by_type_single["rule_flagged_%"], width, label=f"Sabit eşik (≥{FIXED_THRESHOLD}) işaretlediği %")
    ax.set_xticks(x)
    ax.set_xticklabels(by_type_single["type"])
    ax.set_ylabel("%")
    ax.legend()
    ax.set_title("Sabit eşik, tutucu tipine göre sistematik olarak sapıyor")
    fig.tight_layout()
    fig.savefig("results/figures/maintenance_rule_bias.png", dpi=150)
    plt.close(fig)

    # --- Maliyet tabanlı karar analizi (bkz. src/cost_analysis.py) ---
    cost_df = plot_cost_comparison(binary_df, "results/figures/maintenance_cost_analysis.png")
    cost_df.to_csv("results/maintenance_cost_analysis.csv", index=False)
    def _winner(row):
        return "model" if row.model_expected_cost < row.rule_expected_cost else "kural"

    r1 = cost_df.iloc[(cost_df.cost_ratio - 1.0).abs().argmin()]
    r10 = cost_df[cost_df.cost_ratio >= 10].iloc[0]
    print("\n== Maliyet analizi ==")
    print(f"Oran=1 (eşit maliyet) iken daha az maliyetli: {_winner(r1)} "
          f"(model={r1.model_expected_cost:.4f}, kural={r1.rule_expected_cost:.4f})")
    print(f"Oran=10 (kaçırılan bakım, yanlış alarmdan 10x maliyetli) iken daha az maliyetli: {_winner(r10)} "
          f"(model={r10.model_expected_cost:.4f}, kural={r10.rule_expected_cost:.4f})")
    x_cross = cost_df.attrs.get("crossover_ratio")
    if x_cross is not None:
        print(f"Geçiş noktası: maliyet oranı ≈ {x_cross:.2f}")
    else:
        print("Bu oran aralığında geçiş noktası yok; bir yöntem tüm aralıkta daha az maliyetli.")


if __name__ == "__main__":
    main()
