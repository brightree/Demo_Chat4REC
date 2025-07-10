import streamlit as st
from dotenv import load_dotenv
import os
import json
from typing import TypedDict, List, Dict
import openai
from langgraph.graph import StateGraph

# 🎯 1. 초기 설정
load_dotenv()
api_key = os.getenv("MY_API_KEY")

if not api_key:
    st.error("❗OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# 📚 2. 강의 데이터 로드
@st.cache_data
def load_course_data():
    try:
        with open("sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
            return json.load(f)["courses"]
    except Exception as e:
        st.error(f"❗강의 데이터를 불러오지 못했습니다: {e}")
        return []

course_data = load_course_data()

# 🧱 3. 상태 정의
class GraphState(TypedDict):
    user_query: str
    final_response: str

# 🧠 4. 추천 노드
def recommend_courses(state: GraphState) -> GraphState:
    prompt = f"""
너는 삼성전자의 세일즈 러닝 추천 챗봇이야.

사용자 요청:
{state['user_query']}

아래는 세일즈 강의 리스트야. 사용자 상황을 고려해 3~5개 적절한 강의를 추천하고, 간단한 추천 이유도 포함해줘.

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
                {"role": "system", "content": "삼성전자 세일즈 강의 추천 전문가"},
                {"role": "user", "content": prompt}
            ]
        )
        response_text = res.choices[0].message.content.strip()
    except Exception as e:
        response_text = f"❗추천 생성 중 오류 발생: {e}"

    return {**state, "final_response": response_text}

# 🔗 5. LangGraph 구성
builder = StateGraph(GraphState)
builder.add_node("recommend_courses", recommend_courses)
builder.set_entry_point("recommend_courses")
graph = builder.compile()

# 🎨 6. UI 설정
st.set_page_config(
    page_title="삼성 세일즈 강좌 추천 챗봇",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

samsung_blue = "#1428A0"

st.markdown(
    f"""
    <div style="text-align:center;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="180" style="margin-bottom:20px;" />
        <h2 style="color:{samsung_blue};">삼성전자 전용 세일즈 강좌 추천 챗봇</h2>
        <p style="font-size:16px;">성과 압박, 설득 난관 등 다양한 세일즈 상황에 맞춘 강의를 추천해드립니다.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# 📝 7. 사용자 입력
with st.form("query_form"):
    user_input = st.text_area("💬 세일즈 상황이나 고민을 입력해 주세요", height=120)
    submitted = st.form_submit_button("추천받기")

# 🚀 8. 실행
if submitted:
    if not user_input.strip():
        st.warning("❗내용을 입력해 주세요.")
    else:
        with st.spinner("추천 생성 중..."):
            result = graph.invoke({"user_query": user_input})
            st.success("✅ 추천 결과")

            st.markdown(f"""
            <div style="background-color:#f9f9f9;border-left:5px solid {samsung_blue};padding:16px;margin-top:10px;">
            <pre style="white-space:pre-wrap;">{result['final_response']}</pre>
            </div>
            """, unsafe_allow_html=True)
