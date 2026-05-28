#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firebase_ihlal_export.py
Firebase Firestore'daki ihlal kayıtlarını çekip ihlaller.json'a yazar.
Mevcut dagitici.py çıktısıyla birleştirir (haberlerden gelen ihlaller korunur).

Kullanım:
    python scripts/firebase_ihlal_export.py

Ortam değişkenleri (GitHub Actions secret olarak tanımla):
    FIREBASE_PROJECT_ID   : Firebase proje ID (örn. "acele-kamulastirma-xxxxx")
    FIREBASE_COLLECTION   : Firestore koleksiyon adı (örn. "ihlaller" veya "kayitlar")
    GOOGLE_APPLICATION_CREDENTIALS : service account JSON dosyasının yolu
      VEYA
    FIREBASE_SERVICE_ACCOUNT_JSON  : service account JSON içeriği (string olarak)
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ── Bağımlılık kontrolü ───────────────────────────────────────────
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("HATA: firebase-admin kurulu değil.")
    print("      pip install firebase-admin")
    sys.exit(1)

# ── AYARLAR ──────────────────────────────────────────────────────
PROJECT_ID  = os.environ.get("FIREBASE_PROJECT_ID",  "BURAYA_PROJE_ID")
COLLECTION  = os.environ.get("FIREBASE_COLLECTION",  "BURAYA_KOLEKSIYON_ADI")
CIKTI_DOSYA = Path("ihlaller.json")
MAX_KAYIT   = 2000   # Firestore'dan çekilecek maksimum kayıt

# ── Firebase bağlantısı ───────────────────────────────────────────
def firebase_baglanti():
    """Service account JSON'dan ya da ortam değişkeninden bağlanır."""
    sa_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    if sa_json_str:
        # GitHub Actions secret'tan gelen JSON string
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as f:
            f.write(sa_json_str)
            tmp_path = f.name
        cred = credentials.Certificate(tmp_path)
        os.unlink(tmp_path)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        # Dosya yolu verilmişse
        cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    else:
        # Lokal geliştirme: scripts/ yanında serviceAccountKey.json ara
        local_key = Path(__file__).parent / "serviceAccountKey.json"
        if not local_key.exists():
            print("HATA: Service account bulunamadı.")
            print("  → FIREBASE_SERVICE_ACCOUNT_JSON ortam değişkeni,")
            print("  → GOOGLE_APPLICATION_CREDENTIALS ortam değişkeni,")
            print("  → veya scripts/serviceAccountKey.json dosyası gerekli.")
            sys.exit(1)
        cred = credentials.Certificate(str(local_key))

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"projectId": PROJECT_ID})
    return firestore.client()

# ── Veri normalleştirme ────────────────────────────────────────────
def normalize(doc_id, data: dict) -> dict:
    """Firestore belgesini ihlaller.json formatına dönüştürür."""
    # Tarih alanlarını ISO string'e çevir
    def _tarih(v):
        if v is None:
            return None
        if hasattr(v, "isoformat"):          # datetime
            return v.isoformat()
        if hasattr(v, "_seconds"):           # Firestore Timestamp
            return datetime.fromtimestamp(v.seconds, tz=timezone.utc).isoformat()
        return str(v)

    tarih = _tarih(data.get("tarih") or data.get("date") or data.get("eklenme"))

    return {
        "id":          str(data.get("id") or doc_id),
        "baslik":      str(data.get("baslik") or data.get("title") or data.get("ad") or ""),
        "konum":       str(data.get("konum") or data.get("il") or data.get("yer") or ""),
        "kategori":    str(data.get("kategori") or data.get("tur") or data.get("tip") or ""),
        "siddet":      str(data.get("siddet") or data.get("oncelik") or "takipte").lower(),
        "tarih":       tarih or "",
        "aciklama":    str(data.get("aciklama") or data.get("ozet") or data.get("desc") or ""),
        "kaynak":      str(data.get("kaynak") or data.get("source") or ""),
        "kaynak_url":  str(data.get("kaynak_url") or data.get("url") or data.get("link") or ""),
        "etiketler":   list(data.get("etiketler") or data.get("tags") or []),
        # Orijinal alanları da koru (fazladan alan zarar vermez)
        **{k: v for k, v in data.items()
           if k not in ("id","baslik","konum","kategori","siddet","tarih",
                        "aciklama","kaynak","kaynak_url","etiketler")},
    }

# ── Mevcut ihlaller.json oku ──────────────────────────────────────
def mevcut_oku() -> list:
    if not CIKTI_DOSYA.exists():
        return []
    try:
        veri = json.loads(CIKTI_DOSYA.read_text(encoding="utf-8"))
        return veri.get("ihlaller", []) if isinstance(veri, dict) else veri
    except Exception as e:
        print(f"  ⚠ Mevcut dosya okunamadı: {e}")
        return []

# ── Ana akış ──────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Firebase İhlal Export")
    print(f"  Proje : {PROJECT_ID}")
    print(f"  Koleksiyon: {COLLECTION}")
    print("=" * 55)

    if PROJECT_ID.startswith("BURAYA") or COLLECTION.startswith("BURAYA"):
        print("\nHATA: FIREBASE_PROJECT_ID ve FIREBASE_COLLECTION ortam değişkenlerini ayarla.")
        sys.exit(1)

    # Firebase'den çek
    print("\nFirebase'e bağlanılıyor…")
    db = firebase_baglanti()

    print(f"'{COLLECTION}' koleksiyonu okunuyor…")
    try:
        docs = list(db.collection(COLLECTION).limit(MAX_KAYIT).stream())
    except Exception as e:
        print(f"HATA: Firestore okuma başarısız: {e}")
        sys.exit(1)

    fb_kayitlar = [normalize(d.id, d.to_dict()) for d in docs]
    print(f"  → {len(fb_kayitlar)} kayıt çekildi")

    # Mevcut ihlaller.json ile birleştir
    mevcut = mevcut_oku()
    mevcut_ids = {str(k["id"]) for k in mevcut}

    # Firebase kayıtları önce (daha güncel), sonra mevcut'tan olmayanlar
    fb_ids = {str(k["id"]) for k in fb_kayitlar}
    sadece_mevcut = [k for k in mevcut if str(k["id"]) not in fb_ids]

    birlesik = fb_kayitlar + sadece_mevcut
    birlesik.sort(key=lambda x: x.get("tarih") or "", reverse=True)
    birlesik = birlesik[:MAX_KAYIT]

    # Yaz
    cikti = {
        "meta": {
            "guncelleme": datetime.now(timezone.utc).isoformat(),
            "toplam":     len(birlesik),
            "firebase":   len(fb_kayitlar),
            "yeni_eklenen": len(fb_kayitlar),
        },
        "ihlaller": birlesik,
    }

    # Atomik yaz (tmp → rename)
    tmp = CIKTI_DOSYA.with_suffix(".tmp")
    json_str = json.dumps(cikti, ensure_ascii=False, indent=2, default=str)
    tmp.write_text(json_str, encoding="utf-8")
    tmp.replace(CIKTI_DOSYA)

    print(f"\n✓ ihlaller.json yazıldı: {len(birlesik)} toplam kayıt")
    print(f"  ({len(fb_kayitlar)} Firebase + {len(sadece_mevcut)} mevcut)")


if __name__ == "__main__":
    main()
