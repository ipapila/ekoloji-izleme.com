#!/opt/plesk/python/3/bin/python3
# -*- coding: utf-8 -*-
"""GitHub raw → httpdocs senkron. Webhook'a bağımlı değil; cron ile dakikalık çalışır.
   VERİ (json) ve KOD (site-data.js, .htaccess, *.html) dosyalarını ayrı listelerle çeker.
   httpdocs bir git deposu olmadığından, deploy bu script ile yapılır."""
import os, sys, json, tempfile, hashlib, urllib.request, urllib.parse

REPO  = "https://raw.githubusercontent.com/ipapila/ekoloji-izleme.com/main"
HEDEF = "/var/www/vhosts/ekoloji-izleme.com/httpdocs"

# Veri dosyaları (içerik JSON olarak doğrulanır)
VERI = ["makaleler.json","haberler.json","ihlaller.json","raporlar.json",
        "kuresel.json","ekosistem.json","direnis.json"]

# Kod dosyaları (GitHub kaynak-of-truth; commit edince otomatik iner)
KOD = [".htaccess","site-data.js","shared.css","nav.js",
       "admin.html","arsiv.html","detay.html","direnis-agi.html",
       "dup_temizle_panel.html","ekosistem.html","haberler.html","harita.html",
       "ihlaller.html","index.html","kuresel.html","makaleler.html",
       "raporlar.html","uluslararasi.html"]

UID = GID = None
try:
    import pwd, grp
    UID = pwd.getpwnam("papila").pw_uid
    GID = grp.getgrnam("psacln").gr_gid
except Exception:
    pass

def sha(b): return hashlib.sha256(b).hexdigest()

def cek(ad):
    url = f"{REPO}/{urllib.parse.quote(ad, safe='/')}?cb={os.urandom(4).hex()}"
    req = urllib.request.Request(url, headers={"User-Agent":"ekoloji-senkron"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def yaz(ad, veri, json_dogrula):
    yol = os.path.join(HEDEF, ad)
    if len(veri) < 30:
        print(f"ATLA {ad}: çok küçük ({len(veri)} bayt)"); return False
    if json_dogrula:
        json.loads(veri)                       # bozuk JSON'u reddet
    if os.path.exists(yol) and sha(open(yol,"rb").read()) == sha(veri):
        return False                           # değişmemiş
    fd, tmp = tempfile.mkstemp(dir=HEDEF, suffix=".tmp"); os.close(fd)
    with open(tmp,"wb") as f: f.write(veri)
    if UID is not None: os.chown(tmp, UID, GID)
    os.chmod(tmp, 0o644)
    os.replace(tmp, yol)                        # atomik
    print(f"GUNCELLENDI {ad}: {len(veri)} bayt"); return True

degisen = 0
for ad in VERI:
    try:
        if yaz(ad, cek(ad), json_dogrula=True): degisen += 1
    except Exception as e:
        print(f"HATA {ad}: {e}", file=sys.stderr)
for ad in KOD:
    try:
        if yaz(ad, cek(ad), json_dogrula=False): degisen += 1
    except Exception as e:
        print(f"HATA {ad}: {e}", file=sys.stderr)

# ── Arşiv klasörü: GitHub API'den listele, DEĞİŞEN .json dosyalarını indir ──
# Arşiv dosya adları dinamik (arsiv/haberler-2026-01.json …) olduğundan dizin
# içeriğini API ile çekeriz. api.github.com saatte 60 istekle sınırlı olduğundan
# (senkron dakikalık çalışır) bu blok ~saatte bir çalışır; ayrıca dosya bazında
# git-blob-sha karşılaştırıp YALNIZCA değişenleri indirir. Kalıcı katalog için kritik.
import time, hashlib

def _git_blob_sha(yol):
    try:
        v = open(yol, "rb").read()
    except Exception:
        return None
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(v))
    h.update(v)
    return h.hexdigest()

def arsiv_senkron():
    api = "https://api.github.com/repos/ipapila/ekoloji-izleme.com/contents/arsiv?ref=main"
    try:
        req = urllib.request.Request(
            api, headers={"User-Agent": "ekoloji-senkron",
                          "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            liste = json.loads(r.read())
    except Exception as e:
        print(f"ARŞIV listesi alınamadı: {e}", file=sys.stderr)
        return 0
    if not isinstance(liste, list):
        return 0
    arsiv_hedef = os.path.join(HEDEF, "arsiv")
    os.makedirs(arsiv_hedef, exist_ok=True)
    n = 0
    for f in liste:
        if f.get("type") != "file" or not f.get("name", "").endswith(".json"):
            continue
        yerel = os.path.join(arsiv_hedef, f["name"])
        # GitHub blob sha == yerel blob sha ise indirme (değişmemiş)
        if os.path.exists(yerel) and _git_blob_sha(yerel) == f.get("sha"):
            continue
        ad = "arsiv/" + f["name"]
        try:
            if yaz(ad, cek(ad), json_dogrula=True):
                n += 1
        except Exception as e:
            print(f"HATA {ad}: {e}", file=sys.stderr)
    return n

# Saatlik kapı: damga dosyasıyla ~50 dakikada bir çalıştır (API limitini koru)
_stamp = os.path.join(HEDEF, ".arsiv_senkron_stamp")
def _arsiv_zamani():
    try:
        return (time.time() - os.path.getmtime(_stamp)) > 3000
    except Exception:
        return True

if _arsiv_zamani():
    degisen += arsiv_senkron()
    try:
        open(_stamp, "w").write(str(int(time.time())))
    except Exception:
        pass

print(f"Bitti — {degisen} dosya güncellendi.")
