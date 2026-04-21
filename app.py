import streamlit as st
import pandas as pd
import requests
import pyrebase
import urllib3
import urllib.parse
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 보안 및 페이지 설정
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="K-건설맵 Master", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <head>
        <meta name="naver-site-verification" content="bfb3f10bce2983b4dd5974ba39d05e3ce5225e73" />
        <meta name="description" content="K-건설맵: 전국 건설 공사 입찰 및 실시간 1순위 개찰 결과를 즉시 확인하세요.">
    </head>
    <style>
        .stApp[data-teststate="running"] .stAppViewBlockContainer { filter: none !important; opacity: 1 !important; }
        [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
        .stApp { transition: none !important; }
        .main-title { background-color: #1e3a8a; color: white; border-radius: 10px; font-weight: 900; font-size: 28px; text-align: center; padding: 20px; margin-bottom: 25px; } 
        .stat-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; } 
        .stat-val { font-size: 20px; font-weight: 700; color: #1e3a8a; }
        .rank-card { background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; border-radius: 10px; padding: 16px; text-align: center; margin-bottom: 8px; }
        .rank-1 { background: linear-gradient(135deg, #b45309 0%, #f59e0b 100%); }
        .rank-2 { background: linear-gradient(135deg, #4b5563 0%, #9ca3af 100%); }
        .rank-3 { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); }
        .info-box { background-color: #eff6ff; border-left: 4px solid #2563eb; border-radius: 6px; padding: 14px 18px; margin: 10px 0; }
        .info-box-title { font-weight: 700; color: #1e3a8a; font-size: 13px; margin-bottom: 4px; }
        .info-box-val { font-size: 18px; font-weight: 800; color: #1e40af; }
    </style>
""", unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))

# ==========================================
# 2. 파이어베이스 및 API 설정
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
# 3. 상수 데이터
# ==========================================
REGION_LIST = [
    "전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"
]

ALL_LICENSES = [
    "[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업",
    "[종합] 산업·환경설비공사업", "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업",
    "[전문] 금속창호·지붕건축물조립공사업", "[전문] 도장·습식·방수·석공사업", "[전문] 조경식재·시설물공사업",
    "[전문] 구조물해체·비계공사업", "[전문] 상·하수도설비공사업", "[전문] 철도·궤도공사업",
    "[전문] 철근·콘크리트공사업", "[전문] 수중·준설공사업", "[전문] 승강기설치공사업",
    "[전문] 기계설비공사업", "[전문] 철강구조물공사업", "[기타] 전기공사업",
    "[기타] 정보통신공사업", "[기타] 소방시설공사업"
]


# ==========================================
# 4. 유틸 함수
# ==========================================
def safe_fmt_amt(raw):
    r = str(raw).strip()
    if not r or r in ('0', 'None', 'nan', 'NaN', ''): return "미발표"
    try:
        return f"{int(float(r)):,}원"
    except:
        return r


def safe_str(raw, default="정보없음"):
    r = str(raw).strip()
    return r if r and r not in ('None', 'nan', 'NaN', '') else default


# ==========================================
# 5. 통계 및 데이터 엔진
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
        if t_v < 802:
            t_v = 802
            db.child("stats").update({"total_visits": t_v})
        u_v = db.child("users").get().val()
        return t_v, m_v, len(u_v) if u_v else 0
    except:
        return 802, 802, 0


def fetch_api_fast(url, params):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, params=params, verify=False, timeout=10, headers=headers)
        if res.status_code == 200: return res.json().get('response', {}).get('body', {}).get('items', [])
    except:
        pass
    return []


# ==========================================
# 6. 1순위 현황판 데이터 엔진
# ==========================================
@st.cache_data(ttl=180, show_spinner=False)
def get_hybrid_1st_bids():
    now = datetime.now(KST)
    cutoff_dt = (now - timedelta(days=180)).replace(tzinfo=None)
    url = 'http://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoCnstwk'
    s_dt = (now - timedelta(days=2)).strftime('%Y%m%d')
    e_dt = now.strftime('%Y%m%d')

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {
            'serviceKey': SAFE_API_KEY, 'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1',
            'inqryBgnDt': s_dt + '0000', 'inqryEndDt': e_dt + '2359', 'type': 'json'
        }
        res = requests.get(url, params=params, verify=False, timeout=25, headers=headers)
        api_items = res.json().get('response', {}).get('body', {}).get('items', []) if res.status_code == 200 else []
    except:
        api_items = []

    # [수정] 인덱스 에러 방지 다이어트 코드
    db_data = db.child("archive_1st").order_by_key().limit_to_last(400).get().val() or {}
    db_items = list(db_data.values()) if db_data else []
    new_rows = {}

    if isinstance(api_items, dict):
        api_items = api_items.get('item', [api_items])
        if isinstance(api_items, dict): api_items = [api_items]

    for item in api_items:
        try:
            bid_no = item.get('bidNtceNo', '')
            bid_ord = item.get('bidNtceOrd', '00')
            full_corp_info = str(item.get('opengCorpInfo', ''))
            first_corp = full_corp_info.split('|')[0]
            corp = first_corp.split('^')

            if len(corp) > 1:
                new_rows[bid_no] = {
                    '1순위업체': corp[0].strip(), '공고번호': bid_no, '공고차수': bid_ord, '날짜': item.get('opengDt', ''),
                    '공고명': item.get('bidNtceNm', ''), '발주기관': item.get('ntceInsttNm', ''),
                    '투찰금액': f"{int(float(corp[3].strip())):,}원" if len(corp) > 3 else '-',
                    '투찰률': f"{corp[4].strip()}%" if len(corp) >= 5 else '-',
                    '전체업체': full_corp_info
                }
        except:
            continue

    if new_rows: db.child("archive_1st").update(new_rows)
    df = pd.DataFrame(list(new_rows.values()) + db_items)

    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df[df['dt'] >= cutoff_dt].sort_values(by='dt', ascending=False)
        df['날짜'] = df['dt'].dt.strftime('%m-%d %H:%M')

    return df


# ==========================================
# 7. 실시간 공고 데이터 엔진
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def get_hybrid_live_bids():
    now = datetime.now(KST)
    cutoff_dt = (now - timedelta(days=180)).replace(tzinfo=None)
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
    s_dt = now.strftime('%Y%m%d')
    params = {'serviceKey': SAFE_API_KEY, 'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1',
              'inqryBgnDt': s_dt + '0000', 'inqryEndDt': s_dt + '2359', 'bidNtceNm': '공사', 'type': 'json'}
    api_items = fetch_api_fast(url, params)

    if isinstance(api_items, dict):
        api_items = api_items.get('item', [api_items])
        if isinstance(api_items, dict): api_items = [api_items]

    # [수정] 인덱스 에러 방지 다이어트 코드
    db_data = db.child("archive_live").order_by_key().limit_to_last(400).get().val() or {}
    db_items = list(db_data.values()) if db_data else []
    new_rows = {}
    for item in api_items:
        bid_no = item.get('bidNtceNo', '')
        new_rows[bid_no] = {
            '공고번호': bid_no, '공고일자': item.get('bidNtceDt', ''), '공고명': item.get('bidNtceNm', ''),
            '발주기관': item.get('ntceInsttNm', ''), '예산금액': int(float(item.get('bdgtAmt', 0))),
            '상세보기': item.get('bidNtceDtlUrl', "https://www.g2b.go.kr/index.jsp")
        }
    if new_rows: db.child("archive_live").update(new_rows)

    df = pd.DataFrame(list(new_rows.values()) + db_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['공고일자'], errors='coerce')
        df = df[df['dt'] >= cutoff_dt].sort_values(by='dt', ascending=False)
        df['공고일자'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


def filter_by_region(df, selected_region):
    if selected_region == "전국(전체)": return df
    region_keywords = {
        "서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"], "광주": ["광주"], "대전": ["대전"], "울산": ["울산"], "세종": ["세종"],
        "경기": ["경기", "경기도"], "강원": ["강원", "강원도"], "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
        "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"], "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"], "제주": ["제주"]
    }
    keywords = region_keywords.get(selected_region, [selected_region])
    pattern = '|'.join(keywords)
    return df[df['발주기관'].str.contains(pattern, na=False) | df['공고명'].str.contains(pattern, na=False)]


# ==========================================
# 8. ★ 핵심 엔진 (기초금액 전용 금고 털기 포함) ★
# ==========================================
def fetch_bid_full_detail(bid_no, base_ord, row):
    headers = {"User-Agent": "Mozilla/5.0"}

    def _safe_list(obj):
        if not obj: return []
        if isinstance(obj, list): return obj
        if isinstance(obj, dict):
            item = obj.get('item')
            if isinstance(item, list): return item
            if isinstance(item, dict): return [item]
            return [obj]
        return []

    # ── API ① 공고문 상세 (inqryDiv=2) ──
    notice_url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
    n_items = []
    try:
        n_res = requests.get(notice_url,
                             params={'serviceKey': SAFE_API_KEY, 'numOfRows': '3', 'pageNo': '1', 'inqryDiv': '2',
                                     'bidNtceNo': bid_no, 'type': 'json'}, verify=False, timeout=10, headers=headers)
        if n_res.status_code == 200: n_items = _safe_list(
            n_res.json().get('response', {}).get('body', {}).get('items', []))
    except:
        pass

    # ── API ③ 기초금액 전용 금고 ──
    bss_url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBssamtPblancListInfoCnstwk'
    b_items = []
    try:
        b_res = requests.get(bss_url,
                             params={'serviceKey': SAFE_API_KEY, 'numOfRows': '3', 'pageNo': '1', 'inqryDiv': '2',
                                     'bidNtceNo': bid_no, 'type': 'json'}, verify=False, timeout=8, headers=headers)
        if b_res.status_code == 200: b_items = _safe_list(
            b_res.json().get('response', {}).get('body', {}).get('items', []))
    except:
        pass

    # ── API ② 개찰결과 상세 ──
    detail_url = 'http://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoCnstwkDtl'
    d_items = []
    successful_ord = base_ord
    test_ords = [base_ord]
    if base_ord == '00':
        test_ords.extend(['01', '02', '03'])
    else:
        test_ords.extend(['00', '01', '02'])

    for t_ord in test_ords:
        try:
            d_res = requests.get(detail_url, params={'serviceKey': SAFE_API_KEY, 'numOfRows': '1', 'pageNo': '1',
                                                     'bidNtceNo': bid_no, 'bidNtceOrd': t_ord, 'type': 'json'},
                                 verify=False, timeout=8, headers=headers)
            if d_res.status_code == 200:
                temp_items = _safe_list(d_res.json().get('response', {}).get('body', {}).get('items', []))
                if temp_items:
                    d_items = temp_items
                    successful_ord = t_ord
                    break
        except:
            continue

    industry = "정보없음"
    est_price = "미발표"
    bid_method = "정보없음"
    plbdg_yn = "단일예가"

    if n_items:
        nd = n_items[0]
        industry = safe_str(nd.get('indstrytyLmtNm', ''), "정보없음")
        bid_method = safe_str(nd.get('bidMthdNm', ''), "정보없음")
        ep_raw = str(nd.get('presmptPrce', '')).strip()
        if ep_raw and ep_raw != '0': est_price = safe_fmt_amt(ep_raw)
        if industry == "정보없음": industry = safe_str(nd.get('bidNtceNm', ''), "정보없음")

    backup_bss = ""
    if b_items:
        bs_raw = str(b_items[0].get('bssAmt', '')).strip()
        if bs_raw and bs_raw != '0': backup_bss = safe_fmt_amt(bs_raw)

    bss_amt = backup_bss if backup_bss else "미발표"
    pre_amt = "미발표"
    suc_amt = safe_str(str(row.get('투찰금액', '')), "미발표")
    suc_rate = safe_str(str(row.get('투찰률', '')), "-")
    corp_info_raw = row.get('전체업체', '')

    if d_items:
        d = d_items[0]
        d_bss = str(d.get('bssAmt', '')).strip()
        if d_bss and d_bss != '0': bss_amt = safe_fmt_amt(d_bss)
        pre_amt = safe_fmt_amt(d.get('presmptPrce', ''))
        s_raw = d.get('sucsfbidAmt', '')
        if s_raw: suc_amt = safe_fmt_amt(s_raw)
        suc_rate = safe_str(str(d.get('sucsfbidRate', suc_rate)), "-")
        plbdg_yn = '사용함(번호 추첨)' if d.get('plbdgYn') == 'Y' else '단일예가'
        corp_info_raw = d.get('opengCorpInfo', corp_info_raw)

    if not corp_info_raw or str(corp_info_raw).strip() in ('', 'nan', 'NaN', 'None'):
        try:
            b_url = 'http://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoCnstwk'
            b_res = requests.get(b_url,
                                 params={'serviceKey': SAFE_API_KEY, 'numOfRows': '2', 'pageNo': '1', 'inqryDiv': '2',
                                         'bidNtceNo': bid_no, 'type': 'json'}, verify=False, timeout=8, headers=headers)
            if b_res.status_code == 200:
                b_items_list = _safe_list(b_res.json().get('response', {}).get('body', {}).get('items', []))
                if b_items_list: corp_info_raw = str(b_items_list[0].get('opengCorpInfo', '')).strip()
        except:
            pass

    corps = []
    if pd.notna(corp_info_raw) and str(corp_info_raw).strip() not in ('', 'nan', 'NaN', 'None'):
        for idx, c in enumerate(str(corp_info_raw).split('|')):
            if idx >= 10: break
            p = c.split('^')
            if len(p) >= 4:
                comp_name = p[0].strip()
                ceo_name = p[2].strip() if len(p) > 2 else ""
                p3_raw = str(p[3]).strip() if len(p) > 3 else ""
                t_rate = f"{p[4].strip()}%" if len(p) > 4 else "-"
                rank_medal = {1: "🥇 1위", 2: "🥈 2위", 3: "🥉 3위"}.get(idx + 1, f"{idx + 1}위")

                try:
                    t_amt = f"{int(float(p3_raw)):,}원" if p3_raw else "-"
                except:
                    t_amt = p3_raw or "-"

                corps.append({
                    '순위': rank_medal,
                    '업체명': f"{comp_name} ({ceo_name})" if ceo_name else comp_name,
                    '투찰금액': t_amt,
                    '투찰률': t_rate,
                })

    return {
        'successful_ord': successful_ord,
        'bss_amt': bss_amt,
        'pre_amt': pre_amt,
        'suc_amt': suc_amt,
        'suc_rate': suc_rate,
        'est_price': est_price,
        'industry': industry,
        'bid_method': bid_method,
        'plbdg_yn': plbdg_yn,
        'corps': corps,
        'has_detail': bool(d_items),
    }


# ==========================================
# 9. 메인 UI 대시보드
# ==========================================
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
        if st.button("🚪 로그아웃"):
            st.session_state['logged_in'] = False
            st.rerun()
        menu_list = ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "📁 K-건설 자료실", "💬 K건설챗"]
    else:
        st.info("💡 **무료 회원가입** 후 내 면허 **맞춤매칭** 및 실시간 **오픈채팅**을 마음껏 이용하세요!")
        menu_list = ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "📁 K-건설 자료실", "💬 K건설챗", "👤 로그인 / 회원가입"]
    menu = st.radio("업무 선택", menu_list)
    st.write("---")
    if st.button("🔄 만능 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 10. 메뉴별 작동 로직
# ==========================================

# ── 🏆 1순위 현황판 ──
if menu == "🏆 1순위 현황판":
    st.subheader("🏆 실시간 1순위 현황판")
    col_t, col_m, col_b = st.columns([2, 1, 1])
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
            tr_cols = st.columns(5)
            rates = [99.0, 99.5, 100.0, 100.5, 101.0]
            labels = ["❄️ 차가움", "🌬️ 서늘함", "🌤️ 적정함", "☀️ 따뜻함", "🔥 뜨거움"]
            for i, r in enumerate(rates):
                with tr_cols[i]:
                    bid_p = int(base_price * (r / 100) * (float(rate_option) / 100))
                    st.info(f"**{labels[i]}**\n\n{r}%\n\n**{bid_p:,}원**")

    df_w = get_hybrid_1st_bids()
    if not df_w.empty:
        df_f = filter_by_region(df_w, selected_region_1st)
        st.info("💡 **맨 왼쪽 [빈 칸]을 클릭하세요!** 상세 분석 리포트가 열립니다.")
        event = st.dataframe(
            df_f[['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률']],
            use_container_width=True, hide_index=True, height=400,
            selection_mode="single-row", on_select="rerun"
        )

        if len(event.selection.rows) > 0:
            row = df_f.iloc[event.selection.rows[0]]
            st.markdown("---")

            bid_no = str(row['공고번호']).strip()
            raw_ord = row.get('공고차수', '00')
            if pd.isna(raw_ord) or str(raw_ord).strip() in ['nan', 'NaN', '']:
                base_ord = '00'
            else:
                try:
                    base_ord = str(int(float(raw_ord))).zfill(2)
                except:
                    base_ord = '00'

            with st.spinner("🔍 조달청 금고 다이렉트 해제 중..."):
                det = fetch_bid_full_detail(bid_no, base_ord, row)

            # ── 상단 4대 금액 카드 (중복 표 삭제됨!) ──
            st.markdown(f"#### ✅ [나노 VIP 분석 리포트]  {row['공고명'][:35]}...")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">💰 기초금액</div><div class="stat-val" style="color:#d97706;font-size:17px;">{det["bss_amt"]}</div></div>',
                    unsafe_allow_html=True)
            with m2:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">📐 추정가격</div><div class="stat-val" style="color:#1e3a8a;font-size:17px;">{det["est_price"]}</div></div>',
                    unsafe_allow_html=True)
            with m3:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">🎯 예정가격</div><div class="stat-val" style="color:#2563eb;font-size:17px;">{det["pre_amt"]}</div></div>',
                    unsafe_allow_html=True)
            with m4:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">🏆 낙찰금액</div><div class="stat-val" style="color:#dc2626;font-size:17px;">{det["suc_amt"]}</div></div>',
                    unsafe_allow_html=True)

            st.write("")

            # ── 1~10순위 전체 순위표 ──
            if det['corps']:
                st.markdown("##### 📋 참여업체 전체 투찰 순위 현황 (TOP 10)")
                corps_df = pd.DataFrame(det['corps'])
                st.dataframe(corps_df, use_container_width=True, hide_index=True)
                if len(det['corps']) == 1 and not det['has_detail']:
                    st.warning("⚠️ 조달청에서 아직 2순위 이하 전체 명단을 전송하지 않았습니다. (개찰 직후 1순위 선공개 상태)")
            else:
                if not det['has_detail']:
                    st.warning("💡 조달청에서 아직 개찰 상세 성적표를 업로드하지 않았습니다. (보통 개찰 직후 딜레이가 발생합니다)")
                else:
                    st.info("참여업체 정보가 없습니다.")

            # ── 하단 버튼 영역 ──
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown("💡 **조달청 보안 정책으로 복사가 필요합니다.**")
                st.caption("1️⃣ 우측 아이콘(📋)을 눌러 공고번호를 복사하세요.")
                st.code(row['공고번호'], language=None)
            with sc2:
                st.link_button("🚀 나라장터 메인 홈페이지 열기", "https://www.g2b.go.kr/index.jsp", use_container_width=True)
                st.link_button("🏢 업체 네이버 검색", f"https://search.naver.com/search.naver?query={row['1순위업체']} 건설",
                               use_container_width=True)

    else:
        st.warning("데이터를 불러오는 중이거나 조회된 공고가 없습니다. 만능 새로고침을 시도해보세요.")

# ── 📊 실시간 공고 ──
elif menu == "📊 실시간 공고 (홈)":
    st.subheader("📊 실시간 입찰 공고")
    df_live = get_hybrid_live_bids()
    if not df_live.empty:
        selected_region_live = st.selectbox("🌍 지역 필터링", REGION_LIST)
        df_live_f = filter_by_region(df_live, selected_region_live)
        col_cfg = {
            "상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
            "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")
        }

        if st.session_state['logged_in'] and st.session_state['user_license']:
            t1, t2 = st.tabs(["🌐 전체 공고", "✨ 내 면허 맞춤매칭"])
            with t1:
                st.dataframe(df_live_f[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                             use_container_width=True, hide_index=True, height=600, column_config=col_cfg)
            with t2:
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
                st.dataframe(matched_df[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                             use_container_width=True, hide_index=True, height=600, column_config=col_cfg)
        else:
            st.dataframe(df_live_f[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                         use_container_width=True, hide_index=True, height=600, column_config=col_cfg)

# ── 📁 K-건설 자료실 ──
elif menu == "📁 K-건설 자료실":
    st.subheader("📁 K-건설 자료실")
    if st.session_state['logged_in']:
        with st.expander("✏️ 새 글 작성하기"):
            t = st.text_input("제목")
            c = st.text_area("내용")
            if st.button("등록"):
                if t and c:
                    db.child("posts").push({"author": st.session_state['user_name'], "title": t, "content": c,
                                            "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M")})
                    st.toast("등록 완료!", icon="✅")
                    st.rerun()
                else:
                    st.toast("제목과 내용을 모두 입력해주세요.", icon="⚠️")
    else:
        st.info("💡 글을 작성하시려면 로그인해 주세요.")

    posts = db.child("posts").get().val()
    if posts:
        for post_id, p in reversed(list(posts.items())):
            expander_title = f"📢 {p.get('title', '제목 없음')} (작성자: {p.get('author', '알수없음')} | {p.get('time', '')[:10]})"
            with st.expander(expander_title):
                st.write(p.get('content', '내용이 없습니다.'))
                if st.session_state['user_name'] == p.get('author') or st.session_state['user_name'] == "명환":
                    st.write("---")
                    if st.button("🗑️ 이 글 삭제하기", key=f"del_{post_id}"):
                        db.child("posts").child(post_id).remove()
                        st.toast("글이 삭제되었습니다!", icon="✅")
                        st.rerun()
    else:
        st.info("등록된 자료가 없습니다. 첫 글의 주인공이 되어보세요!")

# ── 💬 K건설챗 ──
elif menu == "💬 K건설챗":
    st.subheader("💬 K건설챗")
    if not st.session_state['logged_in']:
        st.info("로그인 후 소장님들과 실시간 대화를 나눠보세요!")
    else:
        col1, col2 = st.columns([8, 2])
        with col2:
            if st.button("🔄 대화 새로고침", use_container_width=True): st.rerun()
        chat_box = st.container(height=500)
        try:
            # [수정] 인덱스 에러 원천 차단: 파이썬 내부에서 최신 50개 자르기
            all_chats = db.child("k_chat").get().val()
            chats = dict(list(all_chats.items())[-50:]) if all_chats else None

            with chat_box:
                if chats:
                    chat_list = list(chats.values())
                    chat_list.sort(key=lambda x: x.get('timestamp', 0))
                    for v in chat_list:
                        with st.chat_message("user",
                                             avatar="👷‍♂️" if v['author'] == st.session_state['user_name'] else "👤"):
                            st.markdown(f"**{v['author']}** <small>{v['time']}</small>", unsafe_allow_html=True)
                            st.write(v['message'])
                else:
                    st.info("아직 대화가 없습니다. 첫인사를 남겨보세요!")
        except:
            with chat_box:
                st.info("대화 내역을 불러오는 중이거나 아직 대화가 없습니다.")

        if pr := st.chat_input("메시지를 입력하세요 (현장 상황 공유 등)"):
            db.child("k_chat").push({
                "author": st.session_state['user_name'], "message": pr,
                "time": datetime.now(KST).strftime("%m-%d %H:%M"),
                "timestamp": datetime.now(KST).timestamp()
            })
            st.rerun()

        if st.session_state['user_name'] == "명환":
            st.write("---")
            if st.button("🧹 [관리자] K건설챗 대화방 싹 비우기"):
                db.child("k_chat").remove()
                st.rerun()

# ── 👤 로그인 / 회원가입 ──
elif menu == "👤 로그인 / 회원가입":
    st.subheader("👤 회원 정보 관리")
    t1, t2 = st.tabs(["🔑 로그인", "📝 회원가입"])
    with t1:
        le = st.text_input("이메일", key="login_e")
        lp = st.text_input("비밀번호", type="password", key="login_p")
        if st.button("로그인"):
            le_clean = le.strip().lower()
            if not le_clean or not lp:
                st.toast("이메일과 비밀번호를 모두 입력해주세요.", icon="⚠️")
            else:
                login_success = False
                try:
                    user = auth.sign_in_with_email_and_password(le_clean, lp)
                    info = db.child("users").child(user['localId']).get().val() or {}
                    st.session_state.update({
                        'logged_in': True,
                        'user_name': info.get('name', '소장님'),
                        'user_license': info.get('license', '')
                    })
                    login_success = True
                except Exception as e:
                    st.toast("로그인 실패 🥲 이메일이나 비밀번호를 다시 확인해주세요.", icon="🚨")

                # [수정] 로그인 성공 시에만 안전하게 새로고침 (빨간 에러창 방지)
                if login_success:
                    st.rerun()

    with t2:
        re = st.text_input("가입용 이메일", key="reg_e")
        rp = st.text_input("비밀번호 (6자 이상)", type="password", key="reg_p")
        rn = st.text_input("성함/직함", key="reg_n")
        rl = st.multiselect("보유 면허 (매칭용)", ALL_LICENSES, key="reg_l")
        if st.button("가입하기"):
            re_clean = re.strip().lower()
            if not re_clean or not rp or not rn:
                st.toast("이메일, 비밀번호, 성함을 모두 입력해주세요.", icon="⚠️")
            elif len(rp) < 6:
                st.toast("비밀번호는 최소 6자리 이상이어야 합니다.", icon="⚠️")
            else:
                try:
                    u = auth.create_user_with_email_and_password(re_clean, rp)
                    l_s = ", ".join(rl) if rl else "선택안함"
                    db.child("users").child(u['localId']).set({"name": rn, "license": l_s, "email": re_clean})
                    st.toast("🎉 가입 성공! 왼쪽 탭에서 로그인을 진행해주세요.", icon="✅")
                except:
                    st.toast("가입 실패! 이미 가입된 메일이거나 형식이 잘못되었습니다.", icon="❌")