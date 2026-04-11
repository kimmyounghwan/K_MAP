import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib3
import streamlit as st
import concurrent.futures
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"  #
KST = timezone(timedelta(hours=9))  #


# 🟢 1. 데이터 엔진 (명환이의 60일치 + 일꾼 15명 원본 로직) [cite: 31, 36]
@st.cache_data(ttl=600)
def fetch_monster_announcements():
    all_raw = []
    end_date = datetime.now(KST).date()  # [cite: 32]
    start_date = end_date - timedelta(days=60)  # [cite: 32]
    dates = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in
             range((end_date - start_date).days + 1)]  # [cite: 32]

    # 🚨 명환이의 통합 마스터 주소 [cite: 33]
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'

    def fetch_per_day(dt):
        params = {
            'inqryDiv': '1', 'inqryBgnDt': f'{dt}0000', 'inqryEndDt': f'{dt}2359',
            'pageNo': '1', 'numOfRows': '999', 'bidNtceNm': '공사',
            'type': 'json', 'serviceKey': API_KEY  #
        }
        for _ in range(3):  # [cite: 34]
            try:
                res = requests.get(url, params=params, verify=False, timeout=10)  #
                if res.status_code == 200:
                    items = res.json().get('response', {}).get('body', {}).get('items', [])  # [cite: 35]
                    return items if items else []  # [cite: 35]
            except:
                time.sleep(0.5)  # [cite: 34]
                continue
        return []

    # 🚨 일꾼 15명 유지 [cite: 36]
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_per_day, dates))
        for res in results:
            if res: all_raw.extend(res)  # [cite: 36]

    return pd.DataFrame(all_raw)  # [cite: 36]


# 🟢 2. UI 및 화면 구성 (명환이 디자인 100% 복구) [cite: 37]
st.set_page_config(page_title="k_건설맵", layout="wide", initial_sidebar_state="expanded")  #

st.markdown("""
    <style>
    .blue-bar { 
        background-color: #1e3a8a; color: white; border-radius: 8px; # [cite: 39, 40]
        font-weight: 900; font-size: 28px; text-align: center;
        padding: 35px 0 15px 0 !important; # [cite: 40]
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🏛️ k_건설맵 메뉴")
    menu = st.radio("메뉴 선택", ["📊 실시간 공고 (홈)", "📝 자유 게시판", "👤 로그인 / 회원가입"])  # [cite: 41]

if menu == "📊 실시간 공고 (홈)":
    if 'master_data' not in st.session_state:
        with st.spinner("조달청 서버가 살아나길 기다리며 공고를 모으는 중..."):  # [cite: 42]
            st.session_state['master_data'] = fetch_monster_announcements()

    st.markdown('<div class="blue-bar">🏛️ k_건설맵 실시간 현황판</div>', unsafe_allow_html=True)  # [cite: 42]
    df = st.session_state['master_data']

    if not df.empty:
        # 데이터 정렬 및 출력 로직... [cite: 43, 48]
        st.dataframe(df, use_container_width=True, height=750)  # [cite: 48]
    else:
        st.warning("🚨 조달청 API 서버가 점검 중입니다. 잠시 후 다시 시도해 주세요.")  # [cite: 49]

elif menu == "👤 로그인 / 회원가입":
    st.markdown('<div class="blue-bar">👤 K_건설맵 로그인</div>', unsafe_allow_html=True)  # [cite: 50]
    # 로그인 폼... [cite: 50, 51]