from dotenv import load_dotenv
import os
from openai import OpenAI

# 환경 변수
load_dotenv()
api_key = os.getenv("MY_API_KEY")

# OpenAI API 키 설정
client = OpenAI(api_key=api_key)

# GPT-4.1 nano 모델 호출 (예시)
response = client.chat.completions.create(
    model="gpt-4.1-nano",  
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "GPT 4.1 nano에 대해서 설명해줘."}
    ]
)

# 결과 출력
print(response.choices[0].message.content)