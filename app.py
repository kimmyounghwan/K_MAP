import streamlit as st
import pandas as pd
import requests
import pyrebase
import urllib3
import urllib.parse
from datetime import datetime, timedelta, timezone
import time
import re

# ==========================================
# 1. 보안 및 페이지 설정
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="K-건설맵 Master", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <meta name="naver-site-verification" content="bfb3f10bce2983b4dd5974ba39d05e3ce5225e73" />
        <meta name="description" content="K-건설맵: 전국 건설 공사 입찰 및 실시간 1순위 개찰 결과를 즉시 확인하세요.">
    </head>
    <style>
        /* 모바일 화면 흔들림 및 줌 방지 */
        html, body { overflow-x: hidden; overscroll-behavior-x: none; touch-action: pan-y; }

        .stApp[data-teststate="running"] .stAppViewBlockContainer { filter: none !important; opacity: 1 !important; }
        [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
        .stApp { transition: none !important; }
        .main-title { background-color: #1e3a8a; color: white; border-radius: 10px; font-weight: 900; font-size: 28px; text-align: center; padding: 20px; margin-bottom: 25px; }
        .stat-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px; }
        .stat-label { font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 4px; }
        .stat-val { font-size: 17px; font-weight: 800; color: #1e3a8a; }
        .calc-badge { font-size: 10px; color: #ea580c; font-weight: 700; margin-top: 3px; }
        .guide-box { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 5px; margin-bottom: 15px; font-size: 14px; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))

# ==========================================
# 2. 파이어베이스
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

for k, v in [('logged_in', False), ('user_name', ""), ('user_license', ""), ('user_phone', ""), ('localId', ""),
             ('idToken', "")]:
    if k not in st.session_state: st.session_state[k] = v


# ==========================================
# 3. 방문 누적 카운팅 로직
# ==========================================
def update_stats():
    if 'visited' not in st.session_state:
        try:
            curr = db.child("stats").child("total_visits").get().val()
            if curr is None: curr = 1828
            db.child("stats").update({"total_visits": curr + 1})
            st.session_state['visited'] = True
        except:
            pass


def get_stats():
    try:
        t_v = db.child("stats").child("total_visits").get().val() or 1828
        u_v = db.child("users").get().val()
        return t_v, len(u_v) if u_v else 0
    except:
        return 1828, 0


# ==========================================
# 4. 유틸리티 함수
# ==========================================
REGION_LIST = ["전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남",
               "제주"]
ALL_LICENSES = ["[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업", "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업",
                "[전문] 철근·콘크리트공사업", "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업"]
BASE = 'http://apis.data.go.kr/1230000'

API_TABLE = {
    'cnstwk': {'notice': f'{BASE}/ad/BidPublicInfoService/getBidPblancListInfoCnstwk',
               'result': f'{BASE}/as/ScsbidInfoService/getOpengResultListInfoCnstwk',
               'detail': f'{BASE}/as/ScsbidInfoService/getOpengResultListInfoCnstwkDtl'},
    'etcwk': {'notice': f'{BASE}/ad/BidPublicInfoService/getBidPblancListInfoEtcwk',
              'result': f'{BASE}/as/ScsbidInfoService/getOpengResultListInfoEtcwk',
              'detail': f'{BASE}/as/ScsbidInfoService/getOpengResultListInfoEtcwkDtl'},
}


def get_bid_type(bid_no: str) -> str:
    code = bid_no.strip().upper()
    if len(code) < 5: return 'cnstwk'
    return {'CW': 'cnstwk', 'BK': 'etcwk', 'EW': 'etcwk', 'SV': 'servc', 'GD': 'goods'}.get(code[3:5], 'cnstwk')


def filter_by_region(df, sel):
    if sel == "전국(전체)": return df
    rk = {"서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"], "광주": ["광주"], "대전": ["대전"], "울산": ["울산"],
          "세종": ["세종"], "경기": ["경기", "경기도"], "강원": ["강원", "강원도"], "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
          "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"], "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"], "제주": ["제주"]}
    pat = '|'.join(rk.get(sel, [sel]))
    return df[df['발주기관'].str.contains(pat, na=False) | df['공고명'].str.contains(pat, na=False)]


def raw_to_int(raw) -> int:
    if raw is None: return 0
    r = str(raw).strip().replace(',', '').replace('원', '').replace('%', '')
    try:
        return int(float(r))
    except:
        return 0


def fmt_amt(v: int) -> str:
    return f"{v:,}원" if v > 0 else ''


def get_match_keywords(lic):
    k = []
    if "토목" in lic: k.extend(["토목", "도로", "포장", "하천", "교량", "정비", "관로", "상수도", "하수도"])
    if "건축" in lic: k.extend(["건축", "신축", "증축", "보수", "인테리어", "방수", "도장"])
    if "조경" in lic: k.extend(["조경", "식재", "공원", "수목"])
    if "전기" in lic: k.extend(["전기", "배전", "가로등", "CCTV"])
    if "통신" in lic: k.extend(["통신", "네트워크", "방송"])
    if "소방" in lic: k.extend(["소방", "화재", "스프링클러"])
    if "철근" in lic or "콘크리트" in lic: k.extend(["철콘", "구조물", "옹벽", "배수", "기초"])
    return list(set(k))


def _safe_list(obj):
    if not obj: return []
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        item = obj.get('item')
        return item if isinstance(item, list) else [item] if isinstance(item, dict) else [obj]
    return []


def _api_get(url: str, params: dict, timeout: int = 30) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, params={**params, 'serviceKey': SAFE_API_KEY, 'type': 'json'}, headers=headers,
                         verify=False, timeout=timeout)
        if r.status_code == 200:
            body = r.json().get('response', {}).get('body', {}).get('items', [])
            if isinstance(body, dict): return [body.get('item', {})]
            return body if isinstance(body, list) else []
    except:
        pass
    return []


# ==========================================
# 5. 데이터 팝업창 (Modal Dialog) 함수
# ==========================================
@st.dialog("📋 K-건설맵 정밀 리포트", width="large")
def show_analysis_dialog(row, det, mode="1st"):
    if mode == "1st":
        st.markdown(f"### {row['공고명']}")
        m1, m2, m3, m4 = st.columns(4)

        def _card(col, icon, label, val, key, val_color="#1e3a8a"):
            badge = {'API': '✓ 공식', 'CALC': '🧮 추정'}.get(det['sources'].get(key, ''), '')
            col.markdown(
                f'<div class="stat-card"><div class="stat-label">{icon} {label}</div><div class="stat-val" style="color:{val_color};">{val if val else "-"}</div><div class="calc-badge">{badge}</div></div>',
                unsafe_allow_html=True)

        _card(m1, "💰", "기초금액", det['bss_amt'], 'bss')
        _card(m2, "📐", "추정가격", det['est_price'], 'est')
        _card(m3, "🎯", "예정가격", det['pre_amt'], 'pre')
        _card(m4, "🏆", "낙찰금액", det['suc_amt'], 'suc', "#dc2626")

        if 'CALC' in det['sources'].values():
            st.caption("* 🧮 표시는 수학 공식(기초금액≈추정가격×1.1 또는 예정가격 역산)에 의한 참고용 추정치입니다.")

        if det['corps']:
            st.write("**[개찰 결과 성적표]**")
            st.dataframe(pd.DataFrame(det['corps']), use_container_width=True, hide_index=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("💡 **나라장터 정책상 번호 복사가 필요합니다.**")
            st.code(row['공고번호'], language=None)
        with sc2:
            st.write("")
            st.link_button("🚀 나라장터 홈페이지", "https://www.g2b.go.kr/index.jsp", use_container_width=True)
            st.link_button("🏢 업체 네이버 검색", f"https://search.naver.com/search.naver?query={row['1순위업체']} 건설",
                           use_container_width=True)

    elif mode == "live":
        st.markdown(f"### 🎯 입찰 시뮬레이터")
        st.write(f"**공고명:** {row['공고명']}")
        budget = int(row['예산금액'])
        sim_base_val = budget
        base_label = "예산금액"

        try:
            bid_no_live = str(row['공고번호']).split('-')[0].strip()
            r = requests.get(f'{BASE}/ad/BidPublicInfoService/getBidPblancListInfoCnstwk',
                             params={'serviceKey': SAFE_API_KEY, 'numOfRows': '1', 'pageNo': '1', 'inqryDiv': '2',
                                     'bidNtceNo': bid_no_live, 'type': 'json'}, verify=False, timeout=10)
            if r.status_code == 200:
                items = _safe_list(r.json().get('response', {}).get('body', {}).get('items', []))
                if items:
                    d = items[0]
                    b_val = raw_to_int(d.get('bssAmt', 0))
                    e_val = raw_to_int(d.get('presmptPrce', 0))
                    if b_val > 0:
                        sim_base_val, base_label = b_val, "기초금액 (조달청 발표)"
                    elif e_val > 0:
                        sim_base_val, base_label = int(e_val * 1.1), "기초금액 (추정가격×1.1 역산)"
        except:
            pass

        c1, c2 = st.columns(2)
        with c1:
            sim_base = st.number_input(base_label, value=sim_base_val, step=1000000)
        with c2:
            sim_rate = st.selectbox("투찰 하한율 (%)", ["87.745", "86.745", "87.995", "89.995"])

        st.write("---")
        st.write("💡 **나노 AI 추천 투찰금액 (사정률 5구간)**")
        tr_cols = st.columns(5)
        rates, labels = [99.0, 99.5, 100.0, 100.5, 101.0], ["❄️ 99.0%", "🌬️ 99.5%", "🌤️ 100.0%", "☀️ 100.5%",
                                                            "🔥 101.0%"]
        for i, r in enumerate(rates):
            with tr_cols[i]:
                price = int(sim_base * (r / 100.0) * (float(sim_rate) / 100.0))
                st.info(f"**{labels[i]}**\n\n**{price:,}원**")
        st.caption("⚠️ A값(공제비용) 미반영 순수 산술식입니다. 실제 투찰 시 공고문 확인 필수!")

    elif mode == "job":
        st.markdown(f"### 🤝 구인/구직 상세내용")
        st.write(f"**제목:** {row['title']} | **지역:** {row['region']}")
        st.write(f"**작성자:** {row['author']} | **연락처:** {row['phone']}")
        st.markdown("---")
        st.write(row['content'])


# ==========================================
# 6. 데이터 수집 엔진 (1순위 에러 방어 로직 강화)
# ==========================================
@st.cache_data(ttl=60, show_spinner=False)
def get_hybrid_1st_bids():
    now = datetime.now(KST)
    s_dt = (now - timedelta(days=2)).strftime('%Y%m%d')
    e_dt = now.strftime('%Y%m%d')

    api_items = _api_get(f'{BASE}/as/ScsbidInfoService/getOpengResultListInfoCnstwk',
                         {'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1', 'inqryBgnDt': s_dt + '0000',
                          'inqryEndDt': e_dt + '2359'}, timeout=30)
    api_items.extend(_api_get(f'{BASE}/as/ScsbidInfoService/getOpengResultListInfoEtcwk',
                              {'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1', 'inqryBgnDt': s_dt + '0000',
                               'inqryEndDt': e_dt + '2359'}, timeout=30))

    db_data = db.child("archive_1st").order_by_key().limit_to_last(4000).get().val() or {}
    db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    new_rows = {}

    for it in api_items:
        bid_no = it.get('bidNtceNo', '')
        corp_info_raw = it.get('opengCorpInfo', '')

        # 🛡️ 나노의 방어벽: 조달청이 불량(빈) 데이터를 주면 에러 없이 조용히 패스함!
        if corp_info_raw:
            info = str(corp_info_raw).split('|')[0].split('^')
            if len(info) > 3 and info[0].strip():
                new_rows[bid_no] = {
                    '1순위업체': info[0].strip(),
                    '공고번호': bid_no,
                    '공고차수': it.get('bidNtceOrd', '00'),
                    '날짜': it.get('opengDt', ''),
                    '공고명': it.get('bidNtceNm', ''),
                    '발주기관': it.get('ntceInsttNm', ''),
                    '투찰금액': f"{int(float(info[3])):,}원" if len(info) > 3 else '-',
                    '투찰률': f"{info[4]}%" if len(info) > 4 else '-',
                    '전체업체': corp_info_raw
                }

    if new_rows: db.child("archive_1st").update(new_rows)
    df = pd.DataFrame(list(new_rows.values()) + db_items)

    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='dt', ascending=False)
        df['날짜'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


@st.cache_data(ttl=180, show_spinner=False)
def get_hybrid_live_bids():
    now = datetime.now(KST)
    s_dt = now.strftime('%Y%m%d')
    api_items = _api_get(f'{BASE}/ad/BidPublicInfoService/getBidPblancListInfoCnstwk',
                         {'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1', 'inqryBgnDt': s_dt + '0000',
                          'inqryEndDt': s_dt + '2359', 'bidNtceNm': '공사'}, timeout=30)
    api_items.extend(_api_get(f'{BASE}/ad/BidPublicInfoService/getBidPblancListInfoEtcwk',
                              {'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1', 'inqryBgnDt': s_dt + '0000',
                               'inqryEndDt': s_dt + '2359', 'bidNtceNm': '공사'}, timeout=30))
    db_data = db.child("archive_live").order_by_key().limit_to_last(4000).get().val() or {}
    db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    new_rows = {
        it.get('bidNtceNo'): {'공고번호': it.get('bidNtceNo'), '공고일자': it.get('bidNtceDt'), '공고명': it.get('bidNtceNm'),
                              '발주기관': it.get('ntceInsttNm'), '예산금액': int(float(it.get('bdgtAmt', 0))),
                              '상세보기': it.get('bidNtceDtlUrl', "https://www.g2b.go.kr/index.jsp")} for it in api_items if
        it.get('bidNtceNo')}
    if new_rows: db.child("archive_live").update(new_rows)
    df = pd.DataFrame(list(new_rows.values()) + db_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['공고일자'], errors='coerce')
        df = df.sort_values(by='dt', ascending=False)
        df['공고일자'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


def fetch_detail(row):
    bid_no = str(row['공고번호']).strip()
    res = {'bss_amt': '', 'est_price': '', 'pre_amt': '', 'sources': {}}
    bid_type = get_bid_type(bid_no)
    urls = API_TABLE.get(bid_type, API_TABLE['cnstwk'])
    items = _api_get(urls['notice'], {'numOfRows': '5', 'pageNo': '1', 'inqryDiv': '2', 'bidNtceNo': bid_no})
    if items:
        d = items[0]
        res['bss_amt'] = fmt_amt(raw_to_int(d.get('bssAmt')))
        res['est_price'] = fmt_amt(raw_to_int(d.get('presmptPrce')))
        if res['bss_amt']: res['sources']['bss'] = 'API'
        if res['est_price']: res['sources']['est'] = 'API'

    suc_v = raw_to_int(row.get('투찰금액', ''))
    rate_s = str(row.get('투찰률', '')).replace('%', '').strip()
    rate_v = float(rate_s) if rate_s and rate_s != '-' else 0

    if suc_v > 0 and rate_v > 0:
        res['pre_amt'] = fmt_amt(int(round(suc_v / (rate_v / 100.0))))
        res['sources']['pre'] = 'CALC'
        if not res['bss_amt']:
            res['bss_amt'] = fmt_amt(int(round(raw_to_int(res['est_price']) * 1.1))) if raw_to_int(
                res['est_price']) > 0 else res['pre_amt']
            res['sources']['bss'] = 'CALC'

    if not res['est_price'] and res['bss_amt']:
        res['est_price'] = fmt_amt(int(round(raw_to_int(res['bss_amt']) / 1.1)))
        res['sources']['est'] = 'CALC'

    res['suc_amt'] = row.get('투찰금액', '-')
    corps = []
    corp_raw = row.get('전체업체', '')
    if corp_raw:
        for idx, c in enumerate(str(corp_raw).split('|')[:10]):
            p = c.split('^')
            if len(p) >= 5: corps.append(
                {'순위': f"{idx + 1}위", '업체명': p[0].strip(), '투찰금액': f"{int(float(p[3])):,}원", '투찰률': f"{p[4].strip()}%"})
    res['corps'] = corps
    return res


# ==========================================
# 7. UI 대시보드
# ==========================================
update_stats()
t_visit, u_total = get_stats()

st.markdown('<div class="main-title">🏛️ K-건설맵 Master</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(
    f'<div class="stat-card"><div class="stat-label">📅 오늘 날짜</div><div class="stat-val">{datetime.now(KST).strftime("%Y-%m-%d")}</div></div>',
    unsafe_allow_html=True)
with c2: st.markdown(
    f'<div class="stat-card"><div class="stat-label">📈 누적 방문</div><div class="stat-val">{t_visit:,}명</div></div>',
    unsafe_allow_html=True)
with c3: st.markdown(
    f'<div class="stat-card"><div class="stat-label">👥 전체 회원수</div><div class="stat-val">{u_total:,}명</div></div>',
    unsafe_allow_html=True)
with c4: st.markdown(
    f'<div class="stat-card"><div class="stat-label">🔔 가동 상태</div><div class="stat-val" style="color:green;">정상 가동 중</div></div>',
    unsafe_allow_html=True)

with st.sidebar:
    st.write(f"### 👷 {'👋 ' + st.session_state['user_name'] + ' 소장님' if st.session_state['logged_in'] else 'K-건설맵 메뉴'}")
    menu = st.radio("업무 선택",
                    ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "🤝 K-구인구직", "📁 K-건설 자료실", "💬 K건설챗", "📲 앱처럼 설치하기", "👤 내 정보/로그인"])
    st.write("---")
    if st.button("🔄 만능 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    if st.session_state['logged_in'] and st.button("🚪 로그아웃"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 8. 메뉴 라우팅
# ==========================================
ROWS_PER_PAGE = 20

if menu == "🏆 1순위 현황판":
    st.markdown("#### 🏆 실시간 1순위 현황판")

    st.markdown("""
        <div class="guide-box">
            💡 <b>터치 한 번으로 정밀 분석!</b><br>
            아래 리스트 맨 왼쪽의 <b>[체크박스(ㅁ)]</b>를 터치해 보세요. 상세 리포트가 팝업창으로 즉시 열립니다.
        </div>
    """, unsafe_allow_html=True)

    df_w = get_hybrid_1st_bids()
    if not df_w.empty:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            sel_reg = st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg1")
        with col_f2:
            search_co = st.text_input("🏢 업체명 검색", placeholder="낙찰 업체명을 입력하세요", key="search_main")

        df_f = filter_by_region(df_w, sel_reg)
        if search_co: df_f = df_f[df_f['1순위업체'].str.contains(search_co, na=False)]

        num_pages = max(1, (len(df_f) // ROWS_PER_PAGE) + (1 if len(df_f) % ROWS_PER_PAGE > 0 else 0))
        if "p1" not in st.session_state: st.session_state["p1"] = 1

        start_idx = (st.session_state["p1"] - 1) * ROWS_PER_PAGE
        df_page = df_f.iloc[start_idx: start_idx + ROWS_PER_PAGE]
        event = st.dataframe(df_page[['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률']], use_container_width=True,
                             hide_index=True, height=700, selection_mode="single-row", on_select="rerun")

        st.write("")
        c_p1, c_p2, c_p3 = st.columns([3, 4, 3])
        with c_p2:
            st.selectbox(f"📄 페이지 이동 (총 {num_pages}쪽)", range(1, num_pages + 1), key="p1")

        if len(event.selection.rows) > 0:
            selected_row = df_page.iloc[event.selection.rows[0]]
            with st.spinner("📡 분석 중..."): det = fetch_detail(selected_row)
            show_analysis_dialog(selected_row, det, mode="1st")

elif menu == "📊 실시간 공고 (홈)":
    st.markdown("#### 📊 실시간 입찰 공고")

    st.markdown("""
        <div class="guide-box">
            💡 <b>입찰 시뮬레이터 가동!</b><br>
            아래 리스트 맨 왼쪽의 <b>[체크박스(ㅁ)]</b>를 터치해 보세요. AI 추천 투찰금액이 팝업창으로 열립니다.
        </div>
    """, unsafe_allow_html=True)

    df_live = get_hybrid_live_bids()
    if not df_live.empty:
        df_f = filter_by_region(df_live, st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg2"))
        col_cfg = {"상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
                   "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")}

        if st.session_state['logged_in']:
            t1, t2 = st.tabs(["🌐 전체 공고", "✨ 내 면허 맞춤매칭"])
            with t1:
                n_all = max(1, (len(df_f) // ROWS_PER_PAGE) + 1)
                if "p_all" not in st.session_state: st.session_state["p_all"] = 1
                df_p_all = df_f.iloc[
                    (st.session_state["p_all"] - 1) * ROWS_PER_PAGE: st.session_state["p_all"] * ROWS_PER_PAGE]
                event = st.dataframe(df_p_all[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                                     use_container_width=True, hide_index=True, height=700, column_config=col_cfg,
                                     selection_mode="single-row", on_select="rerun", key="live_all")
                c1, c2, c3 = st.columns([3, 4, 3])
                with c2: st.selectbox(f"📄 페이지 이동 (총 {n_all}쪽)", range(1, n_all + 1), key="p_all")
            with t2:
                kw = get_match_keywords(st.session_state.get('user_license', ''))
                m_full = df_f[df_f['공고명'].str.contains('|'.join(kw), na=False)] if kw else df_f
                n_m = max(1, (len(m_full) // ROWS_PER_PAGE) + 1)
                if "p_m" not in st.session_state: st.session_state["p_m"] = 1
                df_p_m = m_full.iloc[
                    (st.session_state["p_m"] - 1) * ROWS_PER_PAGE: st.session_state["p_m"] * ROWS_PER_PAGE]
                event_m = st.dataframe(df_p_m[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                                       use_container_width=True, hide_index=True, height=700, column_config=col_cfg,
                                       selection_mode="single-row", on_select="rerun", key="live_match")
                c1, c2, c3 = st.columns([3, 4, 3])
                with c2:
                    st.selectbox(f"📄 페이지 이동 (총 {n_m}쪽)", range(1, n_m + 1), key="p_m")
                if len(event_m.selection.rows) > 0: event, df_p_all = event_m, df_p_m
        else:
            n_g = max(1, (len(df_f) // ROWS_PER_PAGE) + 1)
            if "p_g" not in st.session_state: st.session_state["p_g"] = 1
            df_p_g = df_f.iloc[(st.session_state["p_g"] - 1) * ROWS_PER_PAGE: st.session_state["p_g"] * ROWS_PER_PAGE]
            event = st.dataframe(df_p_g[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                                 hide_index=True, height=700, column_config=col_cfg, selection_mode="single-row",
                                 on_select="rerun")
            c1, c2, c3 = st.columns([3, 4, 3])
            with c2:
                st.selectbox(f"📄 페이지 이동 (총 {n_g}쪽)", range(1, n_g + 1), key="p_g")
            df_p_all = df_p_g

        if len(event.selection.rows) > 0:
            show_analysis_dialog(df_p_all.iloc[event.selection.rows[0]], None, mode="live")

elif menu == "🤝 K-구인구직":
    st.markdown("#### 🤝 건설현장 구인구직")
    if st.session_state['logged_in']:
        with st.expander("📝 새 구인/구직 등록하기"):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("분류", ["👷 사람 구합니다", "🚜 일자리 찾습니다"])
            reg = c2.selectbox("지역", REGION_LIST)
            jt = st.text_input("직종 (예: 철근공, 포크레인)")
            ph = st.text_input("연락처", value=st.session_state.get('user_phone', ''))
            ttl = st.text_input("제목")
            con = st.text_area("상세내용")
            if st.button("등록하기"):
                db.child("jobs").push(
                    {"category": cat, "region": reg, "job_type": jt, "phone": ph, "title": ttl, "content": con,
                     "author": st.session_state['user_name'], "time": datetime.now(KST).strftime("%m-%d %H:%M")})
                st.toast("등록 완료!")
                time.sleep(1)
                st.rerun()
    jobs_data = db.child("jobs").get().val()
    if jobs_data:
        df_j = pd.DataFrame(list(jobs_data.values())).iloc[::-1]
        t1, t2 = st.tabs(["👷 사람 구함", "🚜 일자리 찾음"])
        with t1:
            h = df_j[df_j['category'] == "👷 사람 구합니다"]
            ev_h = st.dataframe(h[['time', 'region', 'job_type', 'title', 'author']], use_container_width=True,
                                hide_index=True, selection_mode="single-row", on_select="rerun", key="h_job")
            if len(ev_h.selection.rows) > 0: show_analysis_dialog(h.iloc[ev_h.selection.rows[0]], None, mode="job")
        with t2:
            s = df_j[df_j['category'] == "🚜 일자리 찾습니다"]
            ev_s = st.dataframe(s[['time', 'region', 'job_type', 'title', 'author']], use_container_width=True,
                                hide_index=True, selection_mode="single-row", on_select="rerun", key="s_job")
            if len(ev_s.selection.rows) > 0: show_analysis_dialog(s.iloc[ev_s.selection.rows[0]], None, mode="job")

elif menu == "📲 앱처럼 설치하기":
    st.markdown("### 📲 스마트폰 바탕화면에 앱으로 추가하기")
    col1, col2 = st.columns(2)
    with col1:
        st.info("🍎 **아이폰 (Safari)**\n\n1. 하단 **[공유 버튼(□↑)]** 클릭\n2. **[홈 화면에 추가]** 클릭\n3. **[추가]** 클릭")
    with col2:
        st.success("🤖 **안드로이드 (Chrome)**\n\n1. 상단 **[점 3개(⋮)]** 클릭\n2. **[홈 화면에 추가]** 또는 **[앱 설치]** 클릭\n3. **[추가]** 클릭")

elif menu == "👤 내 정보/로그인":
    st.subheader("👤 회원 정보 관리")
    if not st.session_state['logged_in']:
        t1, t2 = st.tabs(["🔑 로그인", "📝 회원가입"])
        with t1:
            le = st.text_input("이메일")
            lp = st.text_input("비밀번호", type="password")
            if st.button("로그인"):
                try:
                    user = auth.sign_in_with_email_and_password(le.strip().lower(), lp)
                    info = db.child("users").child(user['localId']).get().val() or {}
                    st.session_state.update({'logged_in': True, 'user_name': info.get('name', '소장님'),
                                             'user_license': info.get('license', ''),
                                             'user_phone': info.get('phone', ''), 'localId': user['localId'],
                                             'idToken': user['idToken']})
                    st.rerun()
                except:
                    pass
        with t2:
            re = st.text_input("이메일 가입")
            rp = st.text_input("비번 (6자 이상)", type="password")
            rn = st.text_input("성함")
            rl = st.multiselect("보유 면허 (매칭용)", ALL_LICENSES)
            if st.button("가입하기"):
                try:
                    u = auth.create_user_with_email_and_password(re.strip().lower(), rp)
                    db.child("users").child(u['localId']).set({"name": rn, "license": ", ".join(rl), "email": re})
                    st.success("🎉 가입 성공!")
                except:
                    st.error("가입 실패!")
    else:
        st.write(f"### {st.session_state['user_name']} 소장님 반갑습니다!")
        if st.button("🚪 로그아웃"):
            st.session_state.clear()
            st.rerun()

elif menu == "📁 K-건설 자료실":
    st.subheader("📁 K-건설 자료실")
    if st.session_state['logged_in']:
        with st.expander("✏️ 새 자료 등록"):
            t, c = st.text_input("제목"), st.text_area("내용")
            if st.button("등록") and t and c:
                db.child("posts").push({"author": st.session_state['user_name'], "title": t, "content": c,
                                        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M")})
                st.rerun()
    posts = db.child("posts").get().val()
    if posts:
        for k, v in reversed(list(posts.items())):
            with st.expander(f"📢 {v['title']} (작성자: {v['author']})"): st.write(v['content'])

elif menu == "💬 K건설챗":
    st.subheader("💬 실시간 현장 소통")
    if st.session_state['logged_in']:
        chat_box = st.container(height=400)
        chats_data = db.child("k_chat").get().val()
        if chats_data:
            for v in list(chats_data.values())[-20:]: chat_box.write(f"**{v['author']}**: {v['message']}")
        if msg := st.chat_input("메시지 입력"):
            db.child("k_chat").push(
                {"author": st.session_state['user_name'], "message": msg, "time": datetime.now(KST).strftime("%H:%M")})
            st.rerun()
    else:
        st.info("로그인 후 이용 가능합니다.")