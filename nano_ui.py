import streamlit as st
import pandas as pd
import nano_const

st.set_page_config(page_title="블로그 로직 직통 연결", layout="wide")

st.markdown("""
    <style>
    .main-header { padding: 20px; background-color: #1e3a8a; color: white; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📡 블로그 무적 주소 직통 연결</h1></div>', unsafe_allow_html=True)

st.info("💡 사장님이 주신 블로그 주소로만 통신합니다. 지역/공고명 필터는 모두 제거했습니다.")

if st.button("🚀 블로그 주소로 데이터 몽땅 가져오기", use_container_width=True):
    with st.spinner("블로그에서 확인한 그 주소로 신호를 보내는 중..."):
        items = nano_const.fetch_blog_logic()

        if items:
            df = pd.DataFrame(items)
            st.success(f"🎉 드디어 뚫었다! {len(df)}건의 공고가 쏟아졌어!")
            # 블로그에서 본 컬럼명으로 깔끔하게 출력
            show_df = df[['bidNtceNo', 'bidNtceNm', 'ntceInsttNm', 'bdgtAmt']]
            show_df.columns = ['공고번호', '공고명', '공고기관', '예산금액']
            st.dataframe(show_df, use_container_width=True)

            # 엑셀 저장
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 데이터 엑셀 저장", csv, "블로그_성공데이터.csv", "text/csv")
        else:
            st.error("🚨 연결은 됐는데 데이터가 안 들어와. 조달청 답변을 확인해보자.")

        # 조달청이 뱉은 진짜 답변(Raw Data)을 항상 보여줌 (투명하게!)
        with st.expander("🕵️ 조달청 서버 답변 원문 보기"):
            if 'debug_text' in st.session_state:
                st.code(st.session_state['debug_text'])

