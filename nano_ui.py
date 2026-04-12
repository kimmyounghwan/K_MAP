import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import nano_const

# 1. 페이지 설정
st.set_page_config(page_title="k_건설맵", layout="wide", initial_sidebar_state="expanded")

# 2. 디자인 설정
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    .stApp { background-color: #f8fafc; }

    .blue-bar { 
        background-color: #1e3a8a; color: white; 
        border-radius: 8px; margin-bottom: 15px; 
        font-weight: 900; font-size: 28px; letter-spacing: 2px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        padding-top: 35px !important;    
        padding-bottom: 15px !important; 
    }
    .blue-bar p { margin: 0 !important; padding: 0 !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 사이드바 메뉴
with st.sidebar:
    st.markdown("### 🏛️ k_건설맵 메뉴")
    menu = st.radio("이동할 페이지를 선택하세요:", ["📊 실시간 공고 (홈)", "📝 자유 게시판", "👤 로그인 / 회원가입"])
    st.write("---")
    st.info("💡 최초 1회 로딩 시 조달청 데이터를 가져오느라 약간 느릴 수 있습니다. 이후에는 0.1초 만에 열립니다!")

# 🚀 캐시(기억 장치) 사용
if 'master_data' not in st.session_state:
    with st.spinner("조달청 앞문을 열고 최신 공고를 싹 쓸어오는 중입니다... (조금만 기다려주세요!)"):
        st.session_state['master_data'] = nano_const.fetch_monster_announcements()

# =========================================
# 🟢 메뉴 1: 메인 화면
# ==========================================
if menu == "📊 실시간 공고 (홈)":
    st.markdown('<div class="blue-bar"><p>🏛️ k_건설맵 실시간 현황판</p></div>', unsafe_allow_html=True)

    df = st.session_state['master_data'].copy()

    if not df.empty:
        # 🚨 최신 날짜 1등으로 올리기
        df['정렬용시간'] = pd.to_datetime(df['bidNtceDt'], errors='coerce')
        df = df.sort_values(by='정렬용시간', ascending=False, na_position='last').reset_index(drop=True)

        df['공고일자'] = df['정렬용시간'].dt.strftime('%Y-%m-%d').fillna('날짜미상')
        df['예산금액'] = pd.to_numeric(df['bdgtAmt'], errors='coerce').fillna(0)


        # 링크 생성 로직
        def get_safe_link(row):
            if 'bidNtceDtlUrl' in row and pd.notna(row['bidNtceDtlUrl']) and str(row['bidNtceDtlUrl']).strip() != "":
                return str(row['bidNtceDtlUrl']).replace(":8081", "").replace(":8101", "")
            else:
                return f"https://www.g2b.go.kr/ep/invitation/publish/bidInfoDtl.do?bidno={row['bidNtceNo']}&bidseq={row['bidNtceOrd']}"


        df['🔗 상세내용'] = df.apply(get_safe_link, axis=1)

        # 📊 상단 요약 대시보드
        KST = timezone(timedelta(hours=9))
        today_str = datetime.now(KST).strftime('%Y-%m-%d')
        today_count = len(df[df['공고일자'] == today_str])

        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            st.metric(label="누적 공고(최근 7일)", value=f"{len(df):,}건")
        with col2:
            st.metric(label="오늘(TODAY) 신규", value=f"{today_count}건")
        with col3:
            st.metric(label="데이터 기준일", value=today_str)
        with col4:
            if st.button("🔄 최신 데이터 갱신", use_container_width=True):
                st.cache_data.clear()
                if 'master_data' in st.session_state:
                    del st.session_state['master_data']
                st.rerun()

        st.write("---")

        # 📋 표 출력
        view_df = df[['bidNtceNo', '공고일자', 'bidNtceNm', 'ntceInsttNm', '예산금액', '🔗 상세내용']]
        view_df.columns = ['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세내용']

        st.dataframe(
            view_df,
            use_container_width=True,
            hide_index=True,
            height=750,
            column_config={
                "상세내용": st.column_config.LinkColumn("상세보기", display_text="공고문 열기"),
                "예산금액": st.column_config.NumberColumn("예산금액(원)", format="%,d")
            }
        )
    else:
        st.warning("🚨 조달청 서버 응답이 지연되고 있습니다. '최신 데이터 갱신' 버튼을 눌러주세요.")

# ==========================================
# 🟢 메뉴 2: 자유 게시판
# ==========================================
elif menu == "📝 자유 게시판":
    st.markdown('<div class="blue-bar"><p>📝 회원 자유 게시판</p></div>', unsafe_allow_html=True)
    st.info("이곳에 회원들이 영업 정보를 교환하거나 질문을 올릴 수 있는 게시판이 만들어질 예정입니다.")

# ==========================================
# 🟢 메뉴 3: 로그인 / 회원가입
# ==========================================
elif menu == "👤 로그인 / 회원가입":
    st.markdown('<div class="blue-bar"><p>👤 K_건설맵 로그인</p></div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.write("### 시스템 접속")
        login_id = st.text_input("아이디 (ID)")
        login_pw = st.text_input("비밀번호 (Password)", type="password")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("로그인", use_container_width=True):
                st.warning("로그인 기능은 데이터베이스(DB) 연결 후 작동합니다.")
        with col2:
            if st.button("회원가입", use_container_width=True):
                st.warning("회원가입 폼이 열릴 예정입니다.")