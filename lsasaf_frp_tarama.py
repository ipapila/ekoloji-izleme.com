#!/usr/bin/env python3
"""
LSA SAF FRP-PIXEL (MSG) HDF5 İndirici ve Dönüştürücü
Kullanım: python lsasaf_frp_tarama.py [--inspect]
"""

import os
import sys
import json
import h5py
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

def find_latest_file():
    """Bugünün en güncel HDF5 dosyasını URL'ini döndür."""
    now = datetime.utcnow()
    # LSA SAF dosyaları genelde şu formatta: .../YYYY/MM/DD/HDF5_LSASAF_MSG_FRP-PIXEL-ListProduct_MSG-Disk_YYYYMMDDHHMM
    # Son 3 saati dene (eğer 15dk'da bir geliyorsa)
    for hour_offset in range(0, 4):
        dt = now - timedelta(hours=hour_offset)
        date_path = dt.strftime("%Y/%m/%d")
        # Dakikaları 15'e yuvarla (00,15,30,45) - en sonuncuyu al
        minute_base = (dt.minute // 15) * 15
        dt_rounded = dt.replace(minute=minute_base, second=0, microsecond=0)
        
        # 4 zaman dilimini dene (son 1 saat içindeki 15'lik dilimler)
        for offset_min in [0, -15, -30, -45]:
            check_dt = dt_rounded + timedelta(minutes=offset_min)
            if check_dt > now:
                continue
            time_str = check_dt.strftime("%Y%m%d%H%M")
            url = f"{BASE_URL}/{date_path}/HDF5_LSASAF_MSG_FRP-PIXEL-ListProduct_MSG-Disk_{time_str}"
            # HEAD isteği ile dosyanın var olup olmadığını kontrol et (401 de dönebilir)
            try:
                resp = auth_get(url)  # HEAD yerine GET yap, ama sadece kontrol için; ama indirmeyelim.
                # Eğer 200 gelirse içerik var. Ama bu sadece liste sayfası mı yoksa direkt dosya mı?
                # LSA SAF bu URL'ye GET çekince direkt HDF5 dosyasını döndürüyor.
                print(f"→ Bulunan dosya: {url}")
                return url
            except Exception:
                continue
    raise FileNotFoundError("Son 3 saat içinde uygun HDF5 dosyası bulunamadı.")

def download_hdf5(url, local_path="temp.h5"):
    """Verilen URL'den HDF5 dosyasını indir."""
    print(f"↓ İndiriliyor: {url}")
    resp = auth_get(url)
    total_size = len(resp.content)
    with open(local_path, 'wb') as f:
        f.write(resp.content)
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
        # LSA SAF FRP-PIXEL içindeki tipik dataset isimleri
        # Genelde /FRP, /Latitude, /Longitude, /Time (veya /LAT, /LON)
        possible_frp = ["FRP", "frp", "/FRP", "/frp"]
        possible_lat = ["Latitude", "Lat", "LAT", "/Latitude"]
        possible_lon = ["Longitude", "Lon", "LON", "/Longitude"]
        possible_time = ["Time", "time", "/Time", "/time", "AcqTime"]

        frp_data = None
        lat_data = None
        lon_data = None
        time_data = None

        # Dataset'leri bul
        def find_dataset(possible_names):
            for name in possible_names:
                if name in f:
                    return f[name][:]
                # Grup içindeki göreceli yolları da dene
                for key in f.keys():
                    if isinstance(f[key], h5py.Group):
                        if name in f[key]:
                            return f[key][name][:]
            return None

        # Ana kökten bul
        for name in possible_frp:
            if name in f:
                frp_data = f[name][:]
                break
        if frp_data is None:
            # Grupları tara (örn: /geolocation/Latitude)
            for group_name in f.keys():
                if isinstance(f[group_name], h5py.Group):
                    for ds_name in possible_frp:
                        if ds_name in f[group_name]:
                            frp_data = f[group_name][ds_name][:]
                            break
                    if frp_data is not None:
                        break

        for name in possible_lat:
            if name in f:
                lat_data = f[name][:]
                break
        if lat_data is None:
            for group_name in f.keys():
                if isinstance(f[group_name], h5py.Group):
                    for ds_name in possible_lat:
                        if ds_name in f[group_name]:
                            lat_data = f[group_name][ds_name][:]
                            break
                    if lat_data is not None:
                        break

        for name in possible_lon:
            if name in f:
                lon_data = f[name][:]
                break
        if lon_data is None:
            for group_name in f.keys():
                if isinstance(f[group_name], h5py.Group):
                    for ds_name in possible_lon:
                        if ds_name in f[group_name]:
                            lon_data = f[group_name][ds_name][:]
                            break
                    if lon_data is not None:
                        break

        # Zaman verisini al (opsiyonel)
        for name in possible_time:
            if name in f:
                time_data = f[name][:]
                break
        if time_data is None:
            for group_name in f.keys():
                if isinstance(f[group_name], h5py.Group):
                    for ds_name in possible_time:
                        if ds_name in f[group_name]:
                            time_data = f[group_name][ds_name][:]
                            break
                    if time_data is not None:
                        break

        if frp_data is None or lat_data is None or lon_data is None:
            print("✗ Gerekli dataset'ler (FRP, Lat, Lon) bulunamadı! Lütfen --inspect ile kontrol edin.")
            sys.exit(1)

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
