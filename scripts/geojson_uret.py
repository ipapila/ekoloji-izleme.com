#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/geojson_uret.py — Ekoloji İhlal Tarayıcı
Resmî Gazete, MAPEG, EPDK, ÇED, OGM kaynaklarından ihlal verisi çeker,
Claude API ile analiz eder, data.json'daki ihlaller dizisine ekler.
"""

import env_yukle  # .env dosyasını yükler

import json, os, re, time, datetime, random, string, base64
import requests
from bs4 import BeautifulSoup
import anthropic

# ─── YAPILANDIRMA ──────────────────────────────────────────────────
REPO_OWNER  = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME   = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
FILE_PATH   = "data.json"
API_KEY     = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_YENI    = 20   # tek çalışmada eklenecek max ihlal sayısı

# ─── TARANACAK KAYNAKLAR ───────────────────────────────────────────
KAYNAKLAR = [
    {
        "ad": "Resmî Gazete — Acele Kamulaştırma",
        "url": "https://www.resmigazete.gov.tr/",
        "arama": "https://www.resmigazete.gov.tr/ilanlar/index.php?ilan=acele+kamulastirma",
        "tip_oneri": "Acele Kamulaştırma",
        "kaynak_turu": "resmi",
    },
    {
        "ad": "Resmî Gazete — Maden Ruhsatı",
        "url": "https://www.resmigazete.gov.tr/",
        "arama": "https://www.resmigazete.gov.tr/ilanlar/index.php?ilan=maden+ruhsat",
        "tip_oneri": "Maden Ocağı",
        "kaynak_turu": "resmi",
    },
    {
        "ad": "MAPEG Maden İşlemleri",
        "url": "https://www.mapeg.gov.tr",
        "arama": "https://www.mapeg.gov.tr/duyurular.aspx",
        "tip_oneri": "Maden Ocağı",
        "kaynak_turu": "resmi",
    },
    {
        "ad": "ÇED Kararları",
        "url": "https://ced.csb.gov.tr",
        "arama": "https://ced.csb.gov.tr/projeler",
        "tip_oneri": "Ekolojik İhlal",
        "kaynak_turu": "resmi",
    },
    {
        "ad": "EPDK Duyurular",
        "url": "https://www.epdk.gov.tr",
        "arama": "https://www.epdk.gov.tr/Detay/Icerik/3-0-24-3",
        "tip_oneri": "RES",
        "kaynak_turu": "resmi",
    },
    {
        "ad": "Google News — Acele Kamulaştırma",
        "url": "https://news.google.com",
        "arama": "https://news.google.com/rss/search?q=acele+kamulaştırma+orman+maden&hl=tr&gl=TR&ceid=TR:tr",
        "tip_oneri": "Acele Kamulaştırma",
        "kaynak_turu": "haber",
    },
    {
        "ad": "Google News — RES HES Projesi",
        "url": "https://news.google.com",
        "arama": "https://news.google.com/rss/search?q=RES+HES+proje+izin+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "tip_oneri": "RES",
        "kaynak_turu": "haber",
    },
    {
        "ad": "Google News — Maden Ruhsat",
        "url": "https://news.google.com",
        "arama": "https://news.google.com/rss/search?q=maden+ruhsat+izin+ÇED+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "tip_oneri": "Maden Ocağı",
        "kaynak_turu": "haber",
    },
    {
        "ad": "Bianet — Çevre",
        "url": "https://bianet.org",
        "arama": "https://bianet.org/topic/cevre/feed/rss",
        "tip_oneri": "Ekolojik İhlal",
        "kaynak_turu": "haber",
    },
]

KATEGORILER = [
    "Ekolojik İhlal", "İklim Olayları", "Acele Kamulaştırma", "Kültür Varlığı",
    "Milli Park", "Özel Çevre Koruma Alanı", "Maden Ocağı", "Taş-Mermer Ocağı",
    "Termik Reaktör", "HES", "GES", "RES", "Nükleer Enerji", "Jeotermal",
    "Orman Alanı", "Sulak Alan", "Kıyı İhlalleri",
]

SISTEM_PROMPTU = f"""
Sen Türkiye'deki ekolojik ihlalleri ve çevre projelerini takip eden bir veri analisti asistanısın.

Sana haber metinleri veya resmi belgeler verilecek. Bunlardan somut ekolojik ihlal/proje kayıtları çıkarman gerekiyor.

## Çıkaracağın veri formatı (JSON dizisi):

```json
[
  {{
    "ad": "Proje veya ihlalin kısa adı (max 80 karakter)",
    "tip": "Aşağıdaki 17 kategoriden TAM biri",
    "il": "İl adı (Türkçe, büyük harfle başlayan)",
    "ilce": "İlçe adı veya boş string",
    "durum": "Aktif | Planlama | Devam Ediyor | Yargıda | Durduruldu",
    "belge_no": "Resmî Gazete sayısı, karar numarası veya boş string",
    "kaynak": "Kaynak kurum/site adı",
    "kaynak_link": "Haberin/belgenin DOĞRUDAN URL'si (ana sayfa değil)",
    "aciklama": "1-2 cümle özet",
    "alt_kategori": "Alt kategori veya boş string",
    "kaynak_turu": "resmi | haber | stk"
  }}
]
```

## 17 Kategori (TAM olarak kullan):
{chr(10).join(f"- {k}" for k in KATEGORILER)}

## Kurallar:
- Sadece SOMUT ihlal/proje kayıtları çıkar (genel haberler değil)
- Her kayıt benzersiz bir proje/ihlali temsil etmeli
- il alanı ZORUNLU — bulamazsan kaydı atlat
- kaynak_link ana sayfa olmamalı, direkt haber/belge linki olmalı
- Bulamazsan boş JSON dizisi döndür: []
- SADECE JSON döndür, başka hiçbir şey yazma
"""

# ─── YARDIMCILAR ───────────────────────────────────────────────────

def uid():
    chars = string.ascii_lowercase + string.digits
    return 'r' + ''.join(random.choices(chars, k=9)) + str(int(time.time() * 1000))


def html_cek(url, timeout=15):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "ekoloji-izleme.com-bot/3.0",
    ]
    for ua in user_agents:
        try:
            r = requests.get(url, timeout=timeout,
                             headers={"User-Agent": ua,
                                      "Accept": "text/html,application/xhtml+xml,application/xml,*/*",
                                      "Accept-Language": "tr-TR,tr;q=0.9"})
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"  ⚠ HTTP hatası ({url[:60]}): {e}")
    print(f"  ⚠ Tüm User-Agent'lar başarısız ({url[:60]})")
    return ""


def rss_cek(url):
    """RSS feed'den başlık+link+özet çıkar."""
    import xml.etree.ElementTree as ET
    html = html_cek(url)
    if not html:
        return []
    try:
        root = ET.fromstring(html.encode("utf-8", errors="replace"))
        items = root.findall(".//item") or root.findall(".//entry")
        sonuc = []
        for item in items[:15]:
            def txt(tag):
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""
            baslik = txt("title")
            link   = txt("link") or txt("guid")
            ozet   = txt("description") or txt("summary") or ""
            ozet   = re.sub(r"<[^>]+>", " ", ozet).strip()[:400]
            if baslik and link:
                sonuc.append({"baslik": baslik, "link": link, "ozet": ozet})
        return sonuc
    except Exception as e:
        print(f"  ⚠ RSS parse hatası: {e}")
        return []


def web_metin_cek(url):
    """Sayfadan temiz metin çıkar."""
    html = html_cek(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    metin = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", metin)[:3000]


def claude_analiz(metin, kaynak_ad, tip_oneri, kaynak_turu):
    """Claude API ile metinden ihlal kayıtları çıkar."""
    if not API_KEY:
        print("  ⚠ ANTHROPIC_API_KEY yok, atlanıyor.")
        return []
    try:
        client = anthropic.Anthropic(api_key=API_KEY)
        kullanici = f"""Kaynak: {kaynak_ad}
Önerilen kategori: {tip_oneri}
Kaynak türü: {kaynak_turu}

Metin:
{metin}

Bu metinden ekolojik ihlal/proje kayıtlarını çıkar. Sadece JSON dizisi döndür."""

        yanit = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SISTEM_PROMPTU,
            messages=[{"role": "user", "content": kullanici}],
        )

        ham = ""
        for blok in yanit.content:
            if hasattr(blok, "text"):
                ham = blok.text.strip()
                break

        # JSON temizle
        ham = re.sub(r"^```json\s*", "", ham)
        ham = re.sub(r"^```\s*",    "", ham)
        ham = re.sub(r"\s*```$",    "", ham).strip()

        kayitlar = json.loads(ham)
        if isinstance(kayitlar, list):
            return kayitlar
        return []

    except json.JSONDecodeError:
        print(f"  ⚠ JSON parse hatası (Claude yanıtı)")
        return []
    except anthropic.RateLimitError:
        print("  ⚠ API rate limit — 30sn bekleniyor")
        time.sleep(30)
        return []
    except Exception as e:
        print(f"  ⚠ Claude API hatası: {e}")
        return []


def nominatim_geocode(il, ilce=""):
    """Nominatim ile koordinat bul."""
    sorgu = f"{ilce} {il} Türkiye".strip()
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": sorgu, "format": "json", "limit": 1},
            headers={"User-Agent": "ekoloji-izleme.com/3.0"},
            timeout=10,
        )
        data = r.json()
        if data:
            lat = float(data[0]["lat"]) + random.uniform(-0.003, 0.003)
            lng = float(data[0]["lon"]) + random.uniform(-0.003, 0.003)
            return {"lat": round(lat, 5), "lng": round(lng, 5)}
    except Exception:
        pass
    return {"lat": 0, "lng": 0}


# ─── GITHUB ────────────────────────────────────────────────────────

def github_oku():
    token = os.environ.get("GITHUB_TOKEN")
    raw = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    r = requests.get(raw, timeout=15)
    if r.status_code == 200:
        try:
            sha_r = requests.get(
                f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            sha = sha_r.json().get("sha") if sha_r.status_code == 200 else None
            return r.json(), sha
        except Exception:
            pass
    return None, None


def github_yaz(data, sha):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN yok!")
        return False
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    content = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"ihlal güncellemesi {datetime.date.today()}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=20,
    )
    if r.status_code in (200, 201):
        print(f"✅ GitHub güncellendi — {len(data.get('ihlaller', []))} ihlal")
        return True
    else:
        print(f"❌ GitHub yazma hatası {r.status_code}: {r.text[:200]}")
        return False


# ─── ANA FONKSİYON ─────────────────────────────────────────────────

def main():
    print("📥 data.json okunuyor…")
    data, sha = github_oku()
    if data is None:
        print("⚠ Uzak veri alınamadı — boş yapıyla başlanıyor.")
        data = {"ihlaller": [], "haberler": [], "raporlar": [], "_meta": {}}
        sha = None

    mevcut_ihlaller = data.get("ihlaller", [])
    mevcut_adlar = {
        (i.get("ad", "") + "|" + i.get("il", "")).lower()
        for i in mevcut_ihlaller
    }
    print(f"  Mevcut: {len(mevcut_ihlaller)} ihlal")

    yeni_ihlaller = []
    toplam_eklenen = 0

    for kaynak in KAYNAKLAR:
        if toplam_eklenen >= MAX_YENI:
            print(f"⚠ Max {MAX_YENI} ihlal sınırına ulaşıldı.")
            break

        print(f"\n🔍 {kaynak['ad']} taranıyor…")

        # İçerik çek
        arama_url = kaynak["arama"]
        if "feed/rss" in arama_url or "rss/search" in arama_url:
            # RSS kaynağı
            items = rss_cek(arama_url)
            if not items:
                continue
            metin = "\n\n".join([
                f"Başlık: {i['baslik']}\nLink: {i['link']}\nÖzet: {i['ozet']}"
                for i in items
            ])
        else:
            # Web sayfası
            metin = web_metin_cek(arama_url)
            if not metin:
                continue

        # Claude analizi
        kayitlar = claude_analiz(
            metin,
            kaynak["ad"],
            kaynak["tip_oneri"],
            kaynak["kaynak_turu"],
        )
        print(f"  📋 {len(kayitlar)} kayıt bulundu")

        # İşle ve ekle
        for k in kayitlar:
            if toplam_eklenen >= MAX_YENI:
                break

            ad = k.get("ad", "").strip()
            il = k.get("il", "").strip()
            tip = k.get("tip", "").strip()

            if not ad or not il or not tip:
                continue
            if tip not in KATEGORILER:
                # En yakın kategoriyi bul
                tip = kaynak["tip_oneri"]

            anahtar = (ad + "|" + il).lower()
            if anahtar in mevcut_adlar:
                continue

            # Geocoding
            time.sleep(1.1)  # Nominatim rate limit
            koord = nominatim_geocode(il, k.get("ilce", ""))

            ihlal = {
                "id": uid(),
                "ad": ad,
                "tip": tip,
                "il": il,
                "ilce": k.get("ilce", ""),
                "koordinatlar": koord,
                "alan_ha": 0,
                "durum": k.get("durum", "Aktif"),
                "belge_no": k.get("belge_no", ""),
                "eklenme": datetime.date.today().isoformat(),
                "kaynak": k.get("kaynak", kaynak["ad"]),
                "kaynak_link": k.get("kaynak_link", ""),
                "aciklama": k.get("aciklama", ""),
                "alt_kategori": k.get("alt_kategori", ""),
                "kaynak_turu": k.get("kaynak_turu", kaynak["kaynak_turu"]),
            }

            # ihlaller.html uyumluluğu için ek alanlar
            ihlal["baslik"] = ad
            ihlal["konum"]  = f"{il}{', ' + ihlal['ilce'] if ihlal['ilce'] else ''}"
            ihlal["kategori"] = tip
            ihlal["siddet"]   = "takipte"
            ihlal["tarih"]    = ihlal["eklenme"]
            ihlal["lat"] = koord["lat"] if koord["lat"] != 0 else None
            ihlal["lng"] = koord["lng"] if koord["lng"] != 0 else None

            yeni_ihlaller.append(ihlal)
            mevcut_adlar.add(anahtar)
            toplam_eklenen += 1
            print(f"  ✓ {ad[:60]} [{il}]")

        time.sleep(2)  # Kaynaklar arası bekleme

    if not yeni_ihlaller:
        print("\n✅ Yeni ihlal bulunamadı.")
        return

    print(f"\n✅ {len(yeni_ihlaller)} yeni ihlal ekleniyor…")
    data["ihlaller"] = yeni_ihlaller + mevcut_ihlaller
    data["_meta"] = {
        "guncelleme":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":       "otomatik_tarama_v4",
        "ihlal_sayisi": len(data["ihlaller"]),
        "haber_sayisi": len(data.get("haberler", [])),
    }

    print("📤 GitHub'a yazılıyor…")
    github_yaz(data, sha)


if __name__ == "__main__":
    main()
