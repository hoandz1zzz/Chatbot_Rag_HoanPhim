# HoanPhim AI - RAG Movie Recommendation Backend

Hệ thống backend tư vấn phim thông minh sử dụng kiến trúc **RAG (Retrieval-Augmented Generation)** cho website xem phim **HoanPhim**. Ứng dụng kết hợp tìm kiếm ngữ nghĩa bằng Vector (`pgvector`) và mô hình ngôn ngữ lớn **Google Gemini** để gợi ý phim chính xác, tự nhiên và chống bịa đặt (anti-hallucination).

## Tính năng chính

- **Tìm kiếm ngữ nghĩa (Semantic Search):** Hiểu ý định, tâm trạng và mô tả tự nhiên của người dùng bằng khoảng cách Cosine (`<=>`) trên Vector 768 chiều.
- **Tư vấn có kiểm soát (Anti-hallucination):** Chỉ đề xuất những phim thực sự có trong kho dữ liệu; tự động từ chối khéo và trả về danh sách rỗng nếu không tìm thấy phim phù hợp.
- **Structured JSON Output:** Ép Gemini trả về dữ liệu có cấu trúc (câu trả lời + danh sách `slug`, `name`, `thumb_url`, `genres`), sẵn sàng để Frontend (Next.js) render thẻ phim trực tiếp trong khung chat.
- **Data Pipeline chống trùng lặp:** Tự động cào dữ liệu phim, tổng hợp ngữ cảnh (`content_for_rag`), tạo Embedding và lưu vào PostgreSQL với `slug` làm khóa chính (`ON CONFLICT DO UPDATE`).

## Công nghệ sử dụng

- **Backend Framework:** FastAPI, Uvicorn
- **Database:** PostgreSQL + `pgvector` (chạy qua Docker)
- **AI / Embedding:** Google GenAI SDK (`gemini-embedding-2` 768 dims & `gemini-2.5-flash`)

## Cấu trúc thư mục

```text
├── api.py               # FastAPI server & endpoint /api/chat
├── rag_core.py          # Lõi kết nối DB, tạo Embedding và tìm kiếm Vector
├── seed.py              # Script kéo dữ liệu phim và nạp Vector vào DB
├── docker-compose.yml   # Cấu hình container PostgreSQL + pgvector
├── requirements.txt     # Danh sách thư viện Python
├── .env.example         # Mẫu biến môi trường
└── .gitignore           # Chặn đẩy file nhạy cảm (.env, __pycache__...)
 Hướng dẫn cài đặt & chạy cục bộ
1. Clone dự án & cấu hình biến môi trường
Bash
git clone [https://github.com/](https://github.com/)<username>/<repo-name>.git
cd <repo-name>
Tạo file .env từ file mẫu .env.example và điền API Key của bạn:

Đoạn mã
GEMINI_API_KEY=your_gemini_api_key_here
2. Khởi chạy Database (Docker)
Đảm bảo Docker Desktop đang chạy, sau đó bật container PostgreSQL (pgvector trên cổng 5435):

Bash
docker-compose up -d
3. Cài đặt thư viện Python
Bash
pip install -r requirements.txt
4. Nạp dữ liệu phim (Seed Data)
Chạy script để kéo phim và tạo Vector lưu vào Database:

Bash
python seed.py
5. Khởi chạy API Server
Bash
uvicorn api:app --reload --port 8001
Truy cập giao diện Swagger UI để test trực tiếp tại: http://localhost:8001/docs

 API Reference
POST /api/chat
Gửi câu hỏi tìm phim và nhận câu trả lời tư vấn kèm danh sách phim gợi ý.

Request Body:

JSON
{
  "query": "phim hài lãng mạn Thái Lan",
  "top_k": 5
}
Response Body:

JSON
{
  "answer": "Chào bạn, HoanPhim gợi ý cho bạn bộ phim Hương Tình Miền Quê rất hợp gu hài hước và lãng mạn...",
  "movies": [
    {
      "slug": "huong-tinh-mien-que",
      "name": "Hương Tình Miền Quê",
      "thumb_url": "https://...",
      "genres": "Hài, Chính kịch",
      "similarity": 78.5
    }
  ]
}
```
