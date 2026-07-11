#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Haber Tarayıcı v4
v4 YENİLİKLERİ:
  - 4 koleksiyon: haberler | raporlar | makaleler | uluslararasi
  - Her kaynak `hedef` alanıyla yönlendirilir
  - `icerik_tipi` ve `dil` alanları eklendi
  - SSL hataları otomatik aşılır (verify=False fallback)
  - `haber_kategorisi` alanı: 9 görüntü kategorisinden birini atar
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import time
import urllib3
from datetime import datetime, timezone, timedelta
TR_TZ = timezone(timedelta(hours=3))  # Türkiye saati UTC+3
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════════════════════════════
#  HABER KAYNAKLARI  →  hedef: "haberler"
# ══════════════════════════════════════════════════════════════════

# ── Erişim engelleri nedeniyle DÖNEN alan adları ──
# Bu kaynaklardan kayıt kesilirse önce güncel alan adını kontrol et
# ve YALNIZCA aşağıdaki satırı güncelle:
MA_DOMAIN        = "mezopotamyaajansi44.com"   # Mezopotamya Ajansı (35→40→44...)
YENIYASAM_DOMAIN = "yeniyasamgazetesi9.com"    # Yeni Yaşam (4→6→9...)

RSS_KAYNAKLARI = [
    {"url": "https://bianet.org/topic/cevre/feed/rss",
     "kaynak": "Bianet", "kategori": "Çevre İhlali", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://iklimhaber.org/feed/",
     "kaynak": "İklim Haber", "kategori": "İklim", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://yesilgazete.org/feed/",
     "kaynak": "Yeşil Gazete", "kategori": "Çevre Medyası", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.evrensel.net/rss/ekoloji.xml",
     "kaynak": "Evrensel", "kategori": "Ekoloji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.birgun.net/xml/rss.xml",
     "kaynak": "Birgün", "kategori": "Haber", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:resmigazete.gov.tr+%22kamula%C5%9Ft%C4%B1rma%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Resmi Gazete", "kategori": "Kamulaştırma", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:resmigazete.gov.tr+%22maden%22+OR+%22ihale%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Resmi Gazete", "kategori": "Resmi İhale / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:ilan.gov.tr+%22maden%22+OR+%22enerji%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "İlan Portalı", "kategori": "İhale / Enerji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:gazetepencere.com+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Gazete Pencere", "kategori": "Çevre / Gündem", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:t24.com.tr+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22%C3%87ED%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "T24", "kategori": "Gündem / Çevre", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:diken.com.tr+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22%C3%87ED%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Diken", "kategori": "Gündem / Çevre", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:artigercek.com+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Artı Gerçek", "kategori": "Gündem / Ekoloji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çevre+ihlali+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Çevre İhlali", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=orman+tahribi+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Orman / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=HES+RES+baraj+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "HES / RES / Baraj", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=acele+kamulaştırma+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kamulaştırma", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ÇED+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "ÇED Kararları", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=siyanür+atık+barajı+maden&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Maden Riski / Atık", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=jeotermal+JES+tarım+aydın+manisa&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "JES / Çevre İhlali", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=zeytinlik+maden+projesi+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Tarım Alanları / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.sozcu.com.tr/rss/cevre.xml",
     "kaynak": "Sözcü", "kategori": "Haber", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:mapeg.gov.tr+maden+ruhsat&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "MAPEG (Maden)", "kategori": "Resmi / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.cumhuriyet.com.tr/rss/cevre.rss",
     "kaynak": "Cumhuriyet", "kategori": "Haber", "genel": True, "hedef": "haberler", "dil": "tr"},
    # ── Yerel Basın — 7 Bölge, Tüm Türkiye ──
    {
        "url": "https://www.rizeninsesi.net/rss",
        "kaynak": "Rize'nin Sesi",
        "kategori": "Yerel / Karadeniz",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:gunebakis.com.tr+(çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Günebakış (Trabzon)",
        "kategori": "Yerel / Karadeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:karadenizdesonnokta.com.tr+(çevre+OR+maden+OR+orman+OR+HES)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Karadeniz'de Son Nokta",
        "kategori": "Yerel / Karadeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:aciksoz.com.tr+(çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Açıksöz (Kastamonu)",
        "kategori": "Yerel / Karadeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:gazeterize.com+(çevre+OR+maden+OR+HES+OR+RES+OR+orman)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Gazete Rize",
        "kategori": "Yerel / Karadeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Zonguldak+maden+çevre+OR+kömür+OR+işçi+OR+ocak&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Zonguldak",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Artvin+maden+OR+HES+OR+orman+OR+kamulaştırma+çevre&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Artvin",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Rize+OR+Trabzon+OR+Giresun+OR+Ordu+OR+Samsun+maden+OR+HES+OR+taş+ocağı+çevre+ihlal&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Karadeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Kastamonu+OR+Sinop+OR+Bartın+OR+Karabük+maden+OR+çevre+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Batı Karadeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://www.yeniasir.com.tr/rss/Anasayfa.xml",
        "kaynak": "Yeni Asır (İzmir)",
        "kategori": "Yerel / Ege",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:egedesonsoz.com+(çevre+OR+maden+OR+termik+OR+GES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Ege'de Sonsöz (İzmir)",
        "kategori": "Yerel / Ege",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:muglagazetesi.com.tr+(çevre+OR+maden+OR+Akbelen+OR+Yatağan+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Muğla Gazetesi",
        "kategori": "Yerel / Muğla",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:muglayenigun.com+(çevre+OR+maden+OR+Akbelen+OR+orman)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Muğla Yenigün",
        "kategori": "Yerel / Muğla",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=İzmir+Aliağa+OR+Bergama+OR+Foça+çevre+OR+termik+OR+kirlilik+OR+maden&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / İzmir",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Muğla+Akbelen+OR+Yatağan+OR+Milas+OR+Ula+çevre+OR+maden+OR+orman&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Muğla",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Manisa+OR+Aydın+OR+Denizli+çevre+OR+maden+OR+termik+OR+GES+OR+kamulaştırma+ihlal&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Ege",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Kaz+Dağları+OR+İda+çevre+maden+OR+altın+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Kaz Dağları",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Antalya+çevre+OR+kıyı+OR+maden+OR+GES+OR+kamulaştırma+OR+orman+ihlal&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Antalya",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Mersin+OR+Adana+çevre+OR+termik+OR+maden+OR+kirlilik+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Akdeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Hatay+çevre+OR+maden+OR+orman+OR+sel+OR+kirlilik+&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Hatay",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Isparta+OR+Burdur+OR+Kahramanmaraş+çevre+OR+maden+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Akdeniz",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Çanakkale+çevre+OR+maden+OR+altın+OR+Kaz+Dağları+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Çanakkale",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Kocaeli+OR+Bursa+OR+İzmit+çevre+OR+sanayi+kirliliği+OR+hava+kirliliği+OR+kimyasal&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Marmara",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Tekirdağ+OR+Edirne+OR+Kırklareli+çevre+OR+maden+OR+GES+OR+kamulaştırma+OR+tarım&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Trakya",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Balıkesir+çevre+OR+maden+OR+GES+OR+RES+OR+termik+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Balıkesir",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=İstanbul+çevre+OR+kanal+OR+dolgu+OR+orman+OR+yeşil+alan+OR+kirlilik+ihlal&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / İstanbul",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Ankara+çevre+OR+maden+OR+bor+OR+kömür+OR+hava+kirliliği+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Ankara",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Konya+OR+Eskişehir+çevre+OR+Tuz+Gölü+OR+maden+OR+kamulaştırma+OR+tarım&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / İç Anadolu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Kayseri+OR+Sivas+OR+Çorum+çevre+OR+maden+OR+manyezit+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / İç Anadolu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Diyarbakır+OR+Şanlıurfa+OR+Mardin+çevre+OR+maden+OR+HES+OR+baraj+OR+Fırat+OR+Dicle&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Güneydoğu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Van+OR+Bitlis+OR+Muş+OR+Hakkari+çevre+OR+maden+OR+HES+OR+baraj+OR+orman&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Doğu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Erzurum+OR+Erzincan+OR+Kars+OR+Ardahan+çevre+OR+maden+OR+HES+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Kuzeydoğu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Elazığ+OR+Malatya+OR+Bingöl+OR+Tunceli+çevre+OR+maden+OR+HES+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Doğu Anadolu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Batman+OR+Siirt+OR+Şırnak+çevre+OR+maden+OR+petrol+OR+boru+hattı+OR+kirlilik&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Güneydoğu",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=Amasya+OR+Tokat+OR+Çankırı+çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Orta",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://www.gazeteduvar.com.tr/feeds/rss",
        "kaynak": "Gazete Duvar",
        "kategori": "Çevre / Gündem",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:bianet.org+(yerel+OR+bölge+OR+köy+OR+ilçe)+çevre+OR+maden+OR+HES&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Bianet Bölgesel",
        "kategori": "Yerel / Çevre",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:sendika.org+(maden+OR+çevre+OR+işçi+OR+termik)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Sendika.org",
        "kategori": "Yerel / Emek-Çevre",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=maden+kazası+OR+maden+işçisi+OR+ocak+patlaması+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News",
        "kategori": "Yerel / Maden Kazası",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    # ══════════════════════════════════════════════════════════════
    #  YENİ KAYNAKLAR (2026-06 — GeoJSON derlemelerinden)
    #  Sinop/Boyabat · Mezopotamya Ekoloji · LGBTİ+ İklim Adaleti
    # ══════════════════════════════════════════════════════════════
    # ── Sinop / Boyabat (Cengiz bakır madeni + nükleer karşıtı) ──
    {
        "url": "https://news.google.com/rss/search?q=site:haberkolektif.com+(çevre+OR+ekoloji+OR+maden+OR+nükleer+OR+orman+OR+ÇED+OR+bakır)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Haber Kolektif",
        "kategori": "Çevre / Gündem",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:boyabatsesi.com+(çevre+OR+maden+OR+ÇED+OR+orman+OR+bakır+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Boyabat Sesi",
        "kategori": "Çevre / Gündem",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    # ── Mezopotamya Ekoloji Hareketi ve Kürdistan/Güneydoğu basını ──
    # NOT: mezopotamyaekoloji.org bir arşiv sitesi (son içerik 01/2025, öncesi 2019)
    # — haber akışı üretmiyor. MEH'in güncel faaliyeti basına yansıyanlar
    # üzerinden ve Mezopotamya Ajansı'nın Ekoloji kategorisinden izleniyor.
    {
        "url": "https://news.google.com/rss/search?q=%22Mezopotamya+Ekoloji%22&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Mezopotamya Ekoloji Hareketi (basın yansıması)",
        "kategori": "STK",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    # ── Yeni Yaşam (WordPress; Ekoloji kategorisinin kendi RSS'i) ──
    {
        "url": f"https://{YENIYASAM_DOMAIN}/kategori/ekoloji/feed/",
        "kaynak": "Yeni Yaşam",
        "kategori": "Ekoloji",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": f"https://news.google.com/rss/search?q=site:{MA_DOMAIN}+(ekoloji+OR+çevre+OR+maden+OR+HES+OR+baraj+OR+ÇED+OR+orman+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Mezopotamya Ajansı",
        "kategori": "Ekoloji",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    # ── Bölgesel hedefli sorgular: Doğu/Güneydoğu (mevcut sorgu yalnızca
    #    Diyarbakır/Şanlıurfa/Mardin'i kapsıyordu) ──
    {
        "url": "https://news.google.com/rss/search?q=(Van+OR+Hakkari+OR+Şırnak+OR+Batman+OR+Siirt+OR+Bitlis+OR+Muş)+(maden+OR+HES+OR+baraj+OR+ÇED+OR+orman+OR+ekoloji+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News Bölgesel (Van-Hakkari-Botan)",
        "kategori": "Bölgesel",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=(Dersim+OR+Tunceli+OR+Munzur+OR+Bingöl+OR+Cudi+OR+Gabar+OR+Hevsel)+(maden+OR+HES+OR+baraj+OR+ÇED+OR+orman+OR+petrol+OR+ekoloji)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Google News Bölgesel (Dersim-Botan-Hevsel)",
        "kategori": "Bölgesel",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:amedhaber.net+(çevre+OR+ekoloji+OR+maden+OR+HES+OR+JES+OR+orman+OR+Hevsel+OR+Dicle+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Amed Haber",
        "kategori": "Gündem / Ekoloji",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:kisadalga.net+(çevre+OR+ekoloji+OR+maden+OR+JES+OR+HES+OR+orman+OR+ÇED+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Kısa Dalga",
        "kategori": "Gündem / Çevre",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:politikahaber.com+(çevre+OR+ekoloji+OR+maden+OR+JES+OR+HES+OR+orman+OR+kamulaştırma+OR+ÇED)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Politika Haber",
        "kategori": "Gündem / Çevre",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:anarsisthaberler.net+(çevre+OR+ekoloji+OR+maden+OR+orman+OR+iklim+OR+ağaç)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Anarşist Haberler",
        "kategori": "Gündem / Ekoloji",
        "genel": True,
        "hedef": "haberler",
        "dil": "tr"
    },
    # ── LGBTİ+ / İklim Adaleti & Queer Ekoloji ──
    # hedef "ekosistem": kalıcı (haberler.json aylık budandığı için eskiden
    # bu kayıtlar bir ay sonra ekosistem sayfasından kayboluyordu).
    {
        "url": "https://news.google.com/rss/search?q=site:kaosgl.org+(ekoloji+OR+iklim+OR+çevre+OR+doğa+OR+kuraklık+OR+orman+OR+su+OR+queer+ekoloji)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Kaos GL",
        "kategori": "LGBTİ+ & Çevre",
        "genel": False,
        "bolum": "lgbti",
        "hedef": "ekosistem",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:17mayis.org+(iklim+OR+ekoloji+OR+çevre+OR+doğa+OR+afet)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "17 Mayıs Derneği",
        "kategori": "LGBTİ+ & Çevre",
        "genel": False,
        "bolum": "lgbti",
        "hedef": "ekosistem",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:iklimadaletikoalisyonu.org&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "İklim Adaleti Koalisyonu",
        "kategori": "İklim",
        "genel": False,
        "hedef": "haberler",
        "dil": "tr"
    },
    {
        "url": "https://news.google.com/rss/search?q=site:coalitionrainbow.org+(iklim+OR+ekoloji+OR+çevre+OR+climate+OR+ecology)&hl=tr&gl=TR&ceid=TR:tr",
        "kaynak": "Coalition Rainbow",
        "kategori": "LGBTİ+ & Çevre",
        "genel": False,
        "bolum": "lgbti",
        "hedef": "ekosistem",
        "dil": "tr"
    },
]

# ══════════════════════════════════════════════════════════════════
#  RAPOR / ANALİZ KAYNAKLARI  →  hedef: "raporlar"
# ══════════════════════════════════════════════════════════════════

RAPOR_RSS_KAYNAKLARI = [
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Doğa Derneği", "kategori": "STK Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+raporu+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "İklim Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çevre+araştırma+analiz+Türkiye+üniversite&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Akademik Analiz", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ekoloji+politika+değerlendirme+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Politika Analizi", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ÇED+inceleme+sonuç+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "ÇED Analizi", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=enerji+geçiş+politika+Türkiye+yenilenebilir&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Enerji Politikası", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:shura-enerji.com&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "SHURA Enerji", "kategori": "Enerji Politikası", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://sefia.org/feed/",
     "kaynak": "SEFiA", "kategori": "Enerji Politikası", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=SEFiA+k%C3%B6m%C3%BCr+OR+enerji+OR+iklim&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "SEFiA", "kategori": "Enerji Politikası", "genel": False, "hedef": "raporlar", "dil": "tr"},
]

RAPOR_WEB_KAYNAKLARI = [
    {"url": "https://dogadernegi.org/tr/haberler/",
     "kaynak": "Doğa Derneği", "kategori": "STK Raporu",
     "secici": ".post-title a, h2 a, h3 a, article a",
     "ozet_secici": ".excerpt, p", "genel": False, "hedef": "raporlar", "dil": "tr",
     "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  MAKALE KAYNAKLARI  →  hedef: "makaleler"
#  Makaleler menüsündeki 7 alt başlığa göre gruplanmıştır (bkz. makaleler.html
#  dropdown). "kategori" alanı, dagitici.py'deki KATEGORI_ESLESTIRME /
#  kural_siniflandir ile eşleşecek şekilde admin panel "tur" adlarıyla
#  BİREBİR aynı yazılır: Resmi Açıklama, Basın Bülteni, Bireysel Yazı,
#  Köşe Yazısı, Analiz, Araştırma, Akademik Makale, Röportaj.
# ══════════════════════════════════════════════════════════════════

MAKALE_RSS_KAYNAKLARI = [
    # ── Resmi Açıklamalar ──
    {"url": "https://news.google.com/rss/search?q=site:csb.gov.tr+%22bas%C4%B1n+a%C3%A7%C4%B1klamas%C4%B1%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı", "kategori": "Resmi Açıklama", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:tarimorman.gov.tr+%22bas%C4%B1n+a%C3%A7%C4%B1klamas%C4%B1%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Tarım ve Orman Bakanlığı", "kategori": "Resmi Açıklama", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%C3%A7evre+bakanl%C4%B1%C4%9F%C4%B1+resmi+a%C3%A7%C4%B1klama+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Resmi Açıklama", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Basın Bültenleri (aktif STK'lar) ──
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org+%22bas%C4%B1n+b%C3%BClteni%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Doğa Derneği", "kategori": "Basın Bülteni", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%22350.org%22+T%C3%BCrkiye+bas%C4%B1n+b%C3%BClteni+iklim&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "350.org TR", "kategori": "Basın Bülteni", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%22K%C3%BCresel+Eylem+Grubu%22+bas%C4%B1n+b%C3%BClteni&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Küresel Eylem Grubu", "kategori": "Basın Bülteni", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Bireysel Yazılar ──
    {"url": "https://news.google.com/rss/search?q=medium.com+ekoloji+iklim+kriz+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:yesilgazete.org+%22g%C3%B6r%C3%BC%C5%9F%22+OR+%22yorum%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Yeşil Gazete", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Bağımsız Gazeteciler / Yazarlar (isim bazlı takip) ──
    # Yeni bir isim eklerken: varsa kişisel blog/RSS + o isme özel
    # Google News site: sorguları şeklinde ekle, "kategori" hep "Bireysel Yazı" kalsın.
    {"url": "https://yusufyavuzhaber2022.com/feed/",
     "kaynak": "Yusuf Yavuz (Blog)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:odatv.com+%22Yusuf+Yavuz%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Yusuf Yavuz (Odatv)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:bianet.org+%22Yusuf+Yavuz%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Yusuf Yavuz (Bianet)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    {"url": "https://news.google.com/rss/search?q=site:evrensel.net+%22%C3%96zer+Akdemir%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Özer Akdemir (Evrensel)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:ekolojibirligi.org+%22%C3%96zer+Akdemir%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Özer Akdemir (Ekoloji Birliği)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    {"url": "https://elifince.com/feed/",
     "kaynak": "Elif İnce (Blog)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:iklimadaleti.org+%22Elif+%C4%B0nce%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Elif İnce (İklim Adaleti)", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    {"url": "https://news.google.com/rss/search?q=%22Mine+B.+Tekman%22+ekoloji+OR+n%C3%BCkleer&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Mine B. Tekman", "kategori": "Bireysel Yazı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    {"url": "https://news.google.com/rss/search?q=site:cumhuriyet.com.tr+%22Murat+A%C4%9F%C4%B1rel%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Murat Ağırel (Cumhuriyet)", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    {"url": "https://sokaktv.com/kose-yazilari/feed/",
     "kaynak": "Fatih Bozoğlu (Sokak TV)", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:sokaktv.com+%22Fatih+Bozo%C4%9Flu%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Fatih Bozoğlu (Sokak TV)", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Köşe Yazıları ──
    {"url": "https://bianet.org/bianet/feed/rss",
     "kaynak": "Bianet", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:bianet.org+%22k%C3%B6%C5%9Fe%22+cevre&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Bianet", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:t24.com.tr+%22k%C3%B6%C5%9Fe+yaz%C4%B1s%C4%B1%22+%C3%A7evre+OR+ekoloji+OR+iklim&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "T24", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:artigercek.com+%22k%C3%B6%C5%9Fe%22+%C3%A7evre+OR+ekoloji&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Artı Gerçek", "kategori": "Köşe Yazısı", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Analiz & Araştırma ──
    {"url": "https://news.google.com/rss/search?q=site:iklimhaber.org+%22analiz%22+OR+%22g%C3%B6r%C3%BC%C5%9F%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "İklim Haber", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+kriz+ekoloji+analiz+de%C4%9Ferlendirme+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%C3%A7evre+ekoloji+ara%C5%9Ft%C4%B1rma+bulgular%C4%B1+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Araştırma", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=orman+maden+%C3%A7evre+hukuku+yorum+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Akademik Makaleler ──
    {"url": "https://news.google.com/rss/search?q=site:dergipark.org.tr+ekoloji+OR+%C3%A7evre+OR+iklim&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "DergiPark", "kategori": "Akademik Makale", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%C3%BCniversite+ara%C5%9Ft%C4%B1rmas%C4%B1+ekoloji+OR+iklim+OR+biyo%C3%A7e%C5%9Fitlilik+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Akademik Makale", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%22Levent+Kurnaz%22+iklim&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "M. Levent Kurnaz (Boğaziçi İklim Merkezi)", "kategori": "Akademik Makale", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:yesilgazete.org+%22Sedat+G%C3%BCndo%C4%9Fdu%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Sedat Gündoğdu (Yeşil Gazete)", "kategori": "Akademik Makale", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://www.aykutcoban.org/feed/",
     "kaynak": "Aykut Çoban (Kişisel Site)", "kategori": "Akademik Makale", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:polenekoloji.org+%22Aykut+%C3%87oban%22&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Aykut Çoban (Polen Ekoloji)", "kategori": "Akademik Makale", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── Röportajlar ──
    {"url": "https://news.google.com/rss/search?q=r%C3%B6portaj+ekoloji+OR+%C3%A7evre+OR+iklim+uzman+T%C3%BCrkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Röportaj", "genel": False, "hedef": "makaleler", "dil": "tr"},

    # ── İklim Medyası / Analiz Kuruluşları ──
    {"url": "https://iklimgazetesi.com/feed/",
     "kaynak": "İklim Gazetesi", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://www.ekoiq.com/feed/",
     "kaynak": "ekoIQ", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://www.ekoloji.org/feed/",
     "kaynak": "Toplumsal Ekoloji Grubu", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:ekoloji.org&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Toplumsal Ekoloji Grubu", "kategori": "Analiz", "genel": False, "hedef": "makaleler", "dil": "tr"},
]

MAKALE_WEB_KAYNAKLARI = [
    {"url": "https://politeknik.org.tr",
     "kaynak": "Politeknik", "kategori": "Analiz",
     "secici": ".post-title a, h3 a, h2 a, article a",
     "ozet_secici": ".post-excerpt, p", "genel": False, "hedef": "makaleler", "dil": "tr",
     "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  ULUSLARARASI KAYNAKLAR  →  hedef: "uluslararasi"
# ══════════════════════════════════════════════════════════════════

ULUSLARARASI_RSS_KAYNAKLARI = [
    {"url": "https://www.carbonbrief.org/feed",
     "kaynak": "Carbon Brief", "kategori": "Uluslararası Analiz", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://www.climatechangenews.com/feed/",
     "kaynak": "Climate Home News", "kategori": "Uluslararası Haber", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.mongabay.com/feed/",
     "kaynak": "Mongabay", "kategori": "Uluslararası Haber", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://www.theguardian.com/environment/rss",
     "kaynak": "The Guardian", "kategori": "Uluslararası Haber", "genel": True, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://350.org/feed/",
     "kaynak": "350.org", "kategori": "İklim Hareketi", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://e360.yale.edu/feed.xml",
     "kaynak": "Yale Environment 360", "kategori": "Uluslararası Analiz", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://grist.org/feed/",
     "kaynak": "Grist", "kategori": "Uluslararası Haber", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://insideclimatenews.org/feed/",
     "kaynak": "Inside Climate News", "kategori": "Uluslararası İklim Haberi", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://www.globalpolicyjournal.com/blog/author/%2A/feed",
     "kaynak": "Global Policy Journal", "kategori": "Küresel Politika Analizi", "genel": True, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=Turkey+environment+mining+ecology&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Türkiye / Uluslararası", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=Turkey+climate+deforestation+coal&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Türkiye / İklim", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=Turkey+Akkuyu+nuclear+environment&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Türkiye / Nükleer", "genel": False, "hedef": "uluslararasi", "dil": "en"},
]

ULUSLARARASI_WEB_KAYNAKLARI = []

# ══════════════════════════════════════════════════════════════════
#  EKOSİSTEM & TOPLULUK KAYNAKLARI  →  hedef: "ekosistem"
# ══════════════════════════════════════════════════════════════════

EKOSISTEM_RSS_KAYNAKLARI = [
    {"url": "https://news.google.com/rss/search?q=nesli+tehlike+tür+Türkiye+hayvan+bitki&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Nesli Tehlike Türler", "genel": False,
     "hedef": "ekosistem", "bolum": "turler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=endangered+species+Turkey+IUCN+Red+List&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Nesli Tehlike Türler", "genel": False,
     "hedef": "ekosistem", "bolum": "turler", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org+tür+nesli&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Doğa Derneği", "kategori": "Nesli Tehlike Türler", "genel": False,
     "hedef": "ekosistem", "bolum": "turler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=yaban+hayatı+izleme+Türkiye+gözlem&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yaban Hayatı", "genel": False,
     "hedef": "ekosistem", "bolum": "yaban", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ayı+kurt+vaşak+geyik+yaban+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yaban Hayatı", "genel": False,
     "hedef": "ekosistem", "bolum": "yaban", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Doğa Derneği", "kategori": "Yaban Hayatı", "genel": False,
     "hedef": "ekosistem", "bolum": "yaban", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=habitat+tahribi+bitki+örtüsü+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Bitki & Habitat", "genel": False,
     "hedef": "ekosistem", "bolum": "bitki", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=orman+yangını+ekosistem+Türkiye+bitki&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Bitki & Habitat", "genel": False,
     "hedef": "ekosistem", "bolum": "bitki", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=balık+ölümü+su+kirliliği+deniz+göl+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Su Canlıları", "genel": False,
     "hedef": "ekosistem", "bolum": "su-canlilari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=deniz+canlısı+yunus+kaplumbağa+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Su Canlıları", "genel": False,
     "hedef": "ekosistem", "bolum": "su-canlilari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=hayvan+hakları+hayvan+istismarı+barınak+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Hayvan Hakları", "genel": False,
     "hedef": "ekosistem", "bolum": "hayvan-haklari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=hayvan+hakları+yasa+sokak+hayvanı+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Hayvan Hakları", "genel": False,
     "hedef": "ekosistem", "bolum": "hayvan-haklari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=kadın+çevre+ekoloji+Türkiye+maden+HES&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kadınlar & Ekoloji", "genel": False,
     "hedef": "ekosistem", "bolum": "kadinlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=feminist+ekoloji+kadın+toprak+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kadınlar & Ekoloji", "genel": False,
     "hedef": "ekosistem", "bolum": "kadinlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çiftçi+köylü+tarım+toprak+maden+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Çiftçi & Köylü", "genel": False,
     "hedef": "ekosistem", "bolum": "ciftci", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=zeytinlik+bağ+bahçe+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Çiftçi & Köylü", "genel": False,
     "hedef": "ekosistem", "bolum": "ciftci", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=balıkçı+deniz+kirliliği+av+yasağı+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Balıkçı Toplulukları", "genel": False,
     "hedef": "ekosistem", "bolum": "balikci", "dil": "tr"},
    # "yerli" bölümü iptal edildi — bu iki sorgu zaten direniş içerikli;
    # genel haber akışına yönlendirildi, içerik-bazlı sınıflama onları
    # direnis-agi.html'de "Direniş ve Eylemler" kategorisine düşürür.
    {"url": "https://news.google.com/rss/search?q=yerel+halk+maden+HES+RES+direniş+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Haber", "genel": False,
     "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=köy+halkı+toprak+hakları+direniş+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Haber", "genel": False,
     "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+gençlik+Türkiye+genç+aktivist&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Gençlik & Ekoloji", "genel": False,
     "hedef": "ekosistem", "bolum": "genclik", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Fridays+for+Future+Turkey+climate+youth&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Gençlik & Ekoloji", "genel": False,
     "hedef": "ekosistem", "bolum": "genclik", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=çevre+adaleti+ekolojik+eşitsizlik+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Ekolojik Eşitsizlik", "genel": False,
     "hedef": "ekosistem", "bolum": "esitsizlik", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=environmental+justice+Turkey+inequality&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Ekolojik Eşitsizlik", "genel": False,
     "hedef": "ekosistem", "bolum": "esitsizlik", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=yeşil+alan+park+kentsel+dönüşüm+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kentsel Çevre", "genel": False,
     "hedef": "ekosistem", "bolum": "kentsel", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=hava+kirliliği+şehir+trafik+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Kentsel Çevre", "genel": False,
     "hedef": "ekosistem", "bolum": "kentsel", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+göçü+yerinden+edilme+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "İklim Göçü", "genel": False,
     "hedef": "ekosistem", "bolum": "goc", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=climate+migration+displacement+Turkey&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "İklim Göçü", "genel": False,
     "hedef": "ekosistem", "bolum": "goc", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=savaş+çevre+ekoloji+kirlilik+Ortadoğu&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Savaş & Ekoloji", "genel": False,
     "hedef": "ekosistem", "bolum": "savas", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=war+environment+ecology+Middle+East+pollution&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Savaş & Ekoloji", "genel": False,
     "hedef": "ekosistem", "bolum": "savas", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=drone+insansız+hava+aracı+çevre+etki&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Savaş Teknolojisi", "genel": False,
     "hedef": "ekosistem", "bolum": "savas-teknoloji", "dil": "tr"},

    # ── Engelliler & Erişim (önceden hiç kaynağı yoktu; bolum dogrulamasından
    #    muaf, ekoloji_puani eşiği yine de konuyu çevre/iklimle sınırlar) ──
    {"url": "https://news.google.com/rss/search?q=engelli+iklim+afet+tahliye+erişim+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Engelliler & Erişim", "genel": False,
     "hedef": "ekosistem", "bolum": "engelliler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=engelli+erişim+yeşil+alan+kent+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Engelliler & Erişim", "genel": False,
     "hedef": "ekosistem", "bolum": "engelliler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=disability+climate+disaster+accessibility+Turkey&hl=en&gl=US&ceid=US:en",
     "kaynak": "Google News EN", "kategori": "Engelliler & Erişim", "genel": False,
     "hedef": "ekosistem", "bolum": "engelliler", "dil": "en"},

    # ── LGBTİ+ & Çevre — org kaynakları (Kaos GL, 17 Mayıs, Coalition Rainbow)
    #    HABER listesinde "ekosistem" hedefine taşındı (kalıcılık için).
    #    Burada yalnızca tek siteye bağımlı olmayan, anahtar-kelime kapısına tabi
    #    genel sorgu var (kaynak "Google News" → metinde lgbti/queer aranır): ──
    {"url": "https://news.google.com/rss/search?q=queer+ekoloji+OR+lgbti+iklim+OR+kuir+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "LGBTİ+ & Çevre", "genel": False,
     "hedef": "ekosistem", "bolum": "lgbti", "dil": "tr"},
]

EKOSISTEM_WEB_KAYNAKLARI = [
    {"url": "https://dogadernegi.org/tr/haberler/",
     "kaynak": "Doğa Derneği", "kategori": "Yaban Hayatı",
     "secici": ".post-title a, h2 a, h3 a, article a",
     "ozet_secici": ".excerpt, p",
     "genel": False, "hedef": "ekosistem", "bolum": "yaban", "dil": "tr", "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  WEB SCRAPING — HABER
# ══════════════════════════════════════════════════════════════════

WEB_KAYNAKLARI = [
    {"url": "https://iklimhaber.org",            "kaynak": "İklim Haber",     "kategori": "İklim",
     "secici": "article h2 a, .entry-title a, h2 a", "ozet_secici": "article p",
     "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://medyascope.tv/category/cevre-ekoloji/", "kaynak": "Medyascope", "kategori": "Ekoloji",
     "secici": ".entry-title a, h3 a, article a", "ozet_secici": ".entry-summary p",
     "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://magmadergisi.com",          "kaynak": "Magma Dergisi",   "kategori": "Çevre Medyası",
     "secici": ".card-title a, h3 a, h2 a, article a", "ozet_secici": ".card-text, .excerpt, p",
     "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.csb.gov.tr/duyurular",  "kaynak": "Çevre Bakanlığı", "kategori": "Resmi",
     "secici": ".duyuru-item a, .news-item a, h3 a, h4 a, .list-item a, li a",
     "ozet_secici": ".duyuru-ozet, .news-excerpt, p",
     "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.gazetepencere.com",     "kaynak": "Gazete Pencere",  "kategori": "Haber",
     "secici": ".news-title a, h3 a, h2 a, .card-title a, article a", "ozet_secici": ".news-excerpt, p",
     "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://t24.com.tr",                "kaynak": "T24",             "kategori": "Haber",
     "secici": "h3 a, h2 a, article a, .news-item a, [class*='title'] a", "ozet_secici": "p, [class*='excerpt']",
     "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.diken.com.tr",          "kaynak": "Diken",           "kategori": "Haber",
     "secici": ".entry-title a, h2 a, h3 a, article a", "ozet_secici": ".entry-content p, p",
     "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://artigercek.com",            "kaynak": "Artı Gerçek",     "kategori": "Haber",
     "secici": ".post-title a, h2 a, h3 a, article a", "ozet_secici": ".post-excerpt, p",
     "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  KATEGORİ HARİTASI
# ══════════════════════════════════════════════════════════════════

KATEGORI_HARITALAMA = {
    "Çevre İhlali":              {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Çevre / Gündem":            {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Gündem / Çevre":            {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Gündem / Ekoloji":          {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Ekoloji":                   {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Orman / Maden":             {"eylem": None,               "etiketler": ["Orman Alanı", "Maden Ocağı"]},
    "Maden Riski / Atık":        {"eylem": None,               "etiketler": ["Maden Ocağı", "Atık & Kirlilik"]},
    "Tarım Alanları / Maden":    {"eylem": None,               "etiketler": ["Tarım & Köy", "Maden Ocağı"]},
    "Resmi İhale / Maden":       {"eylem": None,               "etiketler": ["Maden Ocağı"]},
    "Resmi / Maden":             {"eylem": None,               "etiketler": ["Maden Ocağı"]},
    "İhale / Enerji":            {"eylem": None,               "etiketler": ["GES", "RES", "HES"]},
    "Resmi / Enerji":            {"eylem": None,               "etiketler": ["GES", "RES", "HES"]},
    "HES / RES / Baraj":         {"eylem": None,               "etiketler": ["HES", "RES", "Su Ekosistemleri"]},
    "JES / Çevre İhlali":        {"eylem": None,               "etiketler": ["Jeotermal", "Ekolojik İhlal"]},
    "ÇED Kararları":             {"eylem": "Hukuk & Dava",     "etiketler": ["ÇED Kararları"]},
    "ÇED Analizi":               {"eylem": "Hukuk & Dava",     "etiketler": ["ÇED Kararları", "Analiz"]},
    "Kamulaştırma":              {"eylem": "Hukuk & Dava",     "etiketler": ["Acele Kamulaştırma"]},
    "Resmi":                     {"eylem": "Resmi Açıklama",   "etiketler": ["Resmi Açıklama"]},
    "İhale":                     {"eylem": None,               "etiketler": ["İhale"]},
    "İklim":                     {"eylem": None,               "etiketler": ["İklim Olayları"]},
    "STK":                       {"eylem": "STK & Kampanya",   "etiketler": ["STK & Kampanya"]},
    "Mühendislik / Çevre":       {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Çevre Medyası":             {"eylem": None,               "etiketler": []},
    "Haber":                     {"eylem": None,               "etiketler": []},
    "STK Raporu":                {"eylem": "STK & Kampanya",   "etiketler": ["STK & Kampanya", "Rapor"]},
    "İklim Raporu":              {"eylem": None,               "etiketler": ["İklim Olayları", "Rapor"]},
    "Akademik Analiz":           {"eylem": None,               "etiketler": ["Analiz", "Akademik"]},
    "Politika Analizi":          {"eylem": None,               "etiketler": ["Analiz", "Politika"]},
    "Enerji Politikası":         {"eylem": None,               "etiketler": ["Analiz", "Enerji"]},
    "Mühendislik / Analiz":      {"eylem": None,               "etiketler": ["Analiz"]},
    "Köşe / Yorum":              {"eylem": None,               "etiketler": ["Köşe Yazısı"]},
    "Köşe / Görüş":              {"eylem": None,               "etiketler": ["Köşe Yazısı", "Görüş"]},
    "Görüş / Yorum":             {"eylem": None,               "etiketler": ["Görüş", "Yorum"]},
    "Analiz / Yorum":            {"eylem": None,               "etiketler": ["Analiz", "Yorum"]},
    "Yorum / Değerlendirme":     {"eylem": None,               "etiketler": ["Yorum", "Değerlendirme"]},
    "Hukuki Yorum":              {"eylem": "Hukuk & Dava",     "etiketler": ["Hukuki Yorum"]},
    "Nesli Tehlike Türler":      {"eylem": None,               "etiketler": ["Nesli Tehlike Altında Türler"]},
    "Yaban Hayatı":              {"eylem": None,               "etiketler": ["Yaban Hayatı İzleme"]},
    "Bitki & Habitat":           {"eylem": None,               "etiketler": ["Bitki Örtüsü & Habitatlar"]},
    "Su Canlıları":              {"eylem": None,               "etiketler": ["Su Canlıları"]},
    "Hayvan Hakları":            {"eylem": None,               "etiketler": ["Hayvan Hakları & Refahı"]},
    "Kadınlar & Ekoloji":        {"eylem": None,               "etiketler": ["Kadınlar & Ekoloji"]},
    "Çiftçi & Köylü":            {"eylem": None,               "etiketler": ["Çiftçi & Köylü Sorunları"]},
    "Balıkçı Toplulukları":      {"eylem": None,               "etiketler": ["Balıkçı Toplulukları"]},
    "Gençlik & Ekoloji":         {"eylem": None,               "etiketler": ["Çocuklar & Gençlik"]},
    "Ekolojik Eşitsizlik":       {"eylem": None,               "etiketler": ["Ekolojik Eşitsizlik"]},
    "Kentsel Çevre":             {"eylem": None,               "etiketler": ["Kentsel Çevre"]},
    "İklim Göçü":                {"eylem": None,               "etiketler": ["İklim Göçü & Yerinden Edilme"]},
    "Savaş & Ekoloji":           {"eylem": None,               "etiketler": ["Savaş & Ekoloji"]},
    "Savaş Teknolojisi":         {"eylem": None,               "etiketler": ["Savaş Teknolojisi & Çevre"]},
    "Uluslararası Analiz":       {"eylem": None,               "etiketler": ["Uluslararası", "Analiz"]},
    "Uluslararası Haber":        {"eylem": None,               "etiketler": ["Uluslararası"]},
    "Türkiye / Uluslararası":    {"eylem": None,               "etiketler": ["Uluslararası", "Türkiye"]},
    "Türkiye / İklim":           {"eylem": None,               "etiketler": ["Uluslararası", "İklim Olayları"]},
    "Türkiye / Nükleer":         {"eylem": None,               "etiketler": ["Uluslararası", "Nükleer Enerji"]},
    "İklim Hareketi":            {"eylem": "STK & Kampanya",   "etiketler": ["Uluslararası", "STK & Kampanya"]},
}

# ══════════════════════════════════════════════════════════════════
#  FİLTRE SİSTEMİ
# ══════════════════════════════════════════════════════════════════

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
    "plastik kirlilik", "sondaj", "arama ruhsatı",
    "doğal yaşam", "yaban hayat", "kuş türü", "balık türü",
    # hayvan hakları / ekosistem bölüm sözcükleri — gerçek bölüm içeriğinin
    # eşik=1 filtresini geçmesi için (önceden bu sözcükler yoktu; bu yüzden
    # gerçek hayvan hakları haberleri 0 puan alıp eleniyordu).
    "hayvan hakk", "hayvan ihlal", "hayvan istismar", "sokak hayvan",
    "barınak", "sahiplendir", "veteriner", "köpe", "kedi", "yaban hayvan",
]

RAPOR_SINYAL = [
    "rapor", "araştırma", "analiz", "değerlendirme", "inceleme",
    "bulgular", "sonuçlar", "veri", "istatistik", "ölçüm",
]

KOSE_SINYAL = [
    "köşe", "yorum", "görüş", "değerlendirme", "eleştiri",
    "perspektif", "bakış açısı", "analiz", "tartışma",
]

GUCLU_NEGATIF = [
    "faiz", "borsa", "döviz", "kur", "enflasyon", "bütçe açığı",
    "seçim", "cumhurbaşkanı", "milletvekili", "muhalefet", "iktidar partisi",
    "futbol", "maç sonucu", "şampiyon", "transfer", "gol", "penaltı",
    "dizi", "film", "oyuncu", "magazin", "ünlü çift", "nişan", "düğün",
    "moda", "kripto", "bitcoin", "nft", "borsa rallisi",
    "müzik listesi", "konser", "albüm",
]

GENEL_KAYNAK_NEGATIF = [
    "ekonomi", "piyasa", "hisse", "yatırım", "ihracat", "ithalat",
    "savunma", "asker", "muharebe", "operasyon",
    "turizm sezonu", "tatil", "otel",
    "sağlık", "hastane", "ameliyat",
    "eğitim", "üniversite sınav", "okul",
]

# ── İNGİLİZCE SİNYAL LİSTELERİ ─────────────────────────────────────
# dil="en" kaynaklar (Carbon Brief, Guardian, Mongabay, Yale E360, Grist,
# Inside Climate News, Global Policy Journal vb.) için yukarıdaki Türkçe
# anahtar kelimeler hiçbir zaman eşleşmez; ekoloji_puani daima 0 döndürüp
# tüm İngilizce kayıtları elerdi. Bu liste o boşluğu kapatır.
YUKSEK_SINYAL_EN = [
    "environmental violation", "environmental disaster", "environmental impact assessment",
    "deforestation", "illegal logging", "illegal mining", "coal plant", "coal-fired",
    "nuclear plant", "wetland destruction", "biodiversity loss", "endangered species",
    "water pollution", "air pollution", "soil pollution", "oil spill",
    "toxic waste", "hazardous waste", "protected area", "national park",
    "carbon emissions", "greenhouse gas", "extinction crisis", "coastal erosion",
]

ORTA_SINYAL_EN = [
    "climate", "climate change", "environment", "environmental", "ecology", "ecological",
    "pollution", "deforestation", "wildlife", "biodiversity", "conservation",
    "renewable energy", "fossil fuel", "drought", "wildfire", "flood", "landslide",
    "coastal", "ocean", "sea level", "forest", "mining", "dam", "emissions",
    "sustainability", "sustainable", "nature", "habitat", "species", "ecosystem",
    "recycling", "plastic waste", "animal rights", "animal welfare", "endangered",
]

RAPOR_SINYAL_EN = [
    "report", "study", "research", "analysis", "assessment", "findings",
    "data", "statistics", "survey",
]

KOSE_SINYAL_EN = [
    "opinion", "commentary", "op-ed", "perspective", "column", "analysis", "viewpoint",
]

GUCLU_NEGATIF_EN = [
    "stock market", "interest rate", "election result", "football", "soccer match",
    "box office", "celebrity", "album release", "cryptocurrency", "bitcoin",
]

GENEL_KAYNAK_NEGATIF_EN = [
    "trade deal", "gdp growth", "military operation", "national security strategy",
    "election campaign", "tourism season", "stock exchange", "interest rates",
    "hospital", "surgery", "university exam",
]

# ══════════════════════════════════════════════════════════════════
#  9 GÖRÜNTÜ KATEGORİSİ TESPİTİ
# ══════════════════════════════════════════════════════════════════

HABER_9_KAT = [
    "İklim ve Afet", "Maden ve Enerji", "Orman ve Doğa",
    "Su ve Kıyı", "Yaban Hayatı", "Direniş ve Eylemler",
    "Hukuki Süreçler", "Nöbetler ve Gözaltılar", "STK & Kampanyalar",
]


def haber_kategorisi_tespit(kayit: dict) -> str:
    eylem = (kayit.get("eylem") or "").lower()
    kat_raw = kayit.get("kategori") or kayit.get("etiket") or ""
    _TR = str.maketrans("İŞĞÜÖÇ", "işğüöç")
    kat   = kat_raw.translate(_TR).lower()
    metin = " ".join([
        kayit.get("baslik", ""), kayit.get("ozet", ""),
        kayit.get("kategori", ""),
        " ".join(kayit.get("etiketler") or []),
    ]).translate(_TR).lower()

    _D = {
        "iklim":                  "İklim ve Afet",
        "iklim olayları":         "İklim ve Afet",
        "iklim raporu":           "İklim ve Afet",
        "türkiye / iklim":        "İklim ve Afet",
        "hes / res / baraj":      "Maden ve Enerji",
        "orman / maden":          "Maden ve Enerji",
        "maden riski / atık":     "Maden ve Enerji",
        "resmi ihale / maden":    "Maden ve Enerji",
        "resmi / maden":          "Maden ve Enerji",
        "ihale / enerji":         "Maden ve Enerji",
        "resmi / enerji":         "Maden ve Enerji",
        "jes / çevre ihlali":     "Maden ve Enerji",
        "tarım alanları / maden": "Maden ve Enerji",
        "enerji politikası":      "Maden ve Enerji",
        "kamulaştırma":           "Hukuki Süreçler",
        "çed kararları":          "Hukuki Süreçler",
        "çed analizi":            "Hukuki Süreçler",
        "hukuki yorum":           "Hukuki Süreçler",
        "politika analizi":       "Hukuki Süreçler",
        "stk":                    "STK & Kampanyalar",
        "stk raporu":             "STK & Kampanyalar",
        "iklim hareketi":         "STK & Kampanyalar",
        "yaban hayatı":           "Yaban Hayatı",
        "nesli tehlike türler":   "Yaban Hayatı",
        "hayvan hakları":         "Yaban Hayatı",
        "su canlıları":           "Su ve Kıyı",
        "bitki & habitat":        "Orman ve Doğa",
    }
    if kat in _D:
        return _D[kat]

    if "nöbet" in metin or "gözaltı" in metin or "tutuklama" in metin:
        return "Nöbetler ve Gözaltılar"
    if "direniş & eylem" in eylem or any(k in metin for k in
            ["direniş", "protesto", "miting", "yürüyüş", "boykot"]):
        return "Direniş ve Eylemler"
    if "stk & kampanya" in eylem or "stk" in kat or any(k in metin for k in
            ["doğa derneği", "350.org", "küresel eylem grubu"]):
        return "STK & Kampanyalar"
    if "hukuk & dava" in eylem or any(k in metin for k in
            ["mahkeme", "yürütmeyi durdur", "iptal kararı", "çed kararı", "itiraz",
             "acele kamulaştırma"]):
        return "Hukuki Süreçler"

    if "orman yangın" in metin:
        return "Orman ve Doğa"
    if any(k in metin for k in [
            "iklim", "yangın", "sel ", "taşkın", "heyelan",
            "kuraklık", "aşırı sıcak", "sera gazı", "karbon"]):
        return "İklim ve Afet"
    if any(k in metin for k in [
            "yaban hayat", "nesli tehlike", "biyoçeşitlilik",
            "hayvan hakları", "hayvan refahı", "yunus", "kaplumbağa", "flamingo"]):
        return "Yaban Hayatı"
    if any(k in metin for k in [
            "sulak alan", "deniz kirliliği", "su kirliliği",
            "dere yatağı", "balık ölümü", "kıyı dolgu", "deniz dolgusu"]):
        return "Su ve Kıyı"
    if any(k in metin for k in [
            "maden", "hes ", "res ", "ges ", "termik", "nükleer",
            "jeotermal", "baraj", "akkuyu", "sondaj", "santral",
            "kömür", "doğal gaz", "ihale", "kamulaştırma"]):
        return "Maden ve Enerji"
    if any(k in metin for k in [
            "orman", "ağaç", "habitat", "bitki örtüsü", "doğal sit",
            "milli park", "tabiat park", "ormansızlaşma", "yeşil alan",
            "zeytinlik", "tarım arazi"]):
        return "Orman ve Doğa"
    if any(k in metin for k in ["kıyı", "deniz", "göl", "nehir", "dere", "akarsu"]):
        return "Su ve Kıyı"

    return ""


# ── KELİME-SINIRLI ANAHTAR EŞLEŞMESİ ──────────────────────────────
# Düz `anahtar in metin` ALT-DİZGİ eşleşmesidir ve kısa anahtarlarda
# yanlış pozitif üretir: "sel" → "cinsel" içinde, "GES" → "önergesi"
# içinde, "RES" → "adres", "bor" → "borç" içinde eşleşir. Bu yüzden
# alakasız haberler ekoloji puanı kazanıp filtreyi geçer. Aşağıdaki
# yardımcı, anahtarın bir KELİME BAŞINDA geçmesini şart koşar (öncesinde
# harf/rakam OLMAMALI). Kelime SONU serbesttir; Türkçe ekler eşleşmeye
# devam eder: "sel" → "selde"/"sele" eşleşir, "cinsel"e eşleşmez.
_ANAHTAR_RE = {}
def _anahtar_re(k: str):
    r = _ANAHTAR_RE.get(k)
    if r is None:
        r = re.compile(r'(?<!\w)' + re.escape(k.lower()), re.UNICODE)
        _ANAHTAR_RE[k] = r
    return r

def _ara(metin: str, k: str) -> bool:
    return _anahtar_re(k).search(metin) is not None

def _anahtar_var(metin: str, anahtarlar) -> bool:
    return any(_ara(metin, k) for k in anahtarlar)


def ekoloji_puani(baslik: str, ozet: str = "", genel_kaynak: bool = False,
                  hedef: str = "haberler", dil: str = "tr") -> int:
    if dil == "tr":
        yuksek, orta   = YUKSEK_SINYAL, ORTA_SINYAL
        rapor, kose    = RAPOR_SINYAL, KOSE_SINYAL
        guclu_neg      = GUCLU_NEGATIF
        genel_neg      = GENEL_KAYNAK_NEGATIF
    elif dil == "en":
        yuksek, orta   = YUKSEK_SINYAL_EN, ORTA_SINYAL_EN
        rapor, kose    = RAPOR_SINYAL_EN, KOSE_SINYAL_EN
        guclu_neg      = GUCLU_NEGATIF_EN
        genel_neg      = GENEL_KAYNAK_NEGATIF_EN
    else:
        # Türkçe/İngilizce dışındaki diller (Kürtçe, Arapça, Fransızca,
        # Almanca vb.) için elimizde anahtar kelime sözlüğü yok. Böyle bir
        # kaynağı "tr" sanıp Türkçe kelimelerle puanlamak — önceki hata —
        # metni hiç eşleştiremeyip HER ZAMAN 0 puan verir ve kaydı sessizce
        # eler. Bunun yerine: bu dildeki kaynaklar zaten bilinçli olarak
        # ekoloji/iklim konusuna ÖZEL seçilmiş yayın organlarıdır (RSS
        # URL'sinin kendisi zaten konuyu sınırlar) — tıpkı diğer bölümlerdeki
        # GÜVENİLİR_ORG_KAYNAKLAR listesinin anahtar kelime aramadan kabul
        # edilmesi gibi (bkz. bolum_dogrula). O yüzden anahtar kelime
        # filtresini atlayıp kaydı doğrudan kabul ediyoruz.
        # Not: "genel": True (yani geniş/genel konulu) bir kaynağı bu dilde
        # eklerseniz gürültü süzülemez; bu durumda o dil için ayrı bir
        # YUKSEK_SINYAL_XX / ORTA_SINYAL_XX / GENEL_KAYNAK_NEGATIF_XX listesi
        # eklemek gerekir (aşağıdaki TR/EN listeleriyle aynı desende).
        return 5

    metin = (baslik + " " + ozet).lower()
    if _anahtar_var(metin, guclu_neg):
        return 0
    if genel_kaynak and _anahtar_var(metin, genel_neg):
        return 0
    puan = 0
    for k in yuksek:
        if _ara(metin, k):
            puan += 3
    for k in orta:
        if _ara(metin, k):
            puan += 1
    baslik_lower = baslik.lower()
    for k in yuksek:
        if _ara(baslik_lower, k):
            puan += 2
    if hedef in ("raporlar", "makaleler", "uluslararasi") and puan == 0:
        if _anahtar_var(metin, rapor + kose):
            puan = 2
    return puan


def icerik_tipi_tespit(baslik: str, ozet: str, hedef: str, kaynak: str) -> str:
    if hedef == "uluslararasi":
        return "uluslararasi"
    metin = (baslik + " " + ozet).lower()
    if hedef == "raporlar" or any(k in metin for k in RAPOR_SINYAL):
        return "rapor"
    if hedef == "makaleler" or any(k in metin for k in KOSE_SINYAL):
        return "kose"
    return "haber"

# ══════════════════════════════════════════════════════════════════
#  ZENGİNLEŞTİRME
# ══════════════════════════════════════════════════════════════════

DIRENIS_ANAHTAR = ["direniş", "eylem", "protesto", "miting", "yürüyüş", "boykot", "oturma eylemi"]
NOBET_ANAHTAR   = ["nöbet", "gözaltı", "tutuklama", "polis", "biber gazı", "tahliye"]
HUKUK_ANAHTAR   = ["dava", "mahkeme", "iptal", "yargı", "karar", "itiraz", "hukuk", "yürütmeyi durdur"]

EKOSISTEM_ANAHTAR = {
    "Nesli Tehlike Altında Türler": ["nesli tükeniyor", "nesli tehlike", "yaban hayatı azalıyor"],
    "Yaban Hayatı İzleme":          ["yaban hayatı", "vahşi hayat", "ayı", "kurt", "vaşak", "geyik"],
    "Bitki Örtüsü & Habitatlar":    ["orman yangını", "orman tahribi", "ağaç kesiyor", "habitat yok"],
    "Su Canlıları":                  ["balık ölümü", "su canlısı", "deniz canlısı", "su kirlilik"],
    "Çiftçi & Köylü Sorunları":     ["çiftçi", "köylü", "tarım", "köy"],
    "Balıkçı Toplulukları":          ["balıkçı", "balıkçılık"],
    "Kadınlar & Ekoloji":            ["kadın"],
    "LGBTİ+ & Çevre":                ["queer ekoloji", "lgbti+ ekoloj", "lgbti ekoloj", "gökkuşağı ekoloji", "queer climate"],
}



# ══════════════════════════════════════════════════════════════════
#  İÇERİK-BAZLI BÖLÜM DOĞRULAMA
#  Gevşek RSS sorgulu kimlik/toplum bölümleri kaynak "bolum" atasa bile
#  içerik o konuyu doğrulamıyorsa bölüm DÜŞÜRÜLÜR — kayıt kaynağına değil,
#  İÇERİĞİNE göre sınıflandırılır. Doğa/konu-odaklı bölümler (turler, yaban,
#  bitki, su-canlilari, hayvan-haklari, genclik, goc, kentsel, esitsizlik,
#  savas, savas-teknoloji, balikci) burada YOK; kaynağa güvenmeye
#  devam eder. Yeni bir bölüm kirlenirse buraya anahtar kelimeleriyle ekle.
# ══════════════════════════════════════════════════════════════════
BOLUM_DOGRULA_ANAHTAR = {
    "lgbti":    ["lgbti", "lgbtİ", "lgbtq", "queer", "kuir", "eşcinsel",
                 "gökkuşağı", "trans birey", "onur yürüyüş", "onur haftası",
                 "pride", "biseksüel", "interseks", "gey hareket"],
    "kadinlar": ["kadın", "kadınlar", "feminist", "feminizm", "ekofeminist",
                 "ekofeminizm", "kadın kooperatif", "kadın emek", "anneler",
                 "toplumsal cinsiyet", "kadın hakları", "kadın çiftçi",
                 "kadın üretici", "kadın emekçi", "kız çocuk", "ebeveyn"],
    "ciftci":   ["çiftçi", "köylü", "köy ", "tarım", "tarımsal", "ekin",
                 "hasat", "mera", "tohum", "fındık üretic", "çay üretic",
                 "buğday", "besici", "hayvancılık", "süt üretic", "küçük üretici",
                 "üretici", "rençber", "bağcı", "bahçıvan", "kooperatif",
                 "yayla", "otlak", "zeytin üretic", "çiftlik", "ziraat"],
    "hayvan-haklari": ["hayvan", "köpe", "kedi", "barınak", "sokak hayvan",
                       "sahiplendir", "veteriner", "yaban", "pati", "fauna",
                       "at hakları", "eşek", "kısırlaştır"],
}

# Bölüme özgü GÜVENİLİR örgüt kaynakları: tarayıcı bu kaynaklardan zaten
# yalnızca ekoloji/iklim içeriği çeker (RSS sorgu filtresi). Örgüt kimliği +
# ekoloji filtresi bölümü kendiliğinden doğrular; içerikte ayrıca anahtar
# kelime ARANMAZ (örn. Kaos GL'nin Akbelen haberi metinde "queer" geçmese de
# LGBTİ+ & Çevre içeriğidir). İklim Adaleti Koalisyonu bir LGBTİ+ örgütü
# DEĞİLDİR; buraya eklenmez — genel kaynaklar anahtar kelime doğrulamasına
# tabidir, kirlenme koruması aynen sürer.
BOLUM_GUVENILIR_KAYNAK = {
    "lgbti": {"Kaos GL", "17 Mayıs Derneği", "Coalition Rainbow"},
}

def bolum_dogrula(kaynak_bolum, baslik, ozet, kaynak_adi=None):
    """Kaynaktan gelen bolum'u içeriğe göre doğrular.
       güvenilir örgüt kaynağı -> aynen koru (kaynak+filtre doğrulamadır)
       doğrulama gerektirmeyen bölüm -> aynen koru
       gerektiren + içerik doğruluyor -> koru
       gerektiren + içerik doğrulamıyor -> None (bölümsüz, genel akışta kalır)"""
    if not kaynak_bolum:
        return None
    if (kaynak_adi or "").strip() in BOLUM_GUVENILIR_KAYNAK.get(kaynak_bolum, ()):
        return kaynak_bolum
    anahtarlar = BOLUM_DOGRULA_ANAHTAR.get(kaynak_bolum)
    if anahtarlar is None:
        return kaynak_bolum
    metin = (str(baslik or "") + " " + str(ozet or "")).lower()
    return kaynak_bolum if any(k in metin for k in anahtarlar) else None


def zenginlestir(kayit: dict) -> dict:
    metin  = (kayit.get("baslik", "") + " " + kayit.get("ozet", "")).lower()
    eylem  = kayit.get("eylem")
    etiket = list(kayit.get("etiketler") or [])
    if not eylem:
        if any(k in metin for k in NOBET_ANAHTAR):     eylem = "Nöbet & Gözaltı"
        elif any(k in metin for k in DIRENIS_ANAHTAR): eylem = "Direniş & Eylem"
        elif any(k in metin for k in HUKUK_ANAHTAR):   eylem = "Hukuk & Dava"
    for bolum, anahtarlar in EKOSISTEM_ANAHTAR.items():
        if any(k in metin for k in anahtarlar) and bolum not in etiket:
            etiket.append(bolum)
    icerik = kayit.get("icerik_tipi", "haber")
    etiket_icerik = {
        "rapor": "Rapor & Analiz",
        "kose":  "Köşe & Yorum",
        "uluslararasi": "Uluslararası",
        "haber": None,
    }.get(icerik)
    if etiket_icerik and etiket_icerik not in etiket:
        etiket.append(etiket_icerik)
    kayit["eylem"]            = eylem
    kayit["etiketler"]        = etiket
    kayit["haber_kategorisi"] = haber_kategorisi_tespit(kayit)
    return kayit

# ══════════════════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tarayici")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

SSL_NO_VERIFY_HOSTS = {"mapeg.gov.tr", "ilan.gov.tr"}
FALLBACK_SELECTOR   = "article h2 a, article h3 a, .post-title a, .entry-title a, h2.title a, h3.title a, [class*='title'] a, [class*='baslik'] a"


def url_normalize(url: str) -> str:
    try:
        from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
        p = urlparse(url)
        ATLA = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content",
                "fbclid","gclid","mc_cid","mc_eid","ref","source","via","trk"}
        temiz = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in ATLA]
        return urlunparse(p._replace(query=urlencode(temiz), fragment="")).rstrip("/")
    except Exception:
        return url.split("?")[0].rstrip("/")


def baslik_normalize(baslik: str) -> str:
    return re.sub(r"\s+", " ", baslik).strip().lower()


# Google News başlığa ' - Yayıncı' / ' | Yayıncı' ekler ve bu ek çalıştırmalar
# arası değişir (DW↔DW.com, Anadolu Ajansı↔aa.com.tr, Euronews↔Euronews.com).
# Ek başlığı VE haber_id'yi değiştirdiği için aynı haber her seferinde yeni kayıt
# olarak birikiyordu. Bu anahtar yalnızca TEKRAR KARŞILAŞTIRMASI içindir; başlığı
# ve haber_id'yi DEĞİŞTİRMEZ (arşiv ID eşleşmesi korunur).
_BASLIK_EK_RE = re.compile(r"\s*[-–—|]\s*[^-–—|]{1,45}$")
def baslik_dedup_anahtar(baslik: str) -> str:
    s = baslik_normalize(baslik)
    s2 = _BASLIK_EK_RE.sub("", s)
    return s2 if len(s2) >= 15 else s


def haber_id(url: str, baslik: str, kaynak: str = "") -> str:
    """Stabil ID üretir. Google News URL'leri çalıştırmalar arasında değiştiği için
    bu kaynaklarda baslik+kaynak kullanılır."""
    if url and ("news.google.com" in url or "/rss/articles/" in url):
        return hashlib.md5(f"{baslik_normalize(baslik)}|{kaynak.lower().strip()}".encode()).hexdigest()[:12]
    return hashlib.md5(f"{url_normalize(url)}|{baslik_normalize(baslik)}".encode()).hexdigest()[:12]


_LISTELEME_BASLIK_RE = re.compile(
    r"(?:^|/)\s*(?:sayfa|page)\s*:?\s*\d+\b", re.IGNORECASE)
_LISTELEME_TAM_BASLIK = {
    "haberler", "duyurular", "basın açıklamaları", "basın duyurusu",
    "basın bültenleri", "anasayfa", "ana sayfa",
}

def _listeleme_sayfasi_mi(baslik: str) -> bool:
    """Google News bazen site: sorgularında gerçek makale yerine, o sitenin
    sayfalama/listeleme (arşiv) sayfalarını sonuç olarak döndürüyor
    (örn. 'Haberler / Sayfa: 289 - ...'). Bunlar gerçek içerik değildir,
    her taramada 'yeni' görünüp listeyi kirletir; burada eleniyor."""
    if not baslik:
        return False
    if _LISTELEME_BASLIK_RE.search(baslik):
        return True
    # Site adı öncesi ilk parça (örn. "Haberler - T.C. Çevre...") tek başına
    # jenerik bir liste adıysa da ele.
    ilk_parca = re.split(r"\s*[-–—|]\s*", baslik, maxsplit=1)[0].strip().lower()
    return ilk_parca in _LISTELEME_TAM_BASLIK


def tarih_normalize(tarih_str) -> Optional[str]:
    if not tarih_str:
        return None
    try:
        if hasattr(tarih_str, "tm_year"):
            # RSS time.struct_time → Türkiye saatine çevir
            dt = datetime(*tarih_str[:6], tzinfo=timezone.utc).astimezone(TR_TZ)
            return dt.isoformat()
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(str(tarih_str)).astimezone(TR_TZ)
        return dt.isoformat()
    except Exception:
        return str(tarih_str)


def fetch(url: str, timeout: int = 8, ssl_dogrulama: bool = True) -> Optional[requests.Response]:
    verify = ssl_dogrulama and not any(h in url for h in SSL_NO_VERIFY_HOSTS)
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=verify)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r
    except requests.exceptions.SSLError:
        log.warning(f"SSL hatası [{url[:60]}], verify=False ile yeniden deneniyor...")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r
        except Exception as e2:
            log.warning(f"Fetch başarısız [{url[:60]}]: {e2}")
            return None
    except Exception as e:
        log.warning(f"Fetch başarısız [{url[:60]}]: {e}")
        return None

# ══════════════════════════════════════════════════════════════════
#  RSS TARAMA
# ══════════════════════════════════════════════════════════════════

def _rss_tek_kaynak(kaynak: dict) -> tuple:
    """Tek bir RSS kaynağını tarar, (hedef, kayit_listesi) döndürür."""
    genel  = kaynak.get("genel", False)
    hedef  = kaynak.get("hedef", "haberler")
    dil    = kaynak.get("dil", "tr")
    kayitlar = []
    log.info(f"RSS: {kaynak['kaynak']} [{hedef}|{dil}|genel={genel}]")
    try:
        feed = feedparser.parse(kaynak["url"])
        if feed.bozo and not feed.entries:
            return hedef, kayitlar
        kabul = reddedilen = 0
        for entry in feed.entries[:25]:
            baslik = entry.get("title", "").strip()
            link   = entry.get("link", "")
            ozet   = BeautifulSoup(entry.get("summary", ""), "lxml").get_text(" ", strip=True)
            tarih  = tarih_normalize(
                entry.get("published_parsed") or entry.get("updated_parsed"))
            if not baslik or not link:
                continue
            if _listeleme_sayfasi_mi(baslik):
                reddedilen += 1
                continue
            puan = ekoloji_puani(baslik, ozet, genel, hedef, dil)
            esik = 4 if genel else 1
            if puan < esik:
                reddedilen += 1
                continue
            _hm = KATEGORI_HARITALAMA.get(kaynak["kategori"], {})
            kayit = {
                "id":          haber_id(link, baslik, kaynak.get("kaynak", "")),
                "baslik":      baslik,
                "ozet":        ozet[:300] if ozet else "",
                "url":         link,
                "tarih":       tarih,
                "kaynak":      kaynak["kaynak"],
                "kategori":    kaynak["kategori"],
                "kaynak_turu": "rss",
                "icerik_tipi": icerik_tipi_tespit(baslik, ozet, hedef, kaynak["kaynak"]),
                "dil":         dil,
                "eylem":       _hm.get("eylem"),
                "etiketler":   list(_hm.get("etiketler", [])),
                "_puan":       puan,
            }
            _b = bolum_dogrula(kaynak.get("bolum"), kayit.get("baslik"), kayit.get("ozet"), kaynak["kaynak"])
            if _b:
                kayit["bolum"] = _b
            kayit = zenginlestir(kayit)
            kayitlar.append(kayit)
            kabul += 1
        log.info(f"  -> {kaynak['kaynak']}: {kabul} kabul / {reddedilen} reddedildi")
    except Exception as e:
        log.warning(f"  RSS hatasi [{kaynak['kaynak']}]: {e}")
    return hedef, kayitlar


def rss_tara(kaynaklar: list) -> dict:
    sonuc: dict = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(_rss_tek_kaynak, k): k for k in kaynaklar}
        for fut in as_completed(futures):
            try:
                hedef, kayitlar = fut.result()
                for kayit in kayitlar:
                    sonuc.setdefault(hedef, []).append(kayit)
            except Exception as e:
                log.warning(f"  RSS thread hatasi: {e}")
    return sonuc

# ══════════════════════════════════════════════════════════════════
#  WEB SCRAPING
# ══════════════════════════════════════════════════════════════════

def _web_tek_kaynak(kaynak: dict) -> tuple:
    """Tek bir web kaynağını tarar, (hedef, kayit_listesi) döndürür."""
    genel         = kaynak.get("genel", False)
    hedef         = kaynak.get("hedef", "haberler")
    dil           = kaynak.get("dil", "tr")
    ssl_dogrulama = kaynak.get("ssl_dogrulama", True)
    kayitlar = []
    log.info(f"Web: {kaynak['kaynak']} [{hedef}|{dil}|genel={genel}]")
    r = fetch(kaynak["url"], ssl_dogrulama=ssl_dogrulama)
    if not r:
        return hedef, kayitlar
    try:
        soup    = BeautifulSoup(r.text, "lxml")
        kabul = reddedilen = 0
        linkler = soup.select(kaynak["secici"])[:20]
        if not linkler:
            linkler = soup.select(FALLBACK_SELECTOR)[:20]
            if linkler:
                log.info(f"  {kaynak['kaynak']}: fallback selector kullanildi")
        for a in linkler:
            baslik = a.get_text(" ", strip=True)
            if not baslik or len(baslik) < 10:
                continue
            if _listeleme_sayfasi_mi(baslik):
                reddedilen += 1
                continue
            href = a.get("href", "")
            if not href:
                continue
            link = urljoin(kaynak["url"], href)
            ozet = ""
            if kaynak.get("ozet_secici"):
                parent = a.find_parent(["article", "div", "li"])
                if parent:
                    el = parent.select_one(kaynak["ozet_secici"])
                    if el:
                        ozet = el.get_text(" ", strip=True)[:300]
            puan = ekoloji_puani(baslik, ozet, genel, hedef, dil)
            esik = 4 if genel else 1
            if puan < esik:
                reddedilen += 1
                continue
            _hm = KATEGORI_HARITALAMA.get(kaynak["kategori"], {})
            kayit = {
                "id":          haber_id(link, baslik, kaynak.get("kaynak", "")),
                "baslik":      baslik,
                "ozet":        ozet,
                "url":         link,
                "tarih":       datetime.now(TR_TZ).isoformat(),
                "kaynak":      kaynak["kaynak"],
                "kategori":    kaynak["kategori"],
                "kaynak_turu": "web",
                "icerik_tipi": icerik_tipi_tespit(baslik, ozet, hedef, kaynak["kaynak"]),
                "dil":         dil,
                "eylem":       _hm.get("eylem"),
                "etiketler":   list(_hm.get("etiketler", [])),
                "_puan":       puan,
            }
            _b = bolum_dogrula(kaynak.get("bolum"), kayit.get("baslik"), kayit.get("ozet"), kaynak["kaynak"])
            if _b:
                kayit["bolum"] = _b
            kayit = zenginlestir(kayit)
            kayitlar.append(kayit)
            kabul += 1
        log.info(f"  -> {kaynak['kaynak']}: {kabul} kabul / {reddedilen} reddedildi")
    except Exception as e:
        log.warning(f"  Scrape hatasi [{kaynak['kaynak']}]: {e}")
    return hedef, kayitlar


def web_tara(kaynaklar: list) -> dict:
    sonuc: dict = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_web_tek_kaynak, k): k for k in kaynaklar}
        for fut in as_completed(futures):
            try:
                hedef, kayitlar = fut.result()
                for kayit in kayitlar:
                    sonuc.setdefault(hedef, []).append(kayit)
            except Exception as e:
                log.warning(f"  Web thread hatasi: {e}")
    return sonuc

# ══════════════════════════════════════════════════════════════════
#  ANA FONKSİYON
# ══════════════════════════════════════════════════════════════════

def tara(cikti_dosyasi="haberler.json", max_haber=2000, max_diger=1000):
    log.info("=" * 55)
    log.info("  ekoloji-izleme.com — Haber Tarayici v4")
    log.info("=" * 55)

    p = Path(cikti_dosyasi)
    eski: dict = {}
    if p.exists():
        try:
            eski = json.loads(p.read_text(encoding="utf-8"))
            for kol in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
                eski.setdefault(kol, [])
            toplam = sum(len(eski[k]) for k in ("haberler","raporlar","makaleler","uluslararasi","ekosistem"))
            log.info(f"Mevcut: {toplam} kayit")
        except Exception as e:
            log.warning(f"Mevcut dosya okunamadi: {e}, sifirdan baslaniyor.")

    gorulen_idler:     set = set()
    gorulen_urller:    set = set()
    gorulen_basliklar: set = set()
    # baslik → alfanumerik_id haritasi: sayisal ID gelince alfanumerigi siler
    baslik_to_id: dict = {}
    for kol in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
        for h in eski.get(kol, []):
            h_id  = str(h.get("id", ""))
            h_bas = baslik_dedup_anahtar(h.get("baslik", ""))
            gorulen_idler.add(h_id)
            if h.get("url"):  gorulen_urller.add(url_normalize(h["url"]))
            if h_bas:
                gorulen_basliklar.add(h_bas)
                if not h_id.isdigit():
                    baslik_to_id[h_bas] = h_id

    log.info("\n-- RSS: Haberler --")
    rss_haber = rss_tara(RSS_KAYNAKLARI)
    log.info("\n-- RSS: Raporlar --")
    rss_rapor = rss_tara(RAPOR_RSS_KAYNAKLARI)
    log.info("\n-- RSS: Makaleler --")
    rss_makale = rss_tara(MAKALE_RSS_KAYNAKLARI)
    log.info("\n-- RSS: Uluslararasi --")
    rss_ulus = rss_tara(ULUSLARARASI_RSS_KAYNAKLARI)
    log.info("\n-- Web: Haberler --")
    web_haber = web_tara(WEB_KAYNAKLARI)
    log.info("\n-- Web: Raporlar --")
    web_rapor = web_tara(RAPOR_WEB_KAYNAKLARI)
    log.info("\n-- Web: Makaleler --")
    web_makale = web_tara(MAKALE_WEB_KAYNAKLARI)
    log.info("\n-- Web: Uluslararasi --")
    web_ulus = web_tara(ULUSLARARASI_WEB_KAYNAKLARI)
    log.info("\n-- RSS: Ekosistem --")
    rss_ekosistem = rss_tara(EKOSISTEM_RSS_KAYNAKLARI)
    log.info("\n-- Web: Ekosistem --")
    web_ekosistem = web_tara(EKOSISTEM_WEB_KAYNAKLARI)

    def filtrele_yeni(kaynaklar: list) -> list:
        yeni = []
        for h in kaynaklar:
            h_id  = str(h["id"])
            h_url = url_normalize(h.get("url", ""))
            h_bas = baslik_dedup_anahtar(h.get("baslik", ""))

            if h_id in gorulen_idler:
                continue
            if h_url and h_url in gorulen_urller and "news.google.com" not in h_url:
                continue

            # Ayni baslik zaten var mi?
            if h_bas and h_bas in gorulen_basliklar:
                # Mevcut alfanumerik ID'li, yeni sayisal ID'liyse → alfanumerigi sil
                eski_id = baslik_to_id.get(h_bas)
                if eski_id and h_id.isdigit() and not eski_id.isdigit():
                    # Eski alfanumerik kaydi tum koleksiyonlardan temizle
                    for kol_adi in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
                        eski.get(kol_adi, [])[:] = [
                            x for x in eski.get(kol_adi, [])
                            if str(x.get("id", "")) != eski_id
                        ]
                    gorulen_idler.discard(eski_id)
                    gorulen_idler.add(h_id)
                    if h_url: gorulen_urller.add(h_url)
                    baslik_to_id[h_bas] = h_id
                    log.info(f"  [dedup] alfanumerik {eski_id} -> sayisal {h_id}: {h.get('baslik','')[:60]}")
                    h.setdefault("tarama_tarihi", datetime.now(timezone.utc).isoformat())
                    yeni.append(h)
                # Her iki ID de ayni tipte → gercek duplicate, atla
                continue

            h.setdefault("tarama_tarihi", datetime.now(timezone.utc).isoformat())
            yeni.append(h)
            gorulen_idler.add(h_id)
            if h_url: gorulen_urller.add(h_url)
            if h_bas:
                gorulen_basliklar.add(h_bas)
                if not h_id.isdigit():
                    baslik_to_id[h_bas] = h_id
        return yeni

    def birlestir_kaynak(*dicts):
        sonuc = {}
        for d in dicts:
            for k, v in d.items():
                sonuc.setdefault(k, []).extend(v)
        return sonuc

    tum_yeni = birlestir_kaynak(
        rss_haber, rss_rapor, rss_makale, rss_ulus, rss_ekosistem,
        web_haber, web_rapor, web_makale, web_ulus, web_ekosistem,
    )

    koleksiyonlar = {}
    for kol in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
        yeni = filtrele_yeni(tum_yeni.get(kol, []))
        for h in yeni:
            h.pop("_puan", None)
        limit  = max_haber if kol == "haberler" else max_diger
        birles = yeni + eski.get(kol, [])
        birles.sort(key=lambda x: x.get("tarih") or "1970-01-01", reverse=True)
        koleksiyonlar[kol] = birles[:limit]
        log.info(f"  {kol:15s}: +{len(yeni):3d} yeni -> toplam {len(koleksiyonlar[kol])}")

    # ── İçerik-bazlı bölüm doğrulama (her tarama; eski kirli kayıtları da temizler)
    #  Kayıtlar KAYNAĞA değil İÇERİĞE göre sınıflandırılır:
    #   1) GÜVENİLİR örgüt kaynağından geliyorsa (BOLUM_GUVENILIR_KAYNAK)
    #      bölüm koşulsuz garantilenir — kaynak+ekoloji filtresi doğrulamadır.
    #   2) Diğer kaynaklarda, doğrulama gerektiren bölümdeyse (lgbti/kadinlar/
    #      ciftci) ve içerik o konuyu doğrulamıyorsa bölüm DÜŞÜRÜLÜR.
    #  İklim Adaleti Koalisyonu bir LGBTİ+ örgütü DEĞİLDİR; güvenilir listede yok.
    _eklendi = _dusuruldu = 0
    for kol in ("haberler", "ekosistem"):
        for h in koleksiyonlar.get(kol, []):
            kay = (h.get("kaynak") or "").strip()
            _garanti = next((b for b, kk in BOLUM_GUVENILIR_KAYNAK.items() if kay in kk), None)
            if _garanti:
                if h.get("bolum") != _garanti:
                    h["bolum"] = _garanti; _eklendi += 1
                continue
            metin = ((h.get("baslik") or "") + " " + (h.get("ozet") or "")).lower()
            bol = h.get("bolum")
            if bol in BOLUM_DOGRULA_ANAHTAR:
                if not any(k in metin for k in BOLUM_DOGRULA_ANAHTAR[bol]):
                    h["bolum"] = None; _dusuruldu += 1
    if _eklendi or _dusuruldu:
        log.info(f"  [bolum] içerik-doğrulama: +{_eklendi} eklendi / -{_dusuruldu} düşürüldü")

    cikti = {
        "meta": {
            "guncelleme":       datetime.now(TR_TZ).isoformat(),
            "toplam_haber":     len(koleksiyonlar["haberler"]),
            "toplam_rapor":     len(koleksiyonlar["raporlar"]),
            "toplam_makale":    len(koleksiyonlar["makaleler"]),
            "toplam_ulus":      len(koleksiyonlar["uluslararasi"]),
            "toplam_ekosistem": len(koleksiyonlar["ekosistem"]),
        },
        **koleksiyonlar,
    }

    # ── Ana dosyayı yaz (geriye dönük uyumluluk) ──────────────
    json_str = json.dumps(cikti, ensure_ascii=False, indent=2)
    try:
        json.loads(json_str)
    except json.JSONDecodeError as e:
        log.error(f"Uretilen JSON gecersiz: {e}. Yazilmiyor.")
        return cikti

    tmp = p.with_suffix(".tmp")
    tmp.write_text(json_str, encoding="utf-8")
    tmp.replace(p)

    # ── Kategorileri ayrı dosyalara yaz ───────────────────────
    cikti_dir = p.parent
    dosya_haritasi = {
        "haberler":     "haberler_veri.json",
        "raporlar":     "raporlar_veri.json",
        "makaleler":    "makaleler_veri.json",
        "uluslararasi": "uluslararasi_veri.json",
        "ekosistem":    "ekosistem_veri.json",
    }
    for kol, dosya_adi in dosya_haritasi.items():
        parca = {
            "meta": cikti["meta"],
            kol:    koleksiyonlar[kol],
        }
        parca_str = json.dumps(parca, ensure_ascii=False, indent=2)
        parca_tmp = cikti_dir / (dosya_adi + ".tmp")
        parca_tmp.write_text(parca_str, encoding="utf-8")
        parca_tmp.replace(cikti_dir / dosya_adi)
        log.info(f"  {dosya_adi} yazildi ({len(koleksiyonlar[kol])} kayit)")

    log.info(
        f"\n Tamamlandi: {cikti_dosyasi} + 5 ayri dosya | "
        f"{len(koleksiyonlar['haberler'])} haber | "
        f"{len(koleksiyonlar['raporlar'])} rapor | "
        f"{len(koleksiyonlar['makaleler'])} makale | "
        f"{len(koleksiyonlar['uluslararasi'])} uluslararasi | "
        f"{len(koleksiyonlar['ekosistem'])} ekosistem"
    )
    return cikti


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cikti", default="haberler.json")
    parser.add_argument("--max-haber", type=int, default=2000)
    parser.add_argument("--max-diger", type=int, default=1000)
    parser.add_argument("--surekli", action="store_true")
    parser.add_argument("--aralik", type=int, default=180)
    args = parser.parse_args()

    if args.surekli:
        while True:
            try:
                tara(args.cikti, args.max_haber, args.max_diger)
            except KeyboardInterrupt:
                sys.exit(0)
            except Exception as e:
                log.error(f"Tarama hatasi: {e}")
            time.sleep(args.aralik * 60)
    else:
        tara(args.cikti, args.max_haber, args.max_diger)


if __name__ == "__main__":
    main()