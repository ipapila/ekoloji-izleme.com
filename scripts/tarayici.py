#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Haber Tarayıcı (v2 — hassas filtre)
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

# ─── YAPILANDIRMA ──────────────────────────────────────────────────

HARITA_URLS = [
    "https://ekoloji-izleme.com/harita/data.json",
    "https://ekoloji-izleme.com/harita/ihlaller.json",
    "https://ipapila.github.io/Turkiye-katmanlar/data/ihlaller.json",
]

RSS_KAYNAKLARI = [
    # Çevre odaklı kaynaklar — zaten filtrelenmiş, düşük eşik
    {"url": "https://bianet.org/topic/cevre/feed/rss",          "kaynak": "Bianet",       "kategori": "Çevre İhlali", "genel": False},
    {"url": "https://iklimhaber.org/feed/",                      "kaynak": "İklim Haber",  "kategori": "İklim",        "genel": False},
    {"url": "https://yesilgazete.org/feed/",                     "kaynak": "Yeşil Gazete", "kategori": "Çevre Medyası","genel": False},
    {"url": "https://www.tema.org.tr/duyurular?format=feed",     "kaynak": "TEMA",         "kategori": "STK",          "genel": False},
    {"url": "https://www.greenpeace.org/turkey/feed/",           "kaynak": "Greenpeace TR","kategori": "STK",          "genel": False},
    # Google News — konu odaklı sorgular
    {"url": "https://news.google.com/rss/search?q=çevre+ihlali+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Çevre İhlali", "genel": False},
    {"url": "https://news.google.com/rss/search?q=orman+tahribi+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Orman / Maden", "genel": False},
    {"url": "https://news.google.com/rss/search?q=HES+RES+baraj+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "HES / RES / Baraj", "genel": False},
    {"url": "https://news.google.com/rss/search?q=acele+kamulaştırma+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kamulaştırma", "genel": False},
    {"url": "https://news.google.com/rss/search?q=ÇED+maden+Türkiye+2025&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "ÇED Kararları", "genel": False},
    # Genel haberler — yüksek eşik uygulanır
    {"url": "https://www.sozcu.com.tr/rss/cevre.xml",            "kaynak": "Sözcü",        "kategori": "Haber",        "genel": True},
    {"url": "https://www.cumhuriyet.com.tr/rss/cevre.rss",       "kaynak": "Cumhuriyet",   "kategori": "Haber",        "genel": True},
]

WEB_KAYNAKLARI = [
    {"url": "https://yesilgazete.org",           "kaynak": "Yeşil Gazete", "kategori": "Çevre Medyası",
     "secici": "article h2 a, .entry-title a",   "ozet_secici": "article .entry-content p", "genel": False},
    {"url": "https://iklimhaber.org",            "kaynak": "İklim Haber",  "kategori": "İklim",
     "secici": "article h2 a, .entry-title a",   "ozet_secici": "article p",                "genel": False},
    {"url": "https://www.greenpeace.org/turkey/blog/", "kaynak": "Greenpeace TR", "kategori": "STK",
     "secici": ".post-title a, h2 a",            "ozet_secici": ".post-excerpt p",           "genel": False},
    {"url": "https://tr.euronews.com/tag/cevre", "kaynak": "Euronews TR",  "kategori": "Haber",
     "secici": ".article__title a, h3.article__title a", "ozet_secici": ".article__summary", "genel": True},
    {"url": "https://www.csb.gov.tr/duyurular",  "kaynak": "Çevre Bakanlığı", "kategori": "Resmi",
     "secici": ".duyuru-item a, h3 a",           "ozet_secici": ".duyuru-ozet",              "genel": False},
]

# ─── FİLTRE SİSTEMİ ────────────────────────────────────────────────

# Tek başına yeterli — kesinlikle ekoloji haberi
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
]

# Bağlam gerektiren — birden fazlası veya yüksek sinyalle birlikte
ORTA_SINYAL = [
    "çevre", "ekoloji", "orman", "maden", "baraj", "HES", "RES", "GES",
    "kamulaştırma", "doğa", "habitat", "kirlilik", "atık", "iklim",
    "yangın", "sel", "taşkın", "heyelan", "kıyı", "deniz", "göl", "dere",
    "su hakkı", "tarım arazisi", "bor", "altın maden", "jeotermal",
    "ihlal", "ruhsatsız", "izinsiz", "yıkım", "ağaç", "sera gazı",
    "plastik kirlilik", "sondaj", "arama ruhsatı", "TEMA", "WWF", "Greenpeace",
    "doğal yaşam", "yaban hayat", "kuş türü", "balık türü",
]

# Bunlar varsa — ne kadar çevre kelimesi geçerse geçsin reddet
GUCLU_NEGATIF = [
    "faiz", "borsa", "döviz", "kur", "enflasyon", "bütçe açığı",
    "seçim", "cumhurbaşkanı", "milletvekili", "muhalefet", "iktidar partisi",
    "futbol", "maç sonucu", "şampiyon", "transfer", "gol", "penaltı",
    "dizi", "film", "oyuncu", "magazin", "ünlü çift", "nişan", "düğün",
    "moda", "defilé", "koleksiyon",
    "kripto", "bitcoin", "nft", "borsa rallisi",
    "müzik listesi", "konser", "albüm",
    "İsrail", "Gazze", "Ukrayna savaşı", "Rusya savaşı",  # uluslararası siyaset
]

# Genel kaynaklara ek negatif — bağlam dışı tek kelime kullanımları
GENEL_KAYNAK_NEGATIF = [
    "ekonomi", "piyasa", "hisse", "yatırım", "ihracat", "ithalat",
    "savunma", "asker", "muharebe", "operasyon",
    "turizm sezonu", "tatil", "otel",
    "sağlık", "hastane", "ameliyat",  # tıbbi haberler
    "eğitim", "üniversite sınav", "okul",
]


def ekoloji_puani(baslik: str, ozet: str = "", genel_kaynak: bool = False) -> int:
    """
    Haberin ekoloji puanını hesapla.
    0  → ilgisiz
    1+ → ekoloji ile ilgili (eşik: genel kaynak=3, odaklı kaynak=1)
    """
    metin = (baslik + " " + ozet).lower()

    # Güçlü negatif → anında 0
    if any(k.lower() in metin for k in GUCLU_NEGATIF):
        return 0

    # Genel kaynak için ek negatif
    if genel_kaynak and any(k.lower() in metin for k in GENEL_KAYNAK_NEGATIF):
        return 0

    puan = 0

    # Yüksek sinyal: +3 her biri
    for k in YUKSEK_SINYAL:
        if k.lower() in metin:
            puan += 3

    # Orta sinyal: +1 her biri
    for k in ORTA_SINYAL:
        if k.lower() in metin:
            puan += 1

    # Başlıkta geçen yüksek sinyal ekstra +2
    baslik_lower = baslik.lower()
    for k in YUKSEK_SINYAL:
        if k.lower() in baslik_lower:
            puan += 2

    return puan


def cevre_ile_ilgili(baslik: str, ozet: str = "", genel_kaynak: bool = False) -> bool:
    """
    Eşik:
    - Odaklı çevre kaynağı (genel=False): puan >= 1
    - Genel haber kaynağı  (genel=True):  puan >= 4
    """
    puan = ekoloji_puani(baslik, ozet, genel_kaynak)
    esik = 4 if genel_kaynak else 1
    return puan >= esik


# ─── YARDIMCI FONKSİYONLAR ─────────────────────────────────────────

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


def fetch(url: str, timeout: int = 12) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r
    except Exception as e:
        log.warning(f"Fetch başarısız [{url[:60]}]: {e}")
        return None


# ─── HARITA VERİSİ ─────────────────────────────────────────────────

def harita_verisi_cek(urls: list) -> list:
    kayitlar = []
    for url in urls:
        log.info(f"Harita verisi: {url}")
        r = fetch(url)
        if not r:
            continue
        try:
            data = r.json()
            items = (data if isinstance(data, list) else
                     data.get("features") or data.get("ihlaller") or
                     data.get("data") or data.get("items") or [])
            for item in items:
                if item.get("type") == "Feature":
                    props = item.get("properties", {})
                    coords = item.get("geometry", {}).get("coordinates", [])
                    item = {**props}
                    if coords and len(coords) >= 2:
                        item["lng"], item["lat"] = coords[0], coords[1]
                kayit = {
                    "id": item.get("id") or haber_id(url, item.get("baslik", "")),
                    "baslik": item.get("baslik") or item.get("name") or item.get("title", ""),
                    "konum": item.get("konum") or item.get("il") or "",
                    "kategori": item.get("kategori") or item.get("alan_turu") or "",
                    "siddet": item.get("siddet") or "takipte",
                    "tarih": tarih_normalize(item.get("tarih") or item.get("date")),
                    "url": item.get("url") or item.get("kaynak_url") or "",
                    "ozet": item.get("aciklama") or item.get("ozet") or "",
                    "lat": item.get("lat") or item.get("enlem"),
                    "lng": item.get("lng") or item.get("boylam"),
                    "kaynak": "harita",
                }
                if kayit["baslik"]:
                    kayitlar.append(kayit)
            log.info(f"  → {len(items)} kayıt")
        except Exception as e:
            log.warning(f"  JSON parse hatası: {e}")
    return kayitlar


# ─── RSS TARAMA ────────────────────────────────────────────────────

def rss_tara(kaynaklar: list) -> list:
    haberler = []
    for kaynak in kaynaklar:
        genel = kaynak.get("genel", False)
        log.info(f"RSS: {kaynak['kaynak']} [genel={genel}]")
        try:
            feed = feedparser.parse(kaynak["url"])
            if feed.bozo and not feed.entries:
                continue
            kabul = reddedilen = 0
            for entry in feed.entries[:25]:
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
                    log.debug(f"  ✗ [{puan:2d}] {baslik[:60]}")
                    continue

                log.debug(f"  ✓ [{puan:2d}] {baslik[:60]}")
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
            time.sleep(0.8)
        except Exception as e:
            log.warning(f"  RSS hatası: {e}")
    return haberler


# ─── WEB SCRAPING ──────────────────────────────────────────────────

def web_tara(kaynaklar: list) -> list:
    haberler = []
    for kaynak in kaynaklar:
        genel = kaynak.get("genel", False)
        log.info(f"Web: {kaynak['kaynak']} [genel={genel}]")
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
                    parent = a.find_parent(["article", "div", "li"])
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
        time.sleep(1.2)
    return haberler


# ─── ANA FONKSİYON ─────────────────────────────────────────────────

def tara(cikti_dosyasi="haberler.json", harita_urls=None,
         ozet_cek_aktif=False, max_haber=200):
    log.info("═" * 55)
    log.info("  ekoloji-izleme.com — Haber Tarayıcı v2")
    log.info("═" * 55)

    p = Path(cikti_dosyasi)
    if p.exists():
        try:
            eski = json.loads(p.read_text(encoding="utf-8"))
            gorulen_idler = {h.get("id", "") for h in eski.get("haberler", [])}
            # Başlık bazlı ek dedup (Google News URL'leri değişse de yakalanır)
            gorulen_basliklar = {
                re.sub(r"\s+", " ", h.get("baslik", "")).strip().lower()
                for h in eski.get("haberler", []) if h.get("baslik")
            }
            log.info(f"Mevcut dosyada {len(gorulen_idler)} haber.")
        except Exception:
            eski, gorulen_idler, gorulen_basliklar = {"haberler": []}, set(), set()
    else:
        eski, gorulen_idler, gorulen_basliklar = {"haberler": []}, set(), set()

    # Harita verisi çekme KALDIRILDI — eski veriler yeterli,
    # tekrar çekmenin anlamı yok ve haberler listesini kirletiyor.

    log.info("\n── RSS Kaynakları ──")
    rss_haberler = rss_tara(RSS_KAYNAKLARI)

    log.info("\n── Web Scraping ──")
    web_haberler = web_tara(WEB_KAYNAKLARI)

    tum_yeni = []
    for h in rss_haberler + web_haberler:
        baslik_norm = re.sub(r"\s+", " ", h.get("baslik", "")).strip().lower()
        if h["id"] not in gorulen_idler and baslik_norm not in gorulen_basliklar:
            tum_yeni.append(h)
            gorulen_idler.add(h["id"])
            if baslik_norm:
                gorulen_basliklar.add(baslik_norm)

    for h in tum_yeni:
        h.pop("_puan", None)

    birlesik = tum_yeni + eski.get("haberler", [])
    birlesik.sort(key=lambda x: x.get("tarih") or "1970-01-01", reverse=True)
    birlesik = birlesik[:max_haber]

    cikti = {
        "meta": {
            "guncelleme": datetime.now(timezone.utc).isoformat(),
            "toplam": len(birlesik),
            "yeni_eklenen": len(tum_yeni),
        },
        "haberler": birlesik,
    }

    Path(cikti_dosyasi).write_text(
        json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"\n✓ {cikti_dosyasi} → {len(birlesik)} haber ({len(tum_yeni)} yeni)")
    return cikti


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cikti", default="haberler.json")
    parser.add_argument("--harita-url", action="append", dest="harita_urls")
    parser.add_argument("--ozet-cek", action="store_true")
    parser.add_argument("--surekli", action="store_true")
    parser.add_argument("--aralik", type=int, default=180)
    args = parser.parse_args()

    if args.surekli:
        while True:
            try:
                tara(args.cikti, args.harita_urls, args.ozet_cek)
            except KeyboardInterrupt:
                sys.exit(0)
            except Exception as e:
                log.error(f"Tarama hatası: {e}")
            time.sleep(args.aralik * 60)
    else:
        tara(args.cikti, args.harita_urls, args.ozet_cek)

if __name__ == "__main__":
    main()
