"""Kesici takım ve tutucu kodlama taksonomisi.

Bu taksonomi (14 aile harf kodu + format şablonları) genel bir
mühendislik kodlama şemasıdır; herhangi bir firmaya özgü değildir ve
ISO/DIN seviyesinde yaygın kullanılan kısaltmalara (BR, MT, DC, OAL,
LU, NOF, vb.) dayanır. Firma-özel hiçbir kod, stok numarası veya
envanter kaydı içermez.
"""

# 14 takım ailesi: (kod, İngilizce ad, Türkçe karşılık, format şablonu)
TOOL_TAXONOMY = [
    {"code": "EM", "name_en": "Solid End Mill",        "name_tr": "Düz Freze",            "template": "EM-[BR]-[MT]-[DC]-[OAL]-[LU]-[APMX]-[DCONMS]-Z[NOF]"},
    {"code": "ER", "name_en": "Corner Radius End Mill", "name_tr": "Köşe Freze",            "template": "ER-[BR]-[MT]-[DC]-[OAL]-[LU]-[APMX]-[DCONMS]-Z[NOF]-R[RE]"},
    {"code": "EB", "name_en": "Ball Nose End Mill",     "name_tr": "Küre Freze",            "template": "EB-[BR]-[MT]-[DC]-[OAL]-[LU]-[DCONMS]-Z[NOF]"},
    {"code": "ES", "name_en": "Special End Mill",       "name_tr": "Özel Freze",            "template": "ES-[TYPE]-[BR]-[MT]-[DC]-[OAL]-[LU]-[APMX]-[DCONMS]-Z[NOF]"},
    {"code": "DR", "name_en": "Drill",                  "name_tr": "Matkap",                "template": "DR-[TYPE]-[BR]-[MT]-[DC]-[OAL]-[LU]-[DCONMS]-[SIG]"},
    {"code": "RM", "name_en": "Reamer",                 "name_tr": "Rayba",                 "template": "RM-[TYPE]-[BR]-[MT]-[DC]-[OAL]-[LU]-[DCONMS]"},
    {"code": "TP", "name_en": "Tap",                    "name_tr": "Kılavuz",               "template": "TP-[TYPE]-[BR]-[MT]-[THREAD]-[PITCH]-[OAL]-[LU]"},
    {"code": "PT", "name_en": "Spot Drill",             "name_tr": "Punta",                 "template": "PT-[TYPE]-[BR]-[MT]-[DC]-[OAL]-[SIG]"},
    {"code": "DW", "name_en": "Dovetail Cutter",        "name_tr": "Kırlangıç Freze",       "template": "DW-[BR]-[MT]-[DC]-[OAL]-[ANGLE]-Z[NOF]"},
    {"code": "TM", "name_en": "T-Slot Cutter",          "name_tr": "T Freze",               "template": "TM-[BR]-[MT]-[DC]-[CUTW]-[NECK]-[DCONMS]-Z[NOF]"},
    {"code": "FM", "name_en": "Face Mill",              "name_tr": "Tarama Kafası",         "template": "FM-[BR]-[BODY]-[DC]-Z[NOF]-[INSERT]"},
    {"code": "SM", "name_en": "Shoulder Mill",          "name_tr": "Köşe Freze (Takma Uçlu)","template": "SM-[BR]-[BODY]-[DC]-Z[NOF]-[INSERT]"},
    {"code": "IN", "name_en": "Insert",                 "name_tr": "Insert",                "template": "IN-[ISO]-[GRADE]-[GEO]"},
    {"code": "HL", "name_en": "Holder",                 "name_tr": "Tutucu",                "template": "HL-[TYPE]-[INTERFACE]-[SIZE]-[L]-[SYSTEM]"},
]

FAMILY_CODES = [f["code"] for f in TOOL_TAXONOMY]
FAMILY_BY_CODE = {f["code"]: f for f in TOOL_TAXONOMY}

# Format şablonlarındaki kısaltmaların açıklamaları
FIELD_GLOSSARY = {
    "BR": "Brand (Marka)", "MT": "Material / Coating (Takım Malzemesi veya Kaplama)",
    "TYPE": "Takım Tipi", "DC": "Cutting Diameter (Kesici Çapı)",
    "OAL": "Overall Length (Toplam Boy)", "LU": "Usable Length (Kesme Boyu)",
    "APMX": "Maximum Axial Depth of Cut (Maks. Eksenel Kesme Derinliği)",
    "DCONMS": "Shank Diameter (Şaft Çapı)", "NOF": "Number of Flutes (Ağız Sayısı)",
    "RE": "Corner Radius (Köşe Radyüsü)", "SIG": "Point Angle (Uç Açısı)",
    "THREAD": "Diş Ölçüsü", "PITCH": "Hatve", "ANGLE": "Kesme Açısı",
    "CUTW": "Kesme Genişliği", "NECK": "Boyun Çapı", "BODY": "Gövde Tipi / Seri Kodu",
    "INSERT": "Kullanılan Plaka Kodu", "ISO": "ISO Plaka Kodu",
    "GRADE": "Kalite / Kaplama Sınıfı", "GEO": "Talaş Kırıcı Geometrisi",
    "INTERFACE": "Makine Bağlantı Standardı", "SIZE": "Bağlama Ölçüsü",
    "L": "Boy / Uzunluk", "SYSTEM": "Sıkıştırma Sistemi",
}

# --- Tutucu (HL) ailesine özgü alt kategoriler ---
# Bağlantı standardı (INTERFACE) ve bağıl kullanım sıklığı (nitel sıralama;
# gerçek bir sayım değildir, yalnızca sentetik veri üretiminde gerçekçi bir
# ağırlıklandırma sağlamak için kullanılır).
HOLDER_INTERFACES = [
    {"name": "HSK63",  "relative_freq": 10},
    {"name": "BT40",   "relative_freq": 9},
    {"name": "BBT40",  "relative_freq": 6},
    {"name": "HSK100", "relative_freq": 4},
    {"name": "BBT50",  "relative_freq": 3},
    {"name": "SK40",   "relative_freq": 2},
    {"name": "BBT30",  "relative_freq": 2},
    {"name": "CAPTO",  "relative_freq": 2},
]

HOLDER_TYPES = ["Shrink", "Pens&Bilyalı", "Kollet"]
HOLDER_LENGTHS = ["Uzun", "Kısa", "İnce"]
HOLDER_SYSTEMS = ["WELDON", "ER", "DIN6499", "MORSE"]

# Makine ve bağlantı standardı uyumluluğu (örnek, sentetik tezgah parkı)
MACHINES = [
    {"name": "WS01", "interface": "HSK63"},
    {"name": "WS02", "interface": "BT40"},
    {"name": "WS03", "interface": "SK40"},
    {"name": "WS04", "interface": "BBT40"},
    {"name": "WS05", "interface": "HSK100"},
    {"name": "WS06", "interface": "BT40"},
    {"name": "WS07", "interface": "HSK63"},
    {"name": "WS08", "interface": "BBT50"},
    {"name": "WS09", "interface": "BBT30"},
    {"name": "WS10", "interface": "CAPTO"},
]
