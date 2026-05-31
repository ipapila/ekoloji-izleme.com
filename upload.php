<?php
/**
 * upload.php — ekoloji-izleme.com dosya yükleme scripti
 *
 * POST parametreleri:
 *   dosya   : yüklenen dosya ($_FILES)
 *   klasor  : "ortam" (resimler) | "dosya" (belgeler)
 *   secret  : admin şifresi (sabit: "admin")
 *
 * Yanıt (JSON):
 *   { ok: true,  url: "https://...", ad: "dosyaadi.jpg" }
 *   { ok: false, hata: "açıklama" }
 */
error_reporting(0);
ini_set('display_errors', 0);

$ef = __DIR__ . '/.env';
if (file_exists($ef)) {
    foreach (file($ef, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
        if (strpos($l, '=') !== false && strpos($l, '#') !== 0) {
            [$k, $v] = explode('=', $l, 2);
            putenv(trim($k) . '=' . trim($v));
        }
    }
}

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('X-Content-Type-Options: nosniff');

/* ── Hata handler ── */
function hata(string $msg, int $code = 400): void {
    http_response_code($code);
    echo json_encode(['ok' => false, 'hata' => $msg], JSON_UNESCAPED_UNICODE);
    exit;
}

/* ── Yalnızca POST ── */
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    hata('Yalnızca POST destekleniyor.', 405);
}

/* ── Kimlik doğrulama ── */
// ⚠️  Plesk Panel → Environment Variables → UPLOAD_SECRET ile tanımlayın
$_beklenen = getenv('UPLOAD_SECRET');
if (!$_beklenen) {
    hata('Sunucu yapılandırma hatası: UPLOAD_SECRET tanımlı değil', 503);
}
$secret = trim($_POST['secret'] ?? '');
if (!hash_equals($_beklenen, $secret)) {
    hata('Yetkisiz erişim.', 401);
}

/* ── Klasör kontrolü ── */
$klasor = trim($_POST['klasor'] ?? '');
$izinli_klasorler = ['ortam', 'dosya', 'kok'];
if (!in_array($klasor, $izinli_klasorler, true)) {
    hata('Geçersiz klasör: "' . htmlspecialchars($klasor) . '"');
}

/* ── Dosya kontrolü ── */
if (!isset($_FILES['dosya']) || $_FILES['dosya']['error'] !== UPLOAD_ERR_OK) {
    $upload_hatalari = [
        UPLOAD_ERR_INI_SIZE   => 'Dosya php.ini sınırını aşıyor.',
        UPLOAD_ERR_FORM_SIZE  => 'Dosya form sınırını aşıyor.',
        UPLOAD_ERR_PARTIAL    => 'Dosya yarım yüklendi.',
        UPLOAD_ERR_NO_FILE    => 'Dosya seçilmedi.',
        UPLOAD_ERR_NO_TMP_DIR => 'Geçici klasör bulunamadı.',
        UPLOAD_ERR_CANT_WRITE => 'Diske yazılamadı.',
        UPLOAD_ERR_EXTENSION  => 'PHP uzantısı yüklemeyi engelledi.',
    ];
    $kod = $_FILES['dosya']['error'] ?? UPLOAD_ERR_NO_FILE;
    hata($upload_hatalari[$kod] ?? 'Yükleme hatası (kod ' . $kod . ').');
}

/* ── Uzantı & MIME kontrolü ── */
$orijinal_ad = basename($_FILES['dosya']['name']);
$uzanti      = strtolower(pathinfo($orijinal_ad, PATHINFO_EXTENSION));

if ($klasor === 'ortam') {
    $izinli_uzanti = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'avif'];
    $max_boyut_mb  = 10;
} else {
    $izinli_uzanti = [
        'pdf', 'doc', 'docx', 'xls', 'xlsx',
        'ppt', 'pptx', 'zip', 'rar', '7z',
        'csv', 'txt', 'json', 'geojson', 'kml', 'gpx',
        'md', 'odt', 'ods',
    ];
    $max_boyut_mb  = 50;
}

if (!in_array($uzanti, $izinli_uzanti, true)) {
    hata('".' . htmlspecialchars($uzanti) . '" uzantısına izin verilmiyor. '
       . 'İzinliler: ' . implode(', ', $izinli_uzanti));
}

/* ── Boyut kontrolü ── */
$max_boyut = $max_boyut_mb * 1024 * 1024;
if ($_FILES['dosya']['size'] > $max_boyut) {
    hata('Dosya ' . $max_boyut_mb . ' MB sınırını aşıyor ('
       . round($_FILES['dosya']['size'] / 1024 / 1024, 1) . ' MB).');
}

/* ── Görsel ise MIME kontrol ── */
if ($klasor === 'ortam' && function_exists('mime_content_type')) {
    $mime = mime_content_type($_FILES['dosya']['tmp_name']);
    if (!str_starts_with($mime, 'image/') && $mime !== 'image/svg+xml') {
        hata('Geçersiz görsel dosyası (MIME: ' . htmlspecialchars($mime) . ').');
    }
}

/* ── Hedef klasörü oluştur ── */
$hedef_klasor = $klasor === 'kok' ? __DIR__ . '/' : __DIR__ . '/' . $klasor . '/';
if (!is_dir($hedef_klasor)) {
    if (!mkdir($hedef_klasor, 0755, true)) {
        hata('Klasör oluşturulamadı: ' . $klasor, 500);
    }
}

/* ── Benzersiz dosya adı ── */
$temiz_ad = preg_replace('/[^a-zA-Z0-9._-]/', '_', $orijinal_ad);
$temiz_ad = preg_replace('/_+/', '_', $temiz_ad);  // çift alt çizgi temizle
$yeni_ad  = $temiz_ad;
$hedef    = $hedef_klasor . $yeni_ad;

/* ── Taşı ── */
if (!move_uploaded_file($_FILES['dosya']['tmp_name'], $hedef)) {
    hata('Dosya kaydedilemedi. Sunucu izinlerini kontrol edin.', 500);
}

/* ── Mutlak URL oluştur ── */
$proto     = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
$host      = $_SERVER['HTTP_HOST'] ?? 'localhost';
$base_path = rtrim(dirname($_SERVER['SCRIPT_NAME'] ?? ''), '/\\');
$url = $proto . '://' . $host . $base_path . '/' . $klasor . '/' . $yeni_ad;

echo json_encode([
    'ok'  => true,
    'url' => $url,
    'ad'  => $yeni_ad,
    'boy' => round($_FILES['dosya']['size'] / 1024, 1) . ' KB',
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
