#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firebase_ihlal_export.py
Realtime Database'deki kamulastirma kayıtlarını çekip ihlaller.json'a yazar.
- undefined değerler temizlenir
- Mevcut ihlaller.json sıfırdan yazılır (dagitici.py çıktısı korunmaz)
"""

import json
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_URL     = "https://acele-kumulastirma-default-rtdb.europe-west1.firebasedatabase.app"
KOLEKSIYON = "kamulastirma"
CIKTI      = Path("ihlaller.json")


def temizle(v):
    """Bir değeri temizler: 'undefined', None, boş string → None döner."""
    if v is None:
        return None
    if isinstance(v, str) and v.strip().lower() in ("undefined", "null", "none", ""):
        return None
    return v


def kayit_temizle(kayit: dict) -> dict | None:
    """
    Kaydın tüm değerlerini temizler.
    Başlık yoksa (undefined/boş) kaydı tamamen atlar → None döner.
    """
    temiz = {}
    for k, v in kayit.items():
        if isinstance(v, dict):
            ic = {ik: temizle(iv) for ik, iv in v.items()}
            temiz[k] = {ik: iv for ik, iv in ic.items() if iv is not None}
        elif isinstance(v, list):
            temiz[k] = [i for i in v if temizle(i) is not None]
        else:
            t = temizle(v)
            if t is not None:
                temiz[k] = t

    # Başlık zorunlu — yoksa kaydı atla
    baslik = temiz.get("baslik") or temiz.get("title") or temiz.get("ad")
    if not baslik:
        return None

    return temiz


def main():
    print("Firebase Realtime DB okunuyor…")
    url = f"{DB_URL}/{KOLEKSIYON}.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    veri = r.json()

    if not veri:
        print("⚠ Veri boş geldi.")
        return

    # Realtime DB dict döner: { "firebaseKey": {...}, ... }
    if isinstance(veri, dict):
        ham = [{"id": k, **v} for k, v in veri.items() if isinstance(v, dict)]
    elif isinstance(veri, list):
        ham = [{"id": str(i), **v} for i, v in enumerate(veri) if isinstance(v, dict)]
    else:
        print("⚠ Beklenmeyen veri formatı.")
        return

    print(f"  → {len(ham)} ham kayıt alındı")

    # undefined / boş kayıtları temizle
    kayitlar = []
    atlanan = 0
    for h in ham:
        temiz = kayit_temizle(h)
        if temiz:
            kayitlar.append(temiz)
        else:
            atlanan += 1

    print(f"  → {atlanan} kayıt atlandı (undefined/boş başlık)")
    print(f"  → {len(kayitlar)} geçerli kayıt")

    # Tarihe göre sırala
    kayitlar.sort(
        key=lambda x: x.get("tarih") or x.get("date") or x.get("eklenme") or "",
        reverse=True
    )

    # Mevcut ihlaller.json'u SİFIRDAN yaz (eski veri korunmaz)
    cikti = {
        "meta": {
            "guncelleme": datetime.now(timezone.utc).isoformat(),
            "toplam": len(kayitlar),
            "atlanan": atlanan,
        },
        "ihlaller": kayitlar,
    }

    tmp = CIKTI.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(cikti, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )
    tmp.replace(CIKTI)
    print(f"✓ ihlaller.json yazıldı: {len(kayitlar)} kayıt ({atlanan} atlandı)")


if __name__ == "__main__":
    main()
