/**
 * ekoloji-izleme.com — Paylaşılan Veri Deposu
 * Tüm sayfalar bu dosyayı yükler; içerik LocalStorage'da tutulur.
 */
const SITE = {

  defaults: {
    ihlaller: [
      { id: 1, tarih: "2025-05-15", baslik: "Akbelen Ormanlarında İzinsiz Ağaç Kesimine Devam", konum: "Muğla", kategori: "Maden", siddet: "kritik", aciklama: "İktidar destekli maden şirketi ÇED kararına rağmen kesimi sürdürüyor.", kaynak: "Bianet" },
      { id: 2, tarih: "2025-05-14", baslik: "Gediz Havzası'nda Tekstil Fabrikası Atık Deşarjı", konum: "Kütahya", kategori: "Su Kirliliği", siddet: "orta", aciklama: "Çevre izin belgesi olmayan fabrikanın atıkları Gediz Nehri'ne karıştı.", kaynak: "Gazete Duvar" },
      { id: 3, tarih: "2025-05-13", baslik: "Karadeniz Kıyısında Balık Çiftliği Kaçak İnşaat", konum: "Trabzon", kategori: "Kıyı", siddet: "kritik", aciklama: "Kıyı koruma bandı içine izinsiz kafes kurulumu tespit edildi.", kaynak: "Yerel Kaynak" },
      { id: 4, tarih: "2025-05-12", baslik: "Tuz Gölü Çevresinde Sanayi Bölgesi Yayılımı", konum: "Ankara/Konya", kategori: "Tarım Arazisi", siddet: "takipte", aciklama: "DKMPGM onaylı sit alanına yakın bölgede ruhsatsız yapılaşma.", kaynak: "MAPEG" },
      { id: 5, tarih: "2025-05-11", baslik: "Hasankeyf Havzası'nda 3 Yeni HES Lisansı", konum: "Batman/Siirt", kategori: "Su Hakkı", siddet: "kritik", aciklama: "Resmî Gazete'de yayımlanan kararname ile 3 HES projesine lisans verildi.", kaynak: "Resmî Gazete" },
      { id: 6, tarih: "2025-05-10", baslik: "Kazdağları'nda Maden Arama Ruhsatı Yenilendi", konum: "Balıkesir", kategori: "Orman", siddet: "orta", aciklama: "Kazdağları eteklerinde altın arama sahası genişletildi.", kaynak: "MAPEG" },
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
    // detay.html ve diğer sayfalar için ID ile tekil kayıt arama
    return this.getList(key).find(x => String(x.id) === String(id)) || null;
  },

  init() {
    if (!this.get("ihlaller")) this.set("ihlaller", this.defaults.ihlaller);
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

  SESSION_KEY: "ekoloji_admin_session",

  isAdmin() {
    return sessionStorage.getItem(this.SESSION_KEY) === "1";
  },

  login(pass) {
    const HASH = "ZWtvbG9qaTIwMjU="; // btoa("ekoloji2025")
    if (btoa(pass) === HASH) {
      sessionStorage.setItem(this.SESSION_KEY, "1");
      return true;
    }
    return false;
  },

  logout() {
    sessionStorage.removeItem(this.SESSION_KEY);
    sessionStorage.removeItem("ekoloji_admin");
  },
};

SITE.init();
