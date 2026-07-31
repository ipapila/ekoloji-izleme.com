#!/usr/bin/env python3
"""
effis_tarama.py
-----------------
Avrupa Orman Yangınları Bilgi Sistemi'nden (EFFIS — European Forest Fire
Information System, Kopernik/AB Ortak Araştırma Merkezi projesi) iki şey
çeker:

  1) Yangın alanı poligonları (burnt-area) — Türkiye bbox'ı içinde
     MODIS tabanlı yanmış alan sınırları (WFS).
  2) İl bazlı günlük yangın riski — Kanada Fire Weather Index (FWI)
     modelinden, EFFIS'in resmi 6 sınıflı risk skalasına göre
     sınıflandırılmış (WMS GetFeatureInfo, il merkezlerinden nokta
     örnekleme).

Firemap.live'ın gösterdiği "Daily fire danger risk" ve yangın alanı
poligonu bu kaynaktan geliyor — EFFIS tamamen ücretsiz ve Türkiye'yi
(Orta Doğu/Kuzey Afrika grubu) kapsıyor.

NOT: Bu script yazıldığı sırada EFFIS'in canlı sunucusunda geçici bir
sunucu hatası (500 / msLoadSymbolSet) gözlemlendi — hem WMS hem WFS
istekleri aynı hatayı veriyordu. Bu servis tarafı bir arıza gibi
görünüyor; kod dokümante edilmiş resmi endpoint'lere göre yazıldı,
sunucu düzeldiğinde çalışması bekleniyor. İlk çalıştırmayı
workflow_dispatch ile elle tetikleyip çıktıyı kontrol etmen önerilir.

KULLANIM
--------
python effis_tarama.py
Çıktı: effis_yangin_alanlari.geojson, effis_yangin_riski.json
"""

import io
import json
import math
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# GitHub Actions runner'larında IPv6 route sorunu için (bkz. firms_yangin_tarama.py)
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    sonuc = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return sonuc or _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo


# --- Ayarlar -----------------------------------------------------------

EFFIS_WMS = "https://maps.effis.emergency.copernicus.eu/effis"
TURKIYE_BBOX = "25.5,35.5,45.0,42.5"  # west,south,east,north

# EFFIS'in resmi FWI risk sınıfları (kaynak: EFFIS Fire Danger Forecast
# teknik dokümantasyonu). Eşik değerleri sabit — ülkeye bakılmaksızın
# aynı skala kullanılıyor.
FWI_SINIFLARI = [
    (11.2, "Düşük"),
    (21.3, "Orta"),
    (38.0, "Yüksek"),
    (50.0, "Çok Yüksek"),
    (70.0, "Aşırı"),
    (float("inf"), "Çok Aşırı"),
]

# firms_yangin_tarama.py ile aynı il merkezleri (bkz. o dosyadaki
# IL_MERKEZLERI) — risk sorgusu il bazında yapılıyor, 81 istek yeterli.
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


def _istek_yap(url, deneme=3):
    """Ortak retry/backoff'lu GET isteği. Başarısızsa None döner."""
    req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})
    for i in range(1, deneme + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except (OSError, urllib.error.URLError) as e:
            if i < deneme:
                bekleme = 5 * i
                print(f"  ⚠ bağlantı hatası ({e}), {bekleme}sn sonra {i + 1}. deneme...")
                time.sleep(bekleme)
            else:
                print(f"  ✗ {deneme} denemeden sonra bağlanılamadı: {e}")
    return None


def fwi_sinifla(deger):
    for esik, ad in FWI_SINIFLARI:
        if deger < esik:
            return ad
    return "Çok Aşırı"


def il_fwi_cek(il, lat, lng, tarih):
    """Bir il merkezi için EFFIS FWI (Fire Weather Index) değerini
    WMS GetFeatureInfo ile nokta örnekleyerek okur ve sınıflandırır."""
    delta = 0.05  # ~ birkaç km'lik pencere, 8km çözünürlüklü grid için yeterli
    bbox = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"
    url = (
        f"{EFFIS_WMS}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo"
        f"&LAYERS=ecmwf007.fwi&QUERY_LAYERS=ecmwf007.fwi&STYLES="
        f"&SRS=EPSG:4326&BBOX={bbox}&WIDTH=3&HEIGHT=3&X=1&Y=1"
        f"&INFO_FORMAT=application/json&TIME={tarih}"
    )
    yanit = _istek_yap(url, deneme=2)
    if yanit is None:
        return None

    deger = None
    # Önce JSON olarak dene (GeoJSON FeatureCollection -> properties.value/GRAY_INDEX)
    try:
        veri = json.loads(yanit)
        ozellikler = veri.get("features", [{}])[0].get("properties", {})
        for anahtar in ("GRAY_INDEX", "value", "value_0", "FWI"):
            if anahtar in ozellikler:
                deger = float(ozellikler[anahtar])
                break
    except (json.JSONDecodeError, ValueError, IndexError, KeyError, TypeError):
        pass

    # JSON değilse (GML/metin dönmüş olabilir) — metindeki ilk ondalık
    # sayıyı yakala. EFFIS sunucu yapılandırmasına göre format değişebilir.
    if deger is None:
        eslesme = re.search(r"[-+]?\d+\.\d+", yanit)
        if eslesme:
            try:
                deger = float(eslesme.group())
            except ValueError:
                pass

    if deger is None:
        return None

    return {"fwi": round(deger, 1), "risk": fwi_sinifla(deger)}


def tum_illerin_riskini_cek():
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sonuc = {}
    basarisiz = 0
    for il, (lat, lng) in IL_MERKEZLERI.items():
        risk = il_fwi_cek(il, lat, lng, tarih)
        if risk:
            sonuc[il] = risk
        else:
            basarisiz += 1
        time.sleep(0.3)  # EFFIS sunucusuna nazik davran
    print(f"  {len(sonuc)}/{len(IL_MERKEZLERI)} il için risk okundu ({basarisiz} başarısız)")
    return sonuc, tarih


def yangin_alanlarini_cek():
    """Türkiye bbox'ı içindeki EFFIS yangın alanı (burnt-area) poligonlarını
    WFS'ten GeoJSON olarak çeker. Alan şeması EFFIS tarafında değişebileceği
    için gelen özellikleri (properties) olduğu gibi geçiriyoruz."""
    url = (
        f"{EFFIS_WMS}?service=WFS&request=getfeature&typename=ms:modis.ba.poly"
        f"&version=1.1.0&outputformat=GEOJSON&bbox={TURKIYE_BBOX}"
    )
    yanit = _istek_yap(url, deneme=3)
    if yanit is None:
        return {"type": "FeatureCollection", "features": []}

    try:
        veri = json.loads(yanit)
        if veri.get("type") == "FeatureCollection":
            print(f"  {len(veri.get('features', []))} yangın alanı poligonu bulundu")
            return veri
    except json.JSONDecodeError:
        pass

    print(f"  ⚠ EFFIS WFS beklenmeyen bir yanıt döndürdü (ilk 150 karakter): {yanit[:150]}")
    return {"type": "FeatureCollection", "features": []}


def main():
    print("EFFIS'ten Türkiye için günlük yangın riski (FWI) çekiliyor...")
    riskler, tarih = tum_illerin_riskini_cek()

    print("EFFIS'ten yangın alanı poligonları çekiliyor...")
    poligonlar = yangin_alanlarini_cek()

    risk_ciktisi = {
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tarih": tarih,
        "kaynak": "EFFIS (Fire Weather Index, ECMWF modeli)",
        "iller": riskler,
    }
    with open("effis_yangin_riski.json", "w", encoding="utf-8") as f:
        json.dump(risk_ciktisi, f, ensure_ascii=False, indent=2)

    with open("effis_yangin_alanlari.geojson", "w", encoding="utf-8") as f:
        json.dump(poligonlar, f, ensure_ascii=False, indent=2)

    print(
        f"Tamamlandı: {len(riskler)} il riski -> effis_yangin_riski.json, "
        f"{len(poligonlar.get('features', []))} poligon -> effis_yangin_alanlari.geojson"
    )


if __name__ == "__main__":
    main()
