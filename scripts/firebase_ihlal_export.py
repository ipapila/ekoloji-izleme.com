#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firebase_ihlal_export.py
Realtime Database'deki kamulastirma kayıtlarını çekip ihlaller.json'a yazar.
Service account gerekmez — okuma public.
"""

import json
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_URL     = "https://acele-kumulastirma-default-rtdb.europe-west1.firebasedatabase.app"
KOLEKSIYON = "kamulastirma"
CIKTI      = Path("ihlaller.json")

def main():
    print("Firebase Realtime DB okunuyor…")
    url = f"{DB_URL}/{KOLEKSIYON}.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    veri = r.json()

    if not veri:
        print("⚠ Veri boş geldi.")
        return

    # Realtime DB dict döner: { "id1": {...}, "id2": {...} }
    if isinstance(veri, dict):
        kayitlar = [{"id": k, **v} for k, v in veri.items() if isinstance(v, dict)]
    elif isinstance(veri, list):
        kayitlar = [{"id": str(i), **v} for i, v in enumerate(veri) if isinstance(v, dict)]
    else:
        print("⚠ Beklenmeyen veri formatı.")
        return

    print(f"  → {len(kayitlar)} kayıt çekildi")

    # Mevcut ihlaller.json ile birleştir
    mevcut = []
    if CIKTI.exists():
        try:
            d = json.loads(CIKTI.read_text(encoding="utf-8"))
            mevcut = d.get("ihlaller", []) if isinstance(d, dict) else d
        except Exception:
            pass

    # Firebase kayıtları önce (güncel), mevcut'tan sadece Firebase'de olmayanlar
    fb_ids = {str(k["id"]) for k in kayitlar}
    ekstra = [k for k in mevcut if str(k.get("id","")) not in fb_ids]
    birlesik = kayitlar + ekstra
    birlesik.sort(key=lambda x: x.get("tarih") or x.get("date") or "", reverse=True)

    cikti = {
        "meta": {
            "guncelleme": datetime.now(timezone.utc).isoformat(),
            "toplam": len(birlesik),
        },
        "ihlaller": birlesik,
    }

    tmp = CIKTI.with_suffix(".tmp")
    tmp.write_text(json.dumps(cikti, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(CIKTI)
    print(f"✓ ihlaller.json yazıldı: {len(birlesik)} kayıt")

if __name__ == "__main__":
    main()
