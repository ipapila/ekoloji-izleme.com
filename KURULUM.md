# ekoloji-izleme.com — GitHub Repo Kurulum Rehberi

## 1. Repo Oluştur

GitHub'da: **New repository → `ekoloji-izleme.com`**
- Visibility: **Public**
- Add README: Hayır (boş başlayın)

## 2. GitHub Pages Aç

Repo → Settings → Pages
- Source: **Deploy from a branch**
- Branch: **main** / root
- Save

Site birkaç dakika içinde `https://kullaniciadi.github.io/ekoloji-izleme.com/` adresinde yayınlanır.  
Kendi domain'inizi bağlamak için: Settings → Pages → Custom domain → `ekoloji-izleme.com`

## 3. Dosya Yapısı

```
ekoloji-izleme.com/
├── index.html
├── haberler.html
├── raporlar.html
├── ihlaller.html
├── ekosistem.html
├── admin.html
├── shared.css
├── site-data.js
├── nav.js
├── tarayici.py          ← buraya taşıyın
├── haberler.json        ← workflow oluşturacak
├── ekoloji-logo.png
└── .github/
    └── workflows/
        └── haber-tarama.yml
```

## 4. Workflow'a Secret Ekle (opsiyonel)

Repo → Settings → Secrets → Actions → New secret  
`HARITA_URL` = `https://ipapila.github.io/Turkiye-katmanlar/data/ihlaller.json`

## 5. İlk Push

```bash
git clone https://github.com/KULLANICI/ekoloji-izleme.com.git
cd ekoloji-izleme.com

# Dosyaları kopyalayın, sonra:
git add .
git commit -m "İlk kurulum"
git push
```

## 6. Workflow'u Test Et

GitHub → Actions → Haber Tarama → **Run workflow**  
Başarılıysa `haberler.json` repo'ya commit edilir ve site güncellenir.
