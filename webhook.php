<?php
/**
 * webhook.php — GitHub Actions → Plesk dosya alıcısı
 * Sunucuda httpdocs/ kök dizinine koyun.
 * PLESK_UPLOAD_TOKEN secret'ı ile eşleşmeli.
 */

// ── Ayarlar ──────────────────────────────────────────────────
define('SECRET',      getenv('WEBHOOK_SECRET') ?: 'BURAYA_TOKEN_YAZIN');
define('IZIN_DOSYA',  ['data.json', 'ihlaller.json', 'haberler.json', 'rapor.json', 'icerik.json']);
define('HEDEF_DIZIN', __DIR__ . '/');   // httpdocs/ kökü
// ─────────────────────────────────────────────────────────────

header('Content-Type: application/json; charset=utf-8');

// Yalnızca POST kabul et
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'hata' => 'Yalnızca POST kabul edilir']);
    exit;
}

// Token doğrula — iki yöntemden biri yeterli
$token_header = $_SERVER['HTTP_X_WEBHOOK_SECRET']  ?? '';
$token_query  = $_GET['token'] ?? '';
if ($token_header !== SECRET && $token_query !== SECRET) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'hata' => 'Geçersiz token']);
    exit;
}

// Hedef dosya adı
$dosya = $_GET['dosya'] ?? $_GET['file'] ?? 'data.json';
$dosya = basename($dosya); // path traversal önlemi

if (!in_array($dosya, IZIN_DOSYA, true)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'hata' => 'İzin verilmeyen dosya: ' . $dosya]);
    exit;
}

// İçeriği oku
$icerik = file_get_contents('php://input');
if ($icerik === false || strlen($icerik) < 2) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'hata' => 'Boş içerik']);
    exit;
}

// JSON geçerliliğini kontrol et
json_decode($icerik);
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'hata' => 'Geçersiz JSON: ' . json_last_error_msg()]);
    exit;
}

// Dosyayı yaz (önce geçici, sonra atomic rename)
$hedef  = HEDEF_DIZIN . $dosya;
$gecici = $hedef . '.tmp.' . uniqid();

if (file_put_contents($gecici, $icerik) === false) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'hata' => 'Dosya yazılamadı: ' . $hedef]);
    exit;
}

if (!rename($gecici, $hedef)) {
    @unlink($gecici);
    http_response_code(500);
    echo json_encode(['ok' => false, 'hata' => 'Dosya taşınamadı']);
    exit;
}

echo json_encode([
    'ok'    => true,
    'dosya' => $dosya,
    'boyut' => strlen($icerik),
    'zaman' => date('Y-m-d H:i:s T'),
]);
