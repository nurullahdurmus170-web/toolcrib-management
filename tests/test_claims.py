"""README'de yapılan temel iddiaları doğrulayan basit testler.

Bu testler modellerin 'iyi' olduğunu kanıtlamak için değil, README'nin
anlattığı hikayenin kod değiştikçe sessizce bozulmadığını garanti etmek
içindir. Çalıştırmak için:

    python -m pytest tests/ -v

veya pytest kurulu değilse:

    python -m tests.test_claims
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.maintenance_risk import generate_dataset, fixed_threshold_rule
from src.run_maintenance_risk import _run_one_seed as run_maintenance_seed
from src.run_auto_coding import _run_one_seed as run_auto_coding_seed
from src.checkout_log import generate_checkout_log
from src.run_anomaly_detection import rule_based_flag
from sklearn.ensemble import IsolationForest


def test_maintenance_model_beats_fixed_threshold_on_recall():
    """Öğrenilen model, sabit eşik kuralından belirgin biçimde daha
    yüksek recall ile gerçek bakım ihtiyaçlarını yakalamalı (README'nin
    ana iddiası)."""
    _, binary, _ = run_maintenance_seed(seed=0)
    assert binary["model_recall"] > binary["rule_recall"] + 0.2, (
        f"Model recall ({binary['model_recall']:.3f}) sabit eşiği "
        f"({binary['rule_recall']:.3f}) belirgin biçimde geçmeli"
    )


def test_fixed_threshold_misses_most_kollet_risk():
    """Sabit eşik kuralı, Kollet tipindeki gerçek risklerin büyük
    kısmını (>%80) gözden kaçırmalı — README'nin tip-bazlı sapma
    iddiası."""
    df = generate_dataset(n_samples=2500, seed=0)
    kollet = df[df.type == "Kollet"]
    true_risk = kollet["needs_maintenance_soon"] == 1
    rule_caught = fixed_threshold_rule(kollet) == 1
    missed_rate = 1 - (true_risk & rule_caught).sum() / max(1, true_risk.sum())
    assert missed_rate > 0.8, f"Kollet'teki kaçırma oranı {missed_rate:.2f}, >0.8 bekleniyor"


def test_auto_coding_beats_random_baseline():
    """Otomatik kodlama modeli, 10 sınıflı rastgele tahminden (dummy)
    belirgin biçimde iyi olmalı."""
    metrics, _, _ = run_auto_coding_seed(seed=0)
    assert metrics["rf_accuracy"] > metrics["dummy_accuracy"] * 3


def test_holder_family_is_perfectly_separable():
    """HL (Tutucu) ailesi, ağız sayısı=0 özelliği sayesinde diğer
    ailelerle karışmamalı (README'nin HL bulgusu)."""
    _, acc_by_family, _ = run_auto_coding_seed(seed=0)
    assert acc_by_family["HL"] == 1.0, "HL ailesi beklenen şekilde %100 ayrılamadı"


def test_em_er_eb_confusion_persists():
    """EM/ER/EB (düz/köşe/küre freze) arasındaki karışıklık, boy/çap
    oranı eklenmesine rağmen hâlâ belirgin olmalı (README'nin dürüst
    sınırlılık iddiası) — bu testin 'geçmesi', modelin bu ailelerde
    hâlâ zayıf olduğunu doğrular."""
    _, acc_by_family, _ = run_auto_coding_seed(seed=0)
    for code in ["EM", "ER", "EB"]:
        assert acc_by_family[code] < 0.5, (
            f"{code} doğruluğu {acc_by_family[code]:.2f}, beklenenden "
            f"(< 0.5) daha iyi çıktı; README'nin sınırlılık bölümünü güncelle"
        )


def test_anomaly_detection_catches_machine_incompatibility():
    """Kural tabanlı yöntem, makine-standart uyumsuzluğu anomalisini
    (deterministik bir kural olduğu için) tamamen yakalamalı."""
    df = generate_checkout_log(n_days=45, seed=0, anomaly_rate=0.07)
    rule_flag = rule_based_flag(df)
    incompat = df["anomaly_type"] == "uyumsuz_makine"
    assert incompat.sum() > 0, "Test verisinde uyumsuz_makine örneği yok"
    assert (rule_flag[incompat] == 1).all(), "Kural, tüm uyumsuz_makine kayıtlarını yakalamalı"


def test_no_leftover_company_references():
    """Repo genelinde CNK veya firma ismine dair bir iz kalmamalı."""
    root = Path(__file__).resolve().parent.parent
    forbidden = ["cnk", "havacılık", "havacilik"]
    hits = []
    for path in root.rglob("*.py"):
        if ".git" in path.parts or path.name == "test_claims.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in forbidden:
            if term in text:
                hits.append((path, term))
    assert not hits, f"Yasaklı terim bulundu: {hits}"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"OK   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} test geçti")
    if failed:
        sys.exit(1)
