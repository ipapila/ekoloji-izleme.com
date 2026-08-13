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
3) ÖNEMLİ / DOĞRULANMASI GEREKEN KISIM:
   Aşağıdaki BASE_URL ve DOSYA_YOLU_SABLONU değerleri, LSA SAF'ın genel
   dokümantasyonundan çıkarılmış bir İSKELETTİR — ben bu ortamda
   eumetsat.int / ipma.pt alan adlarına ağ erişimine sahip değilim,
   bu yüzden gerçek dizin yapısını / dosya adlandırma kalıbını canlı
   olarak doğrulayamadım. Hesabınızla https://datalsasaf.lsasvcs.ipma.pt/
   adresine tarayıcıdan girip MSG FRP-PIXEL ürününün NRT klasöründeki
   gerçek dosya/URL kalıbını görüp burayı güncellememiz gerekiyor.
   (Muhtemel biçim: tarih/saat bazlı bir NetCDF dosyası, ör.
   .../NETCDF/.../S_NWC_MSG.../FRP-PIXEL_...-YYYYMMDDHHMM.nc gibi —
   ama bunu varsayım olarak koddan çıkarmadım, siz teyit edin.)
4) GitHub Actions secrets'a ekleyin: LSASAF_USER, LSASAF_PASS
5) requirements: pip install netCDF4 requests

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

    adaylar = []
    for geri in range(0, 3):  # son 3 tarama zamanını dene (45 dk'ya kadar)
        zaman = taban_zaman - timedelta(minutes=15 * geri)
        damga = zaman.strftime("%Y%m%d%H%M")
        # TODO: gerçek yol/dosya adı kalıbı ile değiştirilecek
        adaylar.append(
            f"{BASE_URL}/PRODUCTS/MSG/FRP-PIXEL/NETCDF/{zaman:%Y}/{zaman:%m}/{zaman:%d}/"
            f"S_NWC_FRP-PIXEL_MSG_MSG-N-VISIR_{damga}.nc"
        )
    return adaylar


# Türkiye bounding box (FIRMS script'iyle aynı)
TURKIYE_BBOX = (25.5, 35.5, 45.0, 42.5)  # west, south, east, north

# FRP eşiği (MW) — SEVIRI'nin fiziksel alt sınırı ~20 MW civarı
# (kaynak: LSA SAF ürün dokümantasyonu). Bunun altını almak gürültüyü
# artırır, üstünü yükseltmek küçük/başlangıç yangınlarını kaçırır.
FRP_MIN_ESIK = 20

# Bu ürün coğrafi sabit uydudan geldiği için VIIRS/MODIS gibi ayrı
# "confidence" kodu vermiyor; onun yerine kalite bayrağı (quality flag)
# kullanılıyor. TODO: gerçek NetCDF değişken adı/değer aralığı, ürün
# kılavuzuyla (LSA SAF Product User Manual) teyit edilmeli.


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


def netcdf_ayristir(ham_bytes):
    """FRP-PIXEL List Product'ı ayrıştırır. TODO: gerçek değişken adları
    (lat/lon/frp/quality alanlarının tam isimleri) ürün kılavuzundan
    teyit edilecek — burada yaygın kullanılan isimlendirme varsayıldı."""
    import io
    import netCDF4  # pip install netCDF4

    noktalar = []
    with netCDF4.Dataset("memory", memory=ham_bytes) as ds:
        # TODO: değişken adlarını gerçek dosyada `print(ds.variables.keys())`
        # ile doğrulayıp burayı güncelleyin.
        lat = ds.variables.get("FIRE_LATITUDE") or ds.variables.get("latitude")
        lon = ds.variables.get("FIRE_LONGITUDE") or ds.variables.get("longitude")
        frp = ds.variables.get("FRP") or ds.variables.get("frp")
        if lat is None or lon is None or frp is None:
            print("  ⚠ Beklenen değişkenler bulunamadı — NetCDF şemasını kontrol edin:")
            print("    Mevcut değişkenler:", list(ds.variables.keys()))
            return noktalar

        lat_v, lon_v, frp_v = lat[:], lon[:], frp[:]
        for i in range(len(lat_v)):
            try:
                la, lo, f = float(lat_v[i]), float(lon_v[i]), float(frp_v[i])
            except (TypeError, ValueError):
                continue
            if f < FRP_MIN_ESIK:
                continue
            if not _icinde_mi(la, lo, TURKIYE_BBOX):
                continue
            noktalar.append({"lat": la, "lng": lo, "frp": f})
    return noktalar


def kayitlara_donustur(noktalar, urun_zamani):
    kayitlar = []
    for n in noktalar:
        kayitlar.append({
            "id": uid(),
            "tip": "Erken Sinyal (Doğrulanmadı)",
            "ad": "Olası Isı Anomalisi (MSG/SEVIRI - erken sinyal)",
            "koordinatlar": {"lat": n["lat"], "lng": n["lng"]},
            "frp": n["frp"],
            "eklenme": urun_zamani.strftime("%Y-%m-%d"),
            "tespit_saati_utc": urun_zamani.strftime("%H:%M"),
            "kaynak": "EUMETSAT LSA SAF (Meteosat SEVIRI FRP-PIXEL)",
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
        noktalar = netcdf_ayristir(ham)
        urun_zamani = datetime.now(timezone.utc)  # TODO: dosya adından gerçek tarama zamanını çıkar

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
