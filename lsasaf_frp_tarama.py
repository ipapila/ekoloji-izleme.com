#!/usr/bin/env python3
"""
LSA SAF FRP-PIXEL (MSG) HDF5 İndirici ve Dönüştürücü
Kullanım: python lsasaf_frp_tarama.py [--inspect]
"""

import os
import sys
import json
import h5py
import numpy as np
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import time
import re
import math

# ---------------------------- KONFIGURASYON ----------------------------
BASE_URL = "https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/FRP-PIXEL/HDF5"
USER = os.environ.get('LSA_USER')
PASS = os.environ.get('LSA_PASS')
MAX_RETRIES = 3
RETRY_DELAYS = [5, 10, 15]  # saniye

# ---------------------------- YARDIMCI FONKSİYONLAR ----------------------------
def auth_get(url, retry_count=0):
    """Basic Auth ile GET isteği gönder, 401'de otomatik dene."""
    if not USER or not PASS:
        print("✗ HATA: LSA_USER veya LSA_PASS environment değişkenleri tanımlı değil!")
        sys.exit(1)

    auth = HTTPBasicAuth(USER, PASS)
    try:
        resp = requests.get(url, auth=auth, timeout=30)
        if resp.status_code == 401:
            raise requests.exceptions.HTTPError("401 Unauthorized")
        resp.raise_for_status()
        return resp
    except requests.exceptions.HTTPError as e:
        if retry_count < MAX_RETRIES and "401" in str(e):
            delay = RETRY_DELAYS[retry_count] if retry_count < len(RETRY_DELAYS) else 5
            print(f"  ⚠ bağlantı hatası ({e}), {delay}sn sonra {retry_count+2}. deneme...")
            time.sleep(delay)
            return auth_get(url, retry_count + 1)
        else:
            raise

def dosya_var_mi(url):
    """Verilen tam dosya URL'sine GET atıp içeriği döndürür, yoksa
    (401 dışı hata / 404 vb.) None döndürür. Asıl indirme burada DEĞİL,
    find_latest_file() içindeki asıl download_hdf5() çağrısında yapılır —
    burada sadece varlık + erişilebilirlik kontrolü."""
    try:
        return auth_get(url)
    except Exception as e:
        return None

# LSA SAF'ın gerçek dosya adı deseni tam olarak doğrulanamadığından
# (kimlik doğrulama gerektiren klasöre elle bakılamıyor, dizin listeleme de
# bu sunucuda desteklenmiyor — bkz. aşağıdaki not), her zaman damgası için
# BİLİNEN iki varyantı da deniyoruz. "-ListProduct" ekli varyant önce
# denenir çünkü daha önce GERÇEKTEN bu isimle bir dosya başarıyla indirildi
# (141 KB, geçerli HDF5) — sadece dataset içeriği ayrı bir sorundu.
FILENAME_VARYANTLARI = [
    "HDF5_LSASAF_MSG_FRP-PIXEL-ListProduct_MSG-Disk_{ts}",
    "HDF5_LSASAF_MSG_FRP-PIXEL_MSG-Disk_{ts}",
]

def find_latest_file():
    """
    Bugünün en güncel HDF5 dosyasının URL'ini döndürür.

    NOT — dizin listeleme (autoindex) YAKLAŞIMI TERK EDİLDİ: bu sunucu
    klasör GET'lerine standart bir Apache/nginx index HTML'i döndürmüyor
    gibi görünüyor (önceki sürüm sessizce 0 dosya buldu). Bu yüzden
    orijinal ve KANITLANMIŞ ÇALIŞAN yönteme dönüldü: dosya adını zaman
    damgasından tahmin edip doğrudan o URL'ye GET atmak.
    """
    now = datetime.utcnow()
    denenen_url_sayisi = 0

    for hour_offset in range(0, 4):
        dt = now - timedelta(hours=hour_offset)
        date_path = dt.strftime("%Y/%m/%d")
        minute_base = (dt.minute // 15) * 15
        dt_rounded = dt.replace(minute=minute_base, second=0, microsecond=0)

        for offset_min in [0, -15, -30, -45]:
            check_dt = dt_rounded + timedelta(minutes=offset_min)
            if check_dt > now:
                continue
            time_str = check_dt.strftime("%Y%m%d%H%M")

            for varyant in FILENAME_VARYANTLARI:
                url = f"{BASE_URL}/{date_path}/{varyant.format(ts=time_str)}"
                denenen_url_sayisi += 1
                resp = dosya_var_mi(url)
                if resp is not None:
                    print(f"→ Bulunan dosya: {url}")
                    return url

    raise FileNotFoundError(
        f"Son 4 saat içinde uygun HDF5 dosyası bulunamadı ({denenen_url_sayisi} URL denendi, "
        f"her ikisi de -ListProduct'lı ve'siz varyantlarla). Sunucudaki dosya adlandırma deseni "
        f"değişmiş olabilir ya da erişim/kimlik doğrulama sorunu var olabilir."
    )

def download_hdf5(url, local_path="temp.h5"):
    """Verilen URL'den HDF5 dosyasını indir. Dosya .bz2 ile sıkıştırılmış
    geldiyse (bazı LSA SAF ürünlerinde olduğu gibi) otomatik açar."""
    print(f"↓ İndiriliyor: {url}")
    resp = auth_get(url)
    icerik = resp.content
    total_size = len(icerik)

    if url.endswith('.bz2'):
        import bz2
        icerik = bz2.decompress(icerik)
        print(f"  ↳ .bz2 açıldı ({total_size // 1024} KB → {len(icerik) // 1024} KB)")

    with open(local_path, 'wb') as f:
        f.write(icerik)
    print(f"✓ İndirme tamamlandı ({total_size // 1024} KB)")
    return local_path

# ---------------------------- HDF5 İŞLEME ----------------------------
def inspect_hdf5(file_path):
    """HDF5 içindeki tüm dataset/grup yapısını ekrana basar."""
    print(f"\n🔍 HDF5 Yapısı İnceleniyor: {file_path}")
    with h5py.File(file_path, 'r') as f:
        def print_structure(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(f"  📊 Dataset : {name} → shape: {obj.shape}, dtype: {obj.dtype}")
            elif isinstance(obj, h5py.Group):
                print(f"  📁 Group   : {name}")
        f.visititems(print_structure)

def _yapi_dokumu_bas(f):
    """inspect_hdf5 ile aynı çıktıyı üretir — dataset bulunamadığında
    --inspect'i ayrıca çalıştırmaya gerek kalmadan aynı bilgiyi log'a basar."""
    print("  ── HDF5 yapısı ──")
    def yaz(name, obj):
        if isinstance(obj, h5py.Dataset):
            alanlar = f" alanlar: {obj.dtype.names}" if obj.dtype.names else ""
            print(f"    📊 {name} → shape:{obj.shape} dtype:{obj.dtype}{alanlar}")
        elif isinstance(obj, h5py.Group):
            print(f"    📁 {name}")
    f.visititems(yaz)
    print("  ── kök öznitelikler (attrs) ──")
    for k, v in f.attrs.items():
        print(f"    {k}: {v}")


def _tum_datasetleri_topla(f):
    """Dosyanın TAMAMINI (her derinlikteki grubu) tarayıp yol→dataset eşlemi döndürür."""
    datasetler = {}
    def topla(name, obj):
        if isinstance(obj, h5py.Dataset):
            datasetler[name] = obj
    f.visititems(topla)
    return datasetler


def _dataset_bul(datasetler, tam_adaylar, alt_dize_adaylar):
    """
    Üç aşamalı arama:
      1) Herhangi bir derinlikteki dataset'in adı (son path segmenti)
         tam_adaylar'dan biriyle case-insensitive eşleşiyor mu?
      2) Compound (structured) dtype'lı bir dataset içinde, alanlardan
         biri tam_adaylar'dan biriyle eşleşiyor mu? (LSA SAF "List
         Product" dosyaları FRP/LAT/LON'u ayrı dataset yerine TEK bir
         tablo dataset'inin alanları olarak tutuyor olabilir.)
      3) Son çare: dataset adında alt_dize_adaylar'dan biri geçiyor mu?
    Döndürür: (numpy_array, bulunan_yol_bilgisi, orijinal_h5py_dataset) ya da (None, None, None)
    orijinal_h5py_dataset, attrs (scale_factor/offset/fillvalue vb.) okumak için döndürülür.
    """
    tam_kucuk = [a.lower() for a in tam_adaylar]

    for yol, ds in datasetler.items():
        basename = yol.rsplit('/', 1)[-1]
        if basename.lower() in tam_kucuk:
            return ds[:], yol, ds

    for yol, ds in datasetler.items():
        if ds.dtype.names:
            for alan in ds.dtype.names:
                if alan.lower() in tam_kucuk:
                    return ds[alan][:], f"{yol}[{alan}]", ds

    for yol, ds in datasetler.items():
        basename = yol.rsplit('/', 1)[-1].lower()
        if any(sub in basename for sub in alt_dize_adaylar):
            return ds[:], yol, ds
        if ds.dtype.names:
            for alan in ds.dtype.names:
                if any(sub in alan.lower() for sub in alt_dize_adaylar):
                    return ds[alan][:], f"{yol}[{alan}]", ds

    return None, None, None


def _fiziksel_deger(ds, ham_dizi):
    """
    LSA SAF HDF5 dosyalarında sayısal alanlar (FRP, LATITUDE, LONGITUDE vb.)
    genelde ÖLÇEKLENMİŞ tam sayı (digital number) olarak saklanır:
        fiziksel_değer = ham_değer / SCALING_FACTOR + OFFSET
    Bu fonksiyon uygulanmadan ham değerler doğrudan kullanılırsa (önceki
    sürümdeki hata buydu) örn. enlem/boylam -90..90 / -180..180 aralığının
    çok dışında kalır ve process_hdf5() içindeki aralık kontrolü TÜM
    pikselleri sessizce eler → "0 adet yangın pikseli bulundu" yanılgısı.

    CAL_SLOPE/CAL_OFFSET alanları bu üründe 999.0 sentinel (yani
    "kullanılmıyor/uygulanamaz") olarak görüldüğü için kasıtlı olarak
    yok sayılıyor; gerçek ölçek SCALING_FACTOR/OFFSET attrs'ında.
    MISSING_VALUE ile eşleşen hücreler NaN'a çevrilir.
    """
    arr = np.asarray(ham_dizi, dtype=np.float64)
    attrs = dict(ds.attrs) if ds is not None else {}

    missing = attrs.get("MISSING_VALUE")
    if missing is not None:
        arr = np.where(arr == float(missing), np.nan, arr)

    scale = attrs.get("SCALING_FACTOR")
    offset = attrs.get("OFFSET", 0.0)
    if scale is not None and float(scale) not in (0.0, 999.0):
        arr = arr / float(scale) + float(offset)

    return arr


def process_hdf5(file_path):
    """
    HDF5'ten FRP, Lat, Lon, Time verilerini oku, 
    JSON ve GeoJSON üret.
    """
    print(f"\n⚙ Veri işleniyor: {file_path}")
    data = {
        "type": "FeatureCollection",
        "features": []
    }
    
    with h5py.File(file_path, 'r') as f:
        datasetler = _tum_datasetleri_topla(f)

        frp_data, frp_yol, frp_ds = _dataset_bul(
            datasetler, ["FRP", "frp", "FRP_MW", "FRP_PIXEL"], ["frp"]
        )
        lat_data, lat_yol, lat_ds = _dataset_bul(
            datasetler, ["Latitude", "LATITUDE", "Lat", "LAT", "PIXEL_LATITUDE"], ["lat"]
        )
        lon_data, lon_yol, lon_ds = _dataset_bul(
            datasetler, ["Longitude", "LONGITUDE", "Lon", "LON", "PIXEL_LONGITUDE"], ["lon", "long"]
        )
        time_data, time_yol, _ = _dataset_bul(
            datasetler,
            ["Time", "TIME", "AcqTime", "ACQTIME", "ACQUISITION_TIME", "OBSERVATION_TIME"],
            ["time"]
        )

        if frp_data is None or lat_data is None or lon_data is None:
            print("✗ Gerekli dataset'ler (FRP, Lat, Lon) bulunamadı!")
            print(f"  frp:{'bulundu → ' + frp_yol if frp_data is not None else 'BULUNAMADI'}")
            print(f"  lat:{'bulundu → ' + lat_yol if lat_data is not None else 'BULUNAMADI'}")
            print(f"  lon:{'bulundu → ' + lon_yol if lon_data is not None else 'BULUNAMADI'}")
            _yapi_dokumu_bas(f)
            sys.exit(1)

        print(f"  ✓ frp:{frp_yol}  lat:{lat_yol}  lon:{lon_yol}  time:{time_yol or '(yok)'}")

        # Teşhis çıktısı: "0 piksel bulundu" sonucunun gerçek mi (o slotta
        # aktif yangın yok) yoksa veri okumada bir sorun mu (ham/ölçeklenmemiş
        # kod değerleri, yanlış fill-value, vb.) olduğunu ayırt etmek için.
        # LSA SAF ürünlerinde FRP genelde scale_factor/add_offset ile
        # kodlanmış tam sayı olarak saklanabiliyor — bu attrs varsa görürüz.
        frp_ham = frp_data.flatten()
        gecerli_ham = frp_ham[~np.isnan(frp_ham)] if frp_ham.dtype.kind == 'f' else frp_ham
        print(f"  ℹ frp dtype:{frp_data.dtype}  uzunluk:{len(frp_ham)}  "
              f"min:{gecerli_ham.min() if len(gecerli_ham) else '—'}  "
              f"max:{gecerli_ham.max() if len(gecerli_ham) else '—'}  "
              f">0 sayısı:{int((gecerli_ham > 0).sum()) if len(gecerli_ham) else 0}")
        if frp_ds is not None and dict(frp_ds.attrs):
            print(f"  ℹ frp attrs: {dict(frp_ds.attrs)}")
        if lat_ds is not None and dict(lat_ds.attrs):
            print(f"  ℹ lat attrs: {dict(lat_ds.attrs)}")
        if lon_ds is not None and dict(lon_ds.attrs):
            print(f"  ℹ lon attrs: {dict(lon_ds.attrs)}")
        if len(frp_ham):
            print(f"  ℹ frp ilk 10 ham değer: {frp_ham[:10].tolist()}")

        # Ham (dijital) değerleri SCALING_FACTOR/OFFSET attrs'ına göre
        # fiziksel değere çevir (bkz. _fiziksel_deger dokümantasyonu —
        # bu adım eksikti ve "0 piksel bulundu" yanılgısına yol açıyordu).
        frp_data = _fiziksel_deger(frp_ds, frp_data)
        lat_data = _fiziksel_deger(lat_ds, lat_data)
        lon_data = _fiziksel_deger(lon_ds, lon_data)

        frp_olcekli = frp_data.flatten()
        lat_olcekli = lat_data.flatten()
        lon_olcekli = lon_data.flatten()
        gecerli_olcekli = frp_olcekli[~np.isnan(frp_olcekli)]
        print(f"  ℹ [ölçeklendirme sonrası] frp min:{gecerli_olcekli.min() if len(gecerli_olcekli) else '—'}  "
              f"max:{gecerli_olcekli.max() if len(gecerli_olcekli) else '—'}  "
              f">0 sayısı:{int((gecerli_olcekli > 0).sum()) if len(gecerli_olcekli) else 0}")
        if len(lat_olcekli):
            print(f"  ℹ [ölçeklendirme sonrası] lat ilk 5: {lat_olcekli[:5].tolist()}  "
                  f"lon ilk 5: {lon_olcekli[:5].tolist()}")

        # Verileri düzleştir (1D olmayabilir)
        frp_flat = frp_data.flatten()
        lat_flat = lat_data.flatten()
        lon_flat = lon_data.flatten()
        
        # Zaman varsa onu da düzleştir
        if time_data is not None:
            time_flat = time_data.flatten()
        else:
            time_flat = [None] * len(frp_flat)

        # GeoJSON oluştur
        for i in range(len(frp_flat)):
            frp_val = float(frp_flat[i])
            if math.isnan(frp_val) or frp_val <= 0:
                continue  # Sadece pozitif FRP değerlerini al (yangın var)
            
            lat = float(lat_flat[i])
            lon = float(lon_flat[i])
            if lat < -90 or lat > 90 or lon < -180 or lon > 180:
                continue

            prop = {
                "frp": round(frp_val, 2),
                "latitude": lat,
                "longitude": lon
            }
            if time_flat[i] is not None:
                # Zaman genelde sayısal (UTC saniye veya julian gün)
                try:
                    if time_flat[i] > 1e6:  # Unix timestamp (saniye)
                        dt_obj = datetime.utcfromtimestamp(float(time_flat[i]))
                        prop["time"] = dt_obj.isoformat()
                    else:
                        prop["time"] = str(time_flat[i])
                except:
                    prop["time"] = str(time_flat[i])

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": prop
            }
            data["features"].append(feature)

    print(f"✓ {len(data['features'])} adet yangın pikseli bulundu.")
    
    # JSON olarak kaydet
    with open("lsasaf_frp.json", "w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=2, ensure_ascii=False)
    print("✓ lsasaf_frp.json oluşturuldu.")

    # GeoJSON olarak kaydet (zaten aynı formatta)
    with open("lsasaf_frp.geojson", "w", encoding="utf-8") as gf:
        json.dump(data, gf, indent=2, ensure_ascii=False)
    print("✓ lsasaf_frp.geojson oluşturuldu.")

# ---------------------------- ANA FONKSİYON ----------------------------
def main():
    inspect_mode = "--inspect" in sys.argv

    try:
        # 1. En son dosyayı bul
        file_url = find_latest_file()
        
        # 2. Dosyayı indir
        local_file = download_hdf5(file_url)
        
        # 3. İnceleme veya işleme
        if inspect_mode:
            inspect_hdf5(local_file)
        else:
            process_hdf5(local_file)
            
        # 4. Temizlik
        if os.path.exists(local_file):
            os.remove(local_file)
            print("🧹 Geçici dosya silindi.")
            
    except Exception as e:
        print(f"✗ Kritik hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
