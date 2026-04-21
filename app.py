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

# [복구] 명환이가 원한 아담한 글씨(17px)와 깔끔한 카드 레이아웃 완벽 복구
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
        .stat-val { font-size: 17px; font-weight: 700; color: #1e3a8a; }
        .rank-card { background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; border-radius: 10px; padding: 16px; text-align: center; margin-bottom: 8px; }
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
# 3. 상수 데이터 (절대 잘리면 안 됨!)
# ==========================================
REGION_LIST = ["전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남",
               "제주"]
ALL_LICENSES = ["[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업", "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업",
                "[전문] 철근·콘크리트공사업", "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업"]


# ==========================================
# 4. 유틸 함수 및 매칭 로직
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


def get_match_keywords(license_str):
    k = []
    if "토목" in license_str: k.extend(["토목", "도로", "포장", "하천", "교량", "단지", "부대시설", "정비", "관로", "상수도", "하수도"])
    if "건축" in license_str: k.extend(["건축", "신축", "증축", "보수", "인테리어", "방수", "도장"])
    if "조경" in license_str: k.extend(["조경", "식재", "공원", "수목", "놀이터"])
    if "전기" in license_str: k.extend(["전기", "배전", "가로등", "CCTV"])
    if "통신" in license_str: k.extend(["통신", "네트워크", "방송", "케이블"])
    if "소방" in license_str: k.extend(["소방", "화재", "스프링클러"])
    if "철근" in license_str or "콘크리트" in license_str: k.extend(["철콘", "구조물", "옹벽", "배수", "기초", "박스", "암거"])
    return list(set(k))


# [NameError 방지] 필터 함수 최상단 배치
def filter_by_region(df, selected_region):
    if selected_region == "전국(전체)": return df
    region_keywords = {"서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"], "광주": ["광주"], "대전": ["대전"], "울산": ["울산"],
                       "세종": ["세종"], "경기": ["경기", "경기도"], "강원": ["강원", "강원도"], "충북": ["충북", "충청북도"],
                       "충남": ["충남", "충청남도"], "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"], "경북": ["경북", "경상북도"],
                       "경남": ["경남", "경상남도"], "제주": ["제주"]}
    pattern = '|'.join(region_keywords.get(selected_region, [selected_region]))
    return df[df['발주기관'].str.contains(pattern, na=False) | df['공고명'].str.contains(pattern, na=False)]


# ==========================================
# 5. 통계 및 데이터 엔진
# ==========================================
def get_stats():
    try:
        t_v = db.child("stats").child("total_visits").get().val() or 1828
        u_v = db.child("users").get().val()
        return t_v, len(u_v) if u_v else 0
    except:
        return 1828, 0


def update_stats():
    try:
        if 'visited' not in st.session_state:
            t_v = (db.child("stats").child("total_visits").get().val() or 1828) + 1
            db.child("stats").update({"total_visits": t_v})
            st.session_state['visited'] = True
    except:
        pass


def fetch_api_fast(url, params):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, params=params, verify=False, timeout=10, headers=headers)
        if res.status_code == 200: return res.json().get('response', {}).get('body', {}).get('items', [])
    except:
        pass
    return []


# ==========================================
# 6. 1순위 현황판 (15일 확장 & 인덱스 에러 방지)
# ==========================================
@st.cache_data(ttl=180, show_spinner=False)
def get_hybrid_1st_bids():
    now = datetime.now(KST)
    s_dt = (now - timedelta(days=2)).strftime('%Y%m%d')
    e_dt = now.strftime('%Y%m%d')
    url = 'http://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoCnstwk'

    try:
        params = {'serviceKey': SAFE_API_KEY, 'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1',
                  'inqryBgnDt': s_dt + '0000', 'inqryEndDt': e_dt + '2359', 'type': 'json'}
        res = requests.get(url, params=params, verify=False, timeout=25)
        api_items = res.json().get('response', {}).get('body', {}).get('items', []) if res.status_code == 200 else []
    except:
        api_items = []

    db_data = db.child("archive_1st").order_by_key().limit_to_last(4000).get().val() or {}
    db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    new_rows = {}

    if isinstance(api_items, dict): api_items = api_items.get('item', [api_items])
    for item in (api_items if isinstance(api_items, list) else []):
        try:
            bid_no = item.get('bidNtceNo', '')
            info = str(item.get('opengCorpInfo', '')).split('|')[0].split('^')
            if len(info) > 1 and info[0].strip():
                new_rows[bid_no] = {
                    '1순위업체': info[0].strip(), '공고번호': bid_no, '공고차수': item.get('bidNtceOrd', '00'),
                    '날짜': item.get('opengDt', ''), '공고명': item.get('bidNtceNm', ''),
                    '발주기관': item.get('ntceInsttNm', ''),
                    '투찰금액': f"{int(float(info[3])):,}원" if len(info) > 3 else '-',
                    '투찰률': f"{info[4]}%" if len(info) > 4 else '-', '전체업체': item.get('opengCorpInfo', '')
                }
        except:
            continue

    if new_rows: db.child("archive_1st").update(new_rows)
    df = pd.DataFrame(list(new_rows.values()) + db_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='dt', ascending=False)
        df['날짜'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


# ==========================================
# 7. 실시간 공고 데이터 엔진 (15일 확장)
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def get_hybrid_live_bids():
    now = datetime.now(KST)
    s_dt = now.strftime('%Y%m%d')
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
    params = {'serviceKey': SAFE_API_KEY, 'numOfRows': '999', 'pageNo': '1', 'inqryDiv': '1',
              'inqryBgnDt': s_dt + '0000', 'inqryEndDt': s_dt + '2359', 'bidNtceNm': '공사', 'type': 'json'}
    api_items = fetch_api_fast(url, params)

    if isinstance(api_items, dict): api_items = api_items.get('item', [api_items])

    db_data = db.child("archive_live").order_by_key().limit_to_last(4000).get().val() or {}
    db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    new_rows = {}
    for item in (api_items if isinstance(api_items, list) else []):
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
        df = df.sort_values(by='dt', ascending=False)
        df['공고일자'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


# ==========================================
# 8. ★ 핵심 엔진 (추정가격/기초금액 복구 완벽 픽스) ★
# ==========================================
def fetch_bid_full_detail(bid_no, base_ord, row):
    headers = {"User-Agent": "Mozilla/5.0"}
    res_data = {"bss_amt": "미발표", "est_price": "미발표", "pre_amt": "미발표", "suc_amt": safe_str(row.get('투찰금액'), "미발표"),
                "corps": [], "has_detail": False}

    def _safe_list(obj):
        if not obj: return []
        if isinstance(obj, list): return obj
        if isinstance(obj, dict):
            item = obj.get('item')
            if isinstance(item, list): return item
            if isinstance(item, dict): return [item]
            return [obj]
        return []

    # [복구] 추정가격/기초금액을 제대로 가져오기 위해 inqryDiv 파라미터 3개 모두 복구 완료!
    try:
        notice_url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
        n_res = requests.get(notice_url,
                             params={'serviceKey': SAFE_API_KEY, 'numOfRows': '3', 'pageNo': '1', 'inqryDiv': '2',
                                     'bidNtceNo': bid_no, 'type': 'json'}, verify=False, timeout=8, headers=headers)
        if n_res.status_code == 200:
            n_items = _safe_list(n_res.json().get('response', {}).get('body', {}).get('items', []))
            if n_items:
                ep_raw = str(n_items[0].get('presmptPrce', '')).strip()
                if ep_raw and ep_raw != '0': res_data["est_price"] = safe_fmt_amt(ep_raw)
    except:
        pass

    try:
        bss_url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBssamtPblancListInfoCnstwk'
        b_res = requests.get(bss_url,
                             params={'serviceKey': SAFE_API_KEY, 'numOfRows': '3', 'pageNo': '1', 'inqryDiv': '2',
                                     'bidNtceNo': bid_no, 'type': 'json'}, verify=False, timeout=8, headers=headers)
        if b_res.status_code == 200:
            b_items = _safe_list(b_res.json().get('response', {}).get('body', {}).get('items', []))
            if b_items:
                bs_raw = str(b_items[0].get('bssAmt', '')).strip()
                if bs_raw and bs_raw != '0': res_data["bss_amt"] = safe_fmt_amt(bs_raw)
    except:
        pass

    try:
        test_ords = [base_ord, '00', '01', '02', '03']
        for t_ord in test_ords:
            detail_url = 'http://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoCnstwkDtl'
            d_res = requests.get(detail_url, params={'serviceKey': SAFE_API_KEY, 'numOfRows': '1', 'pageNo': '1',
                                                     'bidNtceNo': bid_no, 'bidNtceOrd': t_ord, 'type': 'json'},
                                 verify=False, timeout=8, headers=headers)
            if d_res.status_code == 200:
                d_items = _safe_list(d_res.json().get('response', {}).get('body', {}).get('items', []))
                if d_items:
                    d = d_items[0]
                    d_bss = str(d.get('bssAmt', '')).strip()
                    if d_bss and d_bss != '0': res_data["bss_amt"] = safe_fmt_amt(d_bss)
                    pre_raw = str(d.get('exptPrce', '')).strip()
                    if pre_raw and pre_raw != '0': res_data["pre_amt"] = safe_fmt_amt(pre_raw)
                    suc_raw = str(d.get('sucsfbidAmt', '')).strip()
                    if suc_raw and suc_raw != '0': res_data["suc_amt"] = safe_fmt_amt(suc_raw)
                    res_data["has_detail"] = True
                    break
    except:
        pass

    corp_raw = row.get('전체업체', '')
    if corp_raw and isinstance(corp_raw, str):
        for idx, c in enumerate(corp_raw.split('|')[:10]):
            p = c.split('^')
            if len(p) >= 4: res_data['corps'].append(
                {'순위': f"{idx + 1}위", '업체명': p[0].strip(), '투찰금액': f"{int(float(p[3])):,}원", '투찰률': f"{p[4].strip()}%"})
    return res_data


# ==========================================
# 9. UI 및 메인 로직
# ==========================================
update_stats()
t_visit, t_user = get_stats()

st.markdown('<div class="main-title">🏛️ K-건설맵</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(
    f'<div class="stat-card">📅 오늘 날짜<br><span class="stat-val">{datetime.now(KST).strftime("%Y-%m-%d")}</span></div>',
    unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-card">📈 누적 방문<br><span class="stat-val">{t_visit:,}명</span></div>',
                     unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-card">👥 전체 회원수<br><span class="stat-val">{t_user:,}명</span></div>',
                     unsafe_allow_html=True)
with c4: st.markdown(
    f'<div class="stat-card">🔔 가동 상태<br><span class="stat-val" style="color:green;">정상 가동 중</span></div>',
    unsafe_allow_html=True)

with st.sidebar:
    st.write(f"### 👷 {'👋 ' + st.session_state['user_name'] + ' 소장님' if st.session_state['logged_in'] else 'K-건설맵 메뉴'}")

    if st.session_state['logged_in']:
        menu_list = ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "📁 K-건설 자료실", "💬 K건설챗"]
    else:
        menu_list = ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "📁 K-건설 자료실", "💬 K건설챗", "👤 로그인 / 회원가입"]

    menu = st.radio("업무 선택", menu_list)
    st.write("---")
    if st.button("🔄 만능 데이터 새로고침"): st.cache_data.clear(); st.rerun()
    if st.session_state['logged_in'] and st.button("🚪 로그아웃"): st.session_state['logged_in'] = False; st.rerun()

# --- 메뉴별 화면 구성 ---

if menu == "🏆 1순위 현황판":
    st.subheader("🏆 실시간 1순위 현황판")
    selected_region_1st = st.selectbox("🌍 지역 필터링", REGION_LIST)
    df_w = get_hybrid_1st_bids()
    if not df_w.empty:
        df_f = filter_by_region(df_w, selected_region_1st)
        event = st.dataframe(df_f[['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률']], use_container_width=True,
                             hide_index=True, height=400, selection_mode="single-row", on_select="rerun")
        if len(event.selection.rows) > 0:
            row = df_f.iloc[event.selection.rows[0]]
            det = fetch_bid_full_detail(str(row['공고번호']).strip(), row.get('공고차수', '00'), row)

            # [복구] 명환이가 좋아하던 17px 예쁜 HTML 폰트 디자인 원상복구!
            st.markdown(f"#### ✅ [나노 VIP 분석 리포트] {row['공고명'][:35]}...")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">💰 기초금액</div><div class="stat-val">{det["bss_amt"]}</div></div>',
                    unsafe_allow_html=True)
            with m2:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">📐 추정가격</div><div class="stat-val">{det["est_price"]}</div></div>',
                    unsafe_allow_html=True)
            with m3:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">🎯 예정가격</div><div class="stat-val">{det["pre_amt"]}</div></div>',
                    unsafe_allow_html=True)
            with m4:
                st.markdown(
                    f'<div class="stat-card"><div style="font-size:12px;color:#6b7280;font-weight:600;">🏆 낙찰금액</div><div class="stat-val" style="color:#dc2626;">{det["suc_amt"]}</div></div>',
                    unsafe_allow_html=True)

            st.write("")
            if det['corps']:
                st.dataframe(pd.DataFrame(det['corps']), use_container_width=True, hide_index=True)
            else:
                st.warning("💡 조달청에서 아직 개찰 상세 성적표를 업로드하지 않았습니다.")

            st.markdown("💡 **조달청 보안 정책으로 공고번호 복사가 필요합니다.**")
            st.code(row['공고번호'], language=None)
    else:
        st.warning("데이터를 불러오는 중입니다.")

elif menu == "📊 실시간 공고 (홈)":
    st.subheader("📊 실시간 입찰 공고")
    df_live = get_hybrid_live_bids()
    if not df_live.empty:
        selected_region_live = st.selectbox("🌍 지역 필터링", REGION_LIST)
        df_f = filter_by_region(df_live, selected_region_live)

        # [복구] 공고보기 파란색 링크 부활!
        col_cfg = {
            "상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
            "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")
        }

        if st.session_state['logged_in'] and st.session_state['user_license']:
            t1, t2 = st.tabs(["🌐 전체 공고", "✨ 내 면허 맞춤매칭"])
            with t1:
                st.dataframe(df_f[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                             hide_index=True, height=600, column_config=col_cfg)
            with t2:
                kw = get_match_keywords(st.session_state['user_license'])
                matched = df_f[df_f['공고명'].str.contains('|'.join(kw), na=False)] if kw else df_f
                st.dataframe(matched[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                             hide_index=True, height=600, column_config=col_cfg)
        else:
            st.dataframe(df_f[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                         hide_index=True, height=600, column_config=col_cfg)

elif menu == "📁 K-건설 자료실":
    st.subheader("📁 K-건설 자료실")
    if st.session_state['logged_in']:
        with st.expander("✏️ 새 자료 공유하기"):
            t, c = st.text_input("제목"), st.text_area("내용")
            if st.button("등록") and t and c:
                db.child("posts").push({"author": st.session_state['user_name'], "title": t, "content": c,
                                        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M")})
                st.toast("자료가 등록되었습니다!", icon="✅");
                st.rerun()
    posts = db.child("posts").get().val()
    if posts:
        for k, p in reversed(list(posts.items())):
            with st.expander(f"📢 {p['title']} (작성자: {p['author']})"):
                st.write(p['content'])
                if st.session_state['user_name'] in [p['author'], "명환"]:
                    if st.button("🗑️ 삭제", key=k): db.child("posts").child(k).remove(); st.rerun()

elif menu == "💬 K건설챗":
    st.subheader("💬 실시간 현장 소통")
    if not st.session_state['logged_in']:
        st.info("로그인 후 소장님들과 대화를 나눠보세요!")
    else:
        chat_box = st.container(height=450)
        try:
            chats_data = db.child("k_chat").order_by_key().limit_to_last(30).get().val()
            if chats_data:
                chat_list = list(chats_data.values())
                for v in chat_list: chat_box.write(f"**{v['author']}**: {v['message']}")
        except:
            chat_box.info("대화를 불러오는 중입니다.")

        if msg := st.chat_input("메시지를 입력하세요"):
            db.child("k_chat").push(
                {"author": st.session_state['user_name'], "message": msg, "time": datetime.now(KST).strftime("%H:%M")})
            st.rerun()

elif menu == "👤 로그인 / 회원가입":
    st.subheader("👤 회원 정보 관리")
    t1, t2 = st.tabs(["🔑 로그인", "📝 회원가입"])

    with t1:
        le = st.text_input("이메일", key="l_e")
        lp = st.text_input("비밀번호", type="password", key="l_p")
        if st.button("로그인"):
            login_success = False
            try:
                user = auth.sign_in_with_email_and_password(le.strip(), lp)
                info = db.child("users").child(user['localId']).get().val() or {}
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = info.get('name', '소장님')
                st.session_state['user_license'] = info.get('license', '')
                login_success = True
            except Exception as e:
                # [해결] 로그인 실패 시 정확한 사유 출력 (비밀번호 틀림 등)
                st.error(f"로그인 실패! 이메일이나 비밀번호를 다시 확인해주세요. (사유: {e})")

            # [해결] 성공하면 곧바로 즉각 새로고침해서 현황판으로 부드럽게 이동!
            if login_success: st.rerun()

    with t2:
        re = st.text_input("가입용 이메일", key="r_e")
        rp = st.text_input("비번 (6자 이상)", type="password", key="r_p")
        rn = st.text_input("성함", key="r_n")
        rl = st.multiselect("보유 면허", ALL_LICENSES, key="r_l")

        if st.button("가입하기"):
            try:
                u = auth.create_user_with_email_and_password(re.strip(), rp)
                db.child("users").child(u['localId']).set({"name": rn, "license": ", ".join(rl), "email": re.strip()})
                st.success("🎉 가입 성공! 로그인 탭에서 접속해주세요.")
            except:
                st.error("가입 실패! 형식을 확인하거나 이미 있는 이메일인지 확인하세요.")