import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types  
import psycopg2
from pgvector.psycopg2 import register_vector
import time
from rag_core import get_db_connection, get_embedding


load_dotenv()
client = genai.Client()

def clean_text(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip = True)

def get_movie_detail(slug):
    url = f"https://phim.nguonc.com/api/film/{slug}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("movie", {})
    return {}

def process_movie_data(movie):
    name = movie.get("name")
    original_name = movie.get("original_name")
    slug = movie.get("slug")
    year = movie.get("year")
    total_episodes = movie.get("total_episodes")
    thumb_url = movie.get("thumb_url") or movie.get("thumb_url_webp") or ""
    director = movie.get("director")
    casts = movie.get("casts")

    category = movie.get("category", {})

    genres_list = category.get("2", {}).get("list", [])
    genres = ", ".join(genre.get("name") for genre in genres_list)

    country_list = category.get("4", {}).get("list", [])
    country = country_list[0].get("name") if country_list else "Đang cập nhật"

    raw_des = clean_text(movie.get("description"))
    chunk_parts = [
        f"Tên phim: {name} (Tên gốc: {original_name}).",
        f"Thể loại: {genres}.",
        f"Quốc gia: {country}.",
        f"Năm sản xuất: {year}."
    ]

    if director:
        chunk_parts.append(f"Đạo diễn: {director}.")
    if casts:
        chunk_parts.append(f"Diễn viên: {casts}.")
        
    chunk_parts.append(f"Cốt truyện: {raw_des}")

    return {
        "slug": slug,
        "thumb_url": thumb_url,
        "genres": genres,
        "content_for_rag": " ".join(chunk_parts)
    }

def get_embedding(text):
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents = text,
        config=types.EmbedContentConfig(output_dimensionality=768))
    return response.embeddings[0].values

def setup_database():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")


    cur.execute("""
        CREATE TABLE IF NOT EXISTS movie_embeddings (
            slug VARCHAR PRIMARY KEY,
            name VARCHAR,
            thumb_url VARCHAR,
            genres VARCHAR,
            content_for_rag TEXT,
            embedding VECTOR(768) -- Chỗ này để nhét 768 con số của Gemini
        );
        """)

    conn.commit()
    return conn, cur
def main():
    conn, cur = setup_database()
    for page in range(11, 21):
        print(f"\n📄 Đang kéo danh sách phim Trang {page}...")
        response = requests.get(f"https://phim.nguonc.com/api/films/phim-moi-cap-nhat?page={page}")
        data = response.json()
        items = data.get("items", [])

        if not items:
            print("Không có phim ở trang này.")
            continue


        for index, item in enumerate(items):
            slug = item.get("slug")
            name = item.get("name")
           

            # Kiểm tra xem phim đã có trong DB chưa
            cur.execute("SELECT 1 FROM movie_embeddings WHERE slug = %s;", (slug,))
            if cur.fetchone():
                print(f"   ⏭️ Đã có trong DB, bỏ qua: {name}")
                continue
            print(f"[Trang {page} - {index + 1}/{len(items)}] Đang xử lý: {name}")

            movie_detail = get_movie_detail(slug)
            if not movie_detail:
                print(f"   ⚠️ Bỏ qua vì lỗi lấy chi tiết.")
                continue

            process_data = process_movie_data(movie_detail)

            try:
                embedding = get_embedding(process_data["content_for_rag"])

                # 3. THÊM MỚI: Lưu thẳng vào PostgreSQL (pgvector)
                cur.execute("""
                    INSERT INTO movie_embeddings (slug, name, thumb_url, genres, content_for_rag, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        content_for_rag = EXCLUDED.content_for_rag;
                """, (
                    process_data["slug"],
                    name,
                    process_data["thumb_url"],
                    process_data["genres"],
                    process_data["content_for_rag"],
                    embedding
                ))
                conn.commit()
                print("   💾 Đã lưu vào Database!")

                # Nghỉ 4 giây để tránh vượt giới hạn Free Tier của Gemini
                time.sleep(4)

            except Exception as e:
                conn.rollback() # Hoàn tác nếu lỗi SQL để không kẹt các phim sau
                print(f"   ❌ Lỗi: {e}")

    # 4. THÊM MỚI: Đóng kết nối khi chạy xong toàn bộ
    cur.close()
    conn.close()
    print("\n🎉 Hoàn tất nạp dữ liệu vào Database!")

main()