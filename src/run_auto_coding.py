"""Modül 4 deneyi: gerçek taksonomiyle aile sınıflandırması + kod önerisi.

10 aile (9 kesici takım + HL/Tutucu) ve boy/çap oranı (aspect_ratio)
özelliği dahil, 5 seed üzerinden ortalanmış metrikler.

Kullanım: python -m src.run_auto_coding
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from .auto_coding import generate_tool_records, suggest_code_template, CLASSIFIABLE_FAMILIES

NUMERIC = ["diameter_mm", "length_mm", "flute_count", "aspect_ratio"]
CATEGORICAL = ["material", "coating"]
FAMILY_CODES = list(CLASSIFIABLE_FAMILIES.keys())
SEEDS = [0, 1, 2, 3, 4]


def _run_one_seed(seed):
    df = generate_tool_records(n_per_family=150, seed=seed)
    X = df[NUMERIC + CATEGORICAL]
    y = df["family_code"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=y
    )
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
                             remainder="passthrough")
    clf = Pipeline([("pre", pre), ("model", RandomForestClassifier(n_estimators=300, random_state=seed))])
    clf.fit(X_train, y_train)
    pred = clf.predict(X_test)

    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train[NUMERIC], y_train)
    pred_dummy = dummy.predict(X_test[NUMERIC])

    metrics = {
        "rf_accuracy": accuracy_score(y_test, pred),
        "rf_macro_f1": f1_score(y_test, pred, average="macro"),
        "dummy_accuracy": accuracy_score(y_test, pred_dummy),
        "dummy_macro_f1": f1_score(y_test, pred_dummy, average="macro", zero_division=0),
    }
    per_family = pd.DataFrame({"family_code": y_test, "correct": (y_test.to_numpy() == pred)})
    acc_by_family = per_family.groupby("family_code")["correct"].mean()
    return metrics, acc_by_family, (y_test, pred, df, X_test)


def main():
    metrics_list, acc_by_family_list = [], []
    last_example = None
    for seed in SEEDS:
        metrics, acc_by_family, example = _run_one_seed(seed)
        metrics_list.append(metrics)
        acc_by_family_list.append(acc_by_family)
        last_example = example

    generate_tool_records(n_per_family=150, seed=SEEDS[-1]).to_csv(
        "results/auto_coding_dataset_sample.csv", index=False)

    metrics_df = pd.DataFrame(metrics_list)
    summary = pd.DataFrame([
        {"model": "Random Forest", "accuracy_mean": metrics_df.rf_accuracy.mean(),
         "accuracy_std": metrics_df.rf_accuracy.std(), "macro_f1_mean": metrics_df.rf_macro_f1.mean(),
         "macro_f1_std": metrics_df.rf_macro_f1.std()},
        {"model": "Dummy (en sık aile)", "accuracy_mean": metrics_df.dummy_accuracy.mean(),
         "accuracy_std": metrics_df.dummy_accuracy.std(), "macro_f1_mean": metrics_df.dummy_macro_f1.mean(),
         "macro_f1_std": metrics_df.dummy_macro_f1.std()},
    ])
    summary.to_csv("results/auto_coding_metrics.csv", index=False)
    print(f"== Sınıflandırma metrikleri ({len(SEEDS)} seed ortalaması) ==")
    print(summary.to_string(index=False))

    acc_by_family_df = pd.concat(acc_by_family_list, axis=1)
    acc_summary = pd.DataFrame({
        "family_code": acc_by_family_df.index,
        "accuracy_mean": acc_by_family_df.mean(axis=1).to_numpy(),
        "accuracy_std": acc_by_family_df.std(axis=1).to_numpy(),
    }).sort_values("accuracy_mean")
    acc_summary.to_csv("results/auto_coding_accuracy_by_family.csv", index=False)
    print()
    print(acc_summary.to_string(index=False))

    y_test, pred, df, X_test = last_example
    cm = confusion_matrix(y_test, pred, labels=FAMILY_CODES)
    fig, ax = plt.subplots(figsize=(7, 6.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(FAMILY_CODES)))
    ax.set_yticks(range(len(FAMILY_CODES)))
    ax.set_xticklabels(FAMILY_CODES)
    ax.set_yticklabels(FAMILY_CODES)
    ax.set_xlabel("Tahmin edilen aile kodu")
    ax.set_ylabel("Gerçek aile kodu")
    ax.set_title("Otomatik kodlama — karışıklık matrisi (10 aile)")
    for i in range(len(FAMILY_CODES)):
        for j in range(len(FAMILY_CODES)):
            if cm[i, j] > 0:
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] > cm.max()/2 else "black", fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig("results/figures/auto_coding_confusion_matrix.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh(acc_summary["family_code"], acc_summary["accuracy_mean"],
            xerr=acc_summary["accuracy_std"])
    ax.set_xlabel(f"Doğruluk (ortalama ± std, {len(SEEDS)} seed)")
    ax.set_title("Aile başına sınıflandırma doğruluğu")
    fig.tight_layout()
    fig.savefig("results/figures/auto_coding_accuracy_by_family.png", dpi=150)
    plt.close(fig)

    examples = X_test.iloc[:5].copy()
    examples["gercek_aile"] = y_test.iloc[:5].to_numpy()
    examples["tahmin_aile"] = pred[:5]
    templates, filled = [], []
    for _, row in examples.iterrows():
        tmpl, frow = suggest_code_template(
            row["tahmin_aile"], diameter_mm=row["diameter_mm"], length_mm=row["length_mm"],
            flute_count=row["flute_count"], material=row["material"], coating=row["coating"])
        templates.append(tmpl)
        filled.append(frow)
    examples["format_sablonu"] = templates
    examples["onerilen_kod_taslagi"] = filled
    examples.to_csv("results/auto_coding_code_suggestion_examples.csv", index=False)
    print("\n== Örnek kod önerileri ==")
    print(examples[["gercek_aile", "tahmin_aile", "onerilen_kod_taslagi"]].to_string(index=False))


if __name__ == "__main__":
    main()
