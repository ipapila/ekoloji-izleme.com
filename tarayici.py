#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Haber Tarayıcı v4
v4 YENİLİKLERİ:
  - 4 koleksiyon: haberler | raporlar | makaleler | uluslararasi
  - Her kaynak `hedef` alanıyla yönlendirilir
  - `icerik_tipi` ve `dil` alanları eklendi
  - SSL hataları otomatik aşılır (verify=False fallback)
  - `haber_kategorisi` alanı: 17 görüntü kategorisinden birini atar
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
MA_DOMAIN        = "mezopotamyaajansi44.com"
YENIYASAM_DOMAIN = "yeniyasamgazetesi9.com"

RSS_KAYNAKLARI = [
    {"url": "https://bianet.org/topic/cevre/feed/rss", "kaynak": "Bianet", "kategori": "Çevre İhlali", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://iklimhaber.org/feed/", "kaynak": "İklim Haber", "kategori": "İklim", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://yesilgazete.org/feed/", "kaynak": "Yeşil Gazete", "kategori": "Çevre Medyası", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.evrensel.net/rss/ekoloji.xml", "kaynak": "Evrensel", "kategori": "Ekoloji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.birgun.net/xml/rss.xml", "kaynak": "Birgün", "kategori": "Haber", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:resmigazete.gov.tr+%22kamula%C5%9Ft%C4%B1rma%22&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Resmi Gazete", "kategori": "Kamulaştırma", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:resmigazete.gov.tr+%22maden%22+OR+%22ihale%22&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Resmi Gazete", "kategori": "Resmi İhale / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:ilan.gov.tr+%22maden%22+OR+%22enerji%22&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "İlan Portalı", "kategori": "İhale / Enerji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:gazetepencere.com+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Gazete Pencere", "kategori": "Çevre / Gündem", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:t24.com.tr+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22%C3%87ED%22)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "T24", "kategori": "Gündem / Çevre", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:diken.com.tr+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22+OR+%22%C3%87ED%22)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Diken", "kategori": "Gündem / Çevre", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:artigercek.com+(%22%C3%A7evre%22+OR+%22ekoloji%22+OR+%22maden%22)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Artı Gerçek", "kategori": "Gündem / Ekoloji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çevre+ihlali+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Çevre İhlali", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=orman+tahribi+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Orman / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=HES+RES+baraj+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "HES / RES / Baraj", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=acele+kamulaştırma+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Kamulaştırma", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ÇED+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "ÇED Kararları", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=siyanür+atık+barajı+maden&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Maden Riski / Atık", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=jeotermal+JES+tarım+aydın+manisa&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "JES / Çevre İhlali", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=zeytinlik+maden+projesi+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Tarım Alanları / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.sozcu.com.tr/rss/cevre.xml", "kaynak": "Sözcü", "kategori": "Haber", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:mapeg.gov.tr+maden+ruhsat&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "MAPEG (Maden)", "kategori": "Resmi / Maden", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.cumhuriyet.com.tr/rss/cevre.rss", "kaynak": "Cumhuriyet", "kategori": "Haber", "genel": True, "hedef": "haberler", "dil": "tr"},
    
    # ── Yerel Basın ──
    {"url": "https://www.rizeninsesi.net/rss", "kaynak": "Rize'nin Sesi", "kategori": "Yerel / Karadeniz", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:gunebakis.com.tr+(çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Günebakış (Trabzon)", "kategori": "Yerel / Karadeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:karadenizdesonnokta.com.tr+(çevre+OR+maden+OR+orman+OR+HES)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Karadeniz'de Son Nokta", "kategori": "Yerel / Karadeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:aciksoz.com.tr+(çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Açıksöz (Kastamonu)", "kategori": "Yerel / Karadeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:gazeterize.com+(çevre+OR+maden+OR+HES+OR+RES+OR+orman)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Gazete Rize", "kategori": "Yerel / Karadeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Zonguldak+maden+çevre+OR+kömür+OR+işçi+OR+ocak&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Zonguldak", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Artvin+maden+OR+HES+OR+orman+OR+kamulaştırma+çevre&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Artvin", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Rize+OR+Trabzon+OR+Giresun+OR+Ordu+OR+Samsun+maden+OR+HES+OR+taş+ocağı+çevre+ihlal&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Karadeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kastamonu+OR+Sinop+OR+Bartın+OR+Karabük+maden+OR+çevre+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Batı Karadeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.yeniasir.com.tr/rss/Anasayfa.xml", "kaynak": "Yeni Asır (İzmir)", "kategori": "Yerel / Ege", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:egedesonsoz.com+(çevre+OR+maden+OR+termik+OR+GES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Ege'de Sonsöz (İzmir)", "kategori": "Yerel / Ege", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:muglagazetesi.com.tr+(çevre+OR+maden+OR+Akbelen+OR+Yatağan+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Muğla Gazetesi", "kategori": "Yerel / Muğla", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:muglayenigun.com+(çevre+OR+maden+OR+Akbelen+OR+orman)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Muğla Yenigün", "kategori": "Yerel / Muğla", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=İzmir+Aliağa+OR+Bergama+OR+Foça+çevre+OR+termik+OR+kirlilik+OR+maden&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / İzmir", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Muğla+Akbelen+OR+Yatağan+OR+Milas+OR+Ula+çevre+OR+maden+OR+orman&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Muğla", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Manisa+OR+Aydın+OR+Denizli+çevre+OR+maden+OR+termik+OR+GES+OR+kamulaştırma+ihlal&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Ege", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kaz+Dağları+OR+İda+çevre+maden+OR+altın+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Kaz Dağları", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Antalya+çevre+OR+kıyı+OR+maden+OR+GES+OR+kamulaştırma+OR+orman+ihlal&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Antalya", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Mersin+OR+Adana+çevre+OR+termik+OR+maden+OR+kirlilik+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Akdeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Hatay+çevre+OR+maden+OR+orman+OR+sel+OR+kirlilik+&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Hatay", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Isparta+OR+Burdur+OR+Kahramanmaraş+çevre+OR+maden+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Akdeniz", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Çanakkale+çevre+OR+maden+OR+altın+OR+Kaz+Dağları+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Çanakkale", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kocaeli+OR+Bursa+OR+İzmit+çevre+OR+sanayi+kirliliği+OR+hava+kirliliği+OR+kimyasal&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Marmara", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Tekirdağ+OR+Edirne+OR+Kırklareli+çevre+OR+maden+OR+GES+OR+kamulaştırma+OR+tarım&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Trakya", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Balıkesir+çevre+OR+maden+OR+GES+OR+RES+OR+termik+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Balıkesir", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=İstanbul+çevre+OR+kanal+OR+dolgu+OR+orman+OR+yeşil+alan+OR+kirlilik+ihlal&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / İstanbul", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Ankara+çevre+OR+maden+OR+bor+OR+kömür+OR+hava+kirliliği+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Ankara", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Konya+OR+Eskişehir+çevre+OR+Tuz+Gölü+OR+maden+OR+kamulaştırma+OR+tarım&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / İç Anadolu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kayseri+OR+Sivas+OR+Çorum+çevre+OR+maden+OR+manyezit+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / İç Anadolu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Diyarbakır+OR+Şanlıurfa+OR+Mardin+çevre+OR+maden+OR+HES+OR+baraj+OR+Fırat+OR+Dicle&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Güneydoğu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Van+OR+Bitlis+OR+Muş+OR+Hakkari+çevre+OR+maden+OR+HES+OR+baraj+OR+orman&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Doğu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Erzurum+OR+Erzincan+OR+Kars+OR+Ardahan+çevre+OR+maden+OR+HES+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Kuzeydoğu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Elazığ+OR+Malatya+OR+Bingöl+OR+Tunceli+çevre+OR+maden+OR+HES+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Doğu Anadolu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Batman+OR+Siirt+OR+Şırnak+çevre+OR+maden+OR+petrol+OR+boru+hattı+OR+kirlilik&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Güneydoğu", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Amasya+OR+Tokat+OR+Çankırı+çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Orta", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://www.gazeteduvar.com.tr/feeds/rss", "kaynak": "Gazete Duvar", "kategori": "Çevre / Gündem", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:bianet.org+(yerel+OR+bölge+OR+köy+OR+ilçe)+çevre+OR+maden+OR+HES&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Bianet Bölgesel", "kategori": "Yerel / Çevre", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:sendika.org+(maden+OR+çevre+OR+işçi+OR+termik)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Sendika.org", "kategori": "Yerel / Emek-Çevre", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=maden+kazası+OR+maden+işçisi+OR+ocak+patlaması+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yerel / Maden Kazası", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:haberkolektif.com+(çevre+OR+ekoloji+OR+maden+OR+nükleer+OR+orman+OR+ÇED+OR+bakır)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Haber Kolektif", "kategori": "Çevre / Gündem", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:boyabatsesi.com+(çevre+OR+maden+OR+ÇED+OR+orman+OR+bakır+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Boyabat Sesi", "kategori": "Çevre / Gündem", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=%22Mezopotamya+Ekoloji%22&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Mezopotamya Ekoloji Hareketi (basın yansıması)", "kategori": "STK", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": f"https://{YENIYASAM_DOMAIN}/kategori/ekoloji/feed/", "kaynak": "Yeni Yaşam", "kategori": "Ekoloji", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": f"https://news.google.com/rss/search?q=site:{MA_DOMAIN}+(ekoloji+OR+çevre+OR+maden+OR+HES+OR+baraj+OR+ÇED+OR+orman+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Mezopotamya Ajansı", "kategori": "Ekoloji", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=(Van+OR+Hakkari+OR+Şırnak+OR+Batman+OR+Siirt+OR+Bitlis+OR+Muş)+(maden+OR+HES+OR+baraj+OR+ÇED+OR+orman+OR+ekoloji+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News Bölgesel (Van-Hakkari-Botan)", "kategori": "Bölgesel", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=(Dersim+OR+Tunceli+OR+Munzur+OR+Bingöl+OR+Cudi+OR+Gabar+OR+Hevsel)+(maden+OR+HES+OR+baraj+OR+ÇED+OR+orman+OR+petrol+OR+ekoloji)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News Bölgesel (Dersim-Botan-Hevsel)", "kategori": "Bölgesel", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:amedhaber.net+(çevre+OR+ekoloji+OR+maden+OR+HES+OR+JES+OR+orman+OR+Hevsel+OR+Dicle+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Amed Haber", "kategori": "Gündem / Ekoloji", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:kisadalga.net+(çevre+OR+ekoloji+OR+maden+OR+JES+OR+HES+OR+orman+OR+ÇED+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Kısa Dalga", "kategori": "Gündem / Çevre", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:politikahaber.com+(çevre+OR+ekoloji+OR+maden+OR+JES+OR+HES+OR+orman+OR+kamulaştırma+OR+ÇED)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Politika Haber", "kategori": "Gündem / Çevre", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:anarsisthaberler.net+(çevre+OR+ekoloji+OR+maden+OR+orman+OR+iklim+OR+ağaç)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Anarşist Haberler", "kategori": "Gündem / Ekoloji", "genel": True, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:kaosgl.org+(ekoloji+OR+iklim+OR+çevre+OR+doğa+OR+kuraklık+OR+orman+OR+su+OR+queer+ekoloji)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Kaos GL", "kategori": "LGBTİ+ & Çevre", "genel": False, "bolum": "lgbti", "hedef": "ekosistem", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:17mayis.org+(iklim+OR+ekoloji+OR+çevre+OR+doğa+OR+afet)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "17 Mayıs Derneği", "kategori": "LGBTİ+ & Çevre", "genel": False, "bolum": "lgbti", "hedef": "ekosistem", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:iklimadaletikoalisyonu.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "İklim Adaleti Koalisyonu", "kategori": "İklim", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:coalitionrainbow.org+(iklim+OR+ekoloji+OR+çevre+OR+climate+OR+ecology)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Coalition Rainbow", "kategori": "LGBTİ+ & Çevre", "genel": False, "bolum": "lgbti", "hedef": "ekosistem", "dil": "tr"},

    # ── SKILL DOSYASINDAN EKLENEN YENİ ULUSAL STK & AĞLAR ──
    {"url": "https://news.google.com/rss/search?q=site:iklimagi.org+OR+site:yereliklimagi.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "İklim Ağı", "kategori": "STK", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:keg.org.tr+(iklim+OR+çevre+OR+ekoloji)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Küresel Eylem Grubu", "kategori": "STK", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:afetplatformu.org.tr+(yangın+OR+deprem+OR+sel)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Afet Platformu", "kategori": "İklim Olayları", "genel": False, "hedef": "haberler", "dil": "tr"},

    # ── SU, KIYI VE DENİZ ──
    {"url": "https://news.google.com/rss/search?q=site:supolitikalaridernegi.org+(kuraklık+OR+baraj+OR+HES)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Su Politikaları Derneği", "kategori": "Sulak Alan", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:suhakki.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Su Hakkı Kampanyası", "kategori": "Sulak Alan", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:tudav.org+(deniz+kirliliği+OR+kıyı+dolgu)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "TÜDAV", "kategori": "Kıyı İhlalleri", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:akdenizkoruma.org.tr+OR+site:dekafok.org.tr&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Kıyı Koruma Dernekleri", "kategori": "Kıyı İhlalleri", "genel": False, "hedef": "haberler", "dil": "tr"},

    # ── YEREL MADEN KARŞITI HAREKETLER ──
    {"url": "https://news.google.com/rss/search?q=site:yesilartvindernegi.org+OR+site:ekolojibirligi.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Ekoloji Birliği & Yerel Hareketler", "kategori": "STK", "genel": False, "hedef": "haberler", "dil": "tr"},
    
    # ── AFAD VE DEPREM RİSKİ ÇAPRAZ KONTROLÜ ──
    {"url": "https://news.google.com/rss/search?q=site:afad.gov.tr+(fay+OR+deprem+riski+OR+heyelan)&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "AFAD", "kategori": "İklim Olayları", "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  RAPOR / ANALİZ KAYNAKLARI  →  hedef: "raporlar"
# ══════════════════════════════════════════════════════════════════

RAPOR_RSS_KAYNAKLARI = [
    {"url": "https://news.google.com/rss/search?q=site:wwf.org.tr+rapor+OR+arastirma+OR+yayın&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "WWF Türkiye", "kategori": "STK Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:tema.org.tr+rapor+OR+arastirma&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "TEMA", "kategori": "STK Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Doğa Derneği", "kategori": "STK Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:greenpeace.org+turkey+rapor+OR+report&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Greenpeace TR", "kategori": "STK Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+raporu+Türkiye+2025&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "İklim Raporu", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çevre+araştırma+analiz+Türkiye+üniversite&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Akademik Analiz", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ekoloji+politika+değerlendirme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Politika Analizi", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ÇED+inceleme+sonuç+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "ÇED Analizi", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=enerji+geçiş+politika+Türkiye+yenilenebilir&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Enerji Politikası", "genel": False, "hedef": "raporlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:shura-enerji.com&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "SHURA Enerji", "kategori": "Enerji Politikası", "genel": False, "hedef": "raporlar", "dil": "tr"},
]

RAPOR_WEB_KAYNAKLARI = [
    {"url": "https://www.wwf.org.tr/ne_yapiyoruz/", "kaynak": "WWF Türkiye", "kategori": "STK Raporu", "secici": "article h2 a, .post-title a, h3 a, [class*='title'] a", "ozet_secici": "p, .excerpt", "genel": False, "hedef": "raporlar", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.dogadernegi.org/haberler/", "kaynak": "Doğa Derneği", "kategori": "STK Raporu", "secici": ".post-title a, h2 a, h3 a, article a", "ozet_secici": ".excerpt, p", "genel": False, "hedef": "raporlar", "dil": "tr", "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  KÖŞE / YORUM / MAKALE KAYNAKLARI  →  hedef: "makaleler"
# ══════════════════════════════════════════════════════════════════

MAKALE_RSS_KAYNAKLARI = [
    {"url": "https://bianet.org/bianet/feed/rss", "kaynak": "Bianet", "kategori": "Köşe / Yorum", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:bianet.org+%22k%C3%B6%C5%9Fe%22+OR+%22g%C3%B6r%C3%BC%C5%9F%22+cevre&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Bianet", "kategori": "Köşe / Görüş", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:yesilgazete.org+%22g%C3%B6r%C3%BC%C5%9F%22+OR+%22yorum%22&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Yeşil Gazete", "kategori": "Görüş / Yorum", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:iklimhaber.org+%22analiz%22+OR+%22yorum%22+OR+%22g%C3%B6r%C3%BC%C5%9F%22&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "İklim Haber", "kategori": "Analiz / Yorum", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çevre+ekoloji+köşe+yorum+görüş+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Köşe / Görüş", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+krizi+yorum+değerlendirme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yorum / Değerlendirme", "genel": False, "hedef": "makaleler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=orman+maden+çevre+hukuku+yorum+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Hukuki Yorum", "genel": False, "hedef": "makaleler", "dil": "tr"},
]

MAKALE_WEB_KAYNAKLARI = [
    {"url": "https://politeknik.org.tr", "kaynak": "Politeknik", "kategori": "Mühendislik / Analiz", "secici": ".post-title a, h3 a, h2 a, article a", "ozet_secici": ".post-excerpt, p", "genel": False, "hedef": "makaleler", "dil": "tr", "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  ULUSLARARASI KAYNAKLAR  →  hedef: "uluslararasi"
# ══════════════════════════════════════════════════════════════════

ULUSLARARASI_RSS_KAYNAKLARI = [
    {"url": "https://www.carbonbrief.org/feed", "kaynak": "Carbon Brief", "kategori": "Uluslararası Analiz", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://www.climatechangenews.com/feed/", "kaynak": "Climate Home News", "kategori": "Uluslararası Haber", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.mongabay.com/feed/", "kaynak": "Mongabay", "kategori": "Uluslararası Haber", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://www.theguardian.com/environment/rss", "kaynak": "The Guardian", "kategori": "Uluslararası Haber", "genel": True, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://350.org/feed/", "kaynak": "350.org", "kategori": "İklim Hareketi", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=Turkey+environment+mining+ecology&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Türkiye / Uluslararası", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=Turkey+climate+deforestation+coal&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Türkiye / İklim", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=Turkey+Akkuyu+nuclear+environment&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Türkiye / Nükleer", "genel": False, "hedef": "uluslararasi", "dil": "en"},

    # ── SKILL DOSYASINDAN EKLENEN YENİ ULUSLARARASI MEDYA ──
    {"url": "https://news.google.com/rss/search?q=site:desmog.com+(Turkey+OR+fossil+fuels)&hl=en&gl=US&ceid=US:en", "kaynak": "DeSmog", "kategori": "Uluslararası Analiz", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=site:insideclimatenews.org+(Turkey+OR+emissions)&hl=en&gl=US&ceid=US:en", "kaynak": "Inside Climate News", "kategori": "Uluslararası Haber", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://www.euractiv.com/?feed=mcfeed", "kaynak": "Euractiv", "kategori": "Avrupa İklim Politikası", "genel": False, "hedef": "uluslararasi", "dil": "en"},

    # ── AB RESMİ VE ULUSLARARASI STK'LAR ──
    {"url": "https://news.google.com/rss/search?q=(site:eea.europa.eu+OR+site:climate.ec.europa.eu)+Turkey&hl=en&gl=US&ceid=US:en", "kaynak": "Avrupa Çevre Ajansı & DG CLIMA", "kategori": "Uluslararası Politika", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=(site:caneurope.org+OR+site:bankwatch.org+OR+site:clientearth.org)+Turkey&hl=en&gl=US&ceid=US:en", "kaynak": "Uluslararası İklim Ağları", "kategori": "STK Raporu", "genel": False, "hedef": "uluslararasi", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=site:beyondfossilfuels.org+Turkey&hl=en&gl=US&ceid=US:en", "kaynak": "Beyond Fossil Fuels", "kategori": "Kömürden Çıkış", "genel": False, "hedef": "uluslararasi", "dil": "en"},
]

ULUSLARARASI_WEB_KAYNAKLARI = [
    {"url": "https://www.greenpeace.org/international/tag/turkey/", "kaynak": "Greenpeace International", "kategori": "Türkiye / Uluslararası", "secici": ".post-title a, h2 a, h3 a, [class*='title'] a", "ozet_secici": "p, .excerpt", "genel": False, "hedef": "uluslararasi", "dil": "en", "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  EKOSİSTEM & TOPLULUK KAYNAKLARI  →  hedef: "ekosistem"
# ══════════════════════════════════════════════════════════════════

EKOSISTEM_RSS_KAYNAKLARI = [
    {"url": "https://news.google.com/rss/search?q=nesli+tehlike+tür+Türkiye+hayvan+bitki&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Nesli Tehlike Türler", "genel": False, "hedef": "ekosistem", "bolum": "turler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=endangered+species+Turkey+IUCN+Red+List&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Nesli Tehlike Türler", "genel": False, "hedef": "ekosistem", "bolum": "turler", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org+tür+nesli&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Doğa Derneği", "kategori": "Nesli Tehlike Türler", "genel": False, "hedef": "ekosistem", "bolum": "turler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=yaban+hayatı+izleme+Türkiye+gözlem&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yaban Hayatı", "genel": False, "hedef": "ekosistem", "bolum": "yaban", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=ayı+kurt+vaşak+geyik+yaban+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Yaban Hayatı", "genel": False, "hedef": "ekosistem", "bolum": "yaban", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Doğa Derneği", "kategori": "Yaban Hayatı", "genel": False, "hedef": "ekosistem", "bolum": "yaban", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=habitat+tahribi+bitki+örtüsü+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Bitki & Habitat", "genel": False, "hedef": "ekosistem", "bolum": "bitki", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=orman+yangını+ekosistem+Türkiye+bitki&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Bitki & Habitat", "genel": False, "hedef": "ekosistem", "bolum": "bitki", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=balık+ölümü+su+kirliliği+deniz+göl+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Su Canlıları", "genel": False, "hedef": "ekosistem", "bolum": "su-canlilari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=deniz+canlısı+yunus+kaplumbağa+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Su Canlıları", "genel": False, "hedef": "ekosistem", "bolum": "su-canlilari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=hayvan+hakları+hayvan+istismarı+barınak+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Hayvan Hakları", "genel": False, "hedef": "ekosistem", "bolum": "hayvan-haklari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=hayvan+hakları+yasa+sokak+hayvanı+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Hayvan Hakları", "genel": False, "hedef": "ekosistem", "bolum": "hayvan-haklari", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=kadın+çevre+ekoloji+Türkiye+maden+HES&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Kadınlar & Ekoloji", "genel": False, "hedef": "ekosistem", "bolum": "kadinlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=feminist+ekoloji+kadın+toprak+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Kadınlar & Ekoloji", "genel": False, "hedef": "ekosistem", "bolum": "kadinlar", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=çiftçi+köylü+tarım+toprak+maden+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Çiftçi & Köylü", "genel": False, "hedef": "ekosistem", "bolum": "ciftci", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=zeytinlik+bağ+bahçe+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Çiftçi & Köylü", "genel": False, "hedef": "ekosistem", "bolum": "ciftci", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=balıkçı+deniz+kirliliği+av+yasağı+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Balıkçı Toplulukları", "genel": False, "hedef": "ekosistem", "bolum": "balikci", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=yerel+halk+maden+HES+RES+direniş+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Haber", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=köy+halkı+toprak+hakları+direniş+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Haber", "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+gençlik+Türkiye+genç+aktivist&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Gençlik & Ekoloji", "genel": False, "hedef": "ekosistem", "bolum": "genclik", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Fridays+for+Future+Turkey+climate+youth&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Gençlik & Ekoloji", "genel": False, "hedef": "ekosistem", "bolum": "genclik", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=çevre+adaleti+ekolojik+eşitsizlik+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Ekolojik Eşitsizlik", "genel": False, "hedef": "ekosistem", "bolum": "esitsizlik", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=environmental+justice+Turkey+inequality&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Ekolojik Eşitsizlik", "genel": False, "hedef": "ekosistem", "bolum": "esitsizlik", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=yeşil+alan+park+kentsel+dönüşüm+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Kentsel Çevre", "genel": False, "hedef": "ekosistem", "bolum": "kentsel", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=hava+kirliliği+şehir+trafik+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Kentsel Çevre", "genel": False, "hedef": "ekosistem", "bolum": "kentsel", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=iklim+göçü+yerinden+edilme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "İklim Göçü", "genel": False, "hedef": "ekosistem", "bolum": "goc", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=climate+migration+displacement+Turkey&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "İklim Göçü", "genel": False, "hedef": "ekosistem", "bolum": "goc", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=savaş+çevre+ekoloji+kirlilik+Ortadoğu&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Savaş & Ekoloji", "genel": False, "hedef": "ekosistem", "bolum": "savas", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=war+environment+ecology+Middle+East+pollution&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Savaş & Ekoloji", "genel": False, "hedef": "ekosistem", "bolum": "savas", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=drone+insansız+hava+aracı+çevre+etki&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Savaş Teknolojisi", "genel": False, "hedef": "ekosistem", "bolum": "savas-teknoloji", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=engelli+iklim+afet+tahliye+erişim+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Engelliler & Erişim", "genel": False, "hedef": "ekosistem", "bolum": "engelliler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=engelli+erişim+yeşil+alan+kent+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "Engelliler & Erişim", "genel": False, "hedef": "ekosistem", "bolum": "engelliler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=disability+climate+disaster+accessibility+Turkey&hl=en&gl=US&ceid=US:en", "kaynak": "Google News EN", "kategori": "Engelliler & Erişim", "genel": False, "hedef": "ekosistem", "bolum": "engelliler", "dil": "en"},
    {"url": "https://news.google.com/rss/search?q=queer+ekoloji+OR+lgbti+iklim+OR+kuir+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News", "kategori": "LGBTİ+ & Çevre", "genel": False, "hedef": "ekosistem", "bolum": "lgbti", "dil": "tr"},

    # ── TARIM, PESTİSİT VE KİMYASAL KİRLİLİK ──
    {"url": "https://news.google.com/rss/search?q=site:bugday.org+OR+site:zehirsizsofralar.org+OR+site:zehirsizkentler.org&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Buğday & Zehirsiz Sofralar", "kategori": "Tarım & Pestisit", "genel": False, "hedef": "ekosistem", "bolum": "ciftci", "dil": "tr"},
]

EKOSISTEM_WEB_KAYNAKLARI = [
    {"url": "https://www.dogadernegi.org/haberler/", "kaynak": "Doğa Derneği", "kategori": "Yaban Hayatı", "secici": ".post-title a, h2 a, h3 a, article a", "ozet_secici": ".excerpt, p", "genel": False, "hedef": "ekosistem", "bolum": "yaban", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.greenpeace.org/turkey/tag/iklim-krizi/", "kaynak": "Greenpeace TR", "kategori": "Ekolojik Eşitsizlik", "secici": ".post-title a, h2 a, h3 a, [class*='title'] a", "ozet_secici": ".post-excerpt p, p", "genel": False, "hedef": "ekosistem", "bolum": "esitsizlik", "dil": "tr", "ssl_dogrulama": True},
]

# ══════════════════════════════════════════════════════════════════
#  WEB SCRAPING — HABER
# ══════════════════════════════════════════════════════════════════

WEB_KAYNAKLARI = [
    {"url": "https://iklimhaber.org", "kaynak": "İklim Haber", "kategori": "İklim", "secici": "article h2 a, .entry-title a, h2 a", "ozet_secici": "article p", "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://medyascope.tv/category/cevre-ekoloji/", "kaynak": "Medyascope", "kategori": "Ekoloji", "secici": ".entry-title a, h3 a, article a", "ozet_secici": ".entry-summary p", "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://magmadergisi.com", "kaynak": "Magma Dergisi", "kategori": "Çevre Medyası", "secici": ".card-title a, h3 a, h2 a, article a", "ozet_secici": ".card-text, .excerpt, p", "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.greenpeace.org/turkey/blog/", "kaynak": "Greenpeace TR", "kategori": "STK", "secici": ".post-title a, h2 a, h3 a, .article__title a, [class*='title'] a", "ozet_secici": ".post-excerpt p, [class*='excerpt'], p", "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.csb.gov.tr/duyurular", "kaynak": "Çevre Bakanlığı", "kategori": "Resmi", "secici": ".duyuru-item a, .news-item a, h3 a, h4 a, .list-item a, li a", "ozet_secici": ".duyuru-ozet, .news-excerpt, p", "genel": False, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.gazetepencere.com", "kaynak": "Gazete Pencere", "kategori": "Haber", "secici": ".news-title a, h3 a, h2 a, .card-title a, article a", "ozet_secici": ".news-excerpt, p", "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://t24.com.tr", "kaynak": "T24", "kategori": "Haber", "secici": "h3 a, h2 a, article a, .news-item a, [class*='title'] a", "ozet_secici": "p, [class*='excerpt']", "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://www.diken.com.tr", "kaynak": "Diken", "kategori": "Haber", "secici": ".entry-title a, h2 a, h3 a, article a", "ozet_secici": ".entry-content p, p", "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
    {"url": "https://artigercek.com", "kaynak": "Artı Gerçek", "kategori": "Haber", "secici": ".post-title a, h2 a, h3 a, article a", "ozet_secici": ".post-excerpt, p", "genel": True, "hedef": "haberler", "dil": "tr", "ssl_dogrulama": True},
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
    "Maden Riski / Atık":        {"eylem": None,               "etiketler": ["Maden Ocağı", "Ekolojik İhlal"]},
    "Tarım Alanları / Maden":    {"eylem": None,               "etiketler": ["Orman Alanı", "Maden Ocağı"]},
    "Resmi İhale / Maden":       {"eylem": None,               "etiketler": ["Maden Ocağı"]},
    "Resmi / Maden":             {"eylem": None,               "etiketler": ["Maden Ocağı"]},
    "İhale / Enerji":            {"eylem": None,               "etiketler": ["GES", "RES", "HES"]},
    "Resmi / Enerji":            {"eylem": None,               "etiketler": ["GES", "RES", "HES"]},
    "HES / RES / Baraj":         {"eylem": None,               "etiketler": ["HES", "RES", "Sulak Alan"]},
    "JES / Çevre İhlali":        {"eylem": None,               "etiketler": ["Jeotermal", "Ekolojik İhlal"]},
    "ÇED Kararları":             {"eylem": "Hukuk & Dava",     "etiketler": []},
    "ÇED Analizi":               {"eylem": "Hukuk & Dava",     "etiketler": ["Analiz"]},
    "Kamulaştırma":              {"eylem": "Hukuk & Dava",     "etiketler": ["Acele Kamulaştırma"]},
    "Resmi":                     {"eylem": "Resmi Açıklama",   "etiketler": []},
    "İhale":                     {"eylem": None,               "etiketler": []},
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
    "Nesli Tehlike Türler":      {"eylem": None,               "etiketler": []},
    "Yaban Hayatı":              {"eylem": None,               "etiketler": []},
    "Bitki & Habitat":           {"eylem": None,               "etiketler": ["Orman Alanı"]},
    "Su Canlıları":              {"eylem": None,               "etiketler": ["Sulak Alan"]},
    "Hayvan Hakları":            {"eylem": None,               "etiketler": []},
    "Kadınlar & Ekoloji":        {"eylem": None,               "etiketler": []},
    "Çiftçi & Köylü":            {"eylem": None,               "etiketler": []},
    "Balıkçı Toplulukları":      {"eylem": None,               "etiketler": ["Kıyı İhlalleri"]},
    "Gençlik & Ekoloji":         {"eylem": None,               "etiketler": []},
    "Ekolojik Eşitsizlik":       {"eylem": None,               "etiketler": []},
    "Kentsel Çevre":             {"eylem": None,               "etiketler": []},
    "İklim Göçü":                {"eylem": None,               "etiketler": ["İklim Olayları"]},
    "Savaş & Ekoloji":           {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
    "Savaş Teknolojisi":         {"eylem": None,               "etiketler": ["Ekolojik İhlal"]},
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
    "plastik kirlilik", "sondaj", "arama ruhsatı", "TEMA", "WWF", "Greenpeace",
    "doğal yaşam", "yaban hayat", "kuş türü", "balık türü",
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

# ══════════════════════════════════════════════════════════════════
#  17 GÖRÜNTÜ KATEGORİSİ TESPİTİ
# ══════════════════════════════════════════════════════════════════

HABER_17_KAT = [
    "Ekolojik İhlal", "İklim Olayları", "Acele Kamulaştırma", "Kültür Varlığı",
    "Milli Park", "Özel Çevre Koruma Alanı", "Maden Ocağı", "Taş-Mermer Ocağı",
    "Termik Reaktör", "HES", "GES", "RES", "Nükleer Enerji", "Jeotermal",
    "Orman Alanı", "Sulak Alan", "Kıyı İhlalleri"
]

def haber_kategorisi_tespit(kayit: dict) -> str:
    metin = " ".join([
        kayit.get("baslik", ""), kayit.get("ozet", ""),
        kayit.get("kategori", ""),
        " ".join(kayit.get("etiketler") or []),
    ]).lower()

    if any(k in metin for k in ["milli park", "tabiat parkı"]): return "Milli Park"
    if any(k in metin for k in ["özel çevre koruma", "tabiatı koruma", "wdpa", "doğal sit", "koruma alanı"]): return "Özel Çevre Koruma Alanı"
    if any(k in metin for k in ["arkeolojik sit", "tarihi yapı", "kültürel miras"]): return "Kültür Varlığı"
    if any(k in metin for k in ["acele kamulaştırma", "kamulaştırma kararı", "kamulaştırma"]): return "Acele Kamulaştırma"
    
    if any(k in metin for k in ["nükleer", "akkuyu"]): return "Nükleer Enerji"
    if any(k in metin for k in ["termik santral", "kömürlü santral", "soma termik"]): return "Termik Reaktör"
    if any(k in metin for k in ["jeotermal", "jes ", "sıcak su"]): return "Jeotermal"
    if any(k in metin for k in ["hidroelektrik", "hes ", "baraj", "regülat", "su hakkı"]): return "HES"
    if any(k in metin for k in ["rüzgar enerjisi", "res ", "türbin"]): return "RES"
    if any(k in metin for k in ["güneş enerjisi", "ges ", "solar"]): return "GES"
    
    if any(k in metin for k in ["taş ocağı", "mermer ocağı", "kum ocağı", "çakıl ocağı", "taşocak"]): return "Taş-Mermer Ocağı"
    if any(k in metin for k in ["maden", "kömür", "bakır", "altın", "mapeg", "maden ruhsat", "siyanür"]): return "Maden Ocağı"
    
    if any(k in metin for k in ["kıyı", "deniz kirlil", "kıyı dolgu", "marina ihlali", "koy ", "körfez", "iskele", "denize beton"]): return "Kıyı İhlalleri"
    if any(k in metin for k in ["sulak alan", "göl ", "lagün", "bataklık", "ramsar"]): return "Sulak Alan"
    if any(k in metin for k in ["orman", "ağaçlandırma", "ağaç kesiml", "orman tahribi", "ormansızlaş"]): return "Orman Alanı"
    
    if any(k in metin for k in ["iklim", "deprem", "sel ", "yangın", "afet", "kuraklık", "aşırı sıcaklık", "erozyon", "sera gazı", "karbon", "iklim krizi", "hava kirlil"]): return "İklim Olayları"
    if any(k in metin for k in ["kaçak avcılık", "atık dökümü", "yasadışı kesim", "çev ihlali", "çevre ihlali", "çevre katliamı", "kirlilik", "pestisit"]): return "Ekolojik İhlal"

    return "Ekolojik İhlal" # Default


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


def ekoloji_puani(baslik: str, ozet: str = "", genel_kaynak: bool = False, hedef: str = "haberler") -> int:
    metin = (baslik + " " + ozet).lower()
    if _anahtar_var(metin, GUCLU_NEGATIF): return 0
    if genel_kaynak and _anahtar_var(metin, GENEL_KAYNAK_NEGATIF): return 0
    puan = 0
    for k in YUKSEK_SINYAL:
        if _ara(metin, k): puan += 3
    for k in ORTA_SINYAL:
        if _ara(metin, k): puan += 1
    baslik_lower = baslik.lower()
    for k in YUKSEK_SINYAL:
        if _ara(baslik_lower, k): puan += 2
    if hedef in ("raporlar", "makaleler", "uluslararasi") and puan == 0:
        if _anahtar_var(metin, RAPOR_SINYAL + KOSE_SINYAL): puan = 2
    return puan


def icerik_tipi_tespit(baslik: str, ozet: str, hedef: str, kaynak: str) -> str:
    if hedef == "uluslararasi": return "uluslararasi"
    metin = (baslik + " " + ozet).lower()
    if hedef == "raporlar" or any(k in metin for k in RAPOR_SINYAL): return "rapor"
    if hedef == "makaleler" or any(k in metin for k in KOSE_SINYAL): return "kose"
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

BOLUM_DOGRULA_ANAHTAR = {
    "lgbti":    ["lgbti", "lgbtİ", "lgbtq", "queer", "kuir", "eşcinsel", "gökkuşağı", "trans birey", "onur yürüyüş", "onur haftası", "pride", "biseksüel", "interseks", "gey hareket"],
    "kadinlar": ["kadın", "kadınlar", "feminist", "feminizm", "ekofeminist", "ekofeminizm", "kadın kooperatif", "kadın emek", "anneler", "toplumsal cinsiyet", "kadın hakları", "kadın çiftçi", "kadın üretici", "kadın emekçi", "kız çocuk", "ebeveyn"],
    "ciftci":   ["çiftçi", "köylü", "köy ", "tarım", "tarımsal", "ekin", "hasat", "mera", "tohum", "fındık üretic", "çay üretic", "buğday", "besici", "hayvancılık", "süt üretic", "küçük üretici", "üretici", "rençber", "bağcı", "bahçıvan", "kooperatif", "yayla", "otlak", "zeytin üretic", "çiftlik", "ziraat"],
    "hayvan-haklari": ["hayvan", "köpe", "kedi", "barınak", "sokak hayvan", "sahiplendir", "veteriner", "yaban", "pati", "fauna", "at hakları", "eşek", "kısırlaştır"],
}

BOLUM_GUVENILIR_KAYNAK = {
    "lgbti": {"Kaos GL", "17 Mayıs Derneği", "Coalition Rainbow"},
}

def bolum_dogrula(kaynak_bolum, baslik, ozet, kaynak_adi=None):
    if not kaynak_bolum: return None
    if (kaynak_adi or "").strip() in BOLUM_GUVENILIR_KAYNAK.get(kaynak_bolum, ()): return kaynak_bolum
    anahtarlar = BOLUM_DOGRULA_ANAHTAR.get(kaynak_bolum)
    if anahtarlar is None: return kaynak_bolum
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
    if etiket_icerik and etiket_icerik not in etiket: etiket.append(etiket_icerik)
    kayit["eylem"]            = eylem
    kayit["etiketler"]        = etiket
    kayit["haber_kategorisi"] = haber_kategorisi_tespit(kayit)
    return kayit

# ══════════════════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")
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
        ATLA = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","fbclid","gclid","mc_cid","mc_eid","ref","source","via","trk"}
        temiz = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in ATLA]
        return urlunparse(p._replace(query=urlencode(temiz), fragment="")).rstrip("/")
    except Exception:
        return url.split("?")[0].rstrip("/")

def baslik_normalize(baslik: str) -> str:
    return re.sub(r"\s+", " ", baslik).strip().lower()

_BASLIK_EK_RE = re.compile(r"\s*[-–—|]\s*[^-–—|]{1,45}$")
def baslik_dedup_anahtar(baslik: str) -> str:
    s = baslik_normalize(baslik)
    s2 = _BASLIK_EK_RE.sub("", s)
    return s2 if len(s2) >= 15 else s

def haber_id(url: str, baslik: str, kaynak: str = "") -> str:
    if url and ("news.google.com" in url or "/rss/articles/" in url):
        return hashlib.md5(f"{baslik_normalize(baslik)}|{kaynak.lower().strip()}".encode()).hexdigest()[:12]
    return hashlib.md5(f"{url_normalize(url)}|{baslik_normalize(baslik)}".encode()).hexdigest()[:12]

def tarih_normalize(tarih_str) -> Optional[str]:
    if not tarih_str: return None
    try:
        if hasattr(tarih_str, "tm_year"):
            dt = datetime(*tarih_str[:6], tzinfo=timezone.utc).astimezone(TR_TZ)
            return dt.isoformat()
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(str(tarih_str)).astimezone(TR_TZ)
        return dt.isoformat()
    except Exception:
        return str(tarih_str)

def fetch(url: str, timeout: int = 8, ssl_dogrulama: bool = True) -> Optional[requests.Response]:
    verify = ssl_dogrulama and not any(h in url for h in SSL_NO_VERIFY_HOSTS)
    if not verify: urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=verify)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r
    except requests.exceptions.SSLError:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r
        except Exception:
            return None
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════
#  RSS TARAMA
# ══════════════════════════════════════════════════════════════════

def _rss_tek_kaynak(kaynak: dict) -> tuple:
    genel  = kaynak.get("genel", False)
    hedef  = kaynak.get("hedef", "haberler")
    dil    = kaynak.get("dil", "tr")
    kayitlar = []
    log.info(f"RSS: {kaynak['kaynak']} [{hedef}|{dil}|genel={genel}]")
    try:
        feed = feedparser.parse(kaynak["url"])
        if feed.bozo and not feed.entries: return hedef, kayitlar
        for entry in feed.entries[:25]:
            baslik = entry.get("title", "").strip()
            link   = entry.get("link", "")
            ozet   = BeautifulSoup(entry.get("summary", ""), "lxml").get_text(" ", strip=True)
            tarih  = tarih_normalize(entry.get("published_parsed") or entry.get("updated_parsed"))
            if not baslik or not link: continue
            puan = ekoloji_puani(baslik, ozet, genel, hedef)
            if puan < (4 if genel else 1): continue
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
            }
            _b = bolum_dogrula(kaynak.get("bolum"), kayit.get("baslik"), kayit.get("ozet"), kaynak["kaynak"])
            if _b: kayit["bolum"] = _b
            kayit = zenginlestir(kayit)
            kayitlar.append(kayit)
    except Exception:
        pass
    return hedef, kayitlar

def rss_tara(kaynaklar: list) -> dict:
    sonuc: dict = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for fut in as_completed({ex.submit(_rss_tek_kaynak, k): k for k in kaynaklar}):
            try:
                hedef, kayitlar = fut.result()
                for kayit in kayitlar:
                    sonuc.setdefault(hedef, []).append(kayit)
            except Exception:
                pass
    return sonuc

# ══════════════════════════════════════════════════════════════════
#  WEB SCRAPING
# ══════════════════════════════════════════════════════════════════

def _web_tek_kaynak(kaynak: dict) -> tuple:
    genel         = kaynak.get("genel", False)
    hedef         = kaynak.get("hedef", "haberler")
    dil           = kaynak.get("dil", "tr")
    ssl_dogrulama = kaynak.get("ssl_dogrulama", True)
    kayitlar = []
    log.info(f"Web: {kaynak['kaynak']} [{hedef}|{dil}|genel={genel}]")
    r = fetch(kaynak["url"], ssl_dogrulama=ssl_dogrulama)
    if not r: return hedef, kayitlar
    try:
        soup = BeautifulSoup(r.text, "lxml")
        linkler = soup.select(kaynak["secici"])[:20] or soup.select(FALLBACK_SELECTOR)[:20]
        for a in linkler:
            baslik = a.get_text(" ", strip=True)
            if not baslik or len(baslik) < 10: continue
            href = a.get("href", "")
            if not href: continue
            link = urljoin(kaynak["url"], href)
            ozet = ""
            if kaynak.get("ozet_secici"):
                parent = a.find_parent(["article", "div", "li"])
                if parent:
                    el = parent.select_one(kaynak["ozet_secici"])
                    if el: ozet = el.get_text(" ", strip=True)[:300]
            if ekoloji_puani(baslik, ozet, genel, hedef) < (4 if genel else 1): continue
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
            }
            _b = bolum_dogrula(kaynak.get("bolum"), kayit.get("baslik"), kayit.get("ozet"), kaynak["kaynak"])
            if _b: kayit["bolum"] = _b
            kayit = zenginlestir(kayit)
            kayitlar.append(kayit)
    except Exception:
        pass
    return hedef, kayitlar

def web_tara(kaynaklar: list) -> dict:
    sonuc: dict = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fut in as_completed({ex.submit(_web_tek_kaynak, k): k for k in kaynaklar}):
            try:
                hedef, kayitlar = fut.result()
                for kayit in kayitlar:
                    sonuc.setdefault(hedef, []).append(kayit)
            except Exception:
                pass
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
        except Exception:
            pass

    gorulen_idler, gorulen_urller, gorulen_basliklar = set(), set(), set()
    baslik_to_id: dict = {}
    for kol in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
        for h in eski.get(kol, []):
            h_id = str(h.get("id", ""))
            h_bas = baslik_dedup_anahtar(h.get("baslik", ""))
            gorulen_idler.add(h_id)
            if h.get("url"): gorulen_urller.add(url_normalize(h["url"]))
            if h_bas:
                gorulen_basliklar.add(h_bas)
                if not h_id.isdigit(): baslik_to_id[h_bas] = h_id

    rss_haber = rss_tara(RSS_KAYNAKLARI)
    rss_rapor = rss_tara(RAPOR_RSS_KAYNAKLARI)
    rss_makale = rss_tara(MAKALE_RSS_KAYNAKLARI)
    rss_ulus = rss_tara(ULUSLARARASI_RSS_KAYNAKLARI)
    web_haber = web_tara(WEB_KAYNAKLARI)
    web_rapor = web_tara(RAPOR_WEB_KAYNAKLARI)
    web_makale = web_tara(MAKALE_WEB_KAYNAKLARI)
    web_ulus = web_tara(ULUSLARARASI_WEB_KAYNAKLARI)
    rss_ekosistem = rss_tara(EKOSISTEM_RSS_KAYNAKLARI)
    web_ekosistem = web_tara(EKOSISTEM_WEB_KAYNAKLARI)

    def filtrele_yeni(kaynaklar: list) -> list:
        yeni = []
        for h in kaynaklar:
            h_id, h_url, h_bas = str(h["id"]), url_normalize(h.get("url", "")), baslik_dedup_anahtar(h.get("baslik", ""))
            if h_id in gorulen_idler or (h_url and h_url in gorulen_urller and "news.google.com" not in h_url): continue
            if h_bas and h_bas in gorulen_basliklar:
                eski_id = baslik_to_id.get(h_bas)
                if eski_id and h_id.isdigit() and not eski_id.isdigit():
                    for kol_adi in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
                        eski.get(kol_adi, [])[:] = [x for x in eski.get(kol_adi, []) if str(x.get("id", "")) != eski_id]
                    gorulen_idler.discard(eski_id)
                    gorulen_idler.add(h_id)
                    if h_url: gorulen_urller.add(h_url)
                    baslik_to_id[h_bas] = h_id
                    yeni.append(h)
                continue
            yeni.append(h)
            gorulen_idler.add(h_id)
            if h_url: gorulen_urller.add(h_url)
            if h_bas:
                gorulen_basliklar.add(h_bas)
                if not h_id.isdigit(): baslik_to_id[h_bas] = h_id
        return yeni

    def birlestir_kaynak(*dicts):
        sonuc = {}
        for d in dicts:
            for k, v in d.items(): sonuc.setdefault(k, []).extend(v)
        return sonuc

    tum_yeni = birlestir_kaynak(rss_haber, rss_rapor, rss_makale, rss_ulus, rss_ekosistem, web_haber, web_rapor, web_makale, web_ulus, web_ekosistem)

    koleksiyonlar = {}
    for kol in ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem"):
        yeni = filtrele_yeni(tum_yeni.get(kol, []))
        for h in yeni: h.pop("_puan", None)
        limit = max_haber if kol == "haberler" else max_diger
        birles = yeni + eski.get(kol, [])
        birles.sort(key=lambda x: x.get("tarih") or "1970-01-01", reverse=True)
        koleksiyonlar[kol] = birles[:limit]

    for kol in ("haberler", "ekosistem"):
        for h in koleksiyonlar.get(kol, []):
            kay = (h.get("kaynak") or "").strip()
            _garanti = next((b for b, kk in BOLUM_GUVENILIR_KAYNAK.items() if kay in kk), None)
            if _garanti:
                if h.get("bolum") != _garanti: h["bolum"] = _garanti
                continue
            metin = ((h.get("baslik") or "") + " " + (h.get("ozet") or "")).lower()
            bol = h.get("bolum")
            if bol in BOLUM_DOGRULA_ANAHTAR and not any(k in metin for k in BOLUM_DOGRULA_ANAHTAR[bol]):
                h["bolum"] = None

    cikti = {
        "meta": {"guncelleme": datetime.now(TR_TZ).isoformat(), "toplam_haber": len(koleksiyonlar["haberler"]), "toplam_rapor": len(koleksiyonlar["raporlar"]), "toplam_makale": len(koleksiyonlar["makaleler"]), "toplam_ulus": len(koleksiyonlar["uluslararasi"]), "toplam_ekosistem": len(koleksiyonlar["ekosistem"])},
        **koleksiyonlar,
    }

    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

    cikti_dir = p.parent
    dosya_haritasi = {"haberler": "haberler_veri.json", "raporlar": "raporlar_veri.json", "makaleler": "makaleler_veri.json", "uluslararasi": "uluslararasi_veri.json", "ekosistem": "ekosistem_veri.json"}
    for kol, dosya_adi in dosya_haritasi.items():
        parca = {"meta": cikti["meta"], kol: koleksiyonlar[kol]}
        parca_tmp = cikti_dir / (dosya_adi + ".tmp")
        parca_tmp.write_text(json.dumps(parca, ensure_ascii=False, indent=2), encoding="utf-8")
        parca_tmp.replace(cikti_dir / dosya_adi)

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
            try: tara(args.cikti, args.max_haber, args.max_diger)
            except KeyboardInterrupt: sys.exit(0)
            except Exception: pass
            time.sleep(args.aralik * 60)
    else: tara(args.cikti, args.max_haber, args.max_diger)

if __name__ == "__main__": main()
'''

with open('tarayici.py', 'w', encoding='utf-8') as f:
    f.write(tarayici_content)