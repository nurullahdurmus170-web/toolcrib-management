"""Modül 2: Bağlantı standardı bazında kullanım verisi, A/B/C sınıflandırması
ve raf bölgesi önerisi.

Kendi çalışmalarımdan esinlenerek yaptığım önceki programdaki A/B/C analizi
GEÇMİŞE bakar (toplam kullanım sayısına göre statik sınıflandırma).
Bu modül aynı analizi yapar, ÜSTÜNE talep tahmini ekler: bir
standardın A/B/C sınıfı yakın gelecekte değişebilir mi (ör. B'den
A'ya yükseliyor mu), bu erken fark edilebilir mi?

Not: Bağlantı standartlarının bağıl kullanım sıklığı sıralaması
(src/taxonomy.py) nitel bir varsayımdır; gerçek bir sayım değildir.
"""
import numpy as np
import pandas as pd

from .taxonomy import HOLDER_INTERFACES


def generate_daily_usage(n_days=180, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-04-01", periods=n_days, freq="D")
    rows = []
    for h in HOLDER_INTERFACES:
        name, base = h["name"], h["relative_freq"]
        # B grubundaki bir standarda, son 60 günde yükselen bir trend
        # veriyoruz (A grubuna "yükseliş" senaryosu için)
        rising = name == "BBT40"
        for day_idx, date in enumerate(dates):
            weekday = date.dayofweek
            weekend_factor = 0.2 if weekday >= 5 else 1.0
            level = base * weekend_factor
            if rising and day_idx > n_days - 60:
                level *= 1.0 + 1.5 * (day_idx - (n_days - 60)) / 60.0
            usage = max(0, rng.poisson(max(0.1, level)))
            rows.append({"date": date, "interface": name, "usage_count": usage})
    return pd.DataFrame(rows)
