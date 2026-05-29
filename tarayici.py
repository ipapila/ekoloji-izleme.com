#!/usr/bin/env python3
"""
tarayici.py içindeki 403 veren RSS kaynaklarını
Google News proxy versiyonlarıyla değiştirir.
Kullanım: python3 rss_guncelle.py tarayici.py
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Kullanım: python3 rss_guncelle.py tarayici.py")
    sys.exit(1)

src = Path(sys.argv[1]).read_text(encoding="utf-8")

# 403 veren → Google News proxy ile değiştir
DEGISIKLIKLER = [
    # Bianet çevre RSS → Google News
    (
        '"url": "https://bianet.org/topic/cevre/feed/rss"',
        '"url": "https://news.google.com/rss/search?q=site:bianet.org+%C3%A7evre+OR+ekoloji+OR+maden&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # İklim Haber RSS → Google News
    (
        '"url": "https://iklimhaber.org/feed/"',
        '"url": "https://news.google.com/rss/search?q=site:iklimhaber.org&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Yeşil Gazete RSS → Google News
    (
        '"url": "https://yesilgazete.org/feed/"',
        '"url": "https://news.google.com/rss/search?q=site:yesilgazete.org&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Evrensel RSS → Google News
    (
        '"url": "https://www.evrensel.net/rss/ekoloji.xml"',
        '"url": "https://news.google.com/rss/search?q=site:evrensel.net+%C3%A7evre+OR+ekoloji&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Birgün → Google News (genel=True kalacak)
    (
        '"url": "https://www.birgun.net/xml/rss.xml"',
        '"url": "https://news.google.com/rss/search?q=site:birgun.net+%C3%A7evre+OR+ekoloji+OR+maden&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # TEMA RSS → Google News
    (
        '"url": "https://www.tema.org.tr/duyurular?format=feed"',
        '"url": "https://news.google.com/rss/search?q=site:tema.org.tr&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Greenpeace TR RSS → Google News
    (
        '"url": "https://www.greenpeace.org/turkey/feed/"',
        '"url": "https://news.google.com/rss/search?q=site:greenpeace.org+turkey+%C3%A7evre+OR+iklim&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Sözcü → Google News (zaten 0 kabul veriyordu)
    (
        '"url": "https://www.sozcu.com.tr/rss/cevre.xml"',
        '"url": "https://news.google.com/rss/search?q=site:sozcu.com.tr+%C3%A7evre+OR+ekoloji+OR+maden&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Cumhuriyet → Google News
    (
        '"url": "https://www.cumhuriyet.com.tr/rss/cevre.rss"',
        '"url": "https://news.google.com/rss/search?q=site:cumhuriyet.com.tr+%C3%A7evre+OR+ekoloji&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Makale: Bianet ana feed → Google News
    (
        '"url": "https://bianet.org/bianet/feed/rss"',
        '"url": "https://news.google.com/rss/search?q=site:bianet.org+k%C3%B6%C5%9Fe+OR+g%C3%B6r%C3%BC%C5%9F+OR+yorum+cevre&hl=tr&gl=TR&ceid=TR:tr"'
    ),
    # Doğa Derneği ekosistem RSS → Google News
    (
        '"url": "https://news.google.com/rss/search?q=site:dogadernegi.org+tür+nesli&hl=tr&gl=TR&ceid=TR:tr"',
        '"url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr"'
    ),
]

degistirilen = 0
for eski, yeni in DEGISIKLIKLER:
    if eski in src:
        src = src.replace(eski, yeni, 1)
        degistirilen += 1
        print(f"✓ Değiştirildi: {eski[:60]}...")
    else:
        print(f"⚠ Bulunamadı: {eski[:60]}...")

out = Path(sys.argv[1]).with_stem(Path(sys.argv[1]).stem + "_patched")
out.write_text(src, encoding="utf-8")
print(f"\n✓ {degistirilen} değişiklik → {out}")
