#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firebase_ihlal_export.py — Realtime DB → ihlaller.json
Acele kamulaştırma kayıtlarını çeker, alan adlarından bağımsız çalışır.
"""

import json
import re
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_URL     = "https://acele-kumulastirma-default-rtdb.europe-west1.firebasedatabase.app"
KOLEKSIYON = "kamulastirma"
CIKTI      = Path("ihlaller.json")
BUGUN      = datetime.now(timezone.utc)

BASLIK_ALANLARI = [
    "baslik", "title", "ad", "name", "konu", "karar_no",
    "karar_adi", "aciklama", "ozet", "desc", "description",
    "il", "konum", "yer", "proje_adi", "proje", "alan",
]

KONUM_ALANLARI = [
    "konum", "il", "ilce", "yer", "lokasyon", "location",
    "sehir", "city", "adres", "address",
]

TARIH_ALANLARI = [
    "tarih", "date", "eklenme", "created_at", "createdAt",
    "yayim_tarihi", "karar_tarihi", "resmi_gazete_tarihi",
    "timestamp", "updatedAt", "updated_at",
]

KATEGORI_ALANLARI = [
    "kategori", "category", "tip", "type", "tur", "konu",
    "sinif", "class", "etiket", "tag",
]

ACIKLAMA_ALANLARI = [
    "aciklama", "ozet", "desc", "description", "detay",
    "bilgi", "info", "metin", "icerik", "content",
]


def ilk_dolu(kayit: dict, alanlar: list) -> str:
    for a in alanlar:
        v = kayit.get(a)
        if v and str(v).strip().lower() not in ("undefined", "null", "none", ""):
            return str(v).strip()
    return ""


def tarih_parse(v) -> datetime | None:
    if not v:
        return None
    s = str(v).strip()
    if s.lower() in ("undefined", "null", "none", ""):
        return None
    if re.fullmatch(r"\d{10,13}", s):
        ts = int(s)
        if ts > 1e12:
            ts /= 1000
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"]:
        try:
            dt = datetime.strptime(s[:26], fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except Exception:
            continue
    return None


def resmi_gazete_url(raw: dict) -> str:
    """
    Karar sayısından Resmî Gazete arama URL'si üretir.
    Önce Firebase'deki url/kaynak_url alanına bakar;
    yoksa karar_sayisi'nden otomatik oluşturur.
    """
    # Önce doğrudan kayıtlı URL var mı?
    url = ilk_dolu(raw, ["url", "link", "kaynak_url", "resmi_gazete_url"])
    if url:
        return url

    # karar_sayisi'nden otomatik üret
    ks = raw.get("karar_sayisi")
    if not ks or str(ks).strip().lower() in ("", "belirtilmemiş", "undefined", "null", "none"):
        return ""
    ks = str(ks).strip()
    if re.fullmatch(r"\d+", ks):
        return f"https://www.resmigazete.gov.tr/eskiler/arama?q={ks}"
    return ""


def normalize(fb_key: str, raw: dict) -> dict | None:
    baslik = ilk_dolu(raw, BASLIK_ALANLARI)

    if not baslik:
        il   = ilk_dolu(raw, ["il", "sehir", "city"])
        ilce = ilk_dolu(raw, ["ilce", "district"])
        kno  = ilk_dolu(raw, ["karar_no", "resmi_gazete_no", "no", "id"])
        if il or kno:
            baslik = " / ".join(filter(None, [il, ilce, kno])) or fb_key
        else:
            return None

    tarih_ham = ilk_dolu(raw, TARIH_ALANLARI)
    dt = tarih_parse(tarih_ham)
    if dt and dt > BUGUN:
        tarih_str = ""
    elif dt:
        tarih_str = dt.strftime("%Y-%m-%d")
    else:
        tarih_str = ""

    konum    = ilk_dolu(raw, KONUM_ALANLARI)
    kategori = ilk_dolu(raw, KATEGORI_ALANLARI) or "Acele Kamulaştırma"
    aciklama = ilk_dolu(raw, ACIKLAMA_ALANLARI)
    kaynak   = ilk_dolu(raw, ["kaynak", "source", "resmi_gazete", "gazete"]) or "Resmî Gazete"

    # URL: önce doğrudan kayıtlı, yoksa karar_sayisi'nden otomatik
    url = resmi_gazete_url(raw)

    siddet_ham = ilk_dolu(raw, ["siddet", "severity", "oncelik", "priority"]).lower()
    if "kritik" in siddet_ham or "critical" in siddet_ham or "yüksek" in siddet_ham:
        siddet = "kritik"
    elif "orta" in siddet_ham or "medium" in siddet_ham:
        siddet = "orta"
    else:
        siddet = "takipte"

    etiketler = raw.get("etiketler") or raw.get("tags") or raw.get("labels") or []
    if isinstance(etiketler, str):
        etiketler = [etiketler]

    return {
        "id":         str(raw.get("id") or fb_key),
        "baslik":     baslik,
        "konum":      konum,
        "kategori":   kategori,
        "siddet":     siddet,
        "tarih":      tarih_str,
        "aciklama":   aciklama,
        "kaynak":     kaynak,
        "kaynak_url": url,
        "etiketler":  list(etiketler),
        "_raw": {k: v for k, v in raw.items()
                 if k not in ("baslik","konum","kategori","siddet","tarih",
                              "aciklama","kaynak","kaynak_url","etiketler","id")
                 and v is not None
                 and str(v).lower() not in ("undefined","null","none","")},
    }


def main():
    print("Firebase Realtime DB okunuyor…")
    r = requests.get(f"{DB_URL}/{KOLEKSIYON}.json", timeout=30)
    r.raise_for_status()
    veri = r.json()

    if not veri:
        print("⚠ Veri boş geldi.")
        return

    if isinstance(veri, dict):
        ham = [(k, v) for k, v in veri.items() if isinstance(v, dict)]
    elif isinstance(veri, list):
        ham = [(str(i), v) for i, v in enumerate(veri) if isinstance(v, dict)]
    else:
        print("⚠ Beklenmeyen format.")
        return

    print(f"  → {len(ham)} ham kayıt")
    if ham:
        print(f"  → Örnek kayıt alanları: {list(ham[0][1].keys())}")

    kayitlar = []
    atlanan  = 0
    for fb_key, raw in ham:
        kayit = normalize(fb_key, raw)
        if kayit:
            kayitlar.append(kayit)
        else:
            atlanan += 1

    print(f"  → {len(kayitlar)} geçerli / {atlanan} atlandı")

    # URL istatistiği
    url_dolu = sum(1 for k in kayitlar if k.get("kaynak_url"))
    print(f"  → {url_dolu}/{len(kayitlar)} kayıtta kaynak_url mevcut")

    kayitlar.sort(key=lambda x: x.get("tarih") or "0000", reverse=True)

    cikti = {
        "meta": {
            "guncelleme": BUGUN.isoformat(),
            "toplam":     len(kayitlar),
            "atlanan":    atlanan,
            "kaynak":     "Firebase Realtime DB",
        },
        "ihlaller": kayitlar,
    }

    tmp = CIKTI.with_suffix(".tmp")
    tmp.write_text(json.dumps(cikti, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(CIKTI)
    print(f"✓ ihlaller.json: {len(kayitlar)} kayıt yazıldı")


if __name__ == "__main__":
    main()
