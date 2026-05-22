#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Haber Tarayıcı v3
DÜZELTME: harita_verisi_cek() tamamen silindi, feedparser eklendi, atomic write
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
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

# ─── YAPILANDIRMA ──────────────────────────────────────────────────

RSS_KAYNAKLARI = [
    # ── Çevre odaklı medya ─────────────────────────────────────────
    {"url": "https://bianet.org/topic/cevre/feed/rss",          "kaynak": "Bianet",       "kategori": "Çevre İhlali", "genel": False},
    {"url": "https://iklimhaber.org/feed/",                      "kaynak": "İklim Haber",  "kategori": "İklim",        "genel": False},
    {"url": "https://yesilgazete.org/feed/",                     "kaynak": "Yeşil Gazete", "kategori": "Çevre Medyası","genel": False},
    {"url": "https://www.evrensel.net/rss/ekoloji.xml",          "kaynak": "Evrensel",     "kategori": "Ekoloji",      "genel": False},
    {"url": "https://www.birgun.net/xml/rss.xml",                "kaynak": "Birgün",       "kategori": "Haber",        "genel": True},

    # ── STK & Kampanya ─────────────────────────────────────────────
    {"url": "https://www.tema.org.tr/duyurular?format=feed",     "kaynak": "TEMA",         "kategori": "STK",          "genel": False},
    {"url": "https://www.greenpeace.org/turkey/feed/",           "kaynak": "Greenpeace TR","kategori": "STK",          "genel": False},

    # ── Resmi Gazete & İhale izleme ────────────────────────────────
    {"url": "https://news.google.com/rss/search?q=site:resmigazete.gov.tr+%22kamula%C5%9Ft%C4%B1rma%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Resmi Gazete", "kategori": "Kamulaştırma", "genel": False},
    {"url": "https://news.google.com/rss/search?q=site:resmigazete.gov.tr+%22maden%22+OR+%22ihale%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Resmi Gazete", "kategori": "Resmi İhale / Maden", "genel": False},
    {"url": "https://news.google.com/rss/search?q=site:ilan.gov.tr+%22maden%22+OR+%22enerji%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "İlan Portalı", "kategori": "İhale / Enerji", "genel": False},

    # ── Site-özel Google News filtreleri ───────────────────────────
    {"url": "https://news.google.com/rss/search?q=site:gazetepencere.com+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22%C3%87ED%22+OR+%22iklim%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Gazete Pencere", "kategori": "Çevre / Gündem", "genel": False},
    {"url": "https://news.google.com/rss/search?q=site:t24.com.tr+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22kamula%C5%9Ft%C4%B1rma%22+OR+%22%C3%87ED%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "T24", "kategori": "Gündem / Çevre", "genel": False},
    {"url": "https://news.google.com/rss/search?q=site:diken.com.tr+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22%C3%87ED%22+OR+%22do%C4%9Fa%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Diken", "kategori": "Gündem / Çevre", "genel": False},
    {"url": "https://news.google.com/rss/search?q=site:artigercek.com+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22kamula%C5%9Ft%C4%B1rma%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Artı Gerçek", "kategori": "Gündem / Ekoloji", "genel": False},

    # ── Konu & bölge odaklı sorgular ───────────────────────────────
    {"url": "https://news.google.com/rss/search?q=çevre+ihlali+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Çevre İhlali", "genel": False},
    {"url": "https://news.google.com/rss/search?q=orman+tahribi+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Orman / Maden", "genel": False},
    {"url": "https://news.google.com/rss/search?q=HES+RES+baraj+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "HES / RES / Baraj", "genel": False},
    {"url": "https://news.google.com/rss/search?q=acele+kamulaştırma+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kamulaştırma", "genel": False},
    {"url": "https://news.google.com/rss/search?q=ÇED+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "ÇED Kararları", "genel": False},
    {"url": "https://news.google.com/rss/search?q=siyanür+atık+barajı+maden&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Maden Riski / Atık", "genel": False},
    {"url": "https://news.google.com/rss/search?q=jeotermal+JES+tarım+aydin+manisa&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "JES / Çevre İhlali", "genel": False},
    {"url": "https://news.google.com/rss/search?q=zeytinlik+maden+projesi+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Tarım Alanları / Maden", "genel": False},

    # ── Genel haber kaynakları (yüksek filtre eşiği) ───────────────
    {"url": "https://www.sozcu.com.tr/rss/cevre.xml",            "kaynak": "Sözcü",        "kategori": "Haber",        "genel": True},
    {"url": "https://www.cumhuriyet.com.tr/rss/cevre.rss",       "kaynak": "Cumhuriyet",   "kategori": "Haber",        "genel": True},
]

WEB_KAYNAKLARI = [
    # ── Çevre medyası ──────────────────────────────────────────────
    {"url": "https://yesilgazete.org",           "kaynak": "Yeşil Gazete",    "kategori": "Çevre Medyası",
     "secici": "article h2 a, .entry-title a",   "ozet_secici": "article .entry-content p", "genel": False},
    {"url": "https://iklimhaber.org",            "kaynak": "İklim Haber",     "kategori": "İklim",
     "secici": "article h2 a, .entry-title a",   "ozet_secici": "article p",  "genel": False},
    {"url": "https://www.gazeteduvar.com.tr/ekoloji", "kaynak": "Gazete Duvar", "kategori": "Ekoloji",
     "secici": ".row a, h2 a, .news-box a",      "ozet_secici": ".lead, p",   "genel": False},
    {"url": "https://medyascope.tv/category/cevre-ekoloji/", "kaynak": "Medyascope", "kategori": "Ekoloji",
     "secici": ".entry-title a, h3 a",           "ozet_secici": ".entry-summary p", "genel": False},
    {"url": "https://magmadergisi.com",          "kaynak": "Magma Dergisi",   "kategori": "Çevre Medyası",
     "secici": ".card-title a, h3 a",            "ozet_secici": ".card-text, .excerpt", "genel": False},

    # ── STK & Sivil toplum ─────────────────────────────────────────
    {"url": "https://www.greenpeace.org/turkey/blog/", "kaynak": "Greenpeace TR", "kategori": "STK",
     "secici": ".post-title a, h2 a",            "ozet_secici": ".post-excerpt p", "genel": False},
    {"url": "https://ekolojibirligi.org",        "kaynak": "Ekoloji Birliği", "kategori": "STK / Yerel Basın",
     "secici": ".post-title a, h2.entry-title a","ozet_secici": ".entry-summary p, .post-content p", "genel": False},
    {"url": "https://kuzeyormanlari.org",        "kaynak": "Kuzey Ormanları", "kategori": "STK / Orman",
     "secici": "h2.entry-title a, article a",   "ozet_secici": ".entry-content p", "genel": False},
    {"url": "https://politeknik.org.tr",         "kaynak": "Politeknik",      "kategori": "Mühendislik / Çevre",
     "secici": ".post-title a, h3.post-title a", "ozet_secici": ".post-excerpt", "genel": False},

    # ── Resmi kurumlar ─────────────────────────────────────────────
    {"url": "https://www.csb.gov.tr/duyurular",  "kaynak": "Çevre Bakanlığı", "kategori": "Resmi",
     "secici": ".duyuru-item a, h3 a",           "ozet_secici": ".duyuru-ozet", "genel": False},
    {"url": "https://www.resmigazete.gov.tr",    "kaynak": "Resmi Gazete",    "kategori": "Resmi",
     "secici": ".gazete-baslik a, #content a",   "ozet_secici": ".ozet-metin, p", "genel": False},
    {"url": "https://www.mapeg.gov.tr/Duyurular","kaynak": "MAPEG (Maden)",   "kategori": "Resmi / Maden",
     "secici": ".news-list a, h4 a",             "ozet_secici": ".news-detail, p", "genel": False},
    {"url": "https://www.epdk.gov.tr/Detay/Duyurular", "kaynak": "EPDK (Enerji)", "kategori": "Resmi / Enerji",
     "secici": ".announcement-list a, .title a", "ozet_secici": ".description-text, p", "genel": False},
    {"url": "https://www.ilan.gov.tr",           "kaynak": "İlan Portalı",    "kategori": "İhale",
     "secici": ".ng-item-title a, .ad-card-title","ozet_secici": ".ad-card-description, p", "genel": False},

    # ── Genel haber portalleri (yüksek filtre eşiği) ───────────────
    {"url": "https://tr.euronews.com/tag/cevre", "kaynak": "Euronews TR",     "kategori": "Haber",
     "secici": ".article__title a, h3.article__title a", "ozet_secici": ".article__summary", "genel": True},
    {"url": "https://www.gazetepencere.com",     "kaynak": "Gazete Pencere",  "kategori": "Haber",
     "secici": ".news-title a, h3 a, .card-title a", "ozet_secici": ".news-excerpt, p", "genel": True},
    {"url": "https://t24.com.tr",                "kaynak": "T24",             "kategori": "Haber",
     "secici": "h3 a, ._2b_Xq a, ._3W9uR a",   "ozet_secici": "p, ._1pZp3", "genel": True},
    {"url": "https://www.diken.com.tr",          "kaynak": "Diken",           "kategori": "Haber",
     "secici": ".entry-title a, h2 a",           "ozet_secici": ".entry-content p, p", "genel": True},
    {"url": "https://artigercek.com",            "kaynak": "Artı Gerçek",     "kategori": "Haber",
     "secici": ".post-title a, h2 a, h3 a",     "ozet_secici": ".post-excerpt, p", "genel": True},
]

# ─── FİLTRE SİSTEMİ ────────────────────────────────────────────────

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

ORTA_SINYAL = [
    "çevre", "ekoloji", "orman", "maden", "baraj", "HES", "RES", "GES",
    "kamulaştırma", "doğa", "habitat", "kirlilik", "atık", "iklim",
    "yangın", "sel", "taşkın", "heyelan", "kıyı", "deniz", "göl", "dere",
    "su hakkı", "tarım arazisi", "bor", "altın maden", "jeotermal",
    "ihlal", "ruhsatsız", "izinsiz", "yıkım", "ağaç", "sera gazı",
    "plastik kirlilik", "sondaj", "arama ruhsatı", "TEMA", "WWF", "Greenpeace",
    "doğal yaşam", "yaban hayat", "kuş türü", "balık türü",
]

GUCLU_NEGATIF = [
    "faiz", "borsa", "döviz", "kur", "enflasyon", "bütçe açığı",
    "seçim", "cumhurbaşkanı", "milletvekili", "muhalefet", "iktidar partisi",
    "futbol", "maç sonucu", "şampiyon", "transfer", "gol", "penaltı",
    "dizi", "film", "oyuncu", "magazin", "ünlü çift", "nişan", "düğün",
    "moda", "defilé", "koleksiyon",
    "kripto", "bitcoin", "nft", "borsa rallisi",
    "müzik listesi", "konser", "albüm",
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


def fetch(url: str, timeout: int = 15) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r
    except Exception as e:
        log.warning(f"Fetch başarısız [{url[:60]}]: {e}")
        return None


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

def tara(cikti_dosyasi="haberler.json", max_haber=500):
    log.info("═" * 55)
    log.info("  ekoloji-izleme.com — Haber Tarayıcı v3")
    log.info("═" * 55)

    p = Path(cikti_dosyasi)
    gorulen_idler: set = set()
    gorulen_basliklar: set = set()
    eski_haberler: list = []

    if p.exists():
        try:
            eski = json.loads(p.read_text(encoding="utf-8"))
            eski_haberler = eski.get("haberler", [])
            gorulen_idler = {h.get("id", "") for h in eski_haberler}
            gorulen_basliklar = {
                re.sub(r"\s+", " ", h.get("baslik", "")).strip().lower()
                for h in eski_haberler if h.get("baslik")
            }
            log.info(f"Mevcut dosyada {len(gorulen_idler)} haber.")
        except json.JSONDecodeError as e:
            log.warning(f"Mevcut haberler.json bozuk (char {e.pos}), sıfırdan başlanıyor.")
        except Exception as e:
            log.warning(f"Mevcut haberler.json okunamadı: {e}, sıfırdan başlanıyor.")

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

    birlesik = tum_yeni + eski_haberler
    birlesik.sort(key=lambda x: x.get("tarih") or "1970-01-01", reverse=True)
    birlesik = birlesik[:max_haber]

    cikti = {
        "meta": {
            "guncelleme":  datetime.now(timezone.utc).isoformat(),
            "toplam":      len(birlesik),
            "yeni_eklenen": len(tum_yeni),
        },
        "haberler": birlesik,
    }

    # ── Atomic write: önce .tmp yaz, sonra taşı (yarım yazma önlemi) ──
    json_str = json.dumps(cikti, ensure_ascii=False, indent=2)

    # JSON geçerliliğini kontrol et (yazılmadan önce)
    try:
        json.loads(json_str)
    except json.JSONDecodeError as e:
        log.error(f"❌ Üretilen JSON geçersiz: {e}. Yazılmıyor.")
        return cikti

    tmp = p.with_suffix(".tmp")
    tmp.write_text(json_str, encoding="utf-8")
    tmp.replace(p)  # atomic rename

    log.info(f"\n✓ {cikti_dosyasi} → {len(birlesik)} haber ({len(tum_yeni)} yeni)")
    return cikti


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cikti", default="haberler.json")
    parser.add_argument("--max-haber", type=int, default=500)
    parser.add_argument("--surekli", action="store_true")
    parser.add_argument("--aralik", type=int, default=180)
    args = parser.parse_args()

    if args.surekli:
        while True:
            try:
                tara(args.cikti, args.max_haber)
            except KeyboardInterrupt:
                sys.exit(0)
            except Exception as e:
                log.error(f"Tarama hatası: {e}")
            time.sleep(args.aralik * 60)
    else:
        tara(args.cikti, args.max_haber)


if __name__ == "__main__":
    main()
