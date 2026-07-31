#!/usr/bin/env python3
"""
lsasaf_frp_tarama.py
---------------------
LSA SAF (Land Surface Analysis Satellite Applications Facility, EUMETSAT/
IPMA) FRP-PIXEL ürününden — Meteosat (MSG, ileride MTG) jeostatik uydusunun
15 dakikada bir ürettiği tüm-disk (full-disk) yangın radyatif gücü (Fire
Radiative Power) piksel listesinden — Türkiye bbox'ına denk gelen noktaları
çeker.

ÖNEMLİ — BU SCRIPT İKİ AŞAMALI ÇALIŞACAK ŞEKİLDE YAZILDI
---------------------------------------------------------
LSA SAF'ın herkese açık dizin sunucusunda dosyaları görebiliyoruz (bkz.
mail: kimlik doğrulama / MAP_KEY gerekmiyor), ama HDF5 içindeki dataset
adlarını (FRP, LATITUDE, FIRE_CONFIDENCE vb. gerçek key isimleri ve
ölçekleme/offset attribute'ları) elimizde gerçek bir dosyayı açıp
görmeden %100 doğrulayamıyoruz — bu ortamdan o sunucuya ağ erişimi yok.

Bu yüzden script iki modda çalışıyor:

  1) --inspect modu: en son dosyayı indirir, içindeki TÜM dataset'lerin
     adını, shape'ini, dtype'ını ve attribute'larını (SCALING_FACTOR,
     OFFSET, MISSING_VALUE vb.) ekrana basar, hiçbir varsayım yapmadan.
     ÖNCE BUNU workflow_dispatch ile bir kere elle çalıştır, çıktısını
     Actions log'undan kopyalayıp bana gönder — gerçek key isimlerine
     göre aşağıdaki `ALAN_ADAYLARI` sözlüğünü kesinleştirip normal
     tarama mantığını (firms_yangin_tarama.py ile aynı şema: il/ilçe,
     güven kodu, arşiv) tamamlayacağım.

  2) Normal tarama modu (varsayılan): ALAN_ADAYLARI'ndaki isim adaylarını
     dosyada bulduğu ilk eşleşmeyle kullanıp kayıtlara dönüştürür. Adaylar
     LSA SAF'ın yayınlanmış FRP-PIXEL Product User Manual'ındaki tipik
     isimlere göre kondu ama --inspect ile doğrulanana kadar KESİN kabul
     etme; ilk gerçek çalıştırmada `python lsasaf_frp_tarama.py --inspect`
     çıktısını mutlaka kontrol et.

KULLANIM
--------
  pip install h5py
  python lsasaf_frp_tarama.py --inspect        # yapıyı doğrula (önce bunu çalıştır)
  python lsasaf_frp_tarama.py                  # normal tarama (JSON/GeoJSON üretir)
  python lsasaf_frp_tarama.py --uydu mtg       # MTG operasyonel olduğunda

Kimlik doğrulama / MAP_KEY GEREKMİYOR — LSA SAF dizini herkese açık.
"""

import argparse
import io
import json
import math
import os
import random
import re
import socket
import string
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    import h5py
except ImportError:
    print("HATA: h5py kurulu değil. Önce şunu çalıştır: pip install h5py")
    sys.exit(1)

# GitHub Actions runner'larında IPv6 route sorunu için (bkz. firms_yangin_tarama.py)
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    sonuc = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return sonuc or _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo


# --- Ayarlar -------------------------------------------------------------

LSASAF_TABAN = "https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS"

# Türkiye bounding box: west,south,east,north (firms_yangin_tarama.py ile aynı)
TURKIYE_BBOX = (25.5, 35.5, 45.0, 42.5)

UYDU_YOLLARI = {
    "msg": "MSG/FRP-PIXEL/HDF5",
    "mtg": "MTG/MTFRPPixel/NATIVE",  # MTG şu an demo statüsünde — bkz. LSA SAF mailindeki not
}

# --- HDF5 alan adayları (--inspect ile doğrulanana kadar KESİN DEĞİL) ----
# Her mantıksal alan için, LSA SAF FRP-PIXEL PUM'da (Product User Manual)
# geçen tipik dataset adlarından birkaç aday — script dosyada ilk bulduğu
# adayı kullanır. --inspect çıktısı bunları netleştirecek.
ALAN_ADAYLARI = {
    "lat": ["LATITUDE", "Latitude", "lat"],
    "lon": ["LONGITUDE", "Longitude", "lon"],
    "frp": ["FRP", "Fire_Radiative_Power"],
    "frp_belirsizlik": ["FRP_UNCERTAINTY", "FRPUncertainty"],
    "guven": ["FIRE_CONFIDENCE", "FireConfidence", "CONFIDENCE"],
    "piksel_boyu": ["PIXEL_SIZE", "PixelSize"],
}

IL_MERKEZLERI = {
    "Adana": (37.0000, 35.3213), "Adıyaman": (37.7648, 38.2786),
    "Afyonkarahisar": (38.7507, 30.5567), "Ağrı": (39.7191, 43.0503),
    "Amasya": (40.6499, 35.8353), "Ankara": (39.9334, 32.8597),
    "Antalya": (36.8969, 30.7133), "Artvin": (41.1828, 41.8183),
    "Aydın": (37.8560, 27.8416), "Balıkesir": (39.6484, 27.8826),
    "Bilecik": (40.1451, 29.9798), "Bingöl": (38.8855, 40.4989),
    "Bitlis": (38.4006, 42.1095), "Bolu": (40.7392, 31.6089),
    "Burdur": (37.7203, 30.2908), "Bursa": (40.1826, 29.0665),
    "Çanakkale": (40.1553, 26.4142), "Çankırı": (40.6013, 33.6134),
    "Çorum": (40.5506, 34.9556), "Denizli": (37.7765, 29.0864),
    "Diyarbakır": (37.9144, 40.2306), "Edirne": (41.6771, 26.5557),
    "Elazığ": (38.6810, 39.2264), "Erzincan": (39.7500, 39.5000),
    "Erzurum": (39.9000, 41.2700), "Eskişehir": (39.7767, 30.5206),
    "Gaziantep": (37.0662, 37.3833), "Giresun": (40.9128, 38.3895),
    "Gümüşhane": (40.4602, 39.4813), "Hakkari": (37.5744, 43.7408),
    "Hatay": (36.4018, 36.3498), "Isparta": (37.7648, 30.5566),
    "Mersin": (36.8000, 34.6333), "İstanbul": (41.0082, 28.9784),
    "İzmir": (38.4237, 27.1428), "Kars": (40.6013, 43.0975),
    "Kastamonu": (41.3887, 33.7827), "Kayseri": (38.7312, 35.4787),
    "Kırklareli": (41.7333, 27.2167), "Kırşehir": (39.1425, 34.1709),
    "Kocaeli": (40.8533, 29.8815), "Konya": (37.8746, 32.4932),
    "Kütahya": (39.4242, 29.9833), "Malatya": (38.3552, 38.3095),
    "Manisa": (38.6191, 27.4289), "Kahramanmaraş": (37.5753, 36.9228),
    "Mardin": (37.3212, 40.7245), "Muğla": (37.2153, 28.3636),
    "Muş": (38.9462, 41.7539), "Nevşehir": (38.6939, 34.6857),
    "Niğde": (37.9667, 34.6833), "Ordu": (40.9839, 37.8764),
    "Rize": (41.0201, 40.5234), "Sakarya": (40.6940, 30.4358),
    "Samsun": (41.2867, 36.3300), "Siirt": (37.9333, 41.9500),
    "Sinop": (42.0231, 35.1531), "Sivas": (39.7477, 37.0179),
    "Tekirdağ": (40.9833, 27.5167), "Tokat": (40.3167, 36.5500),
    "Trabzon": (41.0027, 39.7168), "Tunceli": (39.3074, 39.4388),
    "Şanlıurfa": (37.1591, 38.7969), "Uşak": (38.6823, 29.4082),
    "Van": (38.4891, 43.4089), "Yozgat": (39.8181, 34.8147),
    "Zonguldak": (41.4564, 31.7987), "Aksaray": (38.3687, 34.0370),
    "Bayburt": (40.2552, 40.2249), "Karaman": (37.1759, 33.2287),
    "Kırıkkale": (39.8468, 33.5153), "Batman": (37.8812, 41.1351),
    "Şırnak": (37.4187, 42.4918), "Bartın": (41.5811, 32.4610),
    "Ardahan": (41.1105, 42.7022), "Iğdır": (39.9167, 44.0333),
    "Yalova": (40.6500, 29.2667), "Karabük": (41.2061, 32.6204),
    "Kilis": (36.7184, 37.1212), "Osmaniye": (37.0742, 36.2478),
    "Düzce": (40.8438, 31.1565),
}


def en_yakin_il(lat, lng):
    R = 6371.0
    lat1 = math.radians(lat)
    en_yakin, en_kucuk_mesafe = "", float("inf")
    for il, (il_lat, il_lng) in IL_MERKEZLERI.items():
        lat2 = math.radians(il_lat)
        dlat = math.radians(il_lat - lat)
        dlng = math.radians(il_lng - lng)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        mesafe = 2 * R * math.asin(math.sqrt(a))
        if mesafe < en_kucuk_mesafe:
            en_kucuk_mesafe, en_yakin = mesafe, il
    return en_yakin


def uid():
    return "r" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=9)
    ) + str(int(time.time() * 1000))


def _istek_yap(url, deneme=3, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})
    for i in range(1, deneme + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                ham = r.read()
                return ham if binary else ham.decode("utf-8", errors="replace")
        except (OSError, urllib.error.URLError) as e:
            if i < deneme:
                bekleme = 5 * i
                print(f"  ⚠ bağlantı hatası ({e}), {bekleme}sn sonra {i + 1}. deneme...")
                time.sleep(bekleme)
            else:
                print(f"  ✗ {deneme} denemeden sonra bağlanılamadı: {e}")
    return None


def en_son_listproduct_dosyasini_bul(uydu="msg", geriye_saat=3):
    """Bugünkü (gerekirse dünkü) dizin sayfalarını tarayıp en son
    '-ListProduct_' HDF5 dosyasının tam URL'sini döndürür. Dizin sayfası
    düz HTML olduğu için basit bir regex ile link isimlerini çıkarıyoruz —
    tam bir HTML parser'a gerek yok, h5ai çıktısı sabit bir örüntüde."""
    simdi = datetime.now(timezone.utc)
    for gun_farki in (0, 1):  # gece yarısı UTC sınırında dünkü klasöre düşme ihtimaline karşı
        tarih = simdi - timedelta(days=gun_farki)
        yol = f"{LSASAF_TABAN}/{UYDU_YOLLARI[uydu]}/{tarih.year:04d}/{tarih.month:02d}/{tarih.day:02d}/"
        html = _istek_yap(yol)
        if html is None:
            continue
        # Sadece ListProduct dosyalarını al (QualityProduct'ı şimdilik atlıyoruz)
        dosyalar = re.findall(r'href="([^"]*ListProduct[^"]*)"', html)
        if not dosyalar:
            continue
        dosyalar = sorted(set(dosyalar))
        en_son = dosyalar[-1]
        tam_url = en_son if en_son.startswith("http") else yol + en_son.split("/")[-1]
        return tam_url
    return None


def hdf5_yapisini_incele(dosya_yolu):
    """--inspect modu: dosyadaki her dataset'in adını, shape/dtype'ını ve
    attribute'larını basar. Hiçbir varsayım yapmaz — gerçek yapıyı görmek
    için kullanılır."""
    print(f"\n=== {dosya_yolu} içeriği ===")
    with h5py.File(dosya_yolu, "r") as f:
        print("Kök (root) attribute'ları:")
        for k, v in f.attrs.items():
            print(f"  {k} = {v}")

        def yazdir(ad, nesne):
            if isinstance(nesne, h5py.Dataset):
                print(f"\nDataset: {ad}")
                print(f"  shape={nesne.shape}, dtype={nesne.dtype}")
                for k, v in nesne.attrs.items():
                    print(f"  attr[{k}] = {v}")
            else:
                print(f"\nGrup: {ad}")

        f.visititems(yazdir)


def _alan_bul(f, adaylar):
    """ALAN_ADAYLARI listesindeki isimlerden dosyada var olan ilkini döndürür."""
    for ad in adaylar:
        if ad in f:
            return f[ad]
    return None


def _olceklendir(dataset):
    """SCALING_FACTOR / OFFSET attribute'ları varsa uygular, yoksa ham
    değeri döndürür. LSA SAF ürünlerinde tipik attribute adları bunlar,
    ama --inspect çıktısı gerçek adları doğrulayana kadar best-effort."""
    veri = dataset[()].astype("float64")
    olcek = dataset.attrs.get("SCALING_FACTOR")
    kaydirma = dataset.attrs.get("OFFSET")
    if olcek:
        veri = veri / float(olcek)
    if kaydirma:
        veri = veri + float(kaydirma)
    eksik = dataset.attrs.get("MISSING_VALUE")
    if eksik is not None:
        veri[veri == float(eksik)] = float("nan")
    return veri


def hdf5ten_kayitlara_donustur(dosya_yolu, il_ilce_coz=False):
    with h5py.File(dosya_yolu, "r") as f:
        lat_ds = _alan_bul(f, ALAN_ADAYLARI["lat"])
        lon_ds = _alan_bul(f, ALAN_ADAYLARI["lon"])
        frp_ds = _alan_bul(f, ALAN_ADAYLARI["frp"])
        guven_ds = _alan_bul(f, ALAN_ADAYLARI["guven"])

        if lat_ds is None or lon_ds is None or frp_ds is None:
            print(
                "HATA: LATITUDE/LONGITUDE/FRP dataset'leri beklenen adaylarla "
                "bulunamadı. Önce `--inspect` ile gerçek dataset adlarını "
                "kontrol et ve ALAN_ADAYLARI sözlüğünü güncelle."
            )
            print(f"  Denenen lat adayları: {ALAN_ADAYLARI['lat']}")
            print(f"  Denenen lon adayları: {ALAN_ADAYLARI['lon']}")
            print(f"  Denenen frp adayları: {ALAN_ADAYLARI['frp']}")
            print(f"  Dosyadaki kök anahtarlar: {list(f.keys())}")
            return []

        lat = _olceklendir(lat_ds)
        lon = _olceklendir(lon_ds)
        frp = _olceklendir(frp_ds)
        guven = _olceklendir(guven_ds) if guven_ds is not None else None

    bat, guney, dogu, kuzey = TURKIYE_BBOX
    kayitlar = []
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i in range(len(lat)):
        la, lo = float(lat[i]), float(lon[i])
        if math.isnan(la) or math.isnan(lo):
            continue
        if not (bat <= lo <= dogu and guney <= la <= kuzey):
            continue

        frp_deger = float(frp[i]) if not math.isnan(frp[i]) else 0.0
        guven_deger = float(guven[i]) if guven is not None and not math.isnan(guven[i]) else None

        il, ilce, yerlesim = "", "", ""
        if not il_ilce_coz:
            il = en_yakin_il(la, lo)
        konum_ifadesi = yerlesim or ilce or il or "bilinmeyen bir konumda"

        if guven_deger is None:
            guven_kod, guven_seviye = "l", "Düşük"
        elif guven_deger >= 80:
            guven_kod, guven_seviye = "h", "Yüksek"
        elif guven_deger >= 50:
            guven_kod, guven_seviye = "n", "Orta"
        else:
            guven_kod, guven_seviye = "l", "Düşük"

        kayit = {
            "id": uid(),
            "tip": "İklim Olayları",
            "ad": f"Uydu Tespitli Isı Anomalisi (Meteosat){f' ({konum_ifadesi})' if konum_ifadesi != 'bilinmeyen bir konumda' else ''}",
            "il": il,
            "ilce": ilce,
            "yerlesim": yerlesim,
            "koordinatlar": {"lat": la, "lng": lo},
            "alan_ha": 0,
            "durum": "Aktif",
            "belge_no": "",
            "eklenme": tarih,
            "kaynak": "LSA SAF FRP-PIXEL (Meteosat MSG)",
            "kaynak_link": "https://landsaf.ipma.pt/",
            "aciklama": (
                f"Bu nokta, {konum_ifadesi}{' yakınında' if konum_ifadesi != 'bilinmeyen bir konumda' else ''} "
                f"Meteosat jeostatik uydusu tarafından tespit edilen bir ısı anomalisidir "
                f"(Fire Radiative Power: {frp_deger:.1f} MW). "
                "Bu tür tespitler her zaman yangın anlamına gelmez; tarım arazisi yakma, "
                "sanayi tesisi ısısı veya güneş yansıması da benzer sinyal verebilir."
            ),
            "teknik_detay": f"FRP: {frp_deger:.1f} MW, güvenilirlik: {guven_deger}",
            "guven_seviye": guven_seviye,
            "guven_kod": guven_kod,
            "alt_kategori": "",
            "kaynak_turu": "uydu",
        }
        kayitlar.append(kayit)

    return kayitlar


def geojsona_cevir(kayitlar):
    features = []
    for k in kayitlar:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [k["koordinatlar"]["lng"], k["koordinatlar"]["lat"]],
            },
            "properties": {key: v for key, v in k.items() if key != "koordinatlar"},
        })
    return {"type": "FeatureCollection", "features": features}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true", help="HDF5 yapısını incele, hiçbir dönüşüm yapma")
    ap.add_argument("--uydu", choices=["msg", "mtg"], default="msg")
    args = ap.parse_args()

    print(f"LSA SAF FRP-PIXEL ({args.uydu.upper()}) için en son dosya aranıyor...")
    dosya_url = en_son_listproduct_dosyasini_bul(args.uydu)
    if not dosya_url:
        print("✗ Dizin sayfasında ListProduct dosyası bulunamadı.")
        sys.exit(1)
    print(f"→ Bulunan dosya: {dosya_url}")

    ham = _istek_yap(dosya_url, binary=True)
    if ham is None:
        print("✗ Dosya indirilemedi.")
        sys.exit(1)

    yerel_yol = "lsasaf_gecici.h5"
    with open(yerel_yol, "wb") as f:
        f.write(ham)
    print(f"→ İndirildi: {len(ham) / 1024:.0f} KB")

    if args.inspect:
        hdf5_yapisini_incele(yerel_yol)
        os.remove(yerel_yol)
        print(
            "\n--inspect tamamlandı. Yukarıdaki dataset adlarını / "
            "attribute'ları bana gönder, ALAN_ADAYLARI'nı kesinleştirip "
            "tam tarama mantığını (il/ilçe çözümleme, arşiv, GeoJSON) "
            "tamamlayalım."
        )
        return

    kayitlar = hdf5ten_kayitlara_donustur(yerel_yol)
    os.remove(yerel_yol)
    print(f"Türkiye bbox'ı içinde {len(kayitlar)} nokta bulundu.")

    cikti = {
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kayit_sayisi": len(kayitlar),
        "kayitlar": kayitlar,
    }
    with open("lsasaf_frp.json", "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)
    with open("lsasaf_frp.geojson", "w", encoding="utf-8") as f:
        json.dump(geojsona_cevir(kayitlar), f, ensure_ascii=False, indent=2)

    print(f"Tamamlandı: {len(kayitlar)} kayıt -> lsasaf_frp.json / lsasaf_frp.geojson")


if __name__ == "__main__":
    main()
