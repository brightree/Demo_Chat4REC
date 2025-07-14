import streamlit as st
from datetime import datetime, timezone

# ==============================
# 🎨 Streamlit UI
# ==============================
def render_app_ui(graph, save_chat_to_db):
    st.set_page_config(
        page_title="삼성 세일즈 Agentic 챗봇",
        page_icon="💼",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # 이전 채팅 내역 표시
    for turn in st.session_state.chat_history:
        st.chat_message("user").write(turn["user"])
        st.chat_message("assistant").write(turn["bot"])

    samsung_blue = "#1428A0"
    st.markdown(f"""
        <div style="text-align:center; margin-bottom:20px;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="180" />
            <h2 style="color:{samsung_blue};">삼성전자 Sales Agentic Assitant</h2>
            <p style="font-size:15px;">제품 스펙 정보부터 고객 커뮤니케이션 고민까지, 무엇이든 물어보세요!</p>
        </div>
    """, unsafe_allow_html=True)

    user_input = st.chat_input("세일즈 관련 궁금점을 말씀해 주세요.")
    if user_input:
        st.chat_message("user").write(user_input)
        result = graph.invoke({"user_query": user_input})
        response_text = result["final_response"]

        # 어떤 Agent가 응답했는지 표시
        route_used = result.get("route", "")
        if route_used == "agent1":
            response_header = "📱 [제품 정보 Agent]"
        elif route_used == "agent2":
            response_header = "🎓 [학습 추천 Agent]"
        else:
            response_header = "🤖 [Agent 응답]"

        st.chat_message("assistant").write(f"{response_header}\n\n{response_text}")

        # 채팅 내역 저장
        st.session_state.chat_history.append({
            "user": user_input,
            "bot": f"{response_header}\n\n{response_text}"
        })
        save_chat_to_db(user_input, response_text)