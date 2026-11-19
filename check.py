from google import genai
from dotenv import load_dotenv

# Tải API Key từ file .env
load_dotenv()
client = genai.Client()

print("Danh sách các Model chuyên làm Embedding hiện có của Google:\n" + "-"*50)

# Duyệt qua toàn bộ danh sách model Google đang cung cấp
for model in client.models.list():
    # Lọc ra những model có chữ "embedding" trong tên
    if "embedding" in model.name.lower():
        print(f"✅ Tên model: {model.name}")
        print(f"   - Mô tả: {model.description}")
        print("-" * 50)