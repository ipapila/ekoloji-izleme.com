# Tarama Kaynakları

Bu belge, `tarayici.py` ve `yerel_basin_kaynaklari.py` içinde tanımlı tüm veri kaynaklarını
kategorilere ayırarak listeler. Kaynaklar yerel, ulusal, uluslararası, resmî ve özel/STK
ayrımıyla gruplanmıştır.

> **Not:** Kaynakların önemli bir bölümüne doğrudan RSS/web değil, Google News RSS
> *site-sorgularıyla* (`site:...`) erişilir. Bu durumlarda birincil yayıncı adı esas alınmış,
> yalnızca tematik/şehir bazlı sorgular ise **Özel / Agregatör** başlığına konulmuştur.
> Bir kaydın bölümü (`bolum`) kaynak kimliğine değil, `bolum_dogrula()` anahtar-kelime
> doğrulamasına göre atanır.

---

## 1. Resmî Kaynaklar

| Kaynak | Erişim | Kapsam |
|---|---|---|
| Resmî Gazete | `site:resmigazete.gov.tr` (Google News RSS) | Kamulaştırma, maden, ihale |
| İlan Portalı | `site:ilan.gov.tr` (Google News RSS) | Maden / enerji ihaleleri |
| MAPEG | `site:mapeg.gov.tr` (Google News RSS) | Maden ruhsatları |
| EPDK | Anahtar kelime (`EPDK kararı`) | Enerji düzenleme kararları |
| Çevre, Şehircilik ve İklim Değişikliği Bakanlığı | `csb.gov.tr/duyurular` (web) | Resmî duyurular |

---

## 2. Ulusal Kaynaklar (Yayın / Medya)

- Bianet (+ köşe / görüş)
- İklim Haber
- Yeşil Gazete
- Evrensel
- Birgün
- Sözcü
- Cumhuriyet
- Gazete Duvar
- T24
- Diken
- Artı Gerçek
- Gazete Pencere
- Yeni Yaşam
- Mezopotamya Ajansı
- Amed Haber
- Kısa Dalga
- Politika Haber
- Haber Kolektif
- Sendika.org
- Anarşist Haberler
- Kaos GL
- Politeknik

---

## 3. Yerel / Bölgesel Kaynaklar

### Tanımlı yerel yayınlar
- Rize'nin Sesi
- Gazete Rize
- Günebakış (Trabzon)
- Karadeniz'de Son Nokta
- Açıksöz (Kastamonu)
- Boyabat Sesi
- Yeni Asır (İzmir)
- Ege'de Sonsöz (İzmir)
- Muğla Gazetesi
- Muğla Yenigün
- Bianet Bölgesel

### Şehir / bölge bazlı bölgesel sorgular (Google News RSS)
Zonguldak · Artvin · Doğu Karadeniz (Rize-Trabzon-Giresun-Ordu-Samsun) ·
Batı Karadeniz (Kastamonu-Sinop-Bartın-Karabük) · İzmir (Aliağa-Bergama-Foça) ·
Muğla (Akbelen-Yatağan-Milas-Ula) · Manisa-Aydın-Denizli · Kaz Dağları / İda ·
Antalya · Mersin-Adana · Hatay · Isparta-Burdur-Kahramanmaraş · Çanakkale ·
Kocaeli-Bursa-İzmit · Trakya (Tekirdağ-Edirne-Kırklareli) · Balıkesir · İstanbul ·
Ankara · Konya-Eskişehir · Kayseri-Sivas-Çorum · Diyarbakır-Şanlıurfa-Mardin ·
Van-Hakkari-Şırnak-Batman-Siirt-Bitlis-Muş · Erzurum-Erzincan-Kars-Ardahan ·
Elazığ-Malatya-Bingöl-Tunceli · Batman-Siirt-Şırnak · Amasya-Tokat-Çankırı ·
Dersim-Munzur-Cudi-Gabar-Hevsel bölgesel sorguları

---

## 4. Uluslararası Kaynaklar

| Kaynak | Erişim |
|---|---|
| Carbon Brief | `carbonbrief.org/feed` (RSS) |
| Climate Home News | `climatechangenews.com/feed` (RSS) |
| Mongabay | `news.mongabay.com/feed` (RSS) |
| The Guardian (Environment) | `theguardian.com/environment/rss` (RSS) |
| 350.org | `350.org/feed` (RSS) |
| Greenpeace International | `greenpeace.org/international/tag/turkey` (web) |
| Google News EN | Türkiye odaklı İngilizce sorgular (çevre/maden, iklim/kömür, Akkuyu/nükleer) |

---

## 5. Özel / Sivil Toplum & Agregatör

### STK / özel kuruluşlar
- TEMA
- Greenpeace Türkiye
- WWF Türkiye
- Doğa Derneği
- SHURA Enerji Dönüşümü Merkezi
- 17 Mayıs Derneği
- İklim Adaleti Koalisyonu
- Coalition Rainbow
- Mezopotamya Ekoloji Hareketi (basın yansıması)

### Agregatör (birincil yayıncı değil)
- **Google News (TR)** — tematik sorgular: çevre ihlali, orman/maden, HES/RES/baraj,
  acele kamulaştırma, ÇED, siyanür/atık barajı, JES (Aydın-Manisa), zeytinlik/maden,
  maden kazası, sanayi/hava kirliliği vb.
- **Google News (EN)** — uluslararası ve nesli tehlike altındaki türler için İngilizce sorgular.

---

## 6. Kitap Arşivi

| Kaynak | Erişim | Kapsam |
|---|---|---|
| Google Books API | `googleapis.com/books/v1/volumes` (14 anahtar kelime sorgusu, `langRestrict=tr`) | Ekoloji, iklim, orman, biyoçeşitlilik, su, madencilik, sürdürülebilirlik, tarım, direniş, şehircilik, felsefe konulu kitaplar |

**Tasarım notları:**
- Kitaplar `tarayici.py`'deki `kitaplari_guncelle()` fonksiyonuyla taranır ve doğrudan
  `kitaplar.json`'a yazılır — haberler.json akışına dahil edilmez, `dagitici.py`'nin
  kural tabanlı sınıflandırıcısından geçmez.
  Sadece GitHub'a yüklenirken `dagitici.py`'nin gönderim listesine dahildir.
- **Alt-kategori** başlık+özet üzerinden anahtar kelime eşleşmesiyle (`KITAP_KAT_ANAHTAR`)
  belirlenir; sorgu bazlı varsayılan kategoriye düşer.
- **Dijital indirme linki** yalnızca açık erişim/telifsiz kitaplar için doldurulur
  (`accessInfo.publicDomain` veya `saleInfo.saleability == "FREE"`, ayrıca
  pdf/epub erişilebilirliği). Ticari kitaplarda bu alan her zaman boştur —
  yalnızca `tanitim_linki` (Google Books sayfası/yayınevi) gösterilir.
- **Bilinçli tasarım kararı:** `kitaplar.json` aylık budamaya/arşivlemeye TABİ DEĞİLDİR.
  Diğer koleksiyonlar bir haber akışıdır ve eski kayıtlar arşive taşınır; kitap
  arşivi ise kalıcı bir kütüphane kataloğudur — eski kitaplar da canlı sayfada
  aranabilir/gezinilebilir kalmalıdır.
- Google News'in eski kitapları "yeni keşif" gibi sunması riski burada söz konusu
  değildir (RSS değil, doğrudan API sorgusu kullanılır); ancak anahtar kelime
  sorguları zamanla alakasız/düşük kaliteli sonuçlar getirebilir — gerekirse
  `KITAP_SORGULARI` listesi daraltılabilir veya yayınevi bazlı kaynaklar eklenebilir.

---

## Hedef koleksiyon dağılımı

Kaynaklar `hedef` alanına göre şu koleksiyonlara yazılır:

- `haberler` — genel çevre/ihlal haberleri
- `raporlar` — STK ve akademik rapor/analizler (WWF, TEMA, Doğa Derneği, Greenpeace, SHURA…)
- `makaleler` — köşe / görüş / yorum
- `uluslararasi` (kuresel) — uluslararası kaynaklar
- `ekosistem` — türler, yaban, bitki, su canlıları, hayvan hakları, kadınlar, çiftçi,
  balıkçı, gençlik, eşitsizlik, kentsel, göç, savaş, engelliler bölümleri
- `kitaplar` — ekoloji/iklim/çevre konulu kitaplar (kalıcı katalog, ayrı akış)
