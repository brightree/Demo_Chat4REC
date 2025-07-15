import streamlit as st
from datetime import datetime

def render_samsung_header():
    samsung_blue = "#1428A0"
    st.markdown(
        f"""
        <div style="text-align:center; margin-bottom:16px;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="160" />
            <h2 style="color:{samsung_blue}; margin-bottom:4px; font-weight:800;">삼성전자 Sales Agentic Assistant</h2>
            <p style="font-size:16px; margin-bottom:2px; color:#3b466b;">
                제품 스펙 정보부터 고객 커뮤니케이션 고민까지, 무엇이든 물어보세요!
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_app_ui(graph, save_chat_to_db):
    st.set_page_config(
        page_title="삼성 세일즈 Agentic 챗봇",
        page_icon="💼",
        layout="wide"
    )

    # === 세션 상태 초기화 ===
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "selected_tab" not in st.session_state:
        st.session_state.selected_tab = "챗봇"
    if "is_typing" not in st.session_state:
        st.session_state.is_typing = False
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    # === 다크모드 CSS 삽입 ===
    dark_mode = st.session_state.get("dark_mode", False)
    if dark_mode:
        st.markdown("""
        <style>
        /* 전체 페이지 및 메인 컨테이너 */
        html, body, .stApp, .main-container {
            background-color: #1b2437 !important;
            color: #f0f0f0 !important;
        }
        /* 사이드바 */
        section[data-testid="stSidebar"], .css-6qob1r, .stSidebar {
            background-color: #20283b !important;
            color: #f0f0f0 !important;
        }
        /* 헤더 */
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .st-b8, .stText, .stCheckbox {
            color: #f0f0f0 !important;
        }
        /* 카드, 안내문 */
        .stAlert, .st-bc, .st-cq, .st-bc {
            background-color: #223054 !important;
            color: #e1eafd !important;
            border: 1px solid #31416a !important;
        }
        /* 다크모드 토글 라벨 */
        .stCheckbox>label { color: #e1eafd !important; }

        /* 기존 말풍선/버튼 등도 그대로 유지 */
        .chat-bubble-user { background: #2b3350 !important; color: #fff !important; }
        .chat-bubble-assistant { background: #203156 !important; color: #b6cff6 !important; border: 1px solid #42527e; }
        .quick-btn-row { background: transparent; }
        .quick-btn { background: #252b3a !important; color: #b0bfe8 !important; border: 1.5px solid #42527e; }
        .quick-btn:hover { background: #263040 !important; color: #b6cff6 !important; border: 1.5px solid #b6cff6; }
        .chat-time { color: #6b7aa5 !important; }
        </style>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <style>
        .main-container {
            max-width: 680px;
            margin: 0 auto;
            padding: 28px 0 48px 0;
        }
        .chat-bubble-user {
            background: #F5F7FA;
            color: #1B2437;
            padding: 14px 18px;
            border-radius: 17px 17px 5px 17px;
            display: inline-block;
            margin-bottom: 8px;
            font-size: 17px;
            box-shadow: 0 2px 8px 0 rgba(30,48,120,0.03);
            max-width: 90%;
        }
        .chat-bubble-assistant {
            background: #e7f0fd;
            color: #1428A0;
            padding: 14px 18px;
            border-radius: 17px 17px 17px 5px;
            display: inline-block;
            margin-bottom: 8px;
            font-size: 17px;
            font-weight: 500;
            box-shadow: 0 4px 18px 0 rgba(20,40,160,0.10);
            border: 1px solid #b6cff6;
            max-width: 90%;
        }
        .quick-btn-row {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin: 18px 0 22px 0;
        }
        .quick-btn {
            background: #fff;
            border: 1.5px solid #B0BFE8;
            color: #1428A0;
            padding: 9px 24px 9px 24px;
            border-radius: 32px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s, color 0.15s, border 0.18s;
            box-shadow: 0 2px 12px 0 rgba(20,40,160,0.05);
        }
        .quick-btn:hover {
            background: #edf4fd;
            color: #2b52b8;
            border: 1.5px solid #1428A0;
        }
        .chat-time {
            font-size: 12.5px;
            color: #97a2bd;
            margin: 2px 0 15px 3px;
        }
        </style>
        """, unsafe_allow_html=True)

    # === 사이드바 ===
    with st.sidebar:
        st.image("demo/logo_black.png", width=150)
        st.session_state.selected_tab = st.radio(
            "메뉴",
            ("챗봇", "히스토리", "설정"),
            index=["챗봇", "히스토리", "설정"].index(st.session_state.selected_tab)
        )
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.write("**Powered by 삼성전자 Sales AI**")

    # === 메인 컨테이너 (최상단에 단 1번만 로고/헤더!) ===
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    render_samsung_header()

    tab = st.session_state.selected_tab

    # === 각 탭 별 내용 ===
    if tab == "챗봇":
        st.markdown("#### 💬 대화")

        # 퀵 리플라이 버튼 (원하면 key, 텍스트 수정)
        st.markdown('<div class="quick-btn-row">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,1,1], gap="small")
        with col1:
            if st.button("FAQ Button1", key="quick_as", use_container_width=True):
                st.session_state.quick_input = "FAQ Button1"
        with col2:
            if st.button("FAQ Button2", key="quick_stock", use_container_width=True):
                st.session_state.quick_input = "FAQ Button2"
        with col3:
            if st.button("FAQ Button3", key="quick_spec", use_container_width=True):
                st.session_state.quick_input = "FAQ Button3"
        st.markdown('</div>', unsafe_allow_html=True)

        # 퀵 리플라이 버튼 클릭 감지
        import streamlit as stq  # streamlit-query-params 필요시만
        quick_val = stq.get_query_params().get("quick", [""])[0] if hasattr(stq, "get_query_params") else ""
        if quick_val:
            if quick_val == "as":
                st.session_state.quick_input = "FAQ Button1"
            elif quick_val == "stock":
                st.session_state.quick_input = "FAQ Button2"
            elif quick_val == "spec":
                st.session_state.quick_input = "FAQ Button3"

        # 채팅 내역 표시
        for turn in st.session_state.chat_history:
            st.markdown(
                f'<div class="chat-bubble-user">🙍‍♂️ {turn["user"]}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="chat-bubble-assistant">{turn["bot"]}</div>',
                unsafe_allow_html=True
            )
            st.markdown(f'<div class="chat-time">{turn["time"]}</div>', unsafe_allow_html=True)

        # 사용자 입력
        user_input = ""
        if "quick_input" in st.session_state and st.session_state.quick_input:
            user_input = st.session_state.quick_input
            st.session_state.quick_input = ""
        else:
            user_input = st.chat_input("제품 및 세일즈 관련 궁금점을 말씀해 주세요.")

        if user_input:
            st.markdown(
                f'<div class="chat-bubble-user">🙍‍♂️ {user_input}</div>',
                unsafe_allow_html=True
            )
            with st.spinner("AI가 답변을 작성 중입니다..."):
                st.session_state.is_typing = True
                result = graph.invoke({"user_query": user_input})
                response_text = result.get("final_response", "")
                if isinstance(response_text, dict):
                    response_text = response_text.get("result", str(response_text))
                route_used = result.get("route", "")
                if route_used == "agent1":
                    response_header = "📱 [제품 정보 Agent]"
                elif route_used == "agent2":
                    response_header = "🎓 [학습 추천 Agent]"
                else:
                    response_header = "🤖 [Agent 응답]"
                bot_response = f"{response_header}<br><br>{response_text}"
                st.markdown(
                    f'<div class="chat-bubble-assistant">{bot_response}</div>',
                    unsafe_allow_html=True
                )
            st.session_state.is_typing = False
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.chat_history.append({
                "user": user_input,
                "bot": bot_response,
                "time": now
            })
            save_chat_to_db(user_input, response_text)
            st.rerun()

    elif tab == "히스토리":
        st.markdown("#### 📚 대화 히스토리")
        if not st.session_state.chat_history:
            st.info("아직 대화 히스토리가 없습니다.")
        else:
            for idx, turn in enumerate(reversed(st.session_state.chat_history)):
                with st.expander(f"{turn['time']} | {turn['user'][:18]}..."):
                    st.markdown(
                        f'<div class="chat-bubble-user">🙍‍♂️ {turn["user"]}</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<div class="chat-bubble-assistant">{turn["bot"]}</div>',
                        unsafe_allow_html=True
                    )

    elif tab == "설정":
        st.markdown("#### ⚙️ 설정")
        dark_mode_val = st.checkbox("🌙 다크모드", value=st.session_state.dark_mode)
        st.session_state.dark_mode = dark_mode_val        
        st.info("추후 사용자 프로필, 다크모드, 데이터 초기화 등 환경설정 메뉴를 구현 예정!")
        st.info("Router 기반으로 Agent1, Agent2를 구분하는 것이 아닌, 탭에서 Agent1, Agent2를 선택하는 방향도 고려 중")

    st.markdown('</div>', unsafe_allow_html=True)  # main-container end

