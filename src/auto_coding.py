"""Modül 4: Gerçek 14 ailelik kodlama taksonomisiyle otomatik takım
ailesi sınıflandırması ve yapılandırılmış kod önerisi.

Kullandığım kodlama şemasında her aile için ayrı bir Excel dosyası
(dropdown doğrulamalı) manuel olarak dolduruluyordu. Bu modül, yeni bir
takımın ölçülebilir özelliklerinden (çap, toplam boy, ağız sayısı,
malzeme/kaplama) hangi aileye ait olduğunu otomatik önerir VE o
ailenin format şablonuna (src/taxonomy.py) göre yapılandırılmış bir
kod taslağı üretir.

Not: Sentetik veri; gerçek bir firmanın envanter kayıtları değildir.
Yalnızca genel ölçülebilir özelliklerle ayırt edilebilecek 9 aile
(EM, ER, EB, DR, RM, TP, PT, DW, TM) bu sınıflandırmaya dahil
edilmiştir; FM/SM (gövde+plaka tipi), IN (plaka) ve HL (tutucu) farklı
ölçüm mantığına sahip olduğu için bu modülün kapsamı dışında
tutulmuştur (bkz. Sınırlılıklar).
"""
import numpy as np
import pandas as pd

from .taxonomy import FAMILY_BY_CODE

# Sınıflandırmaya dahil edilen aileler ve tipik çap/boy aralıkları (mm).
# HL (Tutucu) için "çap" bağlama ölçüsünü (ör. ER32 kolet için ~32mm)
# temsil eder; tutucularda ağız (flute) kavramı yoktur, bu nedenle
# flute_count=0 atanır (bkz. generate_tool_records) — bu yapay bir sinyal
# değil, fiziksel olarak gerçek bir ayırt edici özelliktir.
CLASSIFIABLE_FAMILIES = {
    "EM": {"diam": (3, 25), "length_mult": (3.0, 6.0)},
    "ER": {"diam": (3, 25), "length_mult": (3.0, 6.0)},
    "EB": {"diam": (3, 20), "length_mult": (3.5, 6.5)},
    "DR": {"diam": (2, 20), "length_mult": (4.0, 8.0)},
    "RM": {"diam": (5, 20), "length_mult": (4.0, 7.0)},
    "TP": {"diam": (3, 16), "length_mult": (3.0, 5.0)},
    "PT": {"diam": (4, 16), "length_mult": (1.5, 3.0)},
    "DW": {"diam": (6, 25), "length_mult": (2.0, 4.0)},
    "TM": {"diam": (8, 40), "length_mult": (1.0, 2.5)},
    "HL": {"diam": (16, 50), "length_mult": (2.0, 4.0)},
}
NO_FLUTE_FAMILIES = {"HL"}

MATERIALS = ["HSS", "Karbür", "Kobalt"]
COATINGS = ["Kaplamasız", "TiN", "TiAlN", "DLC"]


def generate_tool_records(n_per_family=150, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for code, spec in CLASSIFIABLE_FAMILIES.items():
        lo, hi = spec["diam"]
        lmlo, lmhi = spec["length_mult"]
        for _ in range(n_per_family):
            diameter = rng.uniform(lo, hi)
            length = max(8.0, diameter * rng.uniform(lmlo, lmhi) + rng.normal(0, 4))
            flute_count = 0 if code in NO_FLUTE_FAMILIES else int(rng.choice([2, 3, 4, 6]))
            material = rng.choice(MATERIALS)
            coating = rng.choice(COATINGS)
            rows.append({
                "diameter_mm": round(diameter, 2), "length_mm": round(length, 1),
                "flute_count": flute_count, "material": material, "coating": coating,
                "aspect_ratio": round(length / diameter, 3),
                "family_code": code,
            })
    return pd.DataFrame(rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)


def suggest_code_template(family_code, diameter_mm=None, length_mm=None,
                           flute_count=None, material="Belirtilmedi", coating="Belirtilmedi"):
    """Tahmin edilen aile için format şablonunu, bilinen alanlar
    doldurulmuş, bilinmeyenler [ALAN] olarak bırakılmış şekilde döndürür."""
    fam = FAMILY_BY_CODE[family_code]
    template = fam["template"]
    filled = template
    filled = filled.replace("[BR]", material if material else "[BR]")
    filled = filled.replace("[MT]", coating if coating else "[MT]")
    if diameter_mm is not None:
        filled = filled.replace("[DC]", str(int(round(diameter_mm))))
    if length_mm is not None:
        filled = filled.replace("[OAL]", str(int(round(length_mm))))
    if flute_count is not None:
        filled = filled.replace("[NOF]", str(int(flute_count)))
    return template, filled
