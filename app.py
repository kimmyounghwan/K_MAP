import streamlit as st
import pandas as pd
import requests
import pyrebase
import urllib3
import time
from datetime import datetime, timedelta, timezone
import concurrent.futures

# 1. 보안 및 페이지 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="K-건설맵", layout="wide", initial_sidebar_state="expanded")
KST = timezone(timedelta(hours=9))

# ==========================================
# 🔑 2. 파이어베이스 설정 (명환's DB)
# ==========================================
firebaseConfig = {
    "apiKey": "AIzaSyB5uvAzUIbEDTTbxwflTQk3wdzOufc4SE0",
    "authDomain": "k-conmap.firebaseapp.com",
    "databaseURL": "https://k-conmap-default-rtdb.firebaseio.com",
    "projectId": "k-conmap",
    "storageBucket": "k-conmap.firebasestorage.app",
    "messagingSenderId": "230642116525",
    "appId": "1:230642116525:web:f6f3765cf9a7273ba92324"
}

G2B_API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"

@st.cache_resource
def init_firebase():
    firebase = pyrebase.initialize_app(firebaseConfig)
    return firebase.auth(), firebase.database()

auth, db = init_firebase()

# ==========================================
# 🧠 3. 무적의 자동 동기화 엔진 (속도 개선 & 버그 수정)
# ==========================================

def load_from_db():
    try:
        data = db.child("announcements").get().val()
        if data: return pd.DataFrame(list(data.values()))
    except:
        pass
    return pd.DataFrame()

def save_to_db_fast(new_df):
    if new_df.empty: return
    try:
        data_dict = {}
        # 🚨 무한 로딩 방지: 최신 데이터 1000개까지만 DB에 넣도록 안전장치 추가
        safe_df = new_df.head(1000)
        for _, row in safe_df.iterrows():
            key = f"{row['bidNtceNo']}-{row.get('bidNtceOrd', '01')}"
            data_dict[key] = row.dropna().to_dict()
        db.child("announcements").update(data_dict)
    except Exception as e:
        print(f"DB 저장 에러 (무시됨): {e}")

@st.cache_data(ttl=600)
def get_integrated_data():
    all_raw = []
    end_date = datetime.now(KST).date()
    # 🚨 핵심 수정: 30일 -> 5일로 대폭 축소! (빙빙 도는 현상 100% 해결)
    start_date = end_date - timedelta(days=5)
    delta = end_date - start_date
    dates = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(delta.days + 1)]

    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
    headers = {"User-Agent": "Mozilla/5.0"}

    def fetch(dt):
        params = {'inqryDiv': '1', 'inqryBgnDt': f'{dt}0000', 'inqryEndDt': f'{dt}2359',
                  'pageNo': '1', 'numOfRows': '999', 'bidNtceNm': '공사', 'type': 'json', 'serviceKey': G2B_API_KEY}
        try:
            # 타임아웃을 10초로 줄여서 응답 없는 서버에 끌려다니지 않게 만듦
            res = requests.get(url, params=params, verify=False, timeout=10, headers=headers)
            if res.status_code == 200:
                return res.json().get('response', {}).get('body', {}).get('items', [])
        except:
            return []
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch, dates))
        for r in results:
            if r: all_raw.extend(r)

    api_df = pd.DataFrame(all_raw)
    db_df = load_from_db()

    if not api_df.empty:
        save_to_db_fast(api_df)
        st.toast("✅ 조달청 데이터 자동 동기화 완료!", icon="🔄")
        combined_df = pd.concat([api_df, db_df]).drop_duplicates(subset=['bidNtceNo'], keep='first')
        return combined_df
    else:
        st.toast("⚠️ 조달청 서버 지연. 비상 DB 데이터를 불러옵니다.", icon="🚨")
        return db_df

# ==========================================
# 📋 4. 면허 리스트 및 UI 세팅
# ==========================================
ALL_LICENSES = [
    "[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업", "[종합] 산업·환경설비공사업",
    "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업", "[전문] 금속창호·지붕건축물조립공사업", "[전문] 도장·습식·방수·석공사업",
    "[전문] 조경식재·시설물공사업", "[전문] 구조물해체·비계공사업", "[전문] 상·하수도설비공사업", "[전문] 철도·궤도공사업",
    "[전문] 철근·콘크리트공사업", "[전문] 수중·준설공사업", "[전문] 승강기설치공사업", "[전문] 삭도설치공사업",
    "[전문] 기계설비공사업", "[전문] 철강구조물공사업", "[전문] 가스시설시공업", "[전문] 난방공사업",
    "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업", "[기타] 문화재수리업", "기타(직접입력)"
]

st.markdown(
    """<style>.blue-bar { background-color: #1e3a8a; color: white; border-radius: 8px; font-weight: 900; font-size: 28px; text-align: center; padding: 25px; margin-bottom: 20px; }</style>""",
    unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'user_license' not in st.session_state: st.session_state['user_license'] = ""

with st.sidebar:
    st.markdown("### 🏛️ K-건설맵")
    if st.session_state['logged_in']:
        st.success(f"👋 {st.session_state['user_name']} 소장님")
        st.caption(f"보유 면허: {st.session_state['user_license']}")
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False;
            st.rerun()
    st.write("---")
    menu = st.radio("메뉴 이동:", ["📊 실시간 공고 (홈)", "📝 자유 게시판", "👤 로그인 / 회원가입"])
    if st.button("🔄 수동 강제 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 🟢 메뉴 1: 메인 화면 (자동화 & 매칭 시스템)
# ==========================================
if menu == "📊 실시간 공고 (홈)":
    st.markdown('<div class="blue-bar">🏛️ K-건설맵 무한 자동 현황판</div>', unsafe_allow_html=True)

    with st.spinner("데이터 동기화 엔진 가동 중... (최대 10초 소요)"):
        df = get_integrated_data()

    if not df.empty:
        df['정렬시간'] = pd.to_datetime(df['bidNtceDt'], errors='coerce')
        df = df.sort_values(by='정렬시간', ascending=False).reset_index(drop=True)
        df['공고일자'] = df['정렬시간'].dt.strftime('%Y-%m-%d').fillna('미상')
        df['예산금액'] = pd.to_numeric(df.get('bdgtAmt', 0), errors='coerce').fillna(0)

        def make_link(row):
            url = str(row.get('bidNtceDtlUrl', ''))
            if url and url.lower() != 'nan': return url.replace(":8081", "").replace(":8101", "")
            return f"https://www.g2b.go.kr/ep/invitation/publish/bidInfoDtl.do?bidno={row['bidNtceNo']}&bidseq={row.get('bidNtceOrd', '01')}"

        df['🔗 상세보기'] = df.apply(make_link, axis=1)

        view_df = df[['bidNtceNo', '공고일자', 'bidNtceNm', 'ntceInsttNm', '예산금액', '🔗 상세보기']].copy()
        view_df.columns = ['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']

        if st.session_state['logged_in'] and st.session_state['user_license']:
            tab1, tab2 = st.tabs(["🌐 전체 공고 보기", "✨ 내 면허 맞춤 공고"])

            with tab1:
                st.dataframe(view_df, use_container_width=True, hide_index=True, height=700,
                             column_config={"상세보기": st.column_config.LinkColumn("공고문 열기"),
                                            "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")})

            with tab2:
                user_lic = st.session_state['user_license']
                keywords = []
                if "토목" in user_lic: keywords.extend(["토목", "도로", "포장", "하천", "교량", "정비"])
                if "건축" in user_lic: keywords.extend(["건축", "신축", "증축", "보수", "인테리어", "환경개선"])
                if "전기" in user_lic: keywords.extend(["전기", "배전", "가로등", "CCTV", "태양광"])
                if "통신" in user_lic: keywords.extend(["통신", "네트워크", "방송", "CCTV", "케이블"])
                if "소방" in user_lic: keywords.extend(["소방", "화재", "스프링클러", "피난"])
                if "상·하수도" in user_lic: keywords.extend(["상수도", "하수도", "관로", "배수"])
                if "조경" in user_lic: keywords.extend(["조경", "식재", "공원", "수목"])

                if keywords:
                    pattern = '|'.join(keywords)
                    matched_df = view_df[view_df['공고명'].str.contains(pattern, na=False)]
                else:
                    matched_df = view_df

                st.success(f"🎯 시스템이 소장님의 면허({user_lic})를 분석하여 **{len(matched_df)}건**의 맞춤 공고를 찾아냈습니다!")
                st.dataframe(matched_df, use_container_width=True, hide_index=True, height=700,
                             column_config={"상세보기": st.column_config.LinkColumn("공고문 열기"),
                                            "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")})

        else:
            st.info("💡 회원가입 후 로그인하시면 소장님 면허에 딱 맞는 공고만 자동으로 찾아주는 '맞춤 공고' 기능을 사용할 수 있습니다.")
            st.dataframe(view_df, use_container_width=True, hide_index=True, height=700,
                         column_config={"상세보기": st.column_config.LinkColumn("공고문 열기"),
                                        "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")})

    else:
        st.error("데이터를 불러올 수 없습니다. 조달청 서버가 혼잡합니다. 잠시 후 새로고침 해주세요.")

# ==========================================
# 🟢 메뉴 2 & 3: 게시판 및 회원가입
# ==========================================
elif menu == "📝 자유 게시판":
    st.markdown('<div class="blue-bar">📝 K-건설맵 정보 공유판</div>', unsafe_allow_html=True)
    if st.session_state['logged_in']:
        with st.expander("✏️ 글쓰기"):
            t = st.text_input("제목")
            c = st.text_area("내용")
            if st.button("등록"):
                db.child("posts").push({"author": st.session_state['user_name'], "title": t, "content": c,
                                        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M")})
                st.success("등록 완료!");
                st.rerun()
    try:
        posts = db.child("posts").get().val()
        if posts:
            for p in reversed(list(posts.values())):
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"작성자: {p['author']} | 작성시간: {p['time']}")
                    st.write(p['content'])
    except:
        pass

elif menu == "👤 로그인 / 회원가입":
    st.markdown('<div class="blue-bar">👤 회원 정보 관리</div>', unsafe_allow_html=True)
    if not st.session_state['logged_in']:
        t1, t2 = st.tabs(["🔑 로그인", "📝 회원가입"])
        with t2:
            re = st.text_input("이메일")
            rp = st.text_input("비밀번호", type="password")
            rn = st.text_input("대표자 성함")
            rc = st.text_input("회사명")
            rl = st.multiselect("🏗️ 보유 면허 (전체 리스트)", ALL_LICENSES)
            if st.button("가입하기"):
                try:
                    user = auth.create_user_with_email_and_password(re, rp)
                    db.child("users").child(user['localId']).set(
                        {"name": rn, "company": rc, "license": ", ".join(rl), "email": re})
                    st.success("축하합니다! 회원가입 완료.");
                    st.rerun()
                except:
                    st.error("이미 가입된 아이디이거나 형식이 틀립니다.")
        with t1:
            le = st.text_input("아이디(이메일)")
            lp = st.text_input("비밀번호", type="password")
            if st.button("로그인"):
                try:
                    user = auth.sign_in_with_email_and_password(le, lp)
                    info = db.child("users").child(user['localId']).get().val()
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = info['name']
                    st.session_state['user_license'] = info.get('license', '')
                    st.rerun()
                except:
                    st.error("정보가 일치하지 않습니다.")