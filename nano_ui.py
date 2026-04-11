import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib3
import streamlit as st
import concurrent.futures
import time

# --- [메모장 파트 1: 엔진 설정] ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"
KST = timezone(timedelta(hours=9))


@st.cache_data(ttl=600)
def fetch_monster_announcements():
    all_raw = []
    end_date = datetime.now(KST).date()
    start_date = end_date - timedelta(days=60)
    delta = end_date - start_date
    dates = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(delta.days + 1)]

    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'

    def fetch_per_day(dt):
        params = {
            'inqryDiv': '1', 'inqryBgnDt': f'{dt}0000', 'inqryEndDt': f'{dt}2359',
            'pageNo': '1', 'numOfRows': '999', 'bidNtceNm': '공사',
            'type': 'json', 'serviceKey': API_KEY
        }
        for _ in range(3):
            try:
                res = requests.get(url, params=params, verify=False, timeout=10)
                if res.status_code == 200:
                    items = res.json().get('response', {}).get('body', {}).get('items', [])
                    return items if items else []
            except:
                time.sleep(0.5)
                continue
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_per_day, dates))
        for res in results:
            if res: all_raw.extend(res)

    return pd.DataFrame(all_raw)


# --- [메모장 파트 2: UI 설정] ---
st.set_page_config(page_title="k_건설맵", layout="wide", initial_sidebar_state="expanded")

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

with st.sidebar:
    st.markdown("### 🏛️ k_건설맵 메뉴")
    menu = st.radio("이동할 페이지를 선택하세요:", ["📊 실시간 공고 (홈)", "📝 자유 게시판", "👤 로그인 / 회원가입"])
    st.write("---")
    st.info("💡 최초 1회 로딩 시 조달청 데이터를 가져오느라 약간 느릴 수 있습니다.")

if 'master_data' not in st.session_state:
    with st.spinner("조달청에서 안전하게 2개월치 최신 공고를 싹 쓸어오는 중입니다..."):
        # 🚨 여기서 nano_const 대신 자기 자신의 함수를 부르도록만 연결했어!
        st.session_state['master_data'] = fetch_monster_announcements()

if menu == "📊 실시간 공고 (홈)":
    st.markdown('<div class="blue-bar"><p>🏛️ k_건설맵 실시간 현황판</p></div>', unsafe_allow_html=True)
    df = st.session_state['master_data'].copy()
    if not df.empty:
        df['정렬용시간'] = pd.to_datetime(df['bidNtceDt'], errors='coerce')
        df = df.sort_values(by='정렬용시간', ascending=False, na_position='last').reset_index(drop=True)
        df['공고일자'] = df['정렬용시간'].dt.strftime('%Y-%m-%d').fillna('날짜미상')
        df['예산금액'] = pd.to_numeric(df['bdgtAmt'], errors='coerce').fillna(0)


        def get_safe_link(row):
            if 'bidNtceDtlUrl' in row and pd.notna(row['bidNtceDtlUrl']) and str(row['bidNtceDtlUrl']).strip() != "":
                return str(row['bidNtceDtlUrl']).replace(":8081", "").replace(":8101", "")
            return f"https://www.g2b.go.kr/ep/invitation/publish/bidInfoDtl.do?bidno={row['bidNtceNo']}&bidseq={row['bidNtceOrd']}"


        df['🔗 상세내용'] = df.apply(get_safe_link, axis=1)
        today_str = datetime.now(KST).strftime('%Y-%m-%d')
        today_count = len(df[df['공고일자'] == today_str])

        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            st.metric(label="누적 공고(최근 60일)", value=f"{len(df):,}건")
        with col2:
            st.metric(label="오늘(TODAY) 신규", value=f"{today_count}건")
        with col3:
            st.metric(label="데이터 기준일", value=today_str)
        with col4:
            if st.button("🔄 최신 데이터 갱신", use_container_width=True):
                st.cache_data.clear()
                if 'master_data' in st.session_state: del st.session_state['master_data']
                st.rerun()
        st.write("---")
        view_df = df[['bidNtceNo', '공고일자', 'bidNtceNm', 'ntceInsttNm', '예산금액', '🔗 상세내용']]
        view_df.columns = ['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세내용']
        st.dataframe(view_df, use_container_width=True, hide_index=True, height=750,
                     column_config={
                         "상세내용": st.column_config.LinkColumn("상세보기", display_text="공고문 열기"),
                         "예산금액": st.column_config.NumberColumn("예산금액(원)", format="%,d")
                     })
    else:
        st.warning("🚨 조달청 서버 응답이 지연되고 있습니다. '최신 데이터 갱신' 버튼을 눌러주세요.")

elif menu == "📝 자유 게시판":
    st.markdown('<div class="blue-bar"><p>📝 회원 자유 게시판</p></div>', unsafe_allow_html=True)
    st.info("이곳에 회원들이 영업 정보를 교환하거나 질문을 올릴 수 있는 게시판이 만들어질 예정입니다.")

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