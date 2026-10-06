"""Modül 3: Tutucu giriş-çıkış (Çıkış Yap / Giriş Yap) kayıtları.

Kendi çalışmalarımdan esinlenerek yaptığım önceki programdaki
"Giriş/Çıkış" ekranının işlem modeline dayanır: bir tutucu "ÇIKIŞ YAP (ÜRETİME)" ile bir makineye
atanır, sonra "GİRİŞ YAP (RAFA)" ile iade edilir; her işlemde makine
ve operatör bilgisi kaydedilir.

Üç tür anomali kasıtlı olarak eklenir:
  - gec_iade: normalin çok üzerinde süre rafta/üretimde kalma
  - mesai_disi: mesai saatleri dışında/hafta sonu işlem
  - uyumsuz_makine: tutucunun bağlantı standardı, atandığı makineyle
    uyumsuz (ör. BT40 tutucu, HSK63 tezgaha atanmış) — bu, mevcut
    uygulamanın "Makineler" ekranındaki uyumluluk bilgisini kullanarak
    tespit edilebilecek, ama o ekranda otomatik kontrol edilmeyen bir
    hata türüdür.

Not: Gerçek bir firmanın giriş-çıkış verisi kullanılmamıştır.
"""
import numpy as np
import pandas as pd

from .taxonomy import HOLDER_INTERFACES, MACHINES

N_HOLDERS_PER_INTERFACE = 5
WORK_START, WORK_END = 8, 17


def generate_checkout_log(n_days=45, seed=0, anomaly_rate=0.05):
    rng = np.random.default_rng(seed)
    machine_by_interface = {}
    for m in MACHINES:
        machine_by_interface.setdefault(m["interface"], []).append(m["name"])
    all_machines = [m["name"] for m in MACHINES]
    machine_interface = {m["name"]: m["interface"] for m in MACHINES}

    holder_ids, holder_interface = [], {}
    for h in HOLDER_INTERFACES:
        for j in range(1, N_HOLDERS_PER_INTERFACE + 1):
            hid = f"HLD-{h['name']}-{j:02d}"
            holder_ids.append(hid)
            holder_interface[hid] = h["name"]

    typical_minutes = 120  # üretimde tipik kalış süresi (dk)
    operators = [f"Operatör_{i}" for i in range(1, 9)]

    rows = []
    start_date = pd.Timestamp("2026-08-01")
    for day in range(n_days):
        date = start_date + pd.Timedelta(days=day)
        is_weekend = date.dayofweek >= 5
        n_events = rng.poisson(2 if is_weekend else 14)
        for _ in range(n_events):
            holder = holder_ids[rng.integers(0, len(holder_ids))]
            interface = holder_interface[holder]
            operator = operators[rng.integers(0, len(operators))]

            is_anomaly, anomaly_type = False, "normal"
            roll = rng.random()

            # uyumsuz_makine: standardı göz ardı edip rastgele bir makineye ata
            if roll < anomaly_rate / 3:
                machine = all_machines[rng.integers(0, len(all_machines))]
                if machine_interface[machine] != interface:
                    is_anomaly, anomaly_type = True, "uyumsuz_makine"
            else:
                candidates = machine_by_interface.get(interface, all_machines)
                machine = candidates[rng.integers(0, len(candidates))]

            if is_weekend or (not is_anomaly and roll < 2 * anomaly_rate / 3):
                hour = rng.choice([6, 7, 18, 19, 20, 21])
                is_anomaly, anomaly_type = True, "mesai_disi"
            else:
                hour = rng.integers(WORK_START, WORK_END)
            minute = rng.integers(0, 60)
            checkout_time = date + pd.Timedelta(hours=int(hour), minutes=int(minute))

            if not is_anomaly and roll < anomaly_rate:
                duration = typical_minutes * rng.uniform(4, 8)
                is_anomaly, anomaly_type = True, "gec_iade"
            else:
                duration = max(5.0, rng.normal(typical_minutes, typical_minutes * 0.3))

            return_time = checkout_time + pd.Timedelta(minutes=float(duration))
            rows.append({
                "holder_id": holder, "interface": interface, "machine": machine,
                "operator": operator, "checkout_time": checkout_time,
                "return_time": return_time, "duration_min": round(duration, 1),
                "machine_compatible": int(machine_interface[machine] == interface),
                "is_anomaly": int(is_anomaly), "anomaly_type": anomaly_type,
            })

    df = pd.DataFrame(rows).sort_values("checkout_time").reset_index(drop=True)
    df["hour"] = df["checkout_time"].dt.hour
    df["is_weekend"] = (df["checkout_time"].dt.dayofweek >= 5).astype(int)
    return df
