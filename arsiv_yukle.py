#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arsiv_yukle.py — Yerel arsiv/ klasörünü GitHub'a TEK COMMIT ile yükler.

GitHub web arayüzü yüzlerce dosyayı sürükle-bırakta tıkadığı için, bu script
Git Data API (trees + commit) kullanarak arsiv/*.json dosyalarının tamamını
tek seferde, tek commit halinde repoya yazar. Idempotenttir: aynı içerik tekrar
yüklenirse GitHub değişiklik görmez.

Gereksinim: GITHUB_TOKEN (repo yazma yetkili). Diğer pipeline scriptleri gibi.

Kullanım (arsiv/ klasörünün BULUNDUĞU dizinde):
    # token'ı ortamdan al (env_yukle varsa otomatik):
    python3 arsiv_yukle.py
    # veya açıkça:
    GITHUB_TOKEN=ghp_xxx python3 arsiv_yukle.py
"""
import os, sys, json, urllib.request
from pathlib import Path

# Pipeline ile aynı env yükleyici varsa kullan (GITHUB_TOKEN'ı set eder)
try:
    import env_yukle  # noqa: F401
except Exception:
    pass

OWNER  = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO   = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
BRANCH = os.environ.get("GITHUB_BRANCH",      "main")
TOKEN  = os.environ.get("GITHUB_TOKEN")
API    = f"https://api.github.com/repos/{OWNER}/{REPO}"

def istek(yontem, yol, govde=None):
    url = yol if yol.startswith("http") else f"{API}{yol}"
    data = json.dumps(govde).encode() if govde is not None else None
    req = urllib.request.Request(url, data=data, method=yontem, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ekoloji-arsiv-yukle",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def main():
    if not TOKEN:
        print("HATA: GITHUB_TOKEN bulunamadı. Örn: GITHUB_TOKEN=xxx python3 arsiv_yukle.py")
        sys.exit(1)

    arsiv = Path("arsiv")
    if not arsiv.is_dir():
        print("HATA: arsiv/ klasörü bu dizinde yok. arsiv.zip'i burada açın.")
        sys.exit(1)

    dosyalar = sorted(arsiv.glob("*.json"))
    if not dosyalar:
        print("HATA: arsiv/ içinde .json dosyası yok.")
        sys.exit(1)
    print(f"{len(dosyalar)} arşiv dosyası bulundu.")

    # 1) Mevcut dalın commit ve ağaç sha'sı
    ref = istek("GET", f"/git/ref/heads/{BRANCH}")
    commit_sha = ref["object"]["sha"]
    commit = istek("GET", f"/git/commits/{commit_sha}")
    base_tree = commit["tree"]["sha"]

    # 2) Tüm dosyaları tek ağaç olarak hazırla (içerik satır içi)
    tree = [{
        "path": f"arsiv/{p.name}",
        "mode": "100644",
        "type": "blob",
        "content": p.read_text(encoding="utf-8"),
    } for p in dosyalar]

    print("Ağaç oluşturuluyor…")
    yeni_tree = istek("POST", "/git/trees", {"base_tree": base_tree, "tree": tree})

    # 3) Commit + dalı ilerlet
    print("Commit oluşturuluyor…")
    yeni_commit = istek("POST", "/git/commits", {
        "message": f"arşiv: {len(dosyalar)} katalog dosyası yüklendi",
        "tree": yeni_tree["sha"],
        "parents": [commit_sha],
    })
    istek("PATCH", f"/git/refs/heads/{BRANCH}", {"sha": yeni_commit["sha"]})

    print(f"\n✓ Tamamlandı — {len(dosyalar)} dosya tek commit ile yüklendi.")
    print(f"  Commit: {yeni_commit['sha'][:10]}")
    print("  senkron.py ~50 dk içinde httpdocs/arsiv/ altına indirir.")

if __name__ == "__main__":
    main()
