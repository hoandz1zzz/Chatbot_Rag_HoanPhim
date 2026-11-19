import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DB_URL = "postgresql://ai_admin:secretpassword@localhost:5435/ai_rag_db"
client = genai.Client()

def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    cur.close()
    register_vector(conn)
    return conn

def get_embedding(text: str):
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    return response.embeddings[0].values

def search_movies(query: str, top_k: int = 5):
    conn = get_db_connection()
    cur = conn.cursor()

    query_vector = get_embedding(query)

    cur.execute("""
        SELECT slug, name, thumb_url, genres, content_for_rag, (embedding <=> %s::vector) AS distance
        FROM movie_embeddings
        ORDER BY distance ASC
        LIMIT %s;
    """, (query_vector, top_k))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "slug": slug,
            "name": name,
            "thumb_url": thumb_url,
            "genres": genres,
            "content_for_rag": content,
            "similarity": round((1 - distance) * 100, 1)
        }
        for slug, name, thumb_url, genres, content, distance in rows
    ]