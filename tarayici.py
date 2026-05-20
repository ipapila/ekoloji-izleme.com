#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Haber Tarayıcı (v4 — genişletilmiş kaynaklar)
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

# ─── RSS KAYNAKLARI ─────────────────────────────────────────────────
# genel=False → eşik 1 puan  (zaten filtreli kaynak)
# genel=True  → eşik 4 puan  (genel haber kaynağı, sıkı filtre)

RSS_KAYNAKLARI = [

    # ── Çevre / Ekoloji odaklı ──────────────────────────────────────
    {"url": "https://bianet.org/topic/cevre/feed/rss",
     "kaynak": "Bianet Çevre",         "kategori": "Çevre İhlali",   "genel": False},

    {"url": "https://iklimhaber.org/feed/",
     "kaynak": "İklim Haber",           "kategori": "İklim",           "genel": False},

    {"url": "https://yesilgazete.org/feed/",
     "kaynak": "Yeşil Gazete",          "kategori": "Çevre Medyası",   "genel": False},

    {"url": "https://www.ekoiq.com/feed/",
     "kaynak": "Ekoiq",                 "kategori": "Sürdürülebilirlik","genel": False},

    # ── STK / Sivil toplum ──────────────────────────────────────────
    {"url": "https://www.tema.org.tr/duyurular?format=feed",
     "kaynak": "TEMA",                  "kategori": "STK",             "genel": False},

    {"url": "https://www.greenpeace.org/turkey/feed/",
     "kaynak": "Greenpeace TR",         "kategori": "STK",             "genel": False},

    {"url": "https://dogadernegi.org/feed/",
     "kaynak": "Doğa Derneği",          "kategori": "STK",             "genel": False},

    {"url": "https://wwf.org.tr/feed/",
     "kaynak": "WWF Türkiye",           "kategori": "STK",             "genel": False},

    # ── Enerji ──────────────────────────────────────────────────────
    {"url": "https://www.enerjiatlasi.com/rss/haberler.xml",
     "kaynak": "Enerji Atlası",         "kategori": "Enerji",          "genel": False},

    {"url": "https://enerjigunlugu.net/feed/",
     "kaynak": "Enerji Günlüğü",        "kategori": "Enerji",          "genel": False},

    {"url": "https://www.pvtech.org/feed/",          # güneş/yenilenebilir
     "kaynak": "PV Tech",               "kategori": "Güneş Enerjisi",  "genel": False},

    # ── Bağımsız / eleştirel medya ──────────────────────────────────
    {"url": "https://www.gazeteduvar.com.tr/feed/",
     "kaynak": "Gazete Duvar",          "kategori": "Haber",           "genel": True},

    {"url": "https://medyascope.tv/feed/",
     "kaynak": "Medyascope",            "kategori": "Haber",           "genel": True},

    {"url": "https://artigercek.com/feed/",
     "kaynak": "Artı Gerçek",           "kategori": "Haber",           "genel": True},

    {"url": "https://bianet.org/bianet/feed/rss",    # genel Bianet (çevre dışı da var)
     "kaynak": "Bianet Genel",          "kategori": "Haber",           "genel": True},

    # ── Uluslararası Türkçe ─────────────────────────────────────────
    {"url": "https://rss.dw.com/rdf/rss-tur-all",
     "kaynak": "DW Türkçe",             "kategori": "Haber",           "genel": True},

    {"url": "https://feeds.bbci.co.uk/turkish/rss.xml",
     "kaynak": "BBC Türkçe",            "kategori": "Haber",           "genel": True},

    {"url": "https://tr.euronews.com/rss",
     "kaynak": "Euronews TR",           "kategori": "Haber",           "genel": True},

    # ── Türk ana medyası (çevre filtreyle) ──────────────────────────
    {"url": "https://www.cumhuriyet.com.tr/rss/cevre.rss",
     "kaynak": "Cumhuriyet Çevre",      "kategori": "Haber",           "genel": False},

    {"url": "https://www.sozcu.com.tr/rss/cevre.xml",
     "kaynak": "Sözcü Çevre",           "kategori": "Haber",           "genel": True},

    {"url": "https://www.ntv.com.tr/rss/haberleri",
     "kaynak": "NTV",                   "kategori": "Haber",           "genel": True},

    {"url": "https://www.haberturk.com/rss",
     "kaynak": "Habertürk",             "kategori": "Haber",           "genel": True},

    # ── Resmi kaynaklar ─────────────────────────────────────────────
    {"url": "https://www.resmigazete.gov.tr/rss/main.xml",
     "kaynak": "Resmî Gazete",          "kategori": "Resmi",           "genel": False},

    {"url": "https://www.csb.gov.tr/rss/haberler.xml",
     "kaynak": "Çevre Bakanlığı",       "kategori": "Resmi",           "genel": False},

    # ── Anadolu Ajansı ──────────────────────────────────────────────
    {"url": "https://www.aa.com.tr/tr/rss/default?cat=cevre",
     "kaynak": "AA Çevre",              "kategori": "Haber",           "genel": False},

    {"url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
     "kaynak": "AA Ekonomi",            "kategori": "Enerji",          "genel": True},
]

# ─── WEB SCRAPING KAYNAKLARI ────────────────────────────────────────

WEB_KAYNAKLARI = [
    {"url": "https://yesilgazete.org",
     "kaynak": "Yeşil Gazete",     "kategori": "Çevre Medyası",
     "secici": "article h2 a, .entry-title a",
     "ozet_secici": "article .entry-content p",     "genel": False},

    {"url": "https://iklimhaber.org",
     "kaynak": "İklim Haber",      "kategori": "İklim",
     "secici": "article h2 a, .entry-title a",
     "ozet_secici": "article p",                    "genel": False},

    {"url": "https://www.greenpeace.org/turkey/blog/",
     "kaynak": "Greenpeace TR",    "kategori": "STK",
     "secici": ".post-title a, h2 a",
     "ozet_secici": ".post-excerpt p",              "genel": False},

    {"url": "https://www.csb.gov.tr/duyurular",
     "kaynak": "Çevre Bakanlığı",  "kategori": "Resmi",
     "secici": ".duyuru-item a, h3 a",
     "ozet_secici": ".duyuru-ozet",                 "genel": False},

    {"url": "https://www.enerjiatlasi.com/haberler/",
     "kaynak": "Enerji Atlası",    "kategori": "Enerji",
     "secici": "h2 a, h3 a, .haber-baslik a",
     "ozet_secici": ".ozet, p",                     "genel": False},

    {"url": "https://ekolojik.net",
     "kaynak": "Ekolojik",         "kategori": "Çevre Medyası",
     "secici": "article h2 a, .entry-title a",
     "ozet_secici": "article p",                    "genel": False},

    {"url": "https://www.kib.org.tr/haberler",      # Kamu İhale ilanları
     "kaynak": "KİK",              "kategori": "İhale",
     "secici": ".haber-baslik a, h3 a, td a",
     "ozet_secici": ".ozet",                        "genel": False},

    {"url": "https://mapeg.gov.tr/haberler.aspx",   # Maden ve Petrol işleri
     "kaynak": "MAPEG",            "kategori": "Maden",
     "secici": ".haber a, h3 a, .news-title a",
     "ozet_secici": ".haber-ozet, p",               "genel": False},
]

# ─── FİLTRE SİSTEMİ ─────────────────────────────────────────────────

YUKSEK_SINYAL = [
    "çevre ihlali", "çevre katliamı", "ÇED", "çed kararı", "çed raporu",
    "acele kamulaştırma", "taş ocağı", "taşocağı", "maden ocağı",
    "HES projesi", "RES projesi", "GES projesi", "termik santral",
    "nükleer santral", "ağaç katliamı", "ormansızlaşma", "orman tahribi",
    "sulak alan", "milli park", "doğal sit", "koruma alanı",
    "nesli tükenmekte", "nesli tehlike", "biyoçeşitlilik kaybı",
    "su kirliliği", "deniz kirliliği", "hava kirliliği", "toprak kirliliği",
    "atık depolama", "düzensiz depolama", "kaçak maden", "kaçak yapı doğa",
    "MAPEG", "EPDK kararı", "resmî gazete çevre", "resmî gazete maden",
    "ormana yapı", "dere yatağı", "dereye yapı", "kıyı tahribatı",
    "arama ruhsatı", "işletme ruhsatı", "maden ruhsatı",
    "yenilenebilir enerji", "fosil yakıt", "karbon emisyon",
    "iklim krizi", "iklim değişikliği", "küresel ısınma",
    "çevre cezası", "çevre denetim", "çed itiraz",
]

ORTA_SINYAL = [
    "çevre", "ekoloji", "orman", "maden", "baraj", "HES", "RES", "GES",
    "kamulaştırma", "doğa", "habitat", "kirlilik", "atık", "iklim",
    "yangın", "sel", "taşkın", "heyelan", "kıyı", "deniz", "göl", "dere",
    "su hakkı", "tarım arazisi", "bor", "altın maden", "jeotermal",
    "ihlal", "ruhsatsız", "izinsiz", "yıkım", "ağaç", "sera gazı",
    "plastik kirlilik", "sondaj", "TEMA", "WWF", "Greenpeace",
    "doğal yaşam", "yaban hayat", "kuş türü", "balık türü",
    "solar", "güneş enerjisi", "rüzgar enerjisi", "enerji santrali",
    "nükleer", "petrol", "doğalgaz", "kömür", "linyit",
    "ihale", "ruhsat", "lisans", "proje onay", "inşaat izni",
    "sit alanı", "flora", "fauna", "ekosistem",
    "karbon", "emisyon", "hava kalitesi", "PM2", "azot dioksit",
]

GUCLU_NEGATIF = [
    "faiz", "borsa", "döviz", "kur", "enflasyon", "bütçe açığı",
    "seçim", "cumhurbaşkanı", "milletvekili", "muhalefet", "iktidar partisi",
    "futbol", "maç sonucu", "şampiyon", "transfer", "gol", "penaltı",
    "dizi", "film", "oyuncu", "magazin", "ünlü çift", "nişan", "düğün",
    "moda", "defilé", "koleksiyon", "kripto", "bitcoin", "nft",
    "müzik listesi", "konser", "albüm",
    "İsrail", "Gazze", "Ukrayna savaşı", "Rusya savaşı",
]

GENEL_KAYNAK_NEGATIF = [
    "ekonomi", "piyasa", "hisse", "yatırım", "ihracat", "ithalat",
    "savunma", "asker", "muharebe", "operasyon",
    "turizm sezonu", "tatil", "otel",
    "sağlık", "hastane", "ameliyat",
    "eğitim", "üniversite sınav", "okul",
]


def ekoloji_puani(baslik: str, ozet: str = "", genel_kaynak: bool = False) -> int:
    metin = (baslik + " " + ozet).lower()
    if any(k.lower() in metin for k in GUCLU_NEGATIF):
        return 0
    if genel_kaynak and any(k.lower() in metin for k in GENEL_KAYNAK_NEGATIF):
        return 0
    puan = 0
    for k in YUKSEK_SINYAL:
        if k.lower() in metin:
            puan += 3
    for k in ORTA_SINYAL:
        if k.lower() in metin:
            puan += 1
    baslik_lower = baslik.lower()
    for k in YUKSEK_SINYAL:
        if k.lower() in baslik_lower:
            puan += 2
    return puan


# ─── YARDIMCI ────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tarayici")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EkolojiIzleme/2.0; +https://ekoloji-izleme.com)",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def haber_id(url: str, baslik: str) -> str:
    return hashlib.md5(f"{url}|{baslik}".encode("utf-8")).hexdigest()[:12]


def tarih_normalize(tarih_str) -> Optional[str]:
    if not tarih_str:
        return None
    try:
        if hasattr(tarih_str, "tm_year"):
            return datetime(*tarih_str[:6], tzinfo=timezone.utc).isoformat()
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(str(tarih_str)).isoformat()
    except Exception:
        return str(tarih_str)


def fetch(url: str, timeout: int = 15) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r
    except Exception as e:
        log.warning(f"Fetch başarısız [{url[:60]}]: {e}")
        return None


# ─── RSS TARAMA ──────────────────────────────────────────────────────

def rss_tara(kaynaklar: list) -> list:
    haberler = []
    basarili = basarisiz = 0
    for kaynak in kaynaklar:
        genel = kaynak.get("genel", False)
        log.info(f"RSS: {kaynak['kaynak']}")
        try:
            feed = feedparser.parse(kaynak["url"])
            if feed.bozo and not feed.entries:
                log.warning(f"  ⚠ Erişilemiyor — atlandı")
                basarisiz += 1
                continue
            kabul = reddedilen = 0
            for entry in feed.entries[:30]:
                baslik = entry.get("title", "").strip()
                link   = entry.get("link", "")
                ozet   = BeautifulSoup(
                    entry.get("summary", ""), "lxml"
                ).get_text(" ", strip=True)
                tarih  = tarih_normalize(
                    entry.get("published_parsed") or entry.get("updated_parsed")
                )
                if not baslik or not link:
                    continue
                puan = ekoloji_puani(baslik, ozet, genel)
                esik = 4 if genel else 1
                if puan < esik:
                    reddedilen += 1
                    continue
                haberler.append({
                    "id":          haber_id(link, baslik),
                    "baslik":      baslik,
                    "ozet":        ozet[:300] if ozet else "",
                    "url":         link,
                    "tarih":       tarih,
                    "kaynak":      kaynak["kaynak"],
                    "kategori":    kaynak["kategori"],
                    "kaynak_turu": "rss",
                    "_puan":       puan,
                })
                kabul += 1
            log.info(f"  → {kabul} kabul / {reddedilen} reddedildi")
            basarili += 1
            time.sleep(0.5)
        except Exception as e:
            log.warning(f"  Hata: {e}")
            basarisiz += 1

    log.info(f"\nRSS özeti: {basarili} kaynak başarılı, {basarisiz} başarısız")
    return haberler


# ─── WEB SCRAPING ────────────────────────────────────────────────────

def web_tara(kaynaklar: list) -> list:
    haberler = []
    for kaynak in kaynaklar:
        genel = kaynak.get("genel", False)
        log.info(f"Web: {kaynak['kaynak']}")
        r = fetch(kaynak["url"])
        if not r:
            continue
        try:
            soup = BeautifulSoup(r.text, "lxml")
            kabul = reddedilen = 0
            for a in soup.select(kaynak["secici"])[:20]:
                baslik = a.get_text(" ", strip=True)
                if not baslik or len(baslik) < 10:
                    continue
                href = a.get("href", "")
                if not href:
                    continue
                link = urljoin(kaynak["url"], href)
                ozet = ""
                if kaynak.get("ozet_secici"):
                    parent = a.find_parent(["article", "div", "li", "tr"])
                    if parent:
                        ozet_el = parent.select_one(kaynak["ozet_secici"])
                        if ozet_el:
                            ozet = ozet_el.get_text(" ", strip=True)[:300]
                puan = ekoloji_puani(baslik, ozet, genel)
                esik = 4 if genel else 1
                if puan < esik:
                    reddedilen += 1
                    continue
                haberler.append({
                    "id":          haber_id(link, baslik),
                    "baslik":      baslik,
                    "ozet":        ozet,
                    "url":         link,
                    "tarih":       datetime.now(timezone.utc).isoformat(),
                    "kaynak":      kaynak["kaynak"],
                    "kategori":    kaynak["kategori"],
                    "kaynak_turu": "web",
                    "_puan":       puan,
                })
                kabul += 1
            log.info(f"  → {kabul} kabul / {reddedilen} reddedildi")
        except Exception as e:
            log.warning(f"  Scrape hatası: {e}")
        time.sleep(1.0)
    return haberler


# ─── ANA FONKSİYON ───────────────────────────────────────────────────

def tara(cikti_dosyasi="haberler.json", max_haber=500):
    log.info("═" * 55)
    log.info("  ekoloji-izleme.com — Haber Tarayıcı v4")
    log.info("═" * 55)

    p = Path(cikti_dosyasi)
    if p.exists():
        try:
            eski = json.loads(p.read_text(encoding="utf-8"))
            mevcut_haberler = eski.get("haberler", [])
            gorulen_idler   = {h.get("id", "") for h in mevcut_haberler}
            log.info(f"Mevcut: {len(mevcut_haberler)} haber")
        except Exception:
            mevcut_haberler, gorulen_idler = [], set()
    else:
        mevcut_haberler, gorulen_idler = [], set()

    log.info("\n── RSS Kaynakları ──")
    rss_haberler = rss_tara(RSS_KAYNAKLARI)

    log.info("\n── Web Scraping ──")
    web_haberler = web_tara(WEB_KAYNAKLARI)

    # Dedup
    tum_yeni = []
    for h in rss_haberler + web_haberler:
        if h["id"] not in gorulen_idler:
            h.pop("_puan", None)
            tum_yeni.append(h)
            gorulen_idler.add(h["id"])

    birlesik = tum_yeni + mevcut_haberler
    birlesik.sort(key=lambda x: x.get("tarih") or "1970-01-01", reverse=True)
    birlesik = birlesik[:max_haber]

    cikti = {
        "meta": {
            "guncelleme":   datetime.now(timezone.utc).isoformat(),
            "toplam":       len(birlesik),
            "yeni_eklenen": len(tum_yeni),
        },
        "haberler": birlesik,
    }

    Path(cikti_dosyasi).write_text(
        json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"\n✅ {cikti_dosyasi} → {len(birlesik)} haber ({len(tum_yeni)} yeni)")
    return cikti


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cikti", default="haberler.json")
    parser.add_argument("--harita-url", action="append", dest="harita_urls")  # geriye dönük uyumluluk
    parser.add_argument("--ozet-cek", action="store_true")
    parser.add_argument("--surekli", action="store_true")
    parser.add_argument("--aralik", type=int, default=180)
    args = parser.parse_args()

    if args.surekli:
        while True:
            try:
                tara(args.cikti)
            except KeyboardInterrupt:
                sys.exit(0)
            except Exception as e:
                log.error(f"Tarama hatası: {e}")
            time.sleep(args.aralik * 60)
    else:
        tara(args.cikti)

if __name__ == "__main__":
    main()
