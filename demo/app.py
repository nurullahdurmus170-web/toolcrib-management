"""
ToolCrib Management — Demo Paneli
================================
Kendi çalışmalarımdan esinlenerek yaptığım bir envanter programının
sayfa yapısı (Dashboard, Tutucular, Giriş/Çıkış, Makineler, A/B/C
Analizi, Raf Yerleşimi, KPI'lar) temel alınarak, kendi tasarımımla ve
üstüne dört yapay zekâ modülüyle yeniden kurulmuş bir panel.

Çalıştırmak için:
    pip install -r ../requirements.txt
    cd demo
    streamlit run app.py

Not: Tüm veriler sentetiktir; gerçek bir firmanın envanter/kullanım
verisi kullanılmamıştır. Modeller her başlangıçta yeniden eğitilir.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from src.taxonomy import (HOLDER_INTERFACES, HOLDER_TYPES, HOLDER_LENGTHS,
                           HOLDER_SYSTEMS, MACHINES, FAMILY_BY_CODE)
from src.maintenance_risk import generate_dataset as gen_maint, fixed_threshold_rule, FIXED_THRESHOLD
from src.holder_inventory import generate_snapshot
from src.abc_shelf import generate_daily_usage
from src.checkout_log import generate_checkout_log
from src.auto_coding import generate_tool_records, suggest_code_template, CLASSIFIABLE_FAMILIES

st.set_page_config(page_title="ToolCrib Management — Demo", layout="wide")

RISK_STYLE = {
    "LOW":    {"color": "#2e7d32", "label": "DÜŞÜK RİSK"},
    "MEDIUM": {"color": "#f9a825", "label": "ORTA RİSK"},
    "HIGH":   {"color": "#c62828", "label": "YÜKSEK RİSK — BAKIM ÖNERİLİR"},
}
STATUS_COLOR = {"Kullanılabilir": "🟢", "Kullanımda": "🔵", "Bakımda": "🟠"}


@st.cache_resource
def train_maintenance_model():
    df = gen_maint(n_samples=2500, seed=0)
    numeric = ["usage_count", "age_days"]
    categorical = ["interface", "type", "length_category", "system"]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), categorical)],
                             remainder="passthrough")
    clf = Pipeline([("pre", pre), ("model", RandomForestClassifier(
        n_estimators=300, random_state=0, class_weight="balanced"))])
    clf.fit(df[categorical + numeric], df["risk_class"])
    return clf, numeric, categorical


@st.cache_resource
def train_auto_coding_model():
    df = generate_tool_records(n_per_family=150, seed=0)
    numeric = ["diameter_mm", "length_mm", "flute_count", "aspect_ratio"]
    categorical = ["material", "coating"]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), categorical)],
                             remainder="passthrough")
    clf = Pipeline([("pre", pre), ("model", RandomForestClassifier(n_estimators=300, random_state=0))])
    clf.fit(df[numeric + categorical], df["family_code"])
    return clf, numeric, categorical


@st.cache_data
def load_inventory():
    return generate_snapshot(n=48, seed=1)


@st.cache_data
def load_abc_usage():
    return generate_daily_usage(n_days=180, seed=0)


@st.cache_data
def load_checkout_data():
    df = generate_checkout_log(n_days=45, seed=0, anomaly_rate=0.07)
    features = df[["duration_min", "hour", "is_weekend", "machine_compatible"]]
    iso = IsolationForest(n_estimators=300, contamination=df["is_anomaly"].mean(), random_state=0)
    df["iso_flag"] = (iso.fit_predict(features) == -1).astype(int)
    return df


st.title("ToolCrib Management")
st.caption("Tutucu ve kesici takım yönetimi — dört yapay zekâ modülü ile desteklenmiş demo paneli (tüm veriler sentetik)")

inventory = load_inventory()
clf_maint, maint_numeric, maint_categorical = train_maintenance_model()

tabs = st.tabs(["📊 Dashboard", "🔧 Tutucular", "🔄 Giriş/Çıkış", "⚙️ Makineler",
                 "📦 A/B/C & Raf", "🏷️ Otomatik Kodlama", "🎯 KPI'lar"])

# ---------------- DASHBOARD ----------------
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Tutucu", len(inventory))
    c2.metric("Bakım Gereken (model)", int((inventory.risk_class == "HIGH").sum()))
    n_fixed_rule = int(fixed_threshold_rule(inventory).sum())
    c3.metric(f"Sabit Eşik (≥{FIXED_THRESHOLD}) İşaretlediği", n_fixed_rule,
              delta=int((inventory.risk_class == "HIGH").sum()) - n_fixed_rule,
              help="Pozitif fark: modelin, sabit eşiğin gözden kaçırdığı riskli tutucuları da yakaladığı anlamına gelir.")

    st.markdown("**Durum Dağılımı**")
    status_counts = inventory["status"].value_counts()
    cols = st.columns(len(status_counts))
    for col, (status, count) in zip(cols, status_counts.items()):
        col.metric(f"{STATUS_COLOR.get(status,'')} {status}", int(count))

    st.markdown("**En Çok Kullanılan Tutucular**")
    top = inventory.sort_values("usage_count", ascending=False).head(5)
    st.dataframe(top[["holder_id", "interface", "type", "usage_count", "risk_class", "status"]],
                 width="stretch", hide_index=True)

    st.markdown("**🚨 Yüksek Riskli Tutucular (model)**")
    urgent = inventory[inventory.risk_class == "HIGH"].sort_values("usage_count", ascending=False)
    if len(urgent):
        st.dataframe(urgent[["holder_id", "interface", "type", "usage_count", "status"]],
                     width="stretch", hide_index=True)
    else:
        st.info("Şu an yüksek riskli tutucu yok.")

# ---------------- TUTUCULAR / AKILLI ARAMA ----------------
with tabs[1]:
    st.subheader("Tutucular — Akıllı Arama")
    c1, c2, c3 = st.columns(3)
    f_interface = c1.multiselect("Standart", sorted(inventory.interface.unique()))
    f_type = c2.multiselect("Tip", sorted(inventory.type.unique()))
    f_status = c3.multiselect("Durum", sorted(inventory.status.unique()))

    view = inventory.copy()
    if f_interface:
        view = view[view.interface.isin(f_interface)]
    if f_type:
        view = view[view.type.isin(f_type)]
    if f_status:
        view = view[view.status.isin(f_status)]

    st.dataframe(
        view[["holder_id", "interface", "type", "length_category", "system",
              "usage_count", "machine", "status", "risk_class", "zone"]]
        .sort_values("usage_count", ascending=False),
        width="stretch", hide_index=True,
    )
    st.caption(f"{len(view)} / {len(inventory)} tutucu gösteriliyor. "
               "`risk_class`, öğrenilen model tahminidir; sabit bir eşik değildir.")

# ---------------- GİRİŞ/ÇIKIŞ ----------------
with tabs[2]:
    st.subheader("Giriş/Çıkış kayıtları ve anomali tespiti")
    log = load_checkout_data()
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam kayıt", len(log))
    c2.metric("IsolationForest işaretledi", int(log.iso_flag.sum()))
    c3.metric("Bilinen anomali (doğrulama)", int(log.is_anomaly.sum()))

    only_flagged = st.checkbox("Yalnızca işaretlenenleri göster", value=True)
    view = log[log.iso_flag == 1] if only_flagged else log
    st.dataframe(
        view[["holder_id", "interface", "machine", "operator", "checkout_time",
              "duration_min", "machine_compatible", "iso_flag", "anomaly_type"]]
        .sort_values("checkout_time", ascending=False).head(50),
        width="stretch", hide_index=True,
    )
    st.caption("`anomaly_type`, veri üretiminde bilinen gerçek etikettir (doğrulama amaçlı); "
               "gerçek dağıtımda önceden bilinmez.")

# ---------------- MAKİNELER ----------------
with tabs[3]:
    st.subheader("Makineler ve bağlantı standardı uyumluluğu")
    machines_df = pd.DataFrame(MACHINES)
    st.dataframe(machines_df, width="stretch", hide_index=True)

    st.markdown("**Uyumluluk kontrolü**")
    c1, c2 = st.columns(2)
    sel_holder_interface = c1.selectbox("Tutucu standardı", [h["name"] for h in HOLDER_INTERFACES])
    sel_machine = c2.selectbox("Makine", [m["name"] for m in MACHINES])
    machine_interface = next(m["interface"] for m in MACHINES if m["name"] == sel_machine)
    if machine_interface == sel_holder_interface:
        st.success(f"✅ Uyumlu: {sel_machine} ({machine_interface}) ↔ {sel_holder_interface} tutucu")
    else:
        st.error(f"❌ Uyumsuz: {sel_machine} yalnızca {machine_interface} kabul eder, "
                 f"{sel_holder_interface} tutucu takılamaz.")

# ---------------- A/B/C & RAF ----------------
with tabs[4]:
    st.subheader("A/B/C Analizi ve Raf Yerleşimi")
    usage = load_abc_usage()
    interface_pick = st.selectbox("Standart seç", [h["name"] for h in HOLDER_INTERFACES])
    sub = usage[usage.interface == interface_pick].sort_values("date")

    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(sub["date"], sub["usage_count"].rolling(7).mean())
    ax.set_title(f"{interface_pick} — günlük kullanım (7g hareketli ortalama)")
    ax.set_ylabel("Kullanım")
    st.pyplot(fig)
    plt.close(fig)

    row = inventory[inventory.interface == interface_pick].iloc[0] if (inventory.interface == interface_pick).any() else None
    if row is not None:
        c1, c2 = st.columns(2)
        c1.metric("A/B/C Sınıfı", row["abc_class"])
        c2.metric("Önerilen Raf Bölgesi", row["zone"])

# ---------------- OTOMATİK KODLAMA ----------------
with tabs[5]:
    st.subheader("Yeni takım için otomatik aile tespiti ve kod önerisi")
    st.caption("10 aile (EM/ER/EB/DR/RM/TP/PT/DW/TM + HL/Tutucu) ölçülebilir özelliklerden ayırt edilmeye çalışılır.")
    clf_auto, auto_numeric, auto_categorical = train_auto_coding_model()

    c1, c2, c3 = st.columns(3)
    diameter = c1.slider("Çap / bağlama ölçüsü (mm)", 2.0, 50.0, 10.0)
    length = c2.slider("Toplam boy (mm)", 8.0, 250.0, 60.0)
    flute = c3.selectbox("Ağız sayısı (tutucu için 0 seçin)", [0, 2, 3, 4, 6])
    c4, c5 = st.columns(2)
    material = c4.selectbox("Malzeme", ["HSS", "Karbür", "Kobalt"])
    coating = c5.selectbox("Kaplama", ["Kaplamasız", "TiN", "TiAlN", "DLC"])

    row = pd.DataFrame([{
        "diameter_mm": diameter, "length_mm": length, "flute_count": flute,
        "aspect_ratio": round(length / diameter, 3),
        "material": material, "coating": coating,
    }])
    pred_family = clf_auto.predict(row)[0]
    proba = clf_auto.predict_proba(row)[0]
    top3_idx = np.argsort(proba)[::-1][:3]

    fam_info = CLASSIFIABLE_FAMILIES
    fam_name = FAMILY_BY_CODE[pred_family]["name_tr"]
    st.success(f"Önerilen aile: **{pred_family} — {fam_name}** (güven: %{proba.max()*100:.0f})")

    _, filled = suggest_code_template(pred_family, diameter_mm=diameter, length_mm=length,
                                        flute_count=flute, material=material, coating=coating)
    st.code(filled, language=None)
    st.caption(f"Format şablonu: `{FAMILY_BY_CODE[pred_family]['template']}`")

    st.write("En olası 3 aile:")
    for i in top3_idx:
        code = clf_auto.classes_[i]
        st.write(f"- {code} ({FAMILY_BY_CODE[code]['name_tr']}): %{proba[i]*100:.0f}")
    st.caption("⚠️ Bazı aileler (ör. EM/ER/EB frezeler) çap/boy ile güvenilir biçimde "
               "ayırt edilemiyor; ayrıntı için README'deki sınırlılıklar bölümüne bakın.")

# ---------------- KPI ----------------
with tabs[6]:
    st.subheader("Performans Göstergeleri (KPI)")
    c1, c2, c3 = st.columns(3)
    high_risk_rate = (inventory.risk_class == "HIGH").mean() * 100
    c1.metric("Yüksek Riskli Tutucu Oranı", f"%{high_risk_rate:.1f}")

    log = load_checkout_data()
    anomaly_rate = log.iso_flag.mean() * 100
    c2.metric("İşaretlenen Anomali Oranı", f"%{anomaly_rate:.1f}")

    rule_recall_gap = int((inventory.risk_class == "HIGH").sum()) - int(fixed_threshold_rule(inventory).sum())
    c3.metric("Modelin Sabit Eşiğe Göre Ek Yakaladığı", max(0, rule_recall_gap))
    st.caption("Bu KPI'lar anlık envanter görüntüsünden hesaplanır; gerçek bir üretim "
               "ortamında zaman içindeki trend olarak izlenmelidir.")

st.divider()
st.caption("ToolCrib Management — portföy projesi. Tüm veriler sentetiktir.")
