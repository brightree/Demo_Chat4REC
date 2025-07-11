# 연결
from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# 데이터 조회
res = supabase.table("chat_history").select("*").limit(10).order("timestamp", desc=True).execute()
records = res.data

# 출력
for row in records:
    print(f"[{row['timestamp']}] {row['user_input']} → {row['llm_response'][:40]}...")
