<?php
/**
 * konum_kaydet.php
 * ------------------
 * Tarayıcıdan (yangin-izleme.html) gelen "son bilinen konum"u
 * son_konum.json dosyasına yazar. Saatlik FIRMS taraması bu dosyayı
 * okuyup, kaydedilen merkezin 25 km çevresinde yeni bir tespit varsa
 * Telegram alarmı gönderir (bkz. yangin_alarm.py).
 *
 * ÖNEMLİ GÜVENLİK NOTU: Buradaki $KONUM_TOKEN, upload.php'nin
 * kullandığı UPLOAD_SECRET ile AYNI DEĞİL ve olmamalı. Bu endpoint
 * tarayıcıdan (yani herkese açık sayfa kaynağından) çağrıldığı için
 * gömülü token gerçek anlamda "gizli" sayılmaz — sayfa kaynağını
 * görebilen herkes bu token'ı da görebilir. Bu yüzden bu token sadece
 * kaba bir spam/kötüye-kullanım engelidir, upload.php'nin dosya
 * yazma yetkisiyle karıştırılmamalı. Aşağıdaki kısıtlar bu riski
 * azaltır: sadece Türkiye bbox'ı içinde koordinat kabul edilir, tek
 * bir dosya (son_konum.json) her istekte olduğu gibi ÜZERİNE YAZILIR
 * (başka bir dosya adı/yol asla kabul edilmez), body boyutu küçük
 * tutulur.
 */

header('Content-Type: application/json; charset=utf-8');

// Kendi belirleyeceğin token — GitHub Secrets'a değil, doğrudan bu
// dosyanın içine (Plesk sunucusunda) yazman yeterli, çünkü zaten
// tarayıcı tarafında da görünür olacak.
$KONUM_TOKEN = 'BURAYA_KENDI_TOKENINI_YAZ';

$girdi = json_decode(file_get_contents('php://input'), true);

if (!is_array($girdi) || !isset($girdi['token']) || $girdi['token'] !== $KONUM_TOKEN) {
    http_response_code(403);
    echo json_encode(['hata' => 'geçersiz token']);
    exit;
}

$lat = isset($girdi['lat']) ? floatval($girdi['lat']) : null;
$lng = isset($girdi['lng']) ? floatval($girdi['lng']) : null;

// Türkiye bbox'ı (diğer scriptlerle aynı sınırlar) — bariz hatalı/kötü
// niyetli koordinatları baştan ele.
if ($lat === null || $lng === null || $lat < 35.5 || $lat > 42.5 || $lng < 25.5 || $lng > 45.0) {
    http_response_code(400);
    echo json_encode(['hata' => 'koordinat Türkiye sınırları dışında ya da eksik']);
    exit;
}

$cikti = [
    'lat' => $lat,
    'lng' => $lng,
    'guncelleme' => gmdate('Y-m-d\TH:i:s\Z'),
];

$yazildi = file_put_contents(__DIR__ . '/son_konum.json', json_encode($cikti, JSON_UNESCAPED_UNICODE));

if ($yazildi === false) {
    http_response_code(500);
    echo json_encode(['hata' => 'dosyaya yazılamadı']);
    exit;
}

echo json_encode(['tamam' => true]);
