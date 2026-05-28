#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firebase_ihlal_export.py
Realtime Database'deki kamulastirma kayıtlarını çekip ihlaller.json'a yazar.
- undefined değerler temizlenir
- Gelecek tarihli kayıtlar düzeltilir (tarih alanı temizlenir)
- Mevcut ihlaller.json sıfırdan yazılır
"""

import json
import re
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_URL     = "https://acele-kumulastirma-default-rtdb.europe-west1.firebasedatabase.app"
KOLEKSIYON = "kamulastirma"
CIKTI      = Path("ihlaller.json")

BUGUN = datetime.now(timezone.utc)


# ── Tarih ayrıştırma ──────────────────────────────────────────────
def tarih_parse(v) -> datetime | None:
    """Çeşitli formatlardaki tarihi datetime'a çevirir."""
    if not v:
        return None
    s = str(v).strip()
    if s.lower() in ("undefined", "null", "none", ""):
        return None

    # Unix timestamp (milisaniye veya saniye)
    if re.fullmatch(r"\d{10,13}", s):
        ts = int(s)
        if ts > 1e12:
            ts = ts / 1000
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None

    # ISO / çeşitli string formatlar
    formatlar = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    for fmt in formatlar:
        try:
            dt = datetime.strptime(s[:len(fmt)+5], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def tarih_temizle(kayit: dict) -> dict:
    """
    Kayıttaki tarih alanını kontrol eder.
    Gelecek tarihli → tarih alanını siler (bugün belli değil demek).
    Geçerli tarih → ISO string'e normalize eder.
    """
    tarih_alanlari = ["tarih", "date", "eklenme", "created_at", "createdAt"]
    for alan in tarih_alanlari:
        if alan not in kayit:
            continue
        dt = tarih_parse(kayit[alan])
        if dt is None:
            del kayit[alan]
        elif dt > BUGUN:
            # Gelecek tarih — alanı kaldır
            print(f"  ⚠ Gelecek tarih temizlendi: {kayit[alan]} ({kayit.get('baslik','?')[:40]})")
            del kayit[alan]
        else:
            # Geçerli tarih — normalize et
            kayit[alan] = dt.strftime("%Y-%m-%d")
        break  # ilk bulunan tarih alanı yeter
    return kayit


# ── undefined temizleme ───────────────────────────────────────────
def temizle(v):
    if v is None:
        return None
    if isinstance(v, str) and v.strip().lower() in ("undefined", "null", "none", ""):
        return None
    return v


def kayit_temizle(kayit: dict) -> dict | None:
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

    # Başlık zorunlu
    baslik = temiz.get("baslik") or temiz.get("title") or temiz.get("ad")
    if not baslik:
        return None

    # Tarih doğrula / temizle
    temiz = tarih_temizle(temiz)
    return temiz


# ── Ana akış ─────────────────────────────────────────────────────
def main():
    print("Firebase Realtime DB okunuyor…")
    r = requests.get(f"{DB_URL}/{KOLEKSIYON}.json", timeout=30)
    r.raise_for_status()
    veri = r.json()

    if not veri:
        print("⚠ Veri boş geldi.")
        return

    if isinstance(veri, dict):
        ham = [{"id": k, **v} for k, v in veri.items() if isinstance(v, dict)]
    elif isinstance(veri, list):
        ham = [{"id": str(i), **v} for i, v in enumerate(veri) if isinstance(v, dict)]
    else:
        print("⚠ Beklenmeyen veri formatı.")
        return

    print(f"  → {len(ham)} ham kayıt alındı")

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

    # Tarihe göre sırala (tarih yoksa en sona)
    kayitlar.sort(
        key=lambda x: x.get("tarih") or x.get("date") or x.get("eklenme") or "0000",
        reverse=True
    )

    cikti = {
        "meta": {
            "guncelleme": BUGUN.isoformat(),
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
