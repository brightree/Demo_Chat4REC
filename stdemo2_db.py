import streamlit as st
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import TypedDict
import uuid
import openai
from langgraph.graph import StateGraph
from supabase import create_client

# 🎯 초기 설정
load_dotenv()
api_key = os.getenv("MY_API_KEY")
if not api_key:
    st.error("❗OpenAI API 키가 설정되지 않았습니다.")
    st.stop()
client = openai.OpenAI(api_key=api_key)

# 🔗 Supabase 연결
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🧱 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

# 📚 강의 데이터 로드
@st.cache_data
def load_course_data():
    try:
        with open("sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
            return json.load(f)["courses"]
    except Exception as e:
        st.error(f"❗강의 데이터를 불러오지 못했습니다: {e}")
        return []
course_data = load_course_data()

# 🧠 LangGraph 구조
class GraphState(TypedDict):
    user_query: str
    final_response: str

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

builder = StateGraph(GraphState)
builder.add_node("recommend_courses", recommend_courses)
builder.set_entry_point("recommend_courses")
graph = builder.compile()

# 💾 Supabase 저장 함수
def save_chat_to_db(user_input, llm_response):
    supabase.table("chat_history").insert({
        "user_id": "guest_user",
        "conversation_id": st.session_state.conversation_id,
        "turn_index": st.session_state.turn_index,
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": user_input,
        "llm_response": llm_response
    }).execute()
    st.session_state.turn_index += 1

def update_feedback(turn_index, feedback_value):
    supabase.table("chat_history").update({
        "feedback": feedback_value
    }).eq("conversation_id", st.session_state.conversation_id).eq("turn_index", turn_index).execute()

# 🎨 UI 구성
st.set_page_config(page_title="삼성 세일즈 챗봇", layout="centered", initial_sidebar_state="collapsed")
samsung_blue = "#1428A0"
st.markdown(f"""
    <div style="text-align:center;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="180" />
        <h2 style="color:{samsung_blue};">삼성전자 세일즈 강의 추천 챗봇</h2>
    </div>
    """, unsafe_allow_html=True)

# 📝 입력 폼
with st.form("query_form"):
    user_input = st.text_area("💬 세일즈 고민을 입력해 주세요", height=120)
    submitted = st.form_submit_button("추천받기")

# 🚀 응답 생성 + 저장
if submitted and user_input.strip():
    with st.spinner("추천 생성 중..."):
        result = graph.invoke({"user_query": user_input})
        response_text = result["final_response"]
        st.session_state.chat_history.append(
            {"user": user_input, "bot": response_text}
        )
        save_chat_to_db(user_input, response_text)

# 💬 대화 내용 표시 + 피드백 버튼
for idx, turn in enumerate(st.session_state.chat_history):
    # 사용자 메시지 (오른쪽 정렬)
    st.markdown(f"""
    <div style="text-align:right; margin-bottom: 4px;">
        <div style="display: inline-block; background-color:#E3F2FD; color: black; padding: 10px 14px; border-radius: 18px; max-width: 80%; font-size: 15px;">
            {turn['user']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 챗봇 응답 (왼쪽 정렬)
    st.markdown(f"""
    <div style="text-align:left; margin-bottom: 12px;">
        <div style="display: inline-block; background-color:#F1F1F1; color: black; padding: 10px 14px; border-radius: 18px; max-width: 80%; font-size: 15px;">
            <pre style="margin:0; white-space:pre-wrap;">{turn['bot']}</pre>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 피드백 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("👍 좋아요", key=f"like_{idx}"):
            update_feedback(idx, "positive")
    with col2:
        if st.button("👎 별로예요", key=f"dislike_{idx}"):
            update_feedback(idx, "negative")

    st.markdown("---")

