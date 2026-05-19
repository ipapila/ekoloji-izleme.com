"""
env_yukle.py — Proje kök dizinindeki .env dosyasını okur,
os.environ'a yükler. Her script başında:

    import env_yukle  # noqa

satırı yeterli. python-dotenv gerektirmez.
"""
import os
from pathlib import Path

def _yukle():
    # Bu dosyanın bulunduğu dizin = proje kökü
    env_dosyasi = Path(__file__).parent / ".env"
    if not env_dosyasi.exists():
        return  # .env yoksa sessizce geç (GitHub Actions kendi env var'larını kullanır)

    with env_dosyasi.open(encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#") or "=" not in satir:
                continue
            anahtar, _, deger = satir.partition("=")
            anahtar = anahtar.strip()
            deger = deger.strip().strip('"').strip("'")
            # Zaten set edilmişse (örn. GitHub Actions) üzerine yazma
            if anahtar not in os.environ:
                os.environ[anahtar] = deger

_yukle()
