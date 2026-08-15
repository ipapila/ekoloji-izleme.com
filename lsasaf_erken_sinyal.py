#!/usr/bin/env python3
"""
lsasaf_erken_sinyal.py
-----------------------
firms_yangin_tarama.py'nin arka planı: VIIRS ve MODIS kutupsal yörüngeli
uydular, Türkiye üzerinden günde sadece birkaç kez geçiyor (yaklaşık
10:30-13:30 yerel arası bir küme, sonra ~22:00 civarı bir geçiş daha).
Bu iki aralık dışında başlayan bir yangın, bir sonraki geçişe kadar
(saatlerce) VIIRS/MODIS'te GÖRÜNMEZ — bu bir yapılandırma sorunu değil,
yörünge fiziği.

Bu script, EUMETSAT LSA SAF'ın ürettiği Meteosat SEVIRI FRP-PIXEL ürününü
kullanır: coğrafi sabit (geostationary) bir uydu olduğu için Türkiye'yi
HER 15 DAKİKADA BİR tarar. Buna karşılık:
  - Mekansal çözünürlüğü kaba (~3-5 km piksel, VIIRS'in 375m'sine karşı)
  - Yanlış pozitif oranı VIIRS/MODIS'ten belirgin şekilde yüksek (güneş
    yansıması, sıcak çıplak toprak, endüstriyel ısı kaynakları vb.)

NOT (gerçek bir örnek ürün dosyası incelenerek doğrulandı — 2026-08-14):
  - Kullanıcının hesabı MSG-IODC (Indian Ocean Data Coverage) ürününe
    erişiyor, "standart" 0 derece MSG diskine değil. IODC'nin alt uydu
    noktası ~45.5E — yani Türkiye'ye 0 derece diskten çok daha yakın bir
    açı. Bu bir sorun değil, muhtemelen VIIRS/MODIS'e göre bile daha iyi
    bir piksel görüş açısı (view zenith angle) sağlıyor.
  - Dosya formatı NetCDF DEĞİL, çıplak HDF5. h5py kullanılıyor.
  - Tüm sayısal alanlar (LATITUDE, LONGITUDE, FRP, FIRE_CONFIDENCE, ...)
    ölçekli tam sayı: gerçek_değer = ham/SCALING_FACTOR + OFFSET. Bu
    dönüşüm atlanırsa değerler 10-100x yanlış çıkar.
  - Ürün zamanı dosya adından değil, HDF5 root attribute'u
    IMAGE_ACQUISITION_TIME'dan (YYYYMMDDHHMMSS) okunuyor.

Bu yüzden bu ürünün çıktısı asla "doğrulanmış yangın" olarak sunulmaz.
Ayrı bir "erken sinyal" katmanı olarak, firms_yangin.json'dan bağımsız
bir dosyaya (lsasaf_erken_sinyal.json) yazılır ve haritada farklı, açıkça
"ön tespit / doğrulanmadı" etiketli bir katman olarak gösterilmesi
önerilir. Amaç: VIIRS/MODIS'in kör kaldığı saatlerde "bu bölgede olası
bir ısı anomalisi var, takip edin" sinyali vermek — nihai doğrulama
haber eşleşmesi veya bir sonraki VIIRS/MODIS geçişiyle gelir.

KURULUM (yapılması gerekenler — bunlar olmadan script çalışmaz)
-----------------------------------------------------------------
1) https://lsa-saf.eumetsat.int adresinden ücretsiz bir hesap açın.
2) Hesap onaylandıktan sonra "Fire Products" bölümünden FRP-PIXEL
   ürününün NRT (near-real-time) veri servisi erişim bilgilerini alın:
   https://lsa-saf.eumetsat.int/en/data/data-access/
   Tercih edilen erişim noktası: https://datalsasaf.lsasvcs.ipma.pt/
3) DOSYA ADI VE DİZİN YOLU DOĞRULANDI (2026-08-15, açık dizin listelemesi
   üzerinden — kimlik doğrulama olmadan h5ai index sayfaları görüntülendi):
     https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG-IODC/FRP-PIXEL/HDF5/{YYYY}/{MM}/{DD}/{dosya_adi}
   yani daha önce eksik olan bir "/HDF5/" klasör katmanı var — kalıp:
     PRODUCTS/{UYDU}-{BOLGE}/FRP-PIXEL/HDF5/{YYYY}/{MM}/{DD}/
       HDF5_LSASAF_{UYDU}-{BOLGE}_FRP-PIXEL-ListProduct_{BOLGE}-Disk_{YYYYMMDDHHMM}
   (uzantısız — .nc/.h5 yok). Her iki ürün de (ListProduct VE
   QualityProduct) aynı klasörde, 15 dakikada bir üretiliyor;
   ListProduct gerçek piksel/FRP verisini içeriyor. 13 Ağustos 2026
   yangını sırasındaki (18:00-19:15 yerel saat aralığı) dosyaların hepsi
   bu dizinde mevcut olduğu doğrulandı.
4) GitHub Actions secrets'a ekleyin: LSA_USER, LSA_PASS
5) requirements: pip install h5py requests

KULLANIM
--------
python lsasaf_erken_sinyal.py
"""

import os
import sys
import json
import math
import time
import random
import string
from datetime import datetime, timezone, timedelta

import requests

# --- Ayarlar --------------------------------------------------------------

LSASAF_USER = os.environ.get("LSASAF_USER", "").strip()
LSASAF_PASS = os.environ.get("LSASAF_PASS", "").strip()

# TODO: Hesap açıldıktan sonra gerçek NRT veri servisi tabanı ile
# değiştirilecek. Şu an sadece dokümantasyonda geçen genel adres.
BASE_URL = "https://datalsasaf.lsasvcs.ipma.pt"

# TODO: Gerçek dosya/klasör kalıbı hesap panelinden teyit edilecek.
# Aşağıdaki fonksiyon, "en son ~15 dakikalık FRP-PIXEL dosyasının
# adını/urlsini üret" mantığını izole ediyor — böylece kalıp
# değiştiğinde SADECE bu fonksiyon güncellenecek, script'in geri kalanı
# aynı kalacak.
def _en_son_urun_url_adaylari():
    """Şu anki UTC zamana göre, SEVIRI'nin 15 dakikalık tarama
    ritmine uyan (00, 15, 30, 45) en yakın geçmiş 2-3 zaman damgası
    için olası indirme URL'lerini üretir. Gerçek kalıp teyit edilene
    kadar bu fonksiyon PLACEHOLDER'dır."""
    simdi = datetime.now(timezone.utc)
    dakika = (simdi.minute // 15) * 15
    taban_zaman = simdi.replace(minute=dakika, second=0, microsecond=0)

    # Dosya adı VE dizin yolu açık dizin listelemesi üzerinden doğrulandı
    # (2026-08-15): .../FRP-PIXEL/HDF5/{YYYY}/{MM}/{DD}/{dosya_adi}
    # Not: klasör adı büyük harfle "HDF5" — Windows'ta önemsiz ama bu
    # sunucu case-sensitive olabileceğinden aynen korunuyor.
    adaylar = []
    for geri in range(0, 3):  # son 3 tarama zamanını dene (45 dk'ya kadar)
        zaman = taban_zaman - timedelta(minutes=15 * geri)
        damga = zaman.strftime("%Y%m%d%H%M")
        dosya_adi = f"HDF5_LSASAF_MSG-IODC_FRP-PIXEL-ListProduct_IODC-Disk_{damga}"
        adaylar.append(
            f"{BASE_URL}/PRODUCTS/MSG-IODC/FRP-PIXEL/HDF5/{zaman:%Y}/{zaman:%m}/{zaman:%d}/{dosya_adi}"
        )
    return adaylar


# Türkiye bounding box (FIRMS script'iyle aynı)
TURKIYE_BBOX = (25.5, 35.5, 45.0, 42.5)  # west, south, east, north

# FRP eşiği (MW) — SEVIRI'nin fiziksel alt sınırı ~20 MW civarı
# (kaynak: LSA SAF ürün dokümantasyonu). Bunun altını almak gürültüyü
# artırır, üstünü yükseltmek küçük/başlangıç yangınlarını kaçırır.
FRP_MIN_ESIK = 20

# Bu ürünün kendi güven skoru FIRE_CONFIDENCE alanında (0-1 arası, ölçekli
# tam sayı olarak saklı) — gerçek örnek dosyada teyit edildi. VIIRS/MODIS'in
# 0-100 confidence koduyla birebir aynı ölçek değil, karıştırmayın.


def uid():
    return "e" + "".join(random.choices(string.ascii_lowercase + string.digits, k=9)) + str(int(time.time() * 1000))


def _icinde_mi(lat, lng, bbox):
    w, s, e, n = bbox
    return s <= lat <= n and w <= lng <= e


def urun_indir():
    """Son ~45 dakika içindeki tarama zamanlarını sırayla dener,
    ilk başarılı NetCDF indirmeyi döndürür. Hiçbiri yoksa None."""
    if not (LSASAF_USER and LSASAF_PASS):
        print("HATA: LSASAF_USER / LSASAF_PASS tanımlı değil.")
        sys.exit(1)

    for url in _en_son_urun_url_adaylari():
        try:
            r = requests.get(url, auth=(LSASAF_USER, LSASAF_PASS), timeout=30)
            if r.status_code == 200 and r.content:
                print(f"  ✓ İndirildi: {url}")
                return r.content, url
            print(f"  ⚠ {url} -> HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  ⚠ {url} -> bağlantı hatası: {e}")
    return None, None


def _olcekli_oku(ds, ad):
    """LSA SAF HDF5 List Product'larında her alan ham tam sayı olarak
    saklanır; gerçek değer = ham/SCALING_FACTOR + OFFSET. MISSING_VALUE
    ile işaretli hücreler NaN'a çevrilir. Gerçek bir örnek dosya üzerinde
    doğrulandı (LATITUDE/LONGITUDE/FRP/FIRE_CONFIDENCE hepsi bu kalıpta)."""
    dset = ds[ad]
    ham = dset[:].astype("float64")
    sf = float(dset.attrs.get("SCALING_FACTOR", 1.0))
    off = float(dset.attrs.get("OFFSET", 0.0))
    eksik = dset.attrs.get("MISSING_VALUE", None)
    deger = ham / sf + off
    if eksik is not None:
        deger[ham == float(eksik)] = float("nan")
    return deger


def hdf5_ayristir(ham_bytes):
    """FRP-PIXEL List Product'ı (HDF5, NetCDF DEĞİL) ayrıştırır. Değişken
    adları ve ölçekleme, gerçek bir örnek dosya (MSG-IODC,
    IMAGE_ACQUISITION_TIME=20260814110000) üzerinde doğrulandı."""
    import io
    import h5py  # pip install h5py

    noktalar = []
    with h5py.File(io.BytesIO(ham_bytes), "r") as ds:
        gerekli = ("LATITUDE", "LONGITUDE", "FRP", "FIRE_CONFIDENCE")
        eksikler = [ad for ad in gerekli if ad not in ds]
        if eksikler:
            print(f"  ⚠ Beklenen değişkenler bulunamadı: {eksikler}")
            print("    Mevcut değişkenler:", list(ds.keys()))
            return noktalar, None

        lat_v = _olcekli_oku(ds, "LATITUDE")
        lon_v = _olcekli_oku(ds, "LONGITUDE")
        frp_v = _olcekli_oku(ds, "FRP")
        conf_v = _olcekli_oku(ds, "FIRE_CONFIDENCE")
        acqtime_v = ds["ACQTIME"][:] if "ACQTIME" in ds else None

        for i in range(len(lat_v)):
            la, lo, f, c = lat_v[i], lon_v[i], frp_v[i], conf_v[i]
            if any(math.isnan(x) for x in (la, lo, f, c)):
                continue
            if f < FRP_MIN_ESIK:
                continue
            if not _icinde_mi(la, lo, TURKIYE_BBOX):
                continue
            nokta = {"lat": la, "lng": lo, "frp": f, "guven": c}
            if acqtime_v is not None:
                # ACQTIME piksel bazlı tarama saati, HHMM tam sayı (ör. 1111 -> 11:11)
                nokta["acqtime_hhmm"] = f"{int(acqtime_v[i]):04d}"
            noktalar.append(nokta)

        # Ürün zamanı: root attribute IMAGE_ACQUISITION_TIME'dan (YYYYMMDDHHMMSS)
        urun_zamani = None
        ham_zaman = ds.attrs.get("IMAGE_ACQUISITION_TIME")
        if ham_zaman is not None:
            if isinstance(ham_zaman, bytes):
                ham_zaman = ham_zaman.decode()
            try:
                urun_zamani = datetime.strptime(ham_zaman, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

    return noktalar, urun_zamani


def kayitlara_donustur(noktalar, urun_zamani):
    kayitlar = []
    for n in noktalar:
        tespit_saati = urun_zamani.strftime("%H:%M")
        if n.get("acqtime_hhmm"):
            # piksel bazlı gerçek tarama saati mevcutsa onu tercih et
            hhmm = n["acqtime_hhmm"]
            tespit_saati = f"{hhmm[:2]}:{hhmm[2:]}"
        kayitlar.append({
            "id": uid(),
            "tip": "Erken Sinyal (Doğrulanmadı)",
            "ad": "Olası Isı Anomalisi (MSG-IODC/SEVIRI - erken sinyal)",
            "koordinatlar": {"lat": n["lat"], "lng": n["lng"]},
            "frp": round(n["frp"], 1),
            "guven": round(n["guven"], 2),
            "eklenme": urun_zamani.strftime("%Y-%m-%d"),
            "tespit_saati_utc": tespit_saati,
            "kaynak": "EUMETSAT LSA SAF (Meteosat SEVIRI FRP-PIXEL, MSG-IODC)",
            "kaynak_link": "https://lsa-saf.eumetsat.int/en/data/products/fire-products/",
            "aciklama": (
                "Bu, coğrafi sabit uydudan (Meteosat) gelen KABA ÇÖZÜNÜRLÜKLÜ "
                "ve DOĞRULANMAMIŞ bir erken sinyaldir. VIIRS/MODIS henüz bu "
                "bölgeden geçmediği bir saatte tespit edilmiştir. Güneş "
                "yansıması, sıcak çıplak arazi veya endüstriyel ısı kaynağı "
                "olma ihtimali VIIRS/MODIS'e göre daha yüksektir — kesin "
                "doğrulama için bir sonraki VIIRS/MODIS geçişini veya haber "
                "kaynaklarını bekleyin."
            ),
            "dogrulanmis": False,
            "kaynak_turu": "uydu_erken_sinyal",
        })
    return kayitlar


def main():
    print("LSA SAF FRP-PIXEL erken sinyal taraması başlıyor...")
    ham, kaynak_url = urun_indir()
    if ham is None:
        print("Son 45 dakikada indirilebilir ürün bulunamadı, boş çıktı yazılıyor.")
        noktalar, urun_zamani = [], datetime.now(timezone.utc)
    else:
        noktalar, urun_zamani = hdf5_ayristir(ham)
        if urun_zamani is None:
            # header'da IMAGE_ACQUISITION_TIME bulunamadıysa yedek olarak şimdiki zaman
            urun_zamani = datetime.now(timezone.utc)

    kayitlar = kayitlara_donustur(noktalar, urun_zamani)
    print(f"{len(kayitlar)} erken sinyal noktası (Türkiye, FRP>={FRP_MIN_ESIK}MW).")

    cikti = {
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kaynak_urun_url": kaynak_url,
        "kayit_sayisi": len(kayitlar),
        "kayitlar": kayitlar,
        "uyari": "Bu katman doğrulanmamış erken sinyaldir; firms_yangin.json'daki "
                 "VIIRS/MODIS doğrulamalı kayıtlarla KARIŞTIRILMAMALIDIR.",
    }
    with open("lsasaf_erken_sinyal.json", "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print("Tamamlandı: lsasaf_erken_sinyal.json yazıldı.")


if __name__ == "__main__":
    main()
