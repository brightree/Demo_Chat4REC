from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import TypedDict, List, Dict
import openai
from langgraph.graph import StateGraph

# 1. 환경 변수 및 OpenAI 클라이언트 설정
load_dotenv()
api_key = os.getenv("MY_API_KEY")
client = openai.OpenAI(api_key=api_key)

# 2. 강의 데이터 로드
with open("sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
    course_data = json.load(f)["courses"]

# 3. 상태 구조 정의
class GraphState(TypedDict):
    user_query: str
    structured_filter: dict
    filtered_courses: List[Dict]
    final_response: str

# 4. 쿼리 파싱 함수 (자연어 → 조건 JSON)
def parse_query(state: GraphState) -> GraphState:
    field_names = ["course_id", "title", "description", "created_at", "user_rating",
                   "category", "difficulty", "avg_watch_time", "num_reviews", "tags"]

    prompt = f"""
너는 세일즈 학습 분석 챗봇이야.
사용자 요청에서 조건을 추출해서 JSON 필터 형식으로 변환해줘.

가능한 필드는 다음과 같아:
{field_names}

출력 예시:
{{
  "filters": {{
    "created_at": {{"after": "YYYY-MM-DD"}},
    "user_rating": {{"gte": 4.0}},
    "category": "실전 세일즈"
  }},
  "user_context": "성과 압박"
}}

사용자 요청:
'{state['user_query']}'
"""
    res = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "자연어 요청에서 조건을 추출하는 JSON 파서"},
            {"role": "user", "content": prompt}
        ]
    )
    try:
        parsed = json.loads(res.choices[0].message.content)
    except:
        parsed = {}

    return {**state, "structured_filter": parsed}

# 5. 조건에 따라 강의 필터링
def safe_parse_date(val):
    try:
        if isinstance(val, str):
            return datetime.fromisoformat(val)
    except Exception:
        return None
    return None

def evaluate_condition(key: str, value, condition) -> bool:
    # 단순 값 비교
    if not isinstance(condition, dict):
        return value == condition

    # 복합 조건 (gte, lte, after, before 등)
    for op, comp in condition.items():
        if value is None or comp is None:
            return False
        
        if op == "gte":
            return value >= comp
        elif op == "lte":
            return value <= comp
        elif op == "after":
            val_dt = safe_parse_date(value)
            comp_dt = safe_parse_date(comp)
            return val_dt is not None and comp_dt is not None and val_dt > comp_dt
        elif op == "before":
            val_dt = safe_parse_date(value)
            comp_dt = safe_parse_date(comp)
            return val_dt is not None and comp_dt is not None and val_dt < comp_dt

    return False  # 알 수 없는 연산자일 경우

def filter_courses(state: GraphState) -> GraphState:
    filters = state["structured_filter"].get("filters", {})
    results = []

    for course in course_data:
        include = True

        for key, condition in filters.items():
            course_value = course.get(key)

            # 리스트 조건
            if isinstance(condition, list):
                if course_value not in condition:
                    include = False
                    break

            # 단일값/딕셔너리 조건
            elif not evaluate_condition(key, course_value, condition):
                include = False
                break

        if include:
            results.append(course)

    return {**state, "filtered_courses": results}



# 6. 추천 응답 생성
def generate_response(state: GraphState) -> GraphState:
    top_courses = state["filtered_courses"][:5]
    user_context = state["structured_filter"].get("user_context", "")

    summary_prompt = f"""
너는 세일즈 러닝 추천 챗봇이야.
사용자 고민 또는 맥락: "{user_context}"

아래 강의 리스트를 분석해서 각각 어떤 이유로 추천하는지 간결히 설명해줘.
형식:
- 강의 제목: ...
  추천 이유: ...

강의 목록:
{json.dumps(top_courses, ensure_ascii=False, indent=2)}
"""
    res = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "추천 요약 생성기 (이유 포함)"},
            {"role": "user", "content": summary_prompt}]
    )
    return {**state, "final_response": res.choices[0].message.content.strip()}

# 7. LangGraph 구성
builder = StateGraph(GraphState)
builder.add_node("parse_query", parse_query)
builder.add_node("filter_courses", filter_courses)
builder.add_node("generate_response", generate_response)

builder.set_entry_point("parse_query")
builder.add_edge("parse_query", "filter_courses")
builder.add_edge("filter_courses", "generate_response")

graph = builder.compile()

# 8. 실행 함수
def run_chatbot(user_input: str):
    result = graph.invoke({"user_query": user_input})
    print("\n📚 강의 추천 결과:\n")
    print(result["final_response"])

# 9. 테스트 실행
if __name__ == "__main__":
    q = "최근 업로드된 실전 세일즈 강의 중 평균 시청 시간이 긴 편이고, 리뷰 수가 많은 강의 추천해줘. 내 고민은 성과 압박 때문에 무리한 설득을 자주 한다는 거야."
    run_chatbot(q)
