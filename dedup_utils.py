"""
dedup_utils.py — Haber & GeoJSON kayıt tekrarını önler.

Kullanım (tarayici.py içinde):
    from dedup_utils import HaberDedup, geojson_kayit_id

    dedup = HaberDedup("haberler.json")   # mevcut JSON'u yükler
    yeni  = dedup.filtrele(ham_liste)     # tekrarları eler
    dedup.kaydet(yeni)                    # birleştirilmiş JSON'u yazar
"""

import json
import hashlib
import os
import re
from datetime import datetime
from typing import Any


# ──────────────────────────────────────────────
# 1. YARDIMCI: Fingerprint üretimi
# ──────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Küçük harf, boşluk sıkıştır, noktalama at."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text


def haber_id(kayit: dict) -> str:
    """
    Haber kaydı için tekrarlanabilir, deterministik ID.

    Öncelik sırası:
      1. Kayıtta zaten 'id' varsa onu kullan.
      2. 'url' varsa URL hash'i.
      3. başlık + kaynak + tarih (gün) kombinasyonu.
    """
    if kayit.get("id"):
        return str(kayit["id"])

    if kayit.get("url"):
        return hashlib.md5(kayit["url"].encode()).hexdigest()[:12]

    baslik  = _normalize(kayit.get("baslik", kayit.get("title", "")))
    kaynak  = _normalize(kayit.get("kaynak", kayit.get("source", "")))
    tarih   = str(kayit.get("tarih", kayit.get("date", "")))[:10]  # sadece gün

    ham = f"{baslik}|{kaynak}|{tarih}"
    return hashlib.md5(ham.encode()).hexdigest()[:12]


def geojson_kayit_id(ozellik: dict) -> str:
    """
    GeoJSON Feature için fingerprint.
    properties.id > properties.url > (isim + koordinat).
    """
    props = ozellik.get("properties", {})
    geom  = ozellik.get("geometry", {})

    if props.get("id"):
        return f"geo_{props['id']}"

    if props.get("url"):
        return "geo_" + hashlib.md5(props["url"].encode()).hexdigest()[:10]

    isim  = _normalize(props.get("isim", props.get("name", props.get("baslik", ""))))
    koord = str(geom.get("coordinates", ""))
    ham   = f"{isim}|{koord}"
    return "geo_" + hashlib.md5(ham.encode()).hexdigest()[:10]


# ──────────────────────────────────────────────
# 2. ANA SINIF: HaberDedup
# ──────────────────────────────────────────────

class HaberDedup:
    """
    Mevcut haberler.json'u okur, yeni kayıtları filtreler, birleştirir.

    Yapı:
        haberler.json = {
            "meta": { ... },
            "haberler": [ {...}, ... ]
        }
    veya düz liste: [ {...}, ... ]
    """

    def __init__(self, dosya: str = "haberler.json"):
        self.dosya = dosya
        self._mevcut: list[dict] = []
        self._mevcut_idler: set[str] = set()
        self._yukle()

    # ── Yükleme ──────────────────────────────

    def _yukle(self):
        if not os.path.exists(self.dosya):
            return

        try:
            ham = json.load(open(self.dosya, encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            print(f"⚠  {self.dosya} okunamadı, sıfırdan başlanıyor.")
            return

        if isinstance(ham, list):
            liste = ham
        elif isinstance(ham, dict):
            liste = ham.get("haberler", [])
        else:
            return

        for k in liste:
            kid = haber_id(k)
            k.setdefault("_id", kid)          # id alanını kayıtta sakla
            self._mevcut_idler.add(kid)

        self._mevcut = liste
        print(f"✓ Mevcut kayıt yüklendi: {len(self._mevcut)}")

    # ── Filtreleme ────────────────────────────

    def filtrele(self, yeni_liste: list[dict]) -> list[dict]:
        """
        yeni_liste içinden mevcut JSON'da olmayan kayıtları döndür.
        Her kaydın '_id' alanını atar.
        """
        yeni = []
        atla = 0
        for k in yeni_liste:
            kid = haber_id(k)
            if kid in self._mevcut_idler:
                atla += 1
                continue
            k["_id"] = kid
            self._mevcut_idler.add(kid)  # aynı batch içi tekrarı da engelle
            yeni.append(k)

        print(f"✓ Filtre: {len(yeni_liste)} geldi → {len(yeni)} yeni, {atla} tekrar atlandı")
        return yeni

    def filtrele_geojson(self, featureler: list[dict]) -> list[dict]:
        """GeoJSON Feature listesi için filtre."""
        yeni = []
        atla = 0
        for f in featureler:
            fid = geojson_kayit_id(f)
            if fid in self._mevcut_idler:
                atla += 1
                continue
            f.setdefault("properties", {})["_id"] = fid
            self._mevcut_idler.add(fid)
            yeni.append(f)

        print(f"✓ GeoJSON filtre: {len(featureler)} geldi → {len(yeni)} yeni, {atla} tekrar")
        return yeni

    # ── Kaydetme ─────────────────────────────

    def kaydet(
        self,
        yeni_kayitlar: list[dict],
        meta_ekstra: dict | None = None,
        max_kayit: int = 2000,
    ):
        """
        Yeni kayıtları mevcut listeyle birleştir, tarihe göre sırala, kaydet.

        max_kayit: JSON'un sınırsız büyümesini önler (en yeni N kayıt korunur).
        """
        birlesik = yeni_kayitlar + self._mevcut  # yeniler öne
        # Tarihe göre sırala (varsa)
        birlesik.sort(
            key=lambda x: x.get("tarih", x.get("date", "")),
            reverse=True
        )
        # Boyut sınırı
        if len(birlesik) > max_kayit:
            print(f"⚠  {len(birlesik)} kayıt → max {max_kayit}'e kırpıldı")
            birlesik = birlesik[:max_kayit]

        meta = {
            "toplam": len(birlesik),
            "yeni_eklenen": len(yeni_kayitlar),
            "guncelleme": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if meta_ekstra:
            meta.update(meta_ekstra)

        cikti = {"meta": meta, "haberler": birlesik}

        with open(self.dosya, "w", encoding="utf-8") as f:
            json.dump(cikti, f, ensure_ascii=False, indent=2)

        print(f"✅ {self.dosya} kaydedildi: {len(birlesik)} kayıt ({len(yeni_kayitlar)} yeni)")
        return cikti


# ──────────────────────────────────────────────
# 3. GeoJSON → haber listesi dönüştürücü
# ──────────────────────────────────────────────

def geojson_url_den_haberler(url: str, session=None) -> list[dict]:
    """
    Harita GeoJSON URL'sinden kayıtları çekip haber formatına dönüştürür.
    Zaten haberler.json'da olanlar HaberDedup.filtrele() ile elenecek.
    """
    import requests
    try:
        r = (session or requests).get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"⚠  GeoJSON çekilemedi ({url}): {e}")
        return []

    featureler = data if isinstance(data, list) else data.get("features", [])
    haberler = []
    for f in featureler:
        p = f.get("properties", {})
        koord = f.get("geometry", {}).get("coordinates", [])
        h = {
            "_kaynak_tip": "geojson",
            "baslik":  p.get("isim") or p.get("name") or p.get("baslik") or "—",
            "tarih":   p.get("tarih") or p.get("date") or "",
            "kaynak":  p.get("kaynak") or p.get("source") or "harita",
            "url":     p.get("url") or p.get("link") or "",
            "kategori":p.get("kategori") or p.get("category") or "",
            "koordinat": {"lon": koord[0], "lat": koord[1]} if len(koord) >= 2 else {},
            "orijinal_properties": p,
        }
        haberler.append(h)

    print(f"✓ GeoJSON'dan {len(haberler)} kayıt çekildi: {url}")
    return haberler
