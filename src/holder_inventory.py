"""Demo paneli için 'şu anki' tutucu envanteri anlık görüntüsü.

Modül 1'in (maintenance_risk) aynı sentetik üretim mantığını kullanır,
üstüne makine ataması ve operasyonel durum (Kullanılabilir / Kullanımda
/ Bakımda) ekler.
"""
import numpy as np
import pandas as pd

from .maintenance_risk import generate_dataset
from .taxonomy import MACHINES, HOLDER_INTERFACES


def generate_snapshot(n=48, seed=1):
    df = generate_dataset(n_samples=n, seed=seed).reset_index(drop=True)

    machines_by_interface = {}
    for m in MACHINES:
        machines_by_interface.setdefault(m["interface"], []).append(m["name"])

    rng = np.random.default_rng(seed + 1)
    holder_ids, machines, statuses = [], [], []
    for i, row in df.iterrows():
        holder_ids.append(f"HLD-{row['interface']}-{i+1:03d}")
        candidates = machines_by_interface.get(row["interface"], [])
        if row["risk_class"] == "HIGH":
            statuses.append("Bakımda" if rng.random() < 0.75 else "Kullanılabilir")
            machines.append("-")
        elif candidates and rng.random() < 0.35:
            statuses.append("Kullanımda")
            machines.append(rng.choice(candidates))
        else:
            statuses.append("Kullanılabilir")
            machines.append("-")

    df["holder_id"] = holder_ids
    df["machine"] = machines
    df["status"] = statuses

    interface_rank = {h["name"]: h["relative_freq"] for h in HOLDER_INTERFACES}
    order = sorted(interface_rank, key=lambda k: -interface_rank[k])
    cum = np.cumsum([interface_rank[k] for k in order]) / sum(interface_rank.values())
    abc_class = {}
    for name, c in zip(order, cum):
        abc_class[name] = "A" if c <= 0.70 else ("B" if c <= 0.90 else "C")
    zone_map = {"A": "Zone 1", "B": "Zone 2", "C": "Zone 3"}
    df["abc_class"] = df["interface"].map(abc_class)
    df["zone"] = df["abc_class"].map(zone_map)
    return df
