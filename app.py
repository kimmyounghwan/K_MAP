import streamlit as st
import pandas as pd
import requests
import pyrebase
import urllib3
import urllib.parse
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 보안 및 페이지 설정 (네이버 SEO + 강력한 화면 흐림 방지)
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="K-건설맵 V9.9 Master", layout="wide", initial_sidebar_state="expanded")

# ✅ 네이버 서치어드바이저 고유 암호 & 더 강력해진 화면 흐림 방지 CSS
st.markdown("""
    <head>
        <meta name="naver-site-verification" content="bfb3f10bce2983b4dd5974ba39d05e3ce5225e73" />
        <meta name="description" content="K-건설맵: 전국 건설 공사 입찰 및 실시간 1순위 개찰 결과를 즉시 확인하세요.">
    </head>
    <style>
        /* [핵심] 로딩 중 화면 흐려짐 및 스피너(동그라미) 완벽 제거 */
        .stApp[data-teststate="running"] .stAppViewBlockContainer {
            filter: none !important;
            opacity: 1 !important;
        }
        [data-testid="stStatusWidget"] {
            visibility: hidden !important;
            display: none !important;
        }
        /* 화면 전환 시 깜빡임 방지 */
        .stApp {
            transition: none !important;
        }

        /* 메인 디자인 */
        .main-title { background-color: #1e3a8a; color: white; border-radius: 10px; font-weight: 900; font-size: 28px; text-align: center; padding: 20px; margin-bottom: 25px; } 
        .stat-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; } 
        .stat-val { font-size: 20px; font-weight: 700; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))

# ==========================================
# 🔑 2. 파이어베이스 및 API 설정
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
SAFE_API_KEY = urllib.parse.unquote(G2B_API_KEY)


@st.cache_resource
def init_firebase():
    firebase = pyrebase.initialize_app(firebaseConfig)
    return firebase.auth(), firebase.database()


auth, db = init_firebase()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""
if 'user_license' not in st.session_state: st.session_state['user_license'] = ""


# ==========================================
# 📈 3. 통계 엔진 (명환 소장님의 802명 데이터 사수)
# ==========================================
def update_stats():
    try:
        now = datetime.now(KST)
        month_key = now.strftime('%Y-%m')
        if 'visited' not in st.session_state:
            m_v = db.child("stats").child("monthly").child(month_key).get().val() or 0
            db.child("stats").child("monthly").update({month_key: m_v + 1})
            t_v = db.child("stats").child("total_visits").get().val() or 0
            db.child("stats").update({"total_visits": t_v + 1})
            st.session_state['visited'] = True
    except:
        pass


def get_stats():
    try:
        month_key = datetime.now(KST).strftime('%Y-%m')
        m_v = db.child("stats").child("monthly").child(month_key).get().val() or 0
        t_v = db.child("stats").child("total_visits").get().val() or 0

        # ✅ 소장님의 피땀 눈물 데이터 철통 방어! (테스트 기준 802명 이상 유지)
        if t_v < 802:
            t_v = max(t_v, 802)
            db.child("stats").update({"total_visits": t_v})

        # 4월 개설 동기화 (누적=이달)
        if month_key == '2026-04':
            real_val = max(t_v, m_v)
            t_v = real_val
            m_v = real_val
            db.child("stats").child("monthly").update({month_key: m_v})
        else:
            if t_v < m_v: t_v = m_v

        u_v = db.child("users").get().val()
        return t_v, m_v, len(u_v) if u_v else 0
    except:
        return 802, 802, 0


def fetch_api_fast(url, params):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, params=params, verify=False, timeout=8, headers=headers)
        if res.status_code == 200: return res.json().get('response', {}).get('body', {}).get('items', [])
    except:
        pass
    return []


# ==========================================
# ⚡ 4. 하이브리드 엔진 (실시간 데이터 호출)
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def get_hybrid_1st_bids():
    now = datetime.now(KST)
    cutoff_dt = (now - timedelta(days=30)).replace(tzinfo=None)
    url = 'http://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoCnstwk'
    s_dt = (now - timedelta(days=7)).strftime('%Y%m%d')
    e_dt = now.strftime('%Y%m%d')
    api_items = fetch_api_fast(url, {'serviceKey': SAFE_API_KEY, 'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1',
                                     'inqryBgnDt': s_dt + '0000', 'inqryEndDt': e_dt + '2359', 'type': 'json'})
    db_data = db.child("archive_1st").get().val() or {}
    db_items = list(db_data.values()) if db_data else []
    new_rows = {}
    for item in api_items:
        try:
            bid_no = item.get('bidNtceNo', '')
            corp = str(item.get('opengCorpInfo', '')).split('^')
            if len(corp) > 1:
                try:
                    formatted_price = f"{int(corp[3].strip()):,}원"
                except:
                    formatted_price = corp[3].strip() if len(corp) > 3 else '-'
                new_rows[bid_no] = {
                    '1순위업체': corp[0].strip(), '공고번호': bid_no, '날짜': item.get('opengDt', ''),
                    '공고명': item.get('bidNtceNm', ''), '발주기관': item.get('ntceInsttNm', ''),
                    '투찰금액': formatted_price, '투찰률': f"{corp[4].strip()}%" if len(corp) >= 5 else '-'
                }
        except:
            continue
    if new_rows: db.child("archive_1st").update(new_rows)
    combined = list(new_rows.values()) + db_items
    df = pd.DataFrame(combined)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df[df['dt'] >= cutoff_dt]
        df = df.sort_values(by='dt', ascending=False)
        df['날짜'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


def make_link(row):
    url = str(row.get('bidNtceDtlUrl', ''))
    if url and url.lower() != 'nan': return url.replace(":8081", "").replace(":8101", "")
    return f"https://www.g2b.go.kr/ep/invitation/publish/bidInfoDtl.do?bidno={row.get('bidNtceNo', '')}&bidseq={row.get('bidNtceOrd', '01')}"


@st.cache_data(ttl=300, show_spinner=False)
def get_hybrid_live_bids():
    now = datetime.now(KST)
    cutoff_dt = (now - timedelta(days=30)).replace(tzinfo=None)
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
    s_dt = now.strftime('%Y%m%d')
    e_dt = now.strftime('%Y%m%d')
    api_items = fetch_api_fast(url, {'serviceKey': SAFE_API_KEY, 'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1',
                                     'inqryBgnDt': s_dt + '0000', 'inqryEndDt': e_dt + '2359', 'bidNtceNm': '공사',
                                     'type': 'json'})
    db_data = db.child("archive_live").get().val() or {}
    db_items = list(db_data.values()) if db_data else []
    new_rows = {}
    for item in api_items:
        try:
            bid_no = item.get('bidNtceNo', '')
            try:
                clean_amt = int(float(item.get('bdgtAmt', 0)))
            except:
                clean_amt = 0
            new_rows[bid_no] = {
                '공고번호': bid_no, '공고일자': item.get('bidNtceDt', ''), '공고명': item.get('bidNtceNm', ''),
                '발주기관': item.get('ntceInsttNm', ''), '예산금액': clean_amt, '상세보기': make_link(item)
            }
        except:
            continue
    if new_rows: db.child("archive_live").update(new_rows)
    combined = list(new_rows.values()) + db_items
    df = pd.DataFrame(combined)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['공고일자'], errors='coerce')
        df = df[df['dt'] >= cutoff_dt]
        df = df.sort_values(by='dt', ascending=False)
        df['공고일자'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


# ==========================================
# 🌍 4-1. 지역 필터링 모듈
# ==========================================
REGION_LIST = ["전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남",
               "제주"]


def filter_by_region(df, selected_region):
    if selected_region == "전국(전체)": return df
    region_keywords = {"서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"], "광주": ["광주"], "대전": ["대전"], "울산": ["울산"],
                       "세종": ["세종"], "경기": ["경기", "경기도"], "강원": ["강원", "강원도"], "충북": ["충북", "충청북도"],
                       "충남": ["충남", "충청남도"], "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"], "경북": ["경북", "경상북도"],
                       "경남": ["경남", "경상남도"], "제주": ["제주"]}
    keywords = region_keywords.get(selected_region, [selected_region])
    pattern = '|'.join(keywords)
    return df[df['발주기관'].str.contains(pattern, na=False) | df['공고명'].str.contains(pattern, na=False)]


# ==========================================
# 🎨 5. UI 및 메뉴
# ==========================================
ALL_LICENSES = ["[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업", "[종합] 산업·환경설비공사업", "[전문] 지반조성·포장공사업",
                "[전문] 실내건축공사업", "[전문] 금속창호·지붕건축물조립공사업", "[전문] 도장·습식·방수·석공사업", "[전문] 조경식재·시설물공사업", "[전문] 구조물해체·비계공사업",
                "[전문] 상·하수도설비공사업", "[전문] 철도·궤도공사업", "[전문] 철근·콘크리트공사업", "[전문] 수중·준설공사업", "[전문] 승강기설치공사업", "[전문] 기계설비공사업",
                "[전문] 철강구조물공사업", "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업"]

update_stats()
t_visit, m_visit, t_user = get_stats()

st.markdown('<div class="main-title">🏛️ K-건설맵</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(
    f'<div class="stat-card">📅 오늘 날짜<br><span class="stat-val">{datetime.now(KST).strftime("%Y-%m-%d")}</span></div>',
    unsafe_allow_html=True)
with c2: st.markdown(
    f'<div class="stat-card">📈 누적 / 이달 방문<br><span class="stat-val">{t_visit:,}명 / {m_visit:,}명</span></div>',
    unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-card">👥 전체 회원수<br><span class="stat-val">{t_user:,}명</span></div>',
                     unsafe_allow_html=True)
with c4: st.markdown(
    f'<div class="stat-card">🔔 가동 상태<br><span class="stat-val" style="color:green;">정상 운영 중</span></div>',
    unsafe_allow_html=True)

with st.sidebar:
    st.write("### 👷 K-건설맵 메뉴")
    if st.session_state['logged_in']:
        st.success(f"👋 {st.session_state['user_name']} 소장님")
        st.caption(f"보유 면허: {st.session_state['user_license']}")
        if st.button("🚪 로그아웃"): st.session_state['logged_in'] = False; st.session_state['user_name'] = ""; st.rerun()
        menu_list = ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "📝 자유 게시판"]
    else:
        st.info("로그인 후 맞춤 공고와 게시판을 이용하세요.")
        menu_list = ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "📝 자유 게시판", "👤 로그인 / 회원가입"]
    menu = st.radio("업무 선택", menu_list)

    st.write("---")
    # ✅ 할아버지 소장님들도 한 번에 이해하는 친절한 설명서 완벽 복구!
    with st.expander("📱 K-건설맵 폰에 깔기 (엄청 쉬움!)"):
        st.markdown("""
        **[🍎 아이폰 쓰시는 분]**
        1. 화면 맨 아래에 있는 **[네모에 위로 솟은 화살표(공유)]** 버튼을 누르세요.
        2. 메뉴를 손가락으로 살짝 위로 올려서 **[홈 화면에 추가]** 글씨를 찾아서 누르세요.
        3. 오른쪽 위에 있는 **[추가]** 글씨를 누르면 바탕화면에 앱처럼 쏙 들어갑니다!

        **[🤖 갤럭시 쓰시는 분]**
        1. 화면 오른쪽 위(또는 아래)에 있는 **[점 3개(⋮)]** 버튼을 누르세요.
        2. 나오는 메뉴 중간쯤에서 **[홈 화면에 추가]** 글씨를 누르세요.
        3. 한 번 더 **[추가]**를 누르면 바탕화면에 앱처럼 쏙 들어갑니다!
        """)

    st.write("---")
    if st.button("🔄 만능 데이터 새로고침"): st.cache_data.clear(); st.success("캐시를 비웠습니다!"); st.rerun()

# ==========================================
# 🚀 6. 메뉴별 동작 로직
# ==========================================
if menu == "🏆 1순위 현황판":
    st.subheader("🏆 실시간 1순위 현황판")
    col_t, col_m, col_b = st.columns([2, 1, 1])
    with col_t:
        st.write(" ")
    with col_m:
        selected_region_1st = st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg_1st")
    with col_b:
        st.link_button("🚀 나라장터 바로가기", "https://www.g2b.go.kr/index.jsp", use_container_width=True)

    with st.expander("🌡️ 5구간 기초금액(예가) 입찰 온도계"):
        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            base_price = st.number_input("기초금액 입력 (원)", value=0, step=1000000)
        with calc_col2:
            rate_option = st.radio("투찰률 선택 (%)", ["87.745", "86.745"], horizontal=True)
        if base_price > 0:
            st.write("💡 **사정율 구간별 예상 투찰금액**")
            c1, c2, c3, c4, c5 = st.columns(5)
            rates = [99.0, 99.5, 100.0, 100.5, 101.0]
            labels = ["❄️ 차가움", "🌬️ 서늘함", "🌤️ 적정함", "☀️ 따뜻함", "🔥 뜨거움"]
            cols = [c1, c2, c3, c4, c5]
            for i, r in enumerate(rates):
                with cols[i]:
                    bid_p = int(base_price * (r / 100) * (float(rate_option) / 100))
                    st.info(f"**{labels[i]}**\n\n{r}%\n\n**{bid_p:,}원**")

    with st.spinner("데이터 동기화 중..."):
        df_w = get_hybrid_1st_bids()
    if not df_w.empty:
        df_f = filter_by_region(df_w, selected_region_1st)
        st.dataframe(df_f[['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률']], use_container_width=True, hide_index=True,
                     height=600)
    else:
        st.warning("데이터가 없습니다. [새로고침]을 눌러주세요.")

elif menu == "📊 실시간 공고 (홈)":
    st.subheader("📊 실시간 입찰 공고 현황")
    with st.spinner("공고 불러오는 중..."):
        df_live = get_hybrid_live_bids()
    if not df_live.empty:
        today_str = datetime.now(KST).strftime('%m-%d')
        today_count = len(df_live[df_live['공고일자'].str.contains(today_str, na=False)])
        if today_count >= 100:
            thermo = "🔥 아주 뜨거움 (입찰 폭발)"
        elif today_count >= 50:
            thermo = "☀️ 따뜻함 (공고 활발)"
        elif today_count >= 10:
            thermo = "🌤️ 보통 (무난한 하루)"
        else:
            thermo = "❄️ 차가움 (조용함)"
        st.info(f"**🌡️ 오늘의 입찰 온도계:** {thermo} (신규 등록 공고: **{today_count}**건)")

        col_t2, col_m2, col_b2 = st.columns([2, 1, 1])
        with col_t2:
            st.write(" ")
        with col_m2:
            selected_region_live = st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg_live")
        with col_b2:
            st.link_button("🚀 나라장터 바로가기", "https://www.g2b.go.kr/index.jsp", use_container_width=True)

        df_live_f = filter_by_region(df_live, selected_region_live)
        col_cfg = {"상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
                   "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")}
        if st.session_state['logged_in'] and st.session_state['user_license']:
            tab1, tab2 = st.tabs(["🌐 전체 공고 보기", "✨ 내 면허 맞춤 공고 (매칭시스템)"])
            with tab1:
                st.dataframe(df_live_f[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                             hide_index=True, height=650, column_config=col_cfg)
            with tab2:
                user_lic = st.session_state['user_license']
                keywords = []
                if "토목" in user_lic: keywords.extend(["토목", "도로", "포장", "하천", "교량", "정비", "관로", "상수도", "하수도", "부대시설"])
                if "건축" in user_lic: keywords.extend(["건축", "신축", "증축", "보수", "인테리어", "환경개선", "방수", "도장"])
                if "철근" in user_lic or "콘크리트" in user_lic: keywords.extend(
                    ["철근", "콘크리트", "철콘", "구조물", "옹벽", "포장", "배수", "기초", "집수정", "박스", "암거", "석축"])
                if "전기" in user_lic: keywords.extend(["전기", "배전", "가로등", "CCTV", "태양광", "신호등"])
                if "통신" in user_lic: keywords.extend(["통신", "네트워크", "방송", "CCTV", "케이블", "선로"])
                if "소방" in user_lic: keywords.extend(["소방", "화재", "스프링클러", "피난", "경보"])
                if "상·하수도" in user_lic: keywords.extend(["상수도", "하수도", "관로", "배수"])
                if "조경" in user_lic: keywords.extend(["조경", "식재", "공원", "수목", "벌목", "놀이터"])

                matched_df = df_live_f[
                    df_live_f['공고명'].str.contains('|'.join(keywords), na=False)] if keywords else df_live_f
                st.dataframe(matched_df[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                             hide_index=True, height=650, column_config=col_cfg)
        else:
            st.dataframe(df_live_f[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                         hide_index=True, height=650, column_config=col_cfg)
    else:
        st.warning("공고 데이터가 없습니다. 조달청 서버 지연 중이거나 데이터가 없습니다.")

elif menu == "📝 자유 게시판":
    st.subheader("📝 K-건설맵 정보 공유판")
    if not st.session_state['logged_in']:
        st.info("💡 게시판에 글을 작성하시려면 로그인해 주세요.")
    else:
        with st.expander("✏️ 글쓰기"):
            t, c = st.text_input("제목"), st.text_area("내용")
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
    st.subheader("👤 회원 정보 관리")
    t1, t2 = st.tabs(["🔑 로그인", "📝 회원가입"])
    with t2:
        re = st.text_input("이메일", key="r_e")
        rp = st.text_input("비밀번호 (6자리 이상)", type="password", key="r_p")
        rn = st.text_input("성함/직함 (예: 홍길동 소장)", key="r_n")
        rc = st.text_input("회사명", key="r_c")
        rl = st.multiselect("🏗️ 보유 면허", ALL_LICENSES)
        if st.button("가입하기"):
            re_clean = re.strip().lower()
            if not re_clean or not rp or not rn:
                st.warning("이메일, 비밀번호, 성함을 모두 입력해주세요.")
            elif len(rp) < 6:
                st.error("비밀번호는 6자리 이상이어야 합니다.")
            else:
                try:
                    user = auth.create_user_with_email_and_password(re_clean, rp)
                    license_str = ", ".join(rl) if rl else "선택안함"
                    db.child("users").child(user['localId']).set(
                        {"name": rn, "company": rc, "license": license_str, "email": re_clean})
                    st.session_state.update({'logged_in': True, 'user_name': rn, 'user_license': license_str})
                    st.success("가입 완료! 🚀 자동으로 로그인되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error("가입 실패: 이미 가입된 이메일이거나 형식이 잘못되었습니다.")
    with t1:
        le = st.text_input("가입한 이메일", key="l_e")
        lp = st.text_input("비밀번호", type="password", key="l_p")
        if st.button("로그인"):
            le_clean = le.strip().lower()
            if not le_clean or not lp:
                st.warning("이메일과 비밀번호를 모두 입력해주세요.")
            else:
                try:
                    user = auth.sign_in_with_email_and_password(le_clean, lp)
                    info = db.child("users").child(user['localId']).get().val() or {}
                    st.session_state.update({'logged_in': True, 'user_name': info.get('name', '소장님'),
                                             'user_license': info.get('license', '')})
                    st.rerun()
                except Exception as e:
                    st.error("로그인 실패 🥲 이메일이나 비밀번호를 다시 확인해주세요.")
        st.write("---")
        if st.button("🔑 비밀번호 초기화 메일 받기"):
            le_clean = le.strip().lower()
            if le_clean:
                try:
                    auth.send_password_reset_email(le_clean)
                    st.success(f"[{le_clean}]로 초기화 메일이 발송되었습니다. 메일함을 확인해주세요!")
                except:
                    st.error("가입되지 않은 이메일이거나 시스템 오류가 발생했습니다.")
            else:
                st.warning("먼저 위쪽에 '가입한 이메일'을 입력한 뒤 이 버튼을 눌러주세요.")