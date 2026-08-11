# Nhau AI Service — scaffold CrewAI (Match / Recommendation / Moderation)

AI Service chạy **độc lập** (Python, không nhét vào Flutter/Phoenix), đứng
giữa và gọi ngược vào các route REST **đã có sẵn** trong plugin
`custom-api-core` để lấy dữ liệu thật:

```
Flutter → Phoenix / WordPress → AI Service (FastAPI, port 8088) → CrewAI agents
                                        │
                                        ▼
                     gọi lại wp-json/custom/v1/finding-keo/nearby,
                     wp-json/nhau/v1/my-keo, invite/detail, user-stats...
```

## Cấu trúc

```
ai_service/
  main.py                    FastAPI — expose /match /recommend /moderate
  crew.py                    Lắp Agent + Task -> Crew, parse output JSON
  schemas.py                 Pydantic request models
  agents/
    match_agent.py           Chấm điểm % phù hợp user-kèo/user-user
    recommendation_agent.py  Gợi ý top kèo cá nhân hoá theo từng user
    moderation_agent.py      Đánh giá rủi ro nội dung (spam/scam/xúc phạm)
  tools/
    wp_api_client.py         HTTP client thuần gọi vào WordPress REST
    keo_tools.py             Bọc client trên thành CrewAI @tool cho agent dùng
  config/settings.py         Đọc .env
  examples/
    wp-call-ai-service.php   Ví dụ PHP gọi ngược vào AI Service từ plugin
    nhau-ai-service.service  systemd unit mẫu (giống style nhau-simulate.service)
```

## Cài đặt (trên server test/staging — KHÔNG chạy thẳng vào production)

```bash
cd ai_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# sửa .env: OPENAI_API_KEY, WORDPRESS_BASE_URL (domain staging đang dùng cho
# simulate.py), AI_SERVICE_INTERNAL_KEY (tự sinh chuỗi random)
```

Chạy dev:

```bash
uvicorn main:app --reload --port 8088
curl http://127.0.0.1:8088/health
```

## Gọi thử 3 endpoint

```bash
curl -X POST http://127.0.0.1:8088/match \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: <giá trị AI_SERVICE_INTERNAL_KEY>" \
  -d '{"user_id": 42, "lat": 10.7929, "lng": 106.7014, "radius_km": 3}'

curl -X POST http://127.0.0.1:8088/recommend \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: <giá trị AI_SERVICE_INTERNAL_KEY>" \
  -d '{"user_id": 42, "district": "Bình Thạnh"}'

curl -X POST http://127.0.0.1:8088/moderate \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: <giá trị AI_SERVICE_INTERNAL_KEY>" \
  -d '{"content": "Tối nay làm vài chai, anh em nào rảnh qua làm 5-6 lon rồi về.", "content_type": "invite"}'
```

## Việc CẦN LÀM THÊM trước khi chạy thật (quan trọng)

Em viết scaffold dựa trên đọc code plugin/Phoenix hiện có, nhưng **chưa chạy
được ngay 100%** vì vài chỗ cần anh xác nhận/chỉnh lại cho khớp response thật
của site (em không có quyền truy cập server để tự kiểm tra):

1. **`tools/wp_api_client.py`** — em giả định response JSON có dạng
   `{"users": [...]}` / `{"invites": [...]}`. Anh gọi thử curl vào
   `custom/v1/finding-keo/nearby` và `nhau/v1/my-keo` trên site test, xem
   response thật trả field gì rồi chỉnh lại 2-3 dòng parse trong file này.
2. **Route `custom/v1/finding-keo/nearby`** — đọc `finding-keo.php` em thấy
   route này được `register_rest_route` nhưng phần lọc hiện tại theo
   `district`, chưa chắc đã nhận `radius_km` — có thể cần thêm tham số này
   vào callback PHP, hoặc AI Service tự tính khoảng cách Haversine từ danh
   sách trả về (nếu response có sẵn lat/lng của từng user).
3. **Auth cho route cần JWT** (`invite/create`, `my-keo`...) — AI Service
   không giữ mật khẩu user, chỉ có `user_id`. Nếu route đòi JWT, cần 1 trong
   2 cách: (a) đổi các route AI Service cần đọc sang dùng App Password /
   service account riêng cho AI Service, hoặc (b) Phoenix/WordPress lấy sẵn
   dữ liệu rồi gửi thẳng vào body request tới AI Service thay vì để AI
   Service tự gọi ngược lại WordPress.
4. **`AI_SERVICE_INTERNAL_KEY`** — đặt reverse proxy (Traefik anh đang dùng)
   chỉ cho phép AI Service nhận traffic nội bộ, không mở port 8088 ra ngoài.
5. Model đang set mặc định `gpt-4o-mini` qua `OPENAI_MODEL_NAME` — dùng
   chung `OPENAI_API_KEY` đang có trong Phoenix (`spirit_ai/chat.ex`) cũng
   được, không cần key riêng.

## Vì sao chỉ 3 agent, chưa làm Host/Content/Support Agent

Đúng theo hướng đã bàn — 3 agent này thay được phần rule-based đang yếu nhất
hiện tại (`finding-keo.php` lọc cứng theo quận, `keo-priority-sort.php` sort
cứng không cá nhân hoá). Sau khi chạy ổn, thêm agent mới chỉ là thêm 1 file
trong `agents/` + 1 hàm `run_xxx()` trong `crew.py` + 1 route trong
`main.py`, không phải đổi kiến trúc.
