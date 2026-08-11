<?php
/**
 * VÍ DỤ MINH HOẠ — không phải file cần active, chỉ để anh biết cách gọi AI
 * Service từ trong plugin custom-api-core hiện có (vd. thêm vào
 * keo-priority-sort.php hoặc 1 route mới nhau/v1/invite/recommend).
 *
 * Copy phần hàm nhau_call_ai_service() này vào 1 file trong
 * custom-api-core/modules/ (hoặc file helper chung) rồi gọi khi cần.
 */

if (!defined('ABSPATH')) exit;

/**
 * Gọi vào AI Service (FastAPI) đang chạy riêng (vd cùng server, port 8088,
 * đứng sau Traefik/nginx reverse proxy nội bộ - KHÔNG mở public).
 */
function nhau_call_ai_service(string $path, array $body): array {
    $ai_service_url = getenv('AI_SERVICE_URL') ?: 'http://127.0.0.1:8088';
    $internal_key   = getenv('AI_SERVICE_INTERNAL_KEY') ?: '';

    $response = wp_remote_post($ai_service_url . $path, [
        'headers' => [
            'Content-Type'   => 'application/json',
            'X-Internal-Key' => $internal_key,
        ],
        'body'    => wp_json_encode($body),
        'timeout' => 15, // agent LLM có thể mất vài giây, đừng để timeout mặc định 5s cắt ngang
    ]);

    if (is_wp_error($response)) {
        return ['success' => false, 'message' => $response->get_error_message()];
    }

    $code = wp_remote_retrieve_response_code($response);
    $data = json_decode(wp_remote_retrieve_body($response), true);

    if ($code !== 200) {
        return ['success' => false, 'message' => 'AI Service trả lỗi HTTP ' . $code];
    }

    return $data ?: ['success' => false, 'message' => 'Không parse được response'];
}

/**
 * Ví dụ: route mới để Flutter gọi lấy gợi ý kèo cá nhân hoá cho 1 user,
 * thay vì chỉ dùng keo_priority_sort cố định cho tất cả mọi người.
 */
add_action('rest_api_init', function () {
    register_rest_route('nhau/v1', '/invite/recommend', [
        'methods'             => 'GET',
        'callback'            => 'nhau_get_ai_recommendation',
        'permission_callback' => '__return_true',
    ]);
});

function nhau_get_ai_recommendation($request) {
    $user_id  = intval($request->get_param('user_id'));
    $district = sanitize_text_field($request->get_param('district') ?? '');

    if (!$user_id) {
        return ['success' => false, 'message' => 'Thiếu user_id'];
    }

    $result = nhau_call_ai_service('/recommend', [
        'user_id'  => $user_id,
        'district' => $district,
    ]);

    // Nếu AI Service lỗi/timeout -> fallback về sort cũ (keo_priority_sort) để
    // app không bị trắng màn hình, chỉ mất phần cá nhân hoá tạm thời.
    if (empty($result['success'])) {
        // TODO: gọi lại hàm sort cũ trong keo-priority-sort.php ở đây làm fallback
        return ['success' => false, 'fallback' => true, 'message' => $result['message'] ?? 'AI lỗi'];
    }

    return ['success' => true, 'data' => $result['data']];
}
