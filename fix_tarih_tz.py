#!/usr/bin/env python3
"""
tarayici.py'deki tarih damgalarını UTC'den Türkiye saatine (UTC+3) çevirir.
Kullanim: python3 fix_tarih_tz.py tarayici.py
"""
import sys
import shutil

TARGET = sys.argv[1] if len(sys.argv) > 1 else "tarayici.py"
content = open(TARGET, encoding="utf-8").read()

errors = []

# ── PATCH 1: timezone import'una TR_TZ ekle ──────────────────────
OLD1 = "from datetime import datetime, timezone"
NEW1 = "from datetime import datetime, timezone, timedelta\nTR_TZ = timezone(timedelta(hours=3))  # Türkiye saati UTC+3"

if OLD1 in content:
    content = content.replace(OLD1, NEW1, 1)
    print("✓ Patch 1: TR_TZ tanımlandı")
else:
    errors.append("❌ Patch 1: 'from datetime import datetime, timezone' bulunamadı")

# ── PATCH 2: tarih_normalize — UTC yerine TR saati döndür ────────
OLD2 = (
    "def tarih_normalize(tarih_str) -> Optional[str]:\n"
    "    if not tarih_str:\n"
    "        return None\n"
    "    try:\n"
    "        if hasattr(tarih_str, \"tm_year\"):\n"
    "            return datetime(*tarih_str[:6], tzinfo=timezone.utc).isoformat()\n"
    "        from email.utils import parsedate_to_datetime\n"
    "        return parsedate_to_datetime(str(tarih_str)).isoformat()\n"
    "    except Exception:\n"
    "        return str(tarih_str)"
)

NEW2 = (
    "def tarih_normalize(tarih_str) -> Optional[str]:\n"
    "    if not tarih_str:\n"
    "        return None\n"
    "    try:\n"
    "        if hasattr(tarih_str, \"tm_year\"):\n"
    "            # RSS time.struct_time → Türkiye saatine çevir\n"
    "            dt = datetime(*tarih_str[:6], tzinfo=timezone.utc).astimezone(TR_TZ)\n"
    "            return dt.isoformat()\n"
    "        from email.utils import parsedate_to_datetime\n"
    "        dt = parsedate_to_datetime(str(tarih_str)).astimezone(TR_TZ)\n"
    "        return dt.isoformat()\n"
    "    except Exception:\n"
    "        return str(tarih_str)"
)

if OLD2 in content:
    content = content.replace(OLD2, NEW2, 1)
    print("✓ Patch 2: tarih_normalize → TR_TZ")
else:
    errors.append("❌ Patch 2: tarih_normalize fonksiyonu bulunamadı")

# ── PATCH 3: web scraping'deki datetime.now(timezone.utc) → TR_TZ ─
OLD3 = '                    "tarih":       datetime.now(timezone.utc).isoformat(),'
NEW3 = '                    "tarih":       datetime.now(TR_TZ).isoformat(),'

if OLD3 in content:
    content = content.replace(OLD3, NEW3, 1)
    print("✓ Patch 3: web_tara datetime.now → TR_TZ")
else:
    errors.append("❌ Patch 3: web_tara tarih satırı bulunamadı")

# ── PATCH 4: tara() fonksiyonundaki meta guncelleme → TR_TZ ──────
OLD4 = '            "guncelleme":       datetime.now(timezone.utc).isoformat(),'
NEW4 = '            "guncelleme":       datetime.now(TR_TZ).isoformat(),'

if OLD4 in content:
    content = content.replace(OLD4, NEW4, 1)
    print("✓ Patch 4: meta guncelleme → TR_TZ")
else:
    # Zorunlu değil, uyarı ver
    print("⚠ Patch 4: meta guncelleme satırı bulunamadı (önemli değil)")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

shutil.copy(TARGET, TARGET + ".bak_tz")
print(f"✓ Yedek alındı: {TARGET}.bak_tz")
open(TARGET, "w", encoding="utf-8").write(content)
print(f"✓ {TARGET} güncellendi — artık tarihler TR saatiyle (UTC+3) kaydedilecek")
