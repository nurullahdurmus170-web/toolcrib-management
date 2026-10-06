"""Modül 1: Tutucu bakım riski tahmini.

Önceki (daha basit) programımda bakım uyarısı tek bir sabit
kullanım eşiğine (ör. 300) dayanıyordu: eşiğin üstüne çıkan her tutucu, tipi ne olursa olsun aynı
şekilde "bakım gerekli" sayılır. Gerçekte farklı tutucu tipleri ve
bağlantı standartları farklı gerçek dayanım sınırlarına sahiptir.

Bu modül, tutucu tipine/standardına göre DEĞİŞEN bir "gerçek" (gizli)
dayanım sınırı simüle eder ve bir modelin, sabit eşik kuralından daha
iyi bir erken uyarı verip veremeyeceğini test eder.

Not: Gerçek bir firmanın aşınma/arıza verisi kullanılmamıştır; dayanım
sınırları ve ağırlıklar sentetik olarak atanmıştır.
"""
import numpy as np
import pandas as pd

from .taxonomy import HOLDER_INTERFACES, HOLDER_TYPES, HOLDER_LENGTHS, HOLDER_SYSTEMS

FIXED_THRESHOLD = 300  # mevcut basit sistemin kullandığı sabit eşik

# Tip ve bağlantı standardına göre taban dayanım sınırı (sentetik, nitel
# olarak gerçekçi: ince/küçük tutucular daha düşük, ağır/büyük tutucular
# daha yüksek dayanım sınırına sahip olacak şekilde tasarlanmıştır)
TYPE_BASE_LIMIT = {"Shrink": 320, "Pens&Bilyalı": 260, "Kollet": 230}
INTERFACE_LIMIT_FACTOR = {
    "HSK63": 1.05, "BT40": 1.0, "BBT40": 1.1, "HSK100": 1.2,
    "BBT50": 1.15, "SK40": 0.9, "BBT30": 0.8, "CAPTO": 1.0,
}
LENGTH_FACTOR = {"Kısa": 1.1, "Uzun": 1.0, "İnce": 0.75}


def _interface_weights():
    names = [h["name"] for h in HOLDER_INTERFACES]
    weights = np.array([h["relative_freq"] for h in HOLDER_INTERFACES], dtype=float)
    return names, weights / weights.sum()


def generate_dataset(n_samples=2500, seed=0):
    rng = np.random.default_rng(seed)
    names, probs = _interface_weights()

    rows = []
    for _ in range(n_samples):
        interface = rng.choice(names, p=probs)
        htype = rng.choice(HOLDER_TYPES)
        length_cat = rng.choice(HOLDER_LENGTHS)
        system = rng.choice(HOLDER_SYSTEMS)

        true_limit = (TYPE_BASE_LIMIT[htype] * INTERFACE_LIMIT_FACTOR[interface]
                       * LENGTH_FACTOR[length_cat])
        true_limit *= rng.lognormal(mean=0.0, sigma=0.12)  # tutucudan tutucuya değişkenlik
        true_limit = max(50.0, true_limit)

        usage_count = rng.uniform(0, true_limit * 1.15)
        age_days = usage_count * rng.uniform(1.5, 4.0)  # kabaca kullanım sıklığına bağlı yaş

        remaining = true_limit - usage_count
        remaining_frac = remaining / true_limit
        if remaining_frac < 0.10:
            risk = "HIGH"
        elif remaining_frac < 0.30:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        rows.append({
            "interface": interface, "type": htype, "length_category": length_cat,
            "system": system, "usage_count": round(usage_count, 1),
            "age_days": round(age_days, 1),
            "true_limit": round(true_limit, 1),
            "risk_class": risk,
            "needs_maintenance_soon": int(risk == "HIGH"),
        })
    return pd.DataFrame(rows)


def fixed_threshold_rule(df, threshold=FIXED_THRESHOLD):
    """Mevcut basit sistemin kuralı: tip/standart farkı olmadan sabit eşik."""
    return (df["usage_count"] >= threshold).astype(int)
