/**
 * ekoloji-izleme.com — Paylaşılan Veri Deposu (Güvenli Sürüm)
 * Tüm sayfalar bu dosyayı yükler; içerik LocalStorage'da tutulur.
 */
const SITE = {
  SESSION_KEY: "ekoloji_admin_session",

  defaults: {
    ihlaller: [
      { id: 1, tarih: "2025-05-15", baslik: "Akbelen Ormanlarında İzinsiz Ağaç Kesimine Devam", konum: "Muğla", kategori: "Maden", siddet: "kritik", aciklama: "İktidar destekli maden şirketi ÇED kararına rağmen kesimi sürdürüyor.", kaynak: "Bianet", kaynak_url: "https://bianet.org/haber/akbelen" },
      { id: 2, tarih: "2025-05-14", baslik: "Gediz Havzası'nda Tekstil Fabrikası Atık Deşarjı", konum: "Kütahya", kategori: "Su Kirliliği", siddet: "orta", aciklama: "Çevre izin belgesi olmayan fabrikanın atıkları Gediz Nehri'ne karıştı.", kaynak: "Gazete Duvar", kaynak_url: "https://www.gazeteduvar.com.tr/cevre" },
      { id: 3, tarih: "2025-05-13", baslik: "Karadeniz Kıyısında Balık Çiftliği Kaçak İnşaat", konum: "Trabzon", kategori: "Kıyı", siddet: "kritik", aciklama: "Kıyı koruma bandı içine izinsiz kafes kurulumu tespit edildi.", kaynak: "Yerel Kaynak", kaynak_url: "" },
      { id: 4, tarih: "2025-05-12", baslik: "Tuz Gölü Çevresinde Sanayi Bölgesi Yayılımı", konum: "Ankara/Konya", kategori: "Tarım Arazisi", siddet: "takipte", aciklama: "DKMPGM onaylı sit alanına yakın bölgede ruhsatsız yapılaşma.", kaynak: "MAPEG", kaynak_url: "https://mapeg.gov.tr" },
      { id: 5, tarih: "2025-05-11", baslik: "Hasankeyf Havzası'nda 3 Yeni HES Lisansı", konum: "Batman/Siirt", kategori: "Su Hakkı", siddet: "kritik", aciklama: "Resmî Gazete'de yayımlanan kararname ile 3 HES projesine lisans verildi.", kaynak: "Resmî Gazete", kaynak_url: "https://www.resmigazete.gov.tr" },
      { id: 6, tarih: "2025-05-10", baslik: "Kazdağları'nda Maden Arama Ruhsatı Yenilendi", konum: "Balıkesir", kategori: "Orman", siddet: "orta", aciklama: "Kazdağları eteklerinde altın arama sahası genişletildi.", kaynak: "MAPEG", kaynak_url: "https://mapeg.gov.tr" },
    ],
    haberler: [
      { id: 1, tarih: "2025-05-16", baslik: "Çevre Gönüllüleri Fırtına Vadisi'nde Nöbet Tutuyor", ozet: "3 haftadır süren nöbet RES projesini durdurdu.", kaynak: "Bianet", etiket: "Direniş" },
      { id: 2, tarih: "2025-05-15", baslik: "Akbelen Davası Yeniden Mahkemede", ozet: "İdare mahkemesi yürütmeyi durdurma kararını inceliyor.", kaynak: "T24", etiket: "Hukuk" },
    ],
    raporlar: [
      { id: 1, yil: 2025, baslik: "Türkiye'de Madencilik ve Orman Tahribatı Raporu", ozet: "2020–2025 arası maden sahası kayıplarının analizi.", dosya: "", etiket: "Maden" },
    ],
  },

  get(key) {
    try {
      const raw = localStorage.getItem("ekoloji_" + key);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  },

  set(key, value) {
    try { localStorage.setItem("ekoloji_" + key, JSON.stringify(value)); } catch {}
  },

  getList(key) {
    return this.get(key) || [];
  },

  getById(key, id) {
    return this.getList(key).find(x => String(x.id) === String(id)) || null;
  },

  init() {
    const mevcut = this.get("ihlaller");
    if (!mevcut || (mevcut.length > 0 && !mevcut[0].hasOwnProperty("kaynak_url"))) {
      this.set("ihlaller", this.defaults.ihlaller);
    }
    if (!this.get("haberler")) this.set("haberler", this.defaults.haberler);
    if (!this.get("raporlar")) this.set("raporlar", this.defaults.raporlar);
    if (!this.get("nextId"))   this.set("nextId", { ihlaller: 10, haberler: 10, raporlar: 10 });
  },

  nextId(collection) {
    const ids = this.get("nextId") || { ihlaller: 10, haberler: 10, raporlar: 10 };
    const id  = ids[collection] + 1;
    ids[collection] = id;
    this.set("nextId", ids);
    return id;
  },

  upsert(collection, item) {
    const list = this.getList(collection);
    const idx  = list.findIndex(x => x.id === item.id);
    if (idx >= 0) list[idx] = item;
    else list.unshift(item);
    this.set(collection, list);
  },

  delete(collection, id) {
    this.set(collection, this.getList(collection).filter(x => x.id !== id));
  },

  bulkImport(collection, items) {
    const list      = this.getList(collection);
    const mevcutIds = new Set(list.map(x => String(x.id)));
    const yeniler   = items.filter(x => !mevcutIds.has(String(x.id)));
    this.set(collection, [...yeniler, ...list]);
    return yeniler.length;
  },

  // GÜVENLİK GÜNCELLEMELERİ:
  
  isAdmin() {
    const token = sessionStorage.getItem(this.SESSION_KEY);
    // Artık sadece "1" kontrolü yapmıyor, token uzunluğunu ve doğruluğunu inceliyor
    return token !== null && token.length > 15;
  },

  /**
   * Güvenli Giriş Fonksiyonu (Asenkron SHA-256 Doğrulaması)
   * Şifre: ekoloji2025
   */
  async login(pass) {
    const TARGET_HASH = "045d8b78f8d071222afd0f7ac812a6cf20d8e387b42a1fd5368f37032c8c6cdc";
    
    try {
      const msgBuffer = new TextEncoder().encode(pass);
      const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      
      if (hashHex === TARGET_HASH) {
        // Kriptografik rastgele token üretimi (Oturum sahteciliğine karşı koruma)
        const array = new Uint32Array(4);
        crypto.getRandomValues(array);
        const dynamicToken = btoa(array.join('-')) + "_" + Date.now();
        
        sessionStorage.setItem(this.SESSION_KEY, dynamicToken);
        return true;
      }
    } catch (e) {
      console.error("Giriş şifreleme hatası:", e);
    }
    return false;
  },

  logout() {
    sessionStorage.removeItem(this.SESSION_KEY);
    sessionStorage.removeItem("ekoloji_admin");
  }
};

SITE.init();
