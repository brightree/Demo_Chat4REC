from dotenv import load_dotenv
import os
import json
from typing import TypedDict, List, Dict
import openai
from langgraph.graph import StateGraph

# 1. 환경 변수 로드 및 OpenAI 클라이언트 초기화
load_dotenv()
api_key = os.getenv("MY_API_KEY")
client = openai.OpenAI(api_key=api_key)

# 2. 강의 데이터 로드
with open("sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
    course_data = json.load(f)["courses"]

# 3. 상태 정의
class GraphState(TypedDict):
    user_query: str
    final_response: str

# 4. 추천 노드: LLM이 강의 데이터를 해석해 추천
def recommend_courses(state: GraphState) -> GraphState:
    prompt = f"""
너는 세일즈 학습 추천 챗봇이야.

사용자 요청:
{state['user_query']}

아래는 강의 리스트야. 사용자 요청을 고려해서 적절한 강의 3~5개를 추천해줘.
각 강의마다 추천 이유도 간단히 포함해줘.

형식:
- 강의 제목: ...
  추천 이유: ...

강의 목록:
{json.dumps(course_data, ensure_ascii=False, indent=2)}
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "세일즈 강의 추천 전문가"},
                {"role": "user", "content": prompt}
            ]
        )
        response_text = res.choices[0].message.content.strip()
    except Exception as e:
        response_text = f"❗추천 생성 중 오류 발생: {e}"

    return {**state, "final_response": response_text}

# 5. LangGraph 구성
builder = StateGraph(GraphState)
builder.add_node("recommend_courses", recommend_courses)
builder.set_entry_point("recommend_courses")
graph = builder.compile()

# 6. 실행 함수
def run_chatbot(user_input: str):
    result = graph.invoke({"user_query": user_input})
    print("\n📚 강의 추천 결과:\n")
    print(result["final_response"])

# 7. 테스트 실행
if __name__ == "__main__":
    user_input = input("📝 세일즈 관련 고민과 추천 받고 싶은 강의를 말씀해 주세요:\n> ")
    run_chatbot(user_input)
