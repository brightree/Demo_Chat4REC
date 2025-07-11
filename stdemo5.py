# 반영 사항
    # 멀티턴

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
    # 💬 이전 대화 포함
    full_history = ""
    for turn in st.session_state.chat_history:
        full_history += f"사용자: {turn['user']}\n"
        full_history += f"챗봇: {turn['bot']}\n"
    full_history += f"사용자: {state['user_query']}\n"

    prompt = f"""
당신은 삼성전자 영업사원을 위한 "전문 강의 추천 챗봇"입니다.

## 역할
- 삼성전자 영업사원이 제품 설명, 고객 상담, 세일즈 전략 등 업무에서 겪는 고민을 기반으로, 가장 적합한 강의를 추천하는 챗봇입니다.
- 사용자는 바쁜 업무 중 질문하므로, 응답은 항상 **핵심적이고 간결하게**, **친근하면서도 전문적인 어투**로 전달해야 합니다.

## 목표
- 사용자의 고민/상황/선호 스타일을 파악하여 맞춤 강의 3~5개를 추천합니다.
- 단, 사용자가 "지금 바로 추천해줘"라고 말하지 않는 이상, 반드시 **2~3번의 짧은 대화**를 통해 정보를 수집합니다.

## 대화 흐름 지침 (Flow Logic)
1. **정보 수집**
   - 사용자의 응답에 따라 자연스럽게 질문을 이어가며, 한 번에 하나의 질문만 던집니다.
   - 질문은 짧고 명확하게. 다음 흐름을 따라야 합니다:
     - 1차 질문: 어떤 상황이 고민이신가요? (예: 고객 응대, 제품 설명, 매출 저조 등)
     - 2차 질문: 그 중 어떤 유형의 고객이나 제품이 가장 어렵게 느껴지시나요?
     - 3차 질문: 강의 스타일은 어떤 걸 선호하시나요? (짧고 핵심적인가요, 사례 중심인가요?)

2. **즉시 추천 예외**
   - 사용자가 “지금 바로 추천해줘”라고 말하면, 질문 생략 후 바로 추천을 진행합니다.

3. **추천 응답 형식**
   - 강의는 다음 정보를 담되, 자연스럽고 간결한 문장으로 구성합니다:
     - 강의 제목
     - 추천 이유 (사용자 고민과 연결)
     - 링크: https://www.ubion.co.kr/ubion/
   - 추천 강의는 **중요도 순서로 3~5개**, 항목별로 구분해 제시합니다.

4. **예외 응대**
   - 사용자가 농담, 과격한 표현, 욕설 등을 입력하더라도 감정적 대응 없이 원래 주제로 자연스럽게 유도합니다.

## 응답 스타일 (Tone & Format)
- 말투: 친근하지만 단정한 말투 (반말 OK, 무례 X)
- 문장: 짧고 핵심적으로, 정보 밀도 높게
- 불필요한 서두/결론/과잉 설명 배제
- 사용자의 표현을 요약하며 다음 질문 또는 추천으로 자연스럽게 연결

## 응답 예시 (참고용 프라이밍)
사용자: 고객 응대가 힘들어요  
→ 챗봇: 고객 대응이 어려우시군요. 혹시 어떤 유형의 고객이 특히 어려우셨나요? 예를 들면 불만 고객, 설명을 못 알아듣는 고객 등요.  

사용자: 집중이 잘 안돼서 짧은 강의가 좋을 것 같아요  
→ 챗봇: 짧고 핵심 위주 스타일을 선호하시는군요. 그럼 고객 응대와 관련해 바로 써먹을 수 있는 사례 중심 강의 위주로 추천드릴게요.  
→ [강의 추천 시작]


[대화 기록]
{full_history}

이 대화 내용을 바탕으로 추가 질문이 필요하면 자연스럽게 이어가고,  
정보가 충분하다고 판단되면 강의를 추천해줘.


[강의 목록]
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

# 🎨 페이지 UI
st.set_page_config(
    page_title="삼성 세일즈 챗봇",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

samsung_blue = "#1428A0"
st.markdown(f"""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="180" />
        <h2 style="color:{samsung_blue};">삼성전자 세일즈 강의 추천 챗봇</h2>
        <p style="font-size:15px;">제품 정보 부족, 소심한 성격, 커뮤니케이션 고민 등 무엇이든 입력해보세요.</p>
    </div>
""", unsafe_allow_html=True)

# 💬 이전 대화 렌더링
for turn in st.session_state.chat_history:
    # 사용자 메시지 (오른쪽 정렬)
    st.markdown(f"""
    <div style="text-align:right; margin: 8px 0;">
        <div style="display:inline-block; background-color:#DCF8C6; color:#000; padding:10px 14px; border-radius:18px; max-width:70%; font-size:15px;">
            {turn['user']}
        </div> 🦁
    </div>
    """, unsafe_allow_html=True)

    # 챗봇 메시지 (왼쪽 정렬 + 삼성 로고)
    st.markdown(f"""
    <div style="text-align:left; margin: 8px 0;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="32" height="32" style="vertical-align:middle; margin-right:8px;" />
        <div style="display:inline-block; background-color:#F1F0F0; color:#000; padding:10px 14px; border-radius:18px; max-width:75%; font-size:15px;">
            <pre style="white-space:pre-wrap; margin:0;">{turn['bot']}</pre>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 📝 입력창 (하단 고정)
user_input = st.chat_input("세일즈 고민을 입력해 주세요")
if user_input:
    # 오른쪽 말풍선 출력
    st.markdown(f"""
    <div style="text-align:right; margin: 8px 0;">
        <div style="display:inline-block; background-color:#DCF8C6; color:#000; padding:10px 14px; border-radius:18px; max-width:70%; font-size:15px;">
            {user_input}
        </div> 🦁
    </div>
    """, unsafe_allow_html=True)

    # LangGraph 호출
    result = graph.invoke({"user_query": user_input})
    response_text = result["final_response"]

    # 왼쪽 말풍선 출력
    st.markdown(f"""
    <div style="text-align:left; margin: 8px 0; position: relative;">
        <div style="display:inline-block; background-color:#F1F0F0; color:#000; padding:14px 14px 10px 14px; border-radius:18px; max-width:75%; font-size:15px; position:relative;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg"
                width="40" height="14"
                style="position: absolute; top: 10px; left: 10px;" />
            <div style="padding-top: 24px;">
                <pre style="white-space:pre-wrap; margin:0;">{response_text}</pre>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.session_state.chat_history.append({"user": user_input, "bot": response_text})
    save_chat_to_db(user_input, response_text)