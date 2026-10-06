"""Maliyet tabanlı karar çerçevesi: öğrenilen model vs sabit eşik.

Precision/recall/F1 soyut kalır; gerçek bir mühendislik kararı için
"kaçırılan bir bakımın maliyeti" ile "yanlış alarmın maliyeti"
birbirine göre tartılmalıdır. Bu modül, bu iki maliyetin oranına göre
hangi yöntemin daha düşük beklenen maliyete sahip olduğunu gösterir.

Not: Maliyet değerleri (ör. kaçırılan bakımın yanlış alarmdan N kat
daha maliyetli olması) örnektir; gerçek bir firmanın maliyet verisi
değildir. Amaç, kararın maliyet oranına NASIL bağlı olduğunu
göstermektir, kesin bir TL değeri vermek değildir.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def expected_cost_per_record(binary_df, cost_fn, cost_fp, prefix):
    """binary_df: run_maintenance_risk._run_one_seed çıktılarının
    DataFrame'i. prefix: 'model' veya 'rule'. Her seed için kayıt
    başına beklenen maliyeti döndürür (FN ve FP sayılarına dayalı;
    TP ve TN maliyetsiz kabul edilir — doğru tespit/doğru ihmal)."""
    fn = binary_df[f"{prefix}_fn"]
    fp = binary_df[f"{prefix}_fp"]
    n = binary_df["n_test"]
    return (fn * cost_fn + fp * cost_fp) / n


def plot_cost_comparison(binary_df, outpath, cost_fp=1.0, min_ratio=0.1, max_ratio=15):
    """cost_fn/cost_fp oranını min_ratio'dan max_ratio'ya taratıp, her
    oranda hangi yöntemin (model/kural) daha düşük beklenen maliyete
    sahip olduğunu gösteren bir grafik üretir. min_ratio < 1 bölgesi,
    yanlış alarmın kaçırılan bakımdan daha maliyetli olduğu (ör. her
    yanlış alarm gereksiz bir üretim durdurması anlamına geliyorsa)
    senaryoları kapsar."""
    ratios = np.linspace(min_ratio, max_ratio, 100)
    model_costs, rule_costs = [], []
    for r in ratios:
        cost_fn = r * cost_fp
        model_costs.append(expected_cost_per_record(binary_df, cost_fn, cost_fp, "model").mean())
        rule_costs.append(expected_cost_per_record(binary_df, cost_fn, cost_fp, "rule").mean())

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ratios, model_costs, label="Öğrenilen model (RF)")
    ax.plot(ratios, rule_costs, label="Sabit eşik kuralı")
    ax.set_xlabel("Maliyet oranı: kaçırılan bakım / yanlış alarm")
    ax.set_ylabel("Kayıt başına beklenen maliyet (yanlış alarm birimiyle)")
    ax.set_title("Hangi yöntem daha az maliyetli? (maliyet oranına bağlı)")
    ax.legend()

    model_arr, rule_arr = np.array(model_costs), np.array(rule_costs)
    crossover_idx = np.where(np.diff(np.sign(model_arr - rule_arr)))[0]
    x_cross = float(ratios[crossover_idx[0]]) if len(crossover_idx) else None
    if x_cross is not None:
        ax.axvline(x_cross, color="gray", linestyle=":")
        ax.annotate(f"geçiş noktası ≈ {x_cross:.2f}", (x_cross, max(model_costs + rule_costs) * 0.9))

    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)

    df = pd.DataFrame({"cost_ratio": ratios, "model_expected_cost": model_costs,
                        "rule_expected_cost": rule_costs})
    df.attrs["crossover_ratio"] = x_cross
    return df
