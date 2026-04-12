import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import nano_const

st.set_page_config(page_title="k_건설맵", layout="wide", initial_sidebar_state="expanded")
KST = timezone(timedelta(hours=9))

st.markdown("""<style>.blue-bar { background-color: #1e3a8a; color: white; border-radius: 8px; text-align: center; padding: 25px; font-weight: 900; font-size: 30px; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🏛️ k_건설맵 메뉴")
    menu = st.radio("이동할 페이지를 선택하세요:", ["📊 실시간 공고 (홈)", "📝 자유 게시판"])
    if st.button("🔄 최신 데이터 강력 갱신"):
        st.cache_data.clear()
        if 'master_data' in st.session_state: del st.session_state['master_data']
        st.rerun()

if menu == "📊 실시간 공고 (홈)":
    st.markdown('<div class="blue-bar">🏛️ k_건설맵 하이브리드 현황판</div>', unsafe_allow_html=True)
    if 'master_data' not in st.session_state:
        with st.spinner("데이터를 가져오는 중..."):
            st.session_state['master_data'] = nano_const.get_final_data()

    df = st.session_state['master_data'].copy()
    if not df.empty:
        df['정렬용'] = pd.to_datetime(df['공고일시'], errors='coerce')
        df = df.sort_values(by='정렬용', ascending=False).reset_index(drop=True)
        st.dataframe(df[['공고번호', '공고일시', '공고명', '발주기관', '예산금액']], use_container_width=True, height=700, hide_index=True)
    else:
        st.error("🚨 조달청 서버가 응답하지 않습니다. 잠시 후 다시 시도해주세요.")