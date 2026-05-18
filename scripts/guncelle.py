import json
import requests
import os
import base64
import datetime
import xml.etree.ElementTree as ET
import re

REPO_OWNER = "ipapila"
REPO_NAME  = "ekoloji-izleme"
FILE_PATH  = "data.json"

# ── Anahtar kelimeler ──────────────────────────────────────────────
EKOLOJI_KELIMELER = [
    "maden", "taş ocağı", "taşocağı", "orman", "yangın", "HES", "RES", "baraj",
    "termik", "nükleer", "kıyı", "deniz kirliliği", "su kirliliği", "atık",
    "çevre ihlali", "ÇED", "kamulaştırma", "imara açılıyor", "doğa",
    "ekoloji", "biyoçeşitlilik", "nesli tükenmekte", "sera gazı", "iklim",
    "hava kirliliği", "toprak kirliliği", "plastik", "depolama sahası",
    "sondaj", "arama ruhsatı", "işletme ruhsatı", "EPDK", "MAPEG",
    "ağaç katliamı", "ormansızlaşma", "dere", "göl", "sulak alan",
]

KAYNAK_RSS = [
    {
        "ad": "Bianet",
        "url": "https://bianet.org/biamag/feed/rss",
        "etiket": "Haber",
    },
    {
        "ad": "Bianet Çevre",
        "url": "https://bianet.org/topic/cevre/feed/rss",
        "etiket": "Haber",
    },
    {
        "ad": "Gazete Duvar",
        "url": "https://www.gazeteduvar.com.tr/feed",
        "etiket": "Haber",
    },
    {
        "ad": "350.org Türkiye",
        "url": "https://350.org/tr/feed/",
        "etiket": "Direniş",
    },
]

# ── GitHub helpers ─────────────────────────────────────────────────
def get_sha():
    token = os.environ.get("GITHUB_TOKEN")
    url   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    resp  = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if resp.status_code == 200:
        return resp.json().get("sha")
    print(f"⚠️  SHA alınamadı: HTTP {resp.status_code}")
    return None

def get_remote_data():
    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    resp = requests.get(raw_url, timeout=15)
    if resp.status_code == 200:
        try:
            return resp.json(), get_sha()
        except Exception as e:
            print(f"❌ JSON parse hatası: {e}")
            return None, None
    print(f"❌ Veri alınamadı: HTTP {resp.status_code}")
    return None, None

def update_remote_data(new_data, sha):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN bulunamadı!")
        return
    url     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    content = base64.b64encode(
        json.dumps(new_data, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"otomatik güncelleme {datetime.date.today().isoformat()}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=headers, json=payload, timeout=20)
    if resp.status_code in (200, 201):
        ihlal_n = len(new_data.get("ihlaller", []))
        haber_n = len(new_data.get("haberler", []))
        print(f"✅ GitHub güncellendi — {ihlal_n} ihlal, {haber_n} haber.")
    else:
        print(f"❌ Güncelleme hatası: {resp.status_code}")
        print(resp.text[:500])

# ── Temizleyiciler ─────────────────────────────────────────────────
def html_temizle(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:800]

def tarih_normalize(tarih_str):
    """RSS tarihini YYYY-MM-DD formatına çevirir."""
    if not tarih_str:
        return datetime.date.today().isoformat()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            return datetime.datetime.strptime(tarih_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Son çare: ilk 10 karakter
    return tarih_str[:10] if len(tarih_str) >= 10 else datetime.date.today().isoformat()

def ekoloji_mi(baslik, ozet=""):
    metin = (baslik + " " + ozet).lower()
    return any(k.lower() in metin for k in EKOLOJI_KELIMELER)

# ── RSS çekici ─────────────────────────────────────────────────────
def rss_cek(kaynak):
    haberler = []
    try:
        resp = requests.get(kaynak["url"], timeout=20,
                            headers={"User-Agent": "ekoloji-izleme-bot/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        for item in items[:30]:
            def txt(tag):
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            baslik = txt("title")
            ozet   = html_temizle(txt("description") or txt("summary") or txt("content"))
            url    = txt("link") or txt("guid")
            tarih  = tarih_normalize(txt("pubDate") or txt("published") or txt("updated"))

            if not baslik or not url:
                continue
            if not ekoloji_mi(baslik, ozet):
                continue

            haberler.append({
                "baslik": baslik,
                "kaynak": kaynak["ad"],
                "tarih":  tarih,
                "etiket": kaynak["etiket"],
                "ozet":   ozet,
                "url":    url,
            })

        print(f"  📡 {kaynak['ad']}: {len(haberler)} ekoloji haberi bulundu.")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']} RSS hatası: {e}")
    return haberler

# ── Çift kayıt önleme ──────────────────────────────────────────────
def mevcut_url_seti(haberler):
    return {h.get("url", "") for h in haberler}

def sonraki_id(liste):
    if not liste:
        return 1
    return max((x.get("id", 0) for x in liste), default=0) + 1

# ── Ana fonksiyon ──────────────────────────────────────────────────
def main():
    print("📥 Mevcut data.json çekiliyor…")
    data, sha = get_remote_data()

    if data is None:
        print("⚠️  Uzak veri alınamadı — boş yapıyla başlanıyor.")
        data = {"ihlaller": [], "haberler": [], "raporlar": [], "_meta": {}}
        sha  = None

    mevcut_haberler = data.get("haberler", [])
    mevcut_ihlaller = data.get("ihlaller", [])
    mevcut_urls     = mevcut_url_seti(mevcut_haberler)

    print(f"  Mevcut: {len(mevcut_ihlaller)} ihlal, {len(mevcut_haberler)} haber")

    # RSS'leri tara
    print("\n🔍 RSS kaynakları taranıyor…")
    yeni_haberler = []
    id_sayac = sonraki_id(mevcut_haberler)

    for kaynak in KAYNAK_RSS:
        bulunanlar = rss_cek(kaynak)
        for h in bulunanlar:
            if h["url"] not in mevcut_urls:
                h["id"] = id_sayac
                id_sayac += 1
                yeni_haberler.append(h)
                mevcut_urls.add(h["url"])

    print(f"\n✅ {len(yeni_haberler)} yeni haber eklendi.")

    # Listeye ekle (en yeniler başa)
    data["haberler"] = yeni_haberler + mevcut_haberler

    # Meta güncelle
    data["_meta"] = {
        "guncelleme":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":       "otomatik_tarama",
        "versiyon":     "1.0",
        "ihlal_sayisi": len(data["ihlaller"]),
        "haber_sayisi": len(data["haberler"]),
    }

    print("\n📤 GitHub'a yazılıyor…")
    update_remote_data(data, sha)

if __name__ == "__main__":
    main()
