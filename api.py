import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.genai import types
from rag_core import client, search_movies

app = FastAPI(title="HoanPhim AI RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5

class GeminiResponseSchema(BaseModel):
    answer: str
    recommended_slugs: list[str]

@app.post("/api/chat")
def chat_recommend(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")

    try:
        candidates = search_movies(req.query, top_k=req.top_k)

        if not candidates:
            return {
                "answer": "Hiện tại kho phim HoanPhim chưa có bộ nào phù hợp với yêu cầu của bạn.",
                "movies": []
            }

        context_text = "\n\n".join([
            f"- Slug: {m['slug']}\n  Thông tin: {m['content_for_rag']}"
            for m in candidates
        ])

        prompt = f"""
Bạn là trợ lý tư vấn phim thông minh của website HoanPhim.
Dựa CHỈ vào danh sách phim dưới đây, hãy tư vấn cho người dùng những bộ phim phù hợp nhất.
- Trường 'answer': Trả lời thân thiện, ngắn gọn, nêu rõ tên phim và lý do hợp gu.
- Trường 'recommended_slugs': Liệt kê chính xác các 'Slug' của những phim bạn thực sự đề xuất trong câu trả lời.
- Nếu KHÔNG có phim nào thực sự liên quan, hãy từ chối khéo trong 'answer' và để 'recommended_slugs' là mảng rỗng []. Tuyệt đối không bịa phim.

Yêu cầu người dùng: "{req.query}"

Danh sách phim từ kho dữ liệu:
{context_text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiResponseSchema,
            )
        )

        ai_result = json.loads(response.text)
        recommended_slugs = set(ai_result.get("recommended_slugs", []))

        final_movies = [
            {
                "slug": m["slug"],
                "name": m["name"],
                "thumb_url": m["thumb_url"],
                "genres": m["genres"],
                "similarity": m["similarity"]
            }
            for m in candidates if m["slug"] in recommended_slugs
        ]

        return {
            "answer": ai_result.get("answer", ""),
            "movies": final_movies
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))