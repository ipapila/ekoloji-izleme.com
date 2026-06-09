#!/usr/bin/env python3
"""
Tek seferlik migrasyon: haberler.json içinde LGBTİ+ kaynaklarından gelmiş
ama bolum etiketi atanmadan donmuş kayıtlara bolum="lgbti" işler.

Neden gerekli: bu kaynaklara "bolum":"lgbti" eklenmeden ÖNCE taranan kayıtlar
haberler.json'da bolum=None olarak duruyor. tarayici.py'nin dedup'ı (filtrele_yeni)
bu ID'leri "görülmüş" saydığı için kaynak artık bolum taşısa da eski sürüm
yenilenmiyor. Bu script onları yerinde etiketler; ekosistem.html bunları
digerKaynaklardan() ile "LGBTİ+ & Çevre" sekmesine alır.

Kalıcıdır: tarayici bir sonraki taramada eski kayıtları haberler.json'dan
olduğu gibi (bolum dahil) yeniden yükler.

Kullanım (Plesk SSH, httpdocs içinde):
    /opt/plesk/python/3/bin/python3 migrasyon_lgbti_bolum.py            # önizleme
    /opt/plesk/python/3/bin/python3 migrasyon_lgbti_bolum.py --uygula   # yaz
"""
import json, sys, tempfile, os
from pathlib import Path

DOSYA = Path("haberler.json")

# Kaynak adına göre kesin eşleşme (tarayici.py'deki kaynak tanımlarıyla birebir)
LGBTI_KAYNAKLAR = {
    "Kaos GL",
    "17 Mayıs Derneği",
    "İklim Adaleti Koalisyonu",
    "Coalition Rainbow",
}

def main():
    uygula = "--uygula" in sys.argv
    if not DOSYA.exists():
        print("HATA: haberler.json bulunamadı (httpdocs içinde çalıştırın).")
        sys.exit(1)

    veri = json.loads(DOSYA.read_text(encoding="utf-8"))
    haberler = veri.get("haberler", [])

    etiketlenecek = []
    for h in haberler:
        kaynak = (h.get("kaynak") or "").strip()
        if kaynak in LGBTI_KAYNAKLAR and h.get("bolum") != "lgbti":
            etiketlenecek.append(h)

    print(f"Toplam haber: {len(haberler)}")
    print(f"bolum='lgbti' atanacak kayıt: {len(etiketlenecek)}")
    for h in etiketlenecek:
        print(f"   - [{h.get('kaynak')}] {(h.get('baslik') or '')[:60]}  (mevcut bolum={h.get('bolum')})")

    if not etiketlenecek:
        print("Etiketlenecek kayıt yok; değişiklik gerekmiyor.")
        return

    if not uygula:
        print("\n[ÖNİZLEME] Yazmak için: --uygula ekleyin.")
        return

    for h in etiketlenecek:
        h["bolum"] = "lgbti"

    # Atomik yazım
    fd, tmp = tempfile.mkstemp(dir=str(DOSYA.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DOSYA)
    print(f"\n✓ {len(etiketlenecek)} kayıt güncellendi → haberler.json yazıldı.")
    print("  ekosistem.html 'LGBTİ+ & Çevre' sekmesinde görünmeli (Cloudflare/cache temizliği gerekebilir).")

if __name__ == "__main__":
    main()
