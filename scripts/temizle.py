#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/temizle.py — data.json temizleyici
Çalıştır: python scripts/temizle.py
- RES (rüzgar türbini) kayıtlarını siler
- Açıklaması olmayan kayıtları siler
- Sonucu GitHub'a yazar
"""

import env_yukle

import json, os, base64, datetime, requests

REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME  = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
FILE_PATH  = "data.json"

def get_sha():
    token = os.environ.get("GITHUB_TOKEN")
    url   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    return r.json().get("sha") if r.status_code == 200 else None

def main():
    print("📥 data.json çekiliyor…")
    raw = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    r = requests.get(raw, timeout=20)
    if r.status_code != 200:
        print(f"❌ Veri alınamadı: {r.status_code}")
        return

    data = r.json()
    ihlaller = data.get("ihlaller", [])
    onceki   = len(ihlaller)

    print(f"  Mevcut: {onceki} ihlal")

    # ── Filtreler ──────────────────────────────────────────────────
    temiz = []
    silinen_res     = 0
    silinen_bos     = 0

    for i in ihlaller:
        tip = (i.get("tip") or i.get("kategori") or "").strip()

        # 1. RES kayıtlarını sil
        if tip in ("RES", "GES"):
            silinen_res += 1
            continue

        # 2. Açıklaması olmayan veya çok kısa olanları sil
        aciklama = (i.get("aciklama") or "").strip()
        if len(aciklama) < 10:
            silinen_bos += 1
            continue

        temiz.append(i)

    print(f"  Silinen RES/GES     : {silinen_res}")
    print(f"  Silinen açıklamasız : {silinen_bos}")
    print(f"  Kalan               : {len(temiz)}")

    data["ihlaller"] = temiz
    data["_meta"] = {
        "guncelleme":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":       "temizle_v1",
        "ihlal_sayisi": len(temiz),
        "haber_sayisi": len(data.get("haberler", [])),
    }

    # ── GitHub'a yaz ───────────────────────────────────────────────
    token   = os.environ.get("GITHUB_TOKEN")
    sha     = get_sha()
    url     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    content = base64.b64encode(
        json.dumps(data, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"temizlik: RES/GES ve açıklamasız kayıtlar silindi ({onceki}→{len(temiz)})",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers={"Authorization": f"Bearer {token}"},
                        json=payload, timeout=30)
    if resp.status_code in (200, 201):
        print(f"✅ GitHub güncellendi — {onceki} → {len(temiz)} ihlal ({onceki-len(temiz)} silindi)")
    else:
        print(f"❌ Hata {resp.status_code}: {resp.text[:200]}")

if __name__ == "__main__":
    main()
