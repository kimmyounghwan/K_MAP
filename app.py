import streamlit as st
import pandas as pd
import pyrebase
import urllib3
import urllib.parse
from datetime import datetime, timedelta, timezone
import time
import os
import math
import re

# ==========================================
# 1. 페이지 설정
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
        html, body { overflow-x: hidden; overscroll-behavior-x: none; touch-action: pan-y; }
        .stApp[data-teststate="running"] .stAppViewBlockContainer { filter: none !important; opacity: 1 !important; }
        [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
        .stApp { transition: none !important; }

        .main-title { background-color: #1e3a8a; color: white; border-radius: 10px; font-weight: 900; font-size: 28px; text-align: center; padding: 20px; margin-bottom: 25px; }
        .stat-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px; }
        .stat-label { font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 4px; }
        .stat-val { font-size: 17px; font-weight: 800; color: #1e3a8a; }
        .guide-box { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 5px; margin-bottom: 15px; font-size: 14px; color: #1e3a8a; }

        .hit-zone { background: linear-gradient(135deg, #fef3c7, #fde68a); border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; margin: 8px 0; text-align: center; font-weight: 800; font-size: 15px; color: #92400e; }
        .insight-box { background: #1e3a8a; color: white; border-radius: 10px; padding: 15px; margin: 8px 0; text-align: center; }
        .insight-title { font-size: 13px; font-weight: 700; margin-bottom: 6px; color: #93c5fd; }
        .insight-val { font-size: 22px; font-weight: 900; }
        .similar-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; margin: 5px 0; }
        .corp-rank1 { background: linear-gradient(135deg, #fef9c3, #fde047); border: 2px solid #eab308; border-radius: 8px; padding: 10px; margin: 4px 0; font-weight: 800; font-size: 14px; }
        .corp-rank-other { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px; margin: 3px 0; font-size: 13px; }
        .warn-box { background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px; padding: 10px; margin: 6px 0; color: #7f1d1d; font-weight: 700; }
        .ok-box { background: #f0fdf4; border: 2px solid #22c55e; border-radius: 8px; padding: 10px; margin: 6px 0; color: #14532d; font-weight: 700; }
        .diag-box { background: #1e3a8a; color: white; border-radius: 10px; padding: 16px; margin: 8px 0; text-align: center; }
        .diag-title { font-size: 13px; color: #93c5fd; font-weight: 700; margin-bottom: 4px; }
        .diag-val { font-size: 20px; font-weight: 900; }
        .calc-result { background: linear-gradient(135deg, #1e3a8a, #1e40af); color: white; border-radius: 12px; padding: 20px; margin: 10px 0; text-align: center; }
        .calc-price { font-size: 26px; font-weight: 900; color: #fde68a; }
        .calc-label { font-size: 13px; color: #93c5fd; margin-bottom: 6px; }
        .zoom-card { background: linear-gradient(135deg, #fef3c7, #fde68a); border: 2px solid #f59e0b; border-radius: 8px; padding: 10px; margin: 4px 0; text-align: center; font-weight: 800; font-size: 14px; color: #92400e; }
    </style>
""", unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))

# ==========================================
# 2. 파이어베이스 셋팅
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

for k, v in [('logged_in', False), ('user_name', ""), ('user_license', ""),
              ('user_phone', ""), ('localId', ""), ('idToken', "")]:
    if k not in st.session_state:
        st.session_state[k] = v


# ==========================================
# 3. 3년치 마스터 데이터 로딩
# ==========================================
@st.cache_data(show_spinner=False)
def load_master_data():
    file_path = "bid_data_3years.zip"
    if not os.path.exists(file_path):
        st.sidebar.error("🚨 서버 오류: 3년 치 CSV 파일을 찾을 수 없습니다!")
        return None
    try:
        return pd.read_csv(file_path, compression='zip', encoding='utf-8-sig', low_memory=False)
    except Exception as e1:
        try:
            return pd.read_csv(file_path, compression='zip', encoding='cp949', low_memory=False)
        except Exception as e2:
            st.sidebar.error(f"🚨 CSV 읽기 실패!\n원인1: {e1}\n원인2: {e2}")
            return None


big_data = load_master_data()


# ==========================================
# 4. 방문 카운팅
# ==========================================
def update_stats():
    if 'visited' not in st.session_state:
        try:
            curr = db.child("stats").child("total_visits").get().val()
            if curr is None: curr = 1828
            db.child("stats").update({"total_visits": curr + 1})
            st.session_state['visited'] = True
        except Exception:
            pass


def get_stats():
    try:
        t_v = db.child("stats").child("total_visits").get().val() or 1828
        u_v = db.child("users").get().val()
        return t_v, len(u_v) if u_v else 0
    except Exception:
        return 1828, 0


# ==========================================
# 5. 유틸리티 함수
# ==========================================
REGION_LIST = ["전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
               "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
ALL_LICENSES = ["[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업",
                "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업", "[전문] 철근·콘크리트공사업",
                "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업"]


def filter_by_region(df, sel):
    if sel == "전국(전체)": return df
    rk = {
        "서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"],
        "광주": ["광주"], "대전": ["대전"], "울산": ["울산"], "세종": ["세종"],
        "경기": ["경기", "경기도"], "강원": ["강원", "강원도"],
        "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
        "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"],
        "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"], "제주": ["제주"]
    }
    pat = '|'.join(rk.get(sel, [sel]))
    return df[df['발주기관'].str.contains(pat, na=False) | df['공고명'].str.contains(pat, na=False)]


def raw_to_int(raw) -> int:
    if raw is None: return 0
    r = str(raw).strip().replace(',', '').replace('원', '').replace('%', '')
    try:
        return int(float(r))
    except:
        return 0


def to_float_rate(val):
    try:
        return float(str(val).replace('%', '').strip())
    except:
        return None


def get_rate_col(df):
    return '사정률' if '사정률' in df.columns else '투찰률'


def get_match_keywords(lic):
    k = []
    if "토목" in lic: k.extend(["토목", "도로", "포장", "하천", "교량", "정비", "관로", "상수도", "하수도"])
    if "건축" in lic: k.extend(["건축", "신축", "증축", "보수", "인테리어", "방수", "도장"])
    if "조경" in lic: k.extend(["조경", "식재", "공원", "수목"])
    if "전기" in lic: k.extend(["전기", "배전", "가로등", "CCTV"])
    if "통신" in lic: k.extend(["통신", "네트워크", "방송"])
    if "소방" in lic: k.extend(["소방", "화재", "스프링클러"])
    if "철근" in lic or "콘크리트" in lic: k.extend(["철콘", "구조물", "옹벽", "배수", "기초"])
    if "지반" in lic or "포장" in lic: k.extend(["지반", "포장", "아스팔트", "토공"])
    if "실내건축" in lic: k.extend(["실내건축", "인테리어", "내장", "칸막이"])
    return list(set(k))


# ==========================================
# 6. ★ 5대 팩트 분석 엔진 ★
# ==========================================

def engine_heatmap(inst_name, bd):
    if bd is None or bd.empty: return None
    df = bd[bd['발주기관'] == inst_name].copy()
    if df.empty: return None
    rate_col = get_rate_col(df)
    df['rate_f'] = df[rate_col].apply(to_float_rate)
    df = df.dropna(subset=['rate_f'])
    if df.empty: return None
    df['구간'] = (df['rate_f'] // 0.5 * 0.5).apply(lambda x: f"{x:.1f}~{x+0.5:.1f}%")
    zone_counts = df['구간'].value_counts().sort_values(ascending=False)
    return {
        'zone_counts': zone_counts,
        'avg': round(df['rate_f'].mean(), 2),
        'std': round(df['rate_f'].std(), 2),
        'min': round(df['rate_f'].min(), 2),
        'max': round(df['rate_f'].max(), 2),
        'top_zone': zone_counts.index[0],
        'top_count': int(zone_counts.iloc[0]),
        'total': len(df),
        'rate_col': rate_col
    }


def engine_dominant(inst_name, bd):
    if bd is None or bd.empty: return None
    df = bd[bd['발주기관'] == inst_name].copy()
    if df.empty or '1순위업체' not in df.columns: return None
    total = len(df)
    corp_counts = df['1순위업체'].value_counts()
    top_corp = corp_counts.index[0]
    top_count = int(corp_counts.iloc[0])
    monopoly_rate = round(top_count / total * 100, 1)
    recent_top = pd.Series(dtype=int)
    if '날짜' in df.columns:
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=365)
        recent = df[df['dt'] >= cutoff]
        if not recent.empty:
            recent_top = recent['1순위업체'].value_counts().head(5)
    return {
        'corp_counts': corp_counts.head(7),
        'top_corp': top_corp,
        'top_count': top_count,
        'monopoly_rate': monopoly_rate,
        'total': total,
        'recent_top': recent_top
    }


def engine_pattern(inst_name, bd):
    if bd is None or bd.empty: return None
    df = bd[bd['발주기관'] == inst_name].copy()
    if df.empty: return None
    monthly = pd.Series(dtype=int)
    yearly = pd.Series(dtype=int)
    peak_month = None
    if '날짜' in df.columns:
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df2 = df.dropna(subset=['dt'])
        if not df2.empty:
            monthly = df2['dt'].dt.month.value_counts().sort_index()
            yearly = df2['dt'].dt.year.value_counts().sort_index()
            peak_month = int(monthly.idxmax())
    avg_per_year = round(len(df) / max(len(yearly), 1), 1)
    amt_stats = {}
    for c in ['투찰금액', '예산금액']:
        if c in df.columns:
            df['amt_v'] = df[c].apply(raw_to_int)
            df_a = df[df['amt_v'] > 0]
            if not df_a.empty:
                amt_stats = {
                    'col': c,
                    'avg': int(df_a['amt_v'].mean()),
                    'min': int(df_a['amt_v'].min()),
                    'max': int(df_a['amt_v'].max()),
                    'median': int(df_a['amt_v'].median()),
                }
            break
    return {
        'total': len(df), 'monthly': monthly, 'yearly': yearly,
        'peak_month': peak_month, 'avg_per_year': avg_per_year, 'amt_stats': amt_stats
    }


def engine_similar(notice_name, inst_name, bd, top_n=7):
    if bd is None or bd.empty or not notice_name: return None
    stopwords = {'공사', '설치', '사업', '시공', '및', '기타', '위한', '에', '의', '을', '를'}
    keywords = [w for w in re.findall(r'[가-힣]{2,}', notice_name) if w not in stopwords]
    if not keywords: return None
    pattern = '|'.join(keywords[:5])
    matched = bd[bd['공고명'].str.contains(pattern, na=False)].copy()
    if matched.empty: return None
    matched['same_inst'] = 0
    if '발주기관' in matched.columns and inst_name:
        matched['same_inst'] = (matched['발주기관'] == inst_name).astype(int)
    if '날짜' in matched.columns:
        matched['dt'] = pd.to_datetime(matched['날짜'], errors='coerce')
        matched = matched.sort_values(['same_inst', 'dt'], ascending=[False, False])
    result = matched.head(top_n).copy()
    rate_col = get_rate_col(result)
    result['rate_f'] = result[rate_col].apply(to_float_rate)
    valid = result.dropna(subset=['rate_f'])
    rate_dist = None
    if not valid.empty:
        valid2 = valid.copy()
        valid2['구간'] = (valid2['rate_f'] // 0.5 * 0.5).apply(lambda x: f"{x:.1f}~{x+0.5:.1f}%")
        rate_dist = valid2['구간'].value_counts()
    return {
        'cases': result, 'rate_col': rate_col,
        'keywords': keywords[:5], 'rate_dist': rate_dist, 'valid_count': len(valid)
    }


def engine_self_diagnosis(corp_name, bd):
    if bd is None or bd.empty or not corp_name: return None
    df = bd[bd['1순위업체'].str.contains(corp_name, na=False)].copy()
    if df.empty: return None
    total_wins = len(df)
    region_wins = {}
    for reg in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
                "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
        mask = df['발주기관'].str.contains(reg, na=False) | df['공고명'].str.contains(reg, na=False)
        cnt = int(mask.sum())
        if cnt > 0:
            region_wins[reg] = cnt
    region_wins = dict(sorted(region_wins.items(), key=lambda x: x[1], reverse=True))
    best_month = None
    monthly = pd.Series(dtype=int)
    yearly = pd.Series(dtype=int)
    if '날짜' in df.columns:
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df2 = df.dropna(subset=['dt'])
        if not df2.empty:
            monthly = df2['dt'].dt.month.value_counts().sort_index()
            yearly = df2['dt'].dt.year.value_counts().sort_index()
            best_month = int(monthly.idxmax())
    rate_col = get_rate_col(df)
    df['rate_f'] = df[rate_col].apply(to_float_rate)
    df_r = df.dropna(subset=['rate_f'])
    rate_dist = pd.Series(dtype=int)
    avg_rate = None
    if not df_r.empty:
        avg_rate = round(df_r['rate_f'].mean(), 2)
        df_r2 = df_r.copy()
        df_r2['구간'] = (df_r2['rate_f'] // 0.5 * 0.5).apply(lambda x: f"{x:.1f}~{x+0.5:.1f}%")
        rate_dist = df_r2['구간'].value_counts()
    top_inst = df['발주기관'].value_counts().head(5) if '발주기관' in df.columns else pd.Series()
    return {
        'corp_name': corp_name, 'total_wins': total_wins,
        'region_wins': region_wins, 'best_month': best_month,
        'monthly': monthly, 'yearly': yearly,
        'avg_rate': avg_rate, 'rate_dist': rate_dist,
        'top_inst': top_inst, 'rate_col': rate_col
    }


# ==========================================
# ★ 추가 1: 투찰가 계산기 엔진
#   - 1단계: 0.1% 단위 큰 그림 (핫존 표시)
#   - 2단계: 핫존 클릭 시 0.01% 단위 돋보기 모드
# ==========================================
def engine_bid_calculator(inst_name, base_price, bd):
    """0.1% 단위 투찰률 분포 + 추천가 계산"""
    if bd is None or bd.empty or not inst_name or not base_price:
        return None
    df = bd[bd['발주기관'] == inst_name].copy()
    if df.empty:
        return None
    rate_col = get_rate_col(df)
    df['rate_f'] = df[rate_col].apply(to_float_rate)
    df = df.dropna(subset=['rate_f'])
    if df.empty:
        return None
    # 0.1% 단위 구간 (1단계: 큰 그림)
    df['구간_01'] = (df['rate_f'] // 0.1 * 0.1).round(1)
    zone_01 = df['구간_01'].value_counts().sort_values(ascending=False)
    top5     = zone_01.head(5)
    best_rate = float(top5.index[0])
    recommended = int(base_price * best_rate / 100)
    avg_rate = round(df['rate_f'].mean(), 2)
    mid_rate = round(df['rate_f'].median(), 2)
    avg_price = int(base_price * avg_rate / 100)
    mid_price = int(base_price * mid_rate / 100)
    return {
        'df'         : df,
        'total'      : len(df),
        'rate_col'   : rate_col,
        'zone_01'    : zone_01,
        'top5'       : top5,
        'best_rate'  : best_rate,
        'recommended': recommended,
        'avg_rate'   : avg_rate,
        'mid_rate'   : mid_rate,
        'avg_price'  : avg_price,
        'mid_price'  : mid_price,
    }


def engine_zoom(df, hot_rate, base_price):
    """2단계: 0.01% 돋보기 — hot_rate 구간 내 세분화"""
    lower = round(hot_rate, 1)
    upper = round(lower + 0.1, 1)
    mask  = (df['rate_f'] >= lower) & (df['rate_f'] < upper)
    sub   = df[mask].copy()
    if sub.empty:
        return None
    sub['구간_001'] = (sub['rate_f'] // 0.01 * 0.01).round(2)
    zone_001 = sub['구간_001'].value_counts().sort_values(ascending=False)
    best_001 = float(zone_001.index[0])
    return {
        'zone_001'  : zone_001,
        'best_001'  : best_001,
        'best_price': int(base_price * best_001 / 100),
        'total_sub' : len(sub),
        'lower'     : lower,
        'upper'     : upper,
    }


def render_bid_calculator():
    """★ 투찰가 계산기 화면 ★"""
    st.markdown("#### 🧮 실제 데이터 기반 투찰가 계산기")
    st.markdown(
        '<div class="guide-box">'
        '📌 <b>1단계</b>: 0.1% 단위로 발주기관의 낙찰 핫존을 찾습니다.<br>'
        '📌 <b>2단계</b>: 핫존을 선택하면 0.01% 단위 돋보기 분석 + 차트 + 추천 투찰가가 표시됩니다.<br>'
        '추정 없음. 3년 실제 낙찰 데이터만 사용합니다.'
        '</div>', unsafe_allow_html=True)

    if big_data is None or big_data.empty:
        st.info("3년 마스터 데이터가 없습니다.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        inst_input = st.text_input("🏛️ 발주기관명 입력", placeholder="예: 여수시, 전남도청", key="calc_inst")
    with col2:
        base_input = st.text_input("💰 기초금액 입력 (원)", placeholder="예: 150000000", key="calc_base")

    if not (inst_input and base_input):
        return

    base_clean = base_input.replace(',', '').replace('원', '').strip()
    try:
        base_price = int(float(base_clean))
    except:
        st.error("기초금액을 숫자로 입력해주세요. 예: 150000000")
        return

    matching = big_data[big_data['발주기관'].str.contains(inst_input, na=False)]['발주기관'].value_counts()
    if matching.empty:
        st.warning(f"'{inst_input}' 발주기관 데이터가 없습니다.")
        return

    inst_select = st.selectbox(
        f"검색된 기관 {len(matching)}개",
        matching.index.tolist(),
        format_func=lambda x: f"{x} ({matching[x]}건)",
        key="calc_inst_select"
    )

    r = engine_bid_calculator(inst_select, base_price, big_data)
    if r is None:
        st.warning("해당 발주기관의 데이터가 부족합니다.")
        return

    st.markdown("---")
    st.markdown(f"**'{inst_select}' 3년 {r['total']}건 실제 데이터 분석 결과**")

    # 추천가 3종
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="calc-result">'
            f'<div class="calc-label">⭐ 최다발생 구간 추천가</div>'
            f'<div class="calc-price">{r["recommended"]:,}원</div>'
            f'<div style="font-size:12px;color:#93c5fd;margin-top:4px;">투찰률 {r["best_rate"]}%</div>'
            f'</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="calc-result">'
            f'<div class="calc-label">📊 평균 투찰률 기준</div>'
            f'<div class="calc-price">{r["avg_price"]:,}원</div>'
            f'<div style="font-size:12px;color:#93c5fd;margin-top:4px;">투찰률 {r["avg_rate"]}%</div>'
            f'</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div class="calc-result">'
            f'<div class="calc-label">📈 중간값 기준</div>'
            f'<div class="calc-price">{r["mid_price"]:,}원</div>'
            f'<div style="font-size:12px;color:#93c5fd;margin-top:4px;">투찰률 {r["mid_rate"]}%</div>'
            f'</div>', unsafe_allow_html=True)

    # ── 1단계: 0.1% 큰 그림 ──
    st.markdown("---")
    st.markdown("### 📊 1단계 — 0.1% 단위 핫존 분석")
    max_cnt = int(r['top5'].iloc[0])
    for rate_val, cnt in r['top5'].items():
        bar_w   = int(cnt / max_cnt * 100)
        is_best = (rate_val == r['best_rate'])
        color   = "#f59e0b" if is_best else "#3b82f6"
        star    = " ⭐ 핫존" if is_best else ""
        price   = int(base_price * rate_val / 100)
        st.markdown(
            f"""<div style="margin:5px 0;display:flex;align-items:center;gap:8px;">
                <span style="font-size:13px;font-weight:{'900' if is_best else '500'};width:90px;flex-shrink:0;">{rate_val}%{star}</span>
                <div style="background:{color};width:{bar_w}%;height:18px;border-radius:3px;min-width:3px;"></div>
                <span style="font-size:12px;font-weight:700;">{cnt}회 | {price:,}원</span>
            </div>""", unsafe_allow_html=True)

    # ── 2단계: 0.01% 돋보기 모드 ──
    st.markdown("---")
    st.markdown("### 🔬 2단계 — 0.01% 돋보기 모드")
    st.markdown("👇 **핫존 구간을 선택하면 추천 투찰가가 바로 나옵니다.**")

    zone_options = [f"{v}%" for v in r['zone_01'].head(10).index.tolist()]
    selected_zone = st.selectbox("🎯 분석할 핫존 구간 선택 (클릭하면 추천 투찰가 즉시 확인)", zone_options, key="zoom_zone")

    if selected_zone:
        hot_rate = float(selected_zone.replace('%', ''))
        zr = engine_zoom(r['df'], hot_rate, base_price)
        if zr is None:
            st.info("해당 구간의 데이터가 없습니다.")
        else:
            # ★ 추천 투찰가 강조 박스
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#f59e0b,#d97706);color:white;border-radius:12px;'
                f'padding:18px;margin:10px 0;text-align:center;">'
                f'<div style="font-size:13px;font-weight:700;margin-bottom:6px;">🔬 {zr["lower"]}% ~ {zr["upper"]}% 구간 돋보기 분석 ({zr["total_sub"]}건)</div>'
                f'<div style="font-size:14px;margin-bottom:4px;">최다발생 구간: <b>{zr["best_001"]}%</b></div>'
                f'<div style="font-size:28px;font-weight:900;color:#1e3a8a;">⭐ 추천 투찰가</div>'
                f'<div style="font-size:32px;font-weight:900;margin-top:4px;">{zr["best_price"]:,}원</div>'
                f'<div style="font-size:12px;margin-top:6px;opacity:0.9;">투찰률 {zr["best_001"]}% × 기초금액 {base_price:,}원</div>'
                f'</div>', unsafe_allow_html=True)

            # ★ 0.01% 단위 차트
            st.markdown(f"**📊 0.01% 단위 상세 분포** (상위 10개) — 원단위 금액 표시")
            max_z = int(zr['zone_001'].iloc[0]) if not zr['zone_001'].empty else 1
            for rate_val, cnt in zr['zone_001'].head(10).items():
                bar_w   = int(cnt / max_z * 100)
                is_best = (rate_val == zr['best_001'])
                color   = "#f59e0b" if is_best else "#10b981"
                star    = " ⭐ 추천" if is_best else ""
                price   = int(base_price * rate_val / 100)
                pct_of_total = round(cnt / zr['total_sub'] * 100, 1)
                st.markdown(
                    f"""<div style="margin:5px 0;display:flex;align-items:center;gap:8px;">
                        <span style="font-size:13px;font-weight:{'900' if is_best else '500'};width:100px;flex-shrink:0;color:{'#d97706' if is_best else 'inherit'};">{rate_val}%{star}</span>
                        <div style="background:{color};width:{bar_w}%;height:18px;border-radius:3px;min-width:3px;"></div>
                        <span style="font-size:12px;font-weight:700;">{cnt}회({pct_of_total}%) | <b>{price:,}원</b></span>
                    </div>""", unsafe_allow_html=True)

            # ★ 전체 추천가 정리 테이블
            st.markdown("---")
            st.markdown("**📋 투찰가 추천 정리**")
            tbl_data = []
            zone_001_idx = list(zr['zone_001'].head(5).index)
            for rate_val, cnt in zr['zone_001'].head(5).items():
                price = int(base_price * rate_val / 100)
                is_best = (rate_val == zr['best_001'])
                rank_str = "⭐ 1위 추천" if is_best else f"{zone_001_idx.index(rate_val)+1}위"
                tbl_data.append({
                    '순위': rank_str,
                    '투찰률': f"{rate_val}%",
                    '투찰금액 (원단위)': f"{price:,}원",
                    '낙찰 빈도': f"{cnt}회"
                })
            st.dataframe(pd.DataFrame(tbl_data), use_container_width=True, hide_index=True)

    st.caption("* 3년 실제 낙찰 데이터 기준. 투찰 결정은 본인 판단으로 하세요.")


# ==========================================
# 7. 분석 렌더 함수
# ==========================================

def render_heatmap(inst_name):
    r = engine_heatmap(inst_name, big_data)
    if r is None:
        st.info(f"'{inst_name}'의 투찰률 데이터가 없습니다.")
        return
    st.markdown(f"**'{inst_name}' 최근 3년 {r['rate_col']} 구간 분포** (총 {r['total']}건 실제 데이터)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균", f"{r['avg']}%")
    c2.metric("표준편차", f"±{r['std']}%")
    c3.metric("최솟값", f"{r['min']}%")
    c4.metric("최댓값", f"{r['max']}%")
    st.markdown("---")
    st.markdown("**📊 구간별 낙찰 집중도** (0.5% 단위, 상위 12개)")
    top12 = r['zone_counts'].head(12)
    max_cnt = int(top12.iloc[0]) if not top12.empty else 1
    for zone, cnt in top12.items():
        bar_w = int(cnt / max_cnt * 100)
        is_top = (zone == r['top_zone'])
        color = "#f59e0b" if is_top else "#3b82f6"
        star = " ⭐ 최다발생" if is_top else ""
        st.markdown(
            f"""<div style="margin:4px 0;display:flex;align-items:center;gap:8px;">
                <span style="font-size:13px;font-weight:{'900' if is_top else '500'};width:145px;flex-shrink:0;">{zone}{star}</span>
                <div style="background:{color};width:{bar_w}%;height:18px;border-radius:3px;min-width:3px;"></div>
                <span style="font-size:13px;font-weight:700;">{cnt}회 ({round(cnt/r['total']*100,1)}%)</span>
            </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        f'<div class="hit-zone">📌 {r["rate_col"]} 최다 발생 구간: <b>{r["top_zone"]}</b>'
        f' — {r["top_count"]}회 / {r["total"]}건 중 {round(r["top_count"]/r["total"]*100,1)}% 집중</div>',
        unsafe_allow_html=True)
    st.caption(f"* 3년 실제 낙찰 데이터 기준 {r['rate_col']} 분포입니다. 추정 없음.")


def render_dominant(inst_name):
    r = engine_dominant(inst_name, big_data)
    if r is None:
        st.info(f"'{inst_name}'의 낙찰 데이터가 없습니다.")
        return
    st.markdown(f"**'{inst_name}' 최근 3년 낙찰 업체 분포** (총 {r['total']}건 실제 데이터)")
    monopoly = r['monopoly_rate']
    if monopoly >= 40:
        st.markdown(f'<div class="warn-box">⚠️ 독식 경보! <b>{r["top_corp"]}</b>이 전체의 <b>{monopoly}%</b> 독식 중</div>', unsafe_allow_html=True)
    elif monopoly >= 20:
        st.warning(f"🔶 `{r['top_corp']}`이 **{monopoly}%** 점유 중 — 강한 고정 경쟁자 존재")
    else:
        st.markdown(f'<div class="ok-box">✅ 특정 독식 업체 없음 — 비교적 열린 경쟁 구도 ({r["top_corp"]} {monopoly}% 점유)</div>', unsafe_allow_html=True)
    medals = ["🥇", "🥈", "🥉", "4위", "5위", "6위", "7위"]
    for i, (corp, cnt) in enumerate(r['corp_counts'].items()):
        pct = round(cnt / r['total'] * 100, 1)
        if i == 0:
            st.markdown(f'<div class="corp-rank1">{medals[i]} {corp} — {cnt}회 ({pct}%)</div>', unsafe_allow_html=True)
        else:
            m = medals[i] if i < 7 else f"{i+1}위"
            st.markdown(f'<div class="corp-rank-other">{m} {corp} — {cnt}회 ({pct}%)</div>', unsafe_allow_html=True)
    if not r['recent_top'].empty:
        st.markdown("---")
        st.markdown("**📅 최근 1년 낙찰 TOP 5**")
        for corp, cnt in r['recent_top'].items():
            st.info(f"**{corp}**: {cnt}회")


def render_pattern(inst_name):
    r = engine_pattern(inst_name, big_data)
    if r is None:
        st.info(f"'{inst_name}'의 발주 패턴 데이터가 없습니다.")
        return
    st.markdown(f"**'{inst_name}' 발주 패턴** (총 {r['total']}건 실제 데이터)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="insight-box"><div class="insight-title">📅 연평균 발주 건수</div><div class="insight-val">{r["avg_per_year"]}건/년</div></div>', unsafe_allow_html=True)
    with c2:
        peak = f"{r['peak_month']}월" if r['peak_month'] else "-"
        st.markdown(f'<div class="insight-box"><div class="insight-title">🔥 발주 집중 월</div><div class="insight-val">{peak}</div></div>', unsafe_allow_html=True)
    if not r['monthly'].empty:
        st.markdown("**📊 월별 발주 건수 (3년 합산)**")
        month_labels = {1:"1월",2:"2월",3:"3월",4:"4월",5:"5월",6:"6월",
                        7:"7월",8:"8월",9:"9월",10:"10월",11:"11월",12:"12월"}
        max_m = int(r['monthly'].max())
        for m in range(1, 13):
            cnt = int(r['monthly'].get(m, 0))
            bar_w = int(cnt / max_m * 100) if max_m > 0 else 0
            is_peak = (m == r['peak_month'])
            color = "#ef4444" if is_peak else "#6366f1"
            label = " 🔥" if is_peak else ""
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:42px;flex-shrink:0;font-weight:{'800' if is_peak else '500'}">{month_labels[m]}{label}</span>
                    <div style="background:{color};width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    if not r['yearly'].empty:
        st.markdown("---")
        st.markdown("**📈 연도별 발주 건수**")
        cols = st.columns(len(r['yearly']))
        for i, (yr, cnt) in enumerate(r['yearly'].items()):
            cols[i].metric(f"{yr}년", f"{cnt}건")
    if r['amt_stats']:
        a = r['amt_stats']
        st.markdown("---")
        st.markdown(f"**💰 실제 {a['col']} 규모 분포**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("평균", f"{a['avg']//10000:,}만원")
        col2.metric("중간값", f"{a['median']//10000:,}만원")
        col3.metric("최소", f"{a['min']//10000:,}만원")
        col4.metric("최대", f"{a['max']//10000:,}만원")
        st.caption(f"* 실제 {a['col']} 기준. 추정 없음.")


def render_similar(notice_name, inst_name):
    r = engine_similar(notice_name, inst_name, big_data)
    if r is None:
        st.info("유사한 과거 공고를 찾을 수 없습니다.")
        return
    st.markdown(f"**검색 키워드:** `{'`, `'.join(r['keywords'])}`")
    st.markdown(f"유사 과거 사례 **{len(r['cases'])}건** 검색됨")
    rate_col = r['rate_col']
    for _, row in r['cases'].iterrows():
        same_tag = " 🏛️ 동일기관" if str(row.get('발주기관', '')) == inst_name else ""
        rate_val = row.get(rate_col, '-')
        date_val = str(row.get('날짜', '-'))[:10]
        corp_val = row.get('1순위업체', '-')
        name_val = str(row.get('공고명', ''))[:50]
        amt_val  = row.get('투찰금액', '')
        amt_str  = f"{raw_to_int(amt_val):,}원" if amt_val and raw_to_int(amt_val) > 0 else '-'
        st.markdown(
            f'<div class="similar-card">'
            f'<div style="font-size:11px;color:#6b7280;">{date_val} | {row.get("발주기관","")}{same_tag}</div>'
            f'<div style="font-size:13px;font-weight:700;margin:3px 0;">{name_val}</div>'
            f'<span style="color:#dc2626;font-weight:800;">1순위: {corp_val}</span>'
            f' &nbsp;|&nbsp; <span style="color:#1e3a8a;font-weight:800;">{rate_col}: {rate_val}</span>'
            f' &nbsp;|&nbsp; <span style="color:#374151;">낙찰금액: {amt_str}</span>'
            f'</div>', unsafe_allow_html=True)
    if r['rate_dist'] is not None and not r['rate_dist'].empty:
        st.markdown("---")
        st.markdown(f"**📊 유사 공고 {rate_col} 분포**")
        max_cnt = int(r['rate_dist'].iloc[0])
        for zone, cnt in r['rate_dist'].items():
            bar_w = int(cnt / max_cnt * 100)
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:130px;flex-shrink:0;">{zone}</span>
                    <div style="background:#10b981;width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
        top_zone = r['rate_dist'].index[0]
        st.markdown(
            f'<div class="hit-zone">📌 유사 공고 {rate_col} 최다 발생 구간: <b>{top_zone}</b> ({r["valid_count"]}건 실제 데이터 기준)</div>',
            unsafe_allow_html=True)
    st.caption("* 공고명 키워드 기반 실제 낙찰 사례. 추정 없음.")


def render_self_diagnosis(corp_name):
    r = engine_self_diagnosis(corp_name, big_data)
    if r is None:
        st.warning(f"'{corp_name}' 업체의 3년 낙찰 이력이 없습니다.")
        return
    st.markdown(f"**'{r['corp_name']}' 3년 낙찰 팩트 리포트**")
    c1, c2, c3 = st.columns(3)
    best_reg = list(r['region_wins'].keys())[0] if r['region_wins'] else "-"
    best_cnt = list(r['region_wins'].values())[0] if r['region_wins'] else 0
    avg_r    = f"{r['avg_rate']}%" if r['avg_rate'] else "-"
    c1.markdown(f'<div class="diag-box"><div class="diag-title">🏆 3년 총 낙찰 건수</div><div class="diag-val">{r["total_wins"]}건</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="diag-box"><div class="diag-title">📍 최강 지역</div><div class="diag-val">{best_reg} ({best_cnt}건)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="diag-box"><div class="diag-title">🎯 평균 낙찰 {r["rate_col"]}</div><div class="diag-val">{avg_r}</div></div>', unsafe_allow_html=True)
    if r['region_wins']:
        st.markdown("---")
        st.markdown("**📍 지역별 낙찰 건수**")
        max_r = max(r['region_wins'].values())
        for reg, cnt in r['region_wins'].items():
            bar_w = int(cnt / max_r * 100)
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:13px;width:40px;flex-shrink:0;font-weight:700;">{reg}</span>
                    <div style="background:#3b82f6;width:{bar_w}%;height:16px;border-radius:3px;min-width:3px;"></div>
                    <span style="font-size:13px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    if not r['rate_dist'].empty:
        st.markdown("---")
        st.markdown(f"**🎯 낙찰 {r['rate_col']} 구간 분포**")
        max_rd = int(r['rate_dist'].iloc[0])
        for zone, cnt in r['rate_dist'].head(10).items():
            bar_w = int(cnt / max_rd * 100)
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:130px;flex-shrink:0;">{zone}</span>
                    <div style="background:#8b5cf6;width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    if not r['top_inst'].empty:
        st.markdown("---")
        st.markdown("**🏛️ 주요 낙찰 발주기관 TOP 5**")
        for inst, cnt in r['top_inst'].items():
            st.info(f"**{inst}**: {cnt}건")
    if not r['yearly'].empty:
        st.markdown("---")
        st.markdown("**📈 연도별 낙찰 추이**")
        cols = st.columns(len(r['yearly']))
        for i, (yr, cnt) in enumerate(r['yearly'].items()):
            cols[i].metric(f"{yr}년", f"{cnt}건")
    if r['best_month'] and not r['monthly'].empty:
        st.markdown("---")
        st.markdown(f"**📅 월별 낙찰 건수** (집중 월: {r['best_month']}월)")
        month_labels = {1:"1월",2:"2월",3:"3월",4:"4월",5:"5월",6:"6월",
                        7:"7월",8:"8월",9:"9월",10:"10월",11:"11월",12:"12월"}
        max_m = int(r['monthly'].max())
        for m in range(1, 13):
            cnt   = int(r['monthly'].get(m, 0))
            bar_w = int(cnt / max_m * 100) if max_m > 0 else 0
            is_best = (m == r['best_month'])
            color = "#f59e0b" if is_best else "#94a3b8"
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:40px;flex-shrink:0;font-weight:{'800' if is_best else '400'}">{month_labels[m]}</span>
                    <div style="background:{color};width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    st.caption("* 3년 실제 낙찰 데이터 기준. 추정 없음.")


# ==========================================
# 8. Firebase 데이터 로딩 [트래픽 다이어트 + 만능 날짜 번역기 적용]
# 날짜 기준 최근 30일치만 읽어서 요금 절감 및 날짜 빈칸 현상 해결
# ==========================================
DISPLAY_DAYS = 15  # 표시할 최근 일수


def _parse_dt(val):
    """날짜 문자열 → pandas Timestamp (만능 번역기)"""
    if not val or str(val).strip() in ('', 'nan', 'None', '-'):
        return pd.NaT
    s = str(val).strip()
    # 기호 싹 지우고 숫자만 남김
    s = s.replace('-', '').replace(':', '').replace(' ', '').replace('.', '')
    try:
        if len(s) >= 12:
            return pd.to_datetime(s[:12], format='%Y%m%d%H%M')
        elif len(s) == 8:
            return pd.to_datetime(s, format='%Y%m%d')
        else:
            return pd.NaT
    except:
        return pd.NaT


@st.cache_data(ttl=60, show_spinner=False)
def get_hybrid_1st_bids():
    """1순위: 날짜 기준 최근 30일치만 읽기 (요금 절감)"""
    try:
        cutoff_str = (datetime.now(KST).replace(tzinfo=None)
                      - timedelta(days=DISPLAY_DAYS)).strftime('%Y-%m-%d')
        db_data = (db.child("archive_1st")
                     .order_by_child("날짜")
                     .start_at(cutoff_str)
                     .get().val()) or {}
        db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    except Exception:
        # 인덱스 미설정 시 fallback
        try:
            db_data  = db.child("archive_1st").order_by_key().limit_to_last(2000).get().val() or {}
            db_items = list(db_data.values()) if isinstance(db_data, dict) else []
        except Exception:
            db_items = []

    if not db_items:
        return pd.DataFrame()
    df = pd.DataFrame(db_items)
    if df.empty or '공고번호' not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['공고번호']).copy()
    df['dt'] = df['날짜'].apply(_parse_dt) if '날짜' in df.columns else pd.NaT
    df = df.sort_values(by='dt', ascending=False, na_position='last')
    df['날짜'] = df['dt'].apply(lambda x: x.strftime('%m-%d %H:%M') if pd.notna(x) else '-')
    df = df.drop(columns=['dt'])
    return df


@st.cache_data(ttl=180, show_spinner=False)
def get_hybrid_live_bids():
    """실시간 공고: 날짜 기준 최근 30일치만 읽기 (요금 절감)"""
    try:
        cutoff_str = (datetime.now(KST).replace(tzinfo=None)
                      - timedelta(days=DISPLAY_DAYS)).strftime('%Y-%m-%d')
        db_data = (db.child("archive_live")
                     .order_by_child("공고일자")
                     .start_at(cutoff_str)
                     .get().val()) or {}
        db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    except Exception:
        # 인덱스 미설정 시 fallback
        try:
            db_data  = db.child("archive_live").order_by_key().limit_to_last(2000).get().val() or {}
            db_items = list(db_data.values()) if isinstance(db_data, dict) else []
        except Exception:
            db_items = []

    if not db_items:
        return pd.DataFrame()
    df = pd.DataFrame(db_items)
    if df.empty or '공고번호' not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['공고번호']).copy()
    df['dt'] = df['공고일자'].apply(_parse_dt) if '공고일자' in df.columns else pd.NaT
    df = df.sort_values(by='dt', ascending=False, na_position='last')
    df['공고일자'] = df['dt'].apply(lambda x: x.strftime('%m-%d %H:%M') if pd.notna(x) else '-')
    df = df.drop(columns=['dt'])
    return df


def fetch_detail(row):
    """1순위 팝업 — 실제 데이터만"""
    suc_amt = row.get('투찰금액', '-')
    rate = row.get('투찰률', '-')
    corps = []
    corp_raw = row.get('전체업체', '')
    if corp_raw:
        for idx, c in enumerate(str(corp_raw).split('|')[:10]):
            p = c.split('^')
            if len(p) >= 5:
                try:
                    amt_disp = f"{int(float(p[3])):,}원"
                except:
                    amt_disp = p[3]
                corps.append({'순위': f"{idx+1}위", '업체명': p[0].strip(),
                              '투찰금액': amt_disp, '투찰률': f"{p[4].strip()}%"})
    return {'suc_amt': suc_amt, 'rate': rate, 'corps': corps}


# ==========================================
# 9. 공지사항 팝업 (접속 시 1회)
# ==========================================
def show_notice_popup():
    if 'notice_shown' not in st.session_state:
        st.session_state['notice_shown'] = False

    if not st.session_state['notice_shown']:
        @st.dialog("📢 K-건설맵 Master 공지사항")
        def _popup():
            st.markdown("""
                <div style="background:#1e3a8a;color:white;border-radius:10px;padding:16px 20px;">
                    <div style="font-size:16px;font-weight:900;color:#fde68a;margin-bottom:10px;">🏛️ K-건설맵 Master</div>
                    <div style="font-size:13px;line-height:1.9;color:white;">
                    ✅ 전국 실시간 입찰 공고 즉시 확인<br>
                    ✅ 1순위 개찰 결과 15분마다 자동 업데이트<br>
                    ✅ 3년 낙찰 데이터 기반 투찰률 히트맵<br>
                    ✅ 발주기관별 독식업체·발주패턴 분석<br>
                    ✅ 실제 데이터 기반 투찰가 계산기<br>
                    ✅ 매일 맞춤 입찰 리포트 이메일 발송
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("")
            st.markdown("""
                <div style="background:#fef2f2;border:2px solid #ef4444;border-radius:8px;padding:12px 16px;text-align:center;">
                    <div style="font-size:13px;font-weight:900;color:#dc2626;">📢 이용 안내</div>
                    <div style="font-size:13px;color:#7f1d1d;margin-top:6px;line-height:1.8;">
                    <b>2025년 5월 15일</b>부터<br>
                    <b>회원가입 회원에 한하여</b> 서비스 이용이 가능합니다.<br>
                    지금 바로 무료 회원가입 후 이용하세요!
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("")
            if st.button("✅ 확인했습니다", use_container_width=True, type="primary"):
                st.session_state['notice_shown'] = True
                st.rerun()
        _popup()


# ==========================================
# 10. 팝업 다이얼로그
# ==========================================
@st.dialog("📋 K-건설맵 팩트 리포트", width="large")
def show_analysis_dialog(row, det, mode="1st"):

    if mode == "1st":
        st.markdown(f"### {row['공고명']}")

        col1, col2 = st.columns(2)
        col1.markdown(
            f'<div class="stat-card"><div class="stat-label">🏆 낙찰금액 (실제)</div>'
            f'<div class="stat-val" style="color:#dc2626;">{det["suc_amt"]}</div></div>',
            unsafe_allow_html=True)
        col2.markdown(
            f'<div class="stat-card"><div class="stat-label">📊 투찰률 (실제)</div>'
            f'<div class="stat-val">{det["rate"]}</div></div>',
            unsafe_allow_html=True)

        if det['corps']:
            st.markdown("**[개찰 결과 — 실제 데이터]**")
            st.dataframe(pd.DataFrame(det['corps']), use_container_width=True, hide_index=True)

        if big_data is not None and not big_data.empty:
            st.markdown("---")
            st.markdown("#### 📊 3년 팩트 분석")
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🎯 투찰률 히트맵", "🏆 독식업체", "📅 발주패턴", "🔍 유사공고", "🏢 자가진단"
            ])
            inst_name = row.get('발주기관', '')
            notice_name = row.get('공고명', '')
            with tab1: render_heatmap(inst_name)
            with tab2: render_dominant(inst_name)
            with tab3: render_pattern(inst_name)
            with tab4: render_similar(notice_name, inst_name)
            with tab5:
                corp_search = st.text_input("🔍 우리 회사명 입력", placeholder="예: 한국건설", key="sd_1st")
                if corp_search:
                    render_self_diagnosis(corp_search)

        st.markdown("---")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("💡 **나라장터 정책상 번호 복사가 필요합니다.**")
            st.code(row['공고번호'], language=None)
        with sc2:
            st.link_button("🚀 나라장터 홈페이지", "https://www.g2b.go.kr/index.jsp", use_container_width=True)
            st.link_button("🏢 업체 네이버 검색",
                           f"https://search.naver.com/search.naver?query={row.get('1순위업체','')} 건설",
                           use_container_width=True)

    elif mode == "live":
        inst_name = row.get('발주기관', '')
        notice_name = row.get('공고명', '')
        st.markdown(f"### 🎯 입찰 준비 종합 분석")
        st.markdown(f"**발주기관:** `{inst_name}`")
        st.markdown(f"**공고명:** {notice_name}")

        if big_data is not None and not big_data.empty:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🎯 투찰률 히트맵", "🏆 독식업체", "📅 발주패턴", "🔍 유사공고", "🏢 자가진단"
            ])
            with tab1: render_heatmap(inst_name)
            with tab2: render_dominant(inst_name)
            with tab3: render_pattern(inst_name)
            with tab4: render_similar(notice_name, inst_name)
            with tab5:
                corp_search = st.text_input("🔍 우리 회사명 입력", placeholder="예: 한국건설", key="sd_live")
                if corp_search:
                    render_self_diagnosis(corp_search)
        else:
            st.info("3년 마스터 데이터가 없습니다.")

    elif mode == "job":
        st.markdown("### 🤝 구인/구직 상세내용")
        st.write(f"**제목:** {row['title']} | **지역:** {row['region']}")
        st.write(f"**작성자:** {row['author']} | **연락처:** {row['phone']}")
        st.markdown("---")
        st.write(row['content'])


# ==========================================
# 11. UI 대시보드
# ==========================================
show_notice_popup()  # 공지사항 팝업 (접속 시 1회)
update_stats()
t_visit, u_total = get_stats()

st.markdown('<div class="main-title">🏛️ K-건설맵 Master</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="stat-card"><div class="stat-label">📅 오늘 날짜</div><div class="stat-val">{datetime.now(KST).strftime("%Y-%m-%d")}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-card"><div class="stat-label">📈 누적 방문</div><div class="stat-val">{t_visit:,}명</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-card"><div class="stat-label">👥 전체 회원수</div><div class="stat-val">{u_total:,}명</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-card"><div class="stat-label">🔔 가동 상태</div><div class="stat-val" style="color:green;">정상 가동 중</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.write(f"### 👷 {'👋 ' + st.session_state['user_name'] + ' 소장님' if st.session_state['logged_in'] else 'K-건설맵 메뉴'}")
    menu = st.radio("업무 선택", [
        "🏆 1순위 현황판", "📊 실시간 공고 (홈)",
        "🧮 투찰가 계산기",
        "🔍 발주기관 분석", "🏢 업체 자가진단",
        "🤝 K-구인구직", "📁 K-건설 자료실",
        "💬 K건설챗", "📲 앱처럼 설치하기", "👤 내 정보/로그인"
    ])
    st.write("---")
    if st.session_state['logged_in'] and st.button("🚪 로그아웃"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 12. 메뉴 라우팅
# ==========================================
ROWS_PER_PAGE = 20

if menu == "🏆 1순위 현황판":
    st.markdown("#### 🏆 실시간 1순위 현황판")
    st.markdown('<div class="guide-box">💡 <b>터치 한 번으로 팩트 분석!</b> 맨 왼쪽 <b>[체크박스(ㅁ)]</b>를 터치하면 3년 팩트 리포트가 즉시 열립니다.</div>', unsafe_allow_html=True)

    df_w = get_hybrid_1st_bids()
    if not df_w.empty:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            sel_reg = st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg1")
        with col_f2:
            search_co = st.text_input("🏢 업체명 검색", placeholder="낙찰 업체명 입력", key="search_main")

        filter_key = f"{sel_reg}_{search_co}"
        if st.session_state.get("prev_filter_1st") != filter_key:
            st.session_state["p1"] = 1
            st.session_state["prev_filter_1st"] = filter_key

        df_f = filter_by_region(df_w, sel_reg)
        if search_co:
            df_f = df_f[df_f['1순위업체'].str.contains(search_co, na=False)]

        num_pages = max(1, math.ceil(len(df_f) / ROWS_PER_PAGE))
        if "p1" not in st.session_state: st.session_state["p1"] = 1

        start_idx = (st.session_state["p1"] - 1) * ROWS_PER_PAGE
        df_page = df_f.iloc[start_idx: start_idx + ROWS_PER_PAGE]

        event = st.dataframe(
            df_page[['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률']],
            use_container_width=True, hide_index=True, height=700,
            selection_mode="single-row", on_select="rerun")

        c_p1, c_p2, c_p3 = st.columns([3, 4, 3])
        with c_p2:
            st.selectbox(f"📄 페이지 이동 (총 {num_pages}쪽)", range(1, num_pages + 1), key="p1")

        if len(event.selection.rows) > 0:
            selected_row = df_page.iloc[event.selection.rows[0]]
            det = fetch_detail(selected_row)
            show_analysis_dialog(selected_row, det, mode="1st")

elif menu == "📊 실시간 공고 (홈)":
    st.markdown("#### 📊 실시간 입찰 공고")
    st.markdown('<div class="guide-box">💡 <b>입찰 팩트 리포트!</b> 맨 왼쪽 <b>[체크박스(ㅁ)]</b>를 터치하면 해당 발주기관의 3년 팩트 분석이 열립니다.</div>', unsafe_allow_html=True)

    df_live = get_hybrid_live_bids()
    if not df_live.empty:
        sel_reg2 = st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg2")

        if st.session_state.get("prev_filter_live") != sel_reg2:
            st.session_state["p_all"] = 1
            st.session_state["p_m"]   = 1
            st.session_state["p_g"]   = 1
            st.session_state["prev_filter_live"] = sel_reg2

        df_f = filter_by_region(df_live, sel_reg2)
        col_cfg = {
            "상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
            "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")
        }

        selected_row_live = None

        if st.session_state['logged_in']:
            t1, t2 = st.tabs(["🌐 전체 공고", "✨ 내 면허 맞춤매칭"])

            with t1:
                n_all = max(1, math.ceil(len(df_f) / ROWS_PER_PAGE))
                if "p_all" not in st.session_state: st.session_state["p_all"] = 1
                df_p_all = df_f.iloc[(st.session_state["p_all"]-1)*ROWS_PER_PAGE: st.session_state["p_all"]*ROWS_PER_PAGE]
                event_all = st.dataframe(
                    df_p_all[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                    use_container_width=True, hide_index=True, height=700,
                    column_config=col_cfg, selection_mode="single-row", on_select="rerun", key="live_all")
                c1, c2, c3 = st.columns([3, 4, 3])
                with c2: st.selectbox(f"📄 페이지 이동 (총 {n_all}쪽)", range(1, n_all+1), key="p_all")
                if len(event_all.selection.rows) > 0:
                    selected_row_live = df_p_all.iloc[event_all.selection.rows[0]]

            with t2:
                kw     = get_match_keywords(st.session_state.get('user_license', ''))
                m_full = df_f[df_f['공고명'].str.contains('|'.join(kw), na=False)] if kw else df_f
                n_m    = max(1, math.ceil(len(m_full) / ROWS_PER_PAGE))
                if "p_m" not in st.session_state: st.session_state["p_m"] = 1
                df_p_m = m_full.iloc[(st.session_state["p_m"]-1)*ROWS_PER_PAGE: st.session_state["p_m"]*ROWS_PER_PAGE]
                event_m = st.dataframe(
                    df_p_m[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                    use_container_width=True, hide_index=True, height=700,
                    column_config=col_cfg, selection_mode="single-row", on_select="rerun", key="live_match")
                c1, c2, c3 = st.columns([3, 4, 3])
                with c2: st.selectbox(f"📄 페이지 이동 (총 {n_m}쪽)", range(1, n_m+1), key="p_m")
                if len(event_m.selection.rows) > 0:
                    selected_row_live = df_p_m.iloc[event_m.selection.rows[0]]

        else:
            n_g = max(1, math.ceil(len(df_f) / ROWS_PER_PAGE))
            if "p_g" not in st.session_state: st.session_state["p_g"] = 1
            df_p_g  = df_f.iloc[(st.session_state["p_g"]-1)*ROWS_PER_PAGE: st.session_state["p_g"]*ROWS_PER_PAGE]
            event_g = st.dataframe(
                df_p_g[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                use_container_width=True, hide_index=True, height=700,
                column_config=col_cfg, selection_mode="single-row", on_select="rerun")
            c1, c2, c3 = st.columns([3, 4, 3])
            with c2: st.selectbox(f"📄 페이지 이동 (총 {n_g}쪽)", range(1, n_g+1), key="p_g")
            if len(event_g.selection.rows) > 0:
                selected_row_live = df_p_g.iloc[event_g.selection.rows[0]]

        if selected_row_live is not None:
            show_analysis_dialog(selected_row_live, None, mode="live")

elif menu == "🧮 투찰가 계산기":
    render_bid_calculator()

elif menu == "🔍 발주기관 분석":
    st.markdown("#### 🔍 발주기관 심층 분석")
    st.markdown('<div class="guide-box">발주기관명을 입력하면 3년 실제 데이터 기반으로 투찰률 히트맵, 독식업체, 발주패턴을 분석합니다. 추정 없음.</div>', unsafe_allow_html=True)
    if big_data is not None and not big_data.empty:
        inst_input = st.text_input("🏛️ 발주기관명 입력 (일부만 입력해도 됩니다)", placeholder="예: 여수시, 전남도청, 한국도로공사")
        if inst_input:
            matching = big_data[big_data['발주기관'].str.contains(inst_input, na=False)]['발주기관'].value_counts()
            if matching.empty:
                st.warning("검색된 발주기관이 없습니다.")
            else:
                inst_select = st.selectbox(
                    f"검색 결과 {len(matching)}개 기관 — 선택하세요",
                    matching.index.tolist(),
                    format_func=lambda x: f"{x} ({matching[x]}건)"
                )
                if inst_select:
                    st.markdown("---")
                    tab1, tab2, tab3 = st.tabs(["🎯 투찰률 히트맵", "🏆 독식업체 분석", "📅 발주패턴"])
                    with tab1: render_heatmap(inst_select)
                    with tab2: render_dominant(inst_select)
                    with tab3: render_pattern(inst_select)
    else:
        st.info("3년 마스터 데이터가 없습니다.")

elif menu == "🏢 업체 자가진단":
    st.markdown("#### 🏢 업체 자가진단 리포트")
    st.markdown('<div class="guide-box">업체명을 입력하면 3년간 실제 낙찰 이력을 분석합니다. 지역별 강점, 낙찰 투찰률 분포, 주요 발주처를 확인하세요. 추정 없음.</div>', unsafe_allow_html=True)
    if big_data is not None and not big_data.empty:
        corp_input = st.text_input("🏢 업체명 입력 (일부만 입력해도 됩니다)", placeholder="예: 한국건설, 대우건설")
        if corp_input:
            render_self_diagnosis(corp_input)
    else:
        st.info("3년 마스터 데이터가 없습니다.")

elif menu == "🤝 K-구인구직":
    st.markdown("#### 🤝 건설현장 구인구직")
    if st.session_state['logged_in']:
        with st.expander("📝 새 구인/구직 등록하기"):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("분류", ["👷 사람 구합니다", "🚜 일자리 찾습니다"])
            reg = c2.selectbox("지역", REGION_LIST)
            jt  = st.text_input("직종 (예: 철근공, 포크레인)")
            ph  = st.text_input("연락처", value=st.session_state.get('user_phone', ''))
            ttl = st.text_input("제목")
            con = st.text_area("상세내용")
            if st.button("등록하기"):
                db.child("jobs").push({
                    "category": cat, "region": reg, "job_type": jt, "phone": ph,
                    "title": ttl, "content": con,
                    "author": st.session_state['user_name'],
                    "time": datetime.now(KST).strftime("%m-%d %H:%M")
                })
                st.toast("등록 완료!")
                time.sleep(1)
                st.rerun()
    jobs_data = db.child("jobs").get().val()
    if jobs_data:
        df_j = pd.DataFrame(list(jobs_data.values())).iloc[::-1]
        t1, t2 = st.tabs(["👷 사람 구함", "🚜 일자리 찾음"])
        with t1:
            h    = df_j[df_j['category'] == "👷 사람 구합니다"]
            ev_h = st.dataframe(h[['time', 'region', 'job_type', 'title', 'author']],
                                use_container_width=True, hide_index=True,
                                selection_mode="single-row", on_select="rerun", key="h_job")
            if len(ev_h.selection.rows) > 0:
                show_analysis_dialog(h.iloc[ev_h.selection.rows[0]], None, mode="job")
        with t2:
            s    = df_j[df_j['category'] == "🚜 일자리 찾습니다"]
            ev_s = st.dataframe(s[['time', 'region', 'job_type', 'title', 'author']],
                                use_container_width=True, hide_index=True,
                                selection_mode="single-row", on_select="rerun", key="s_job")
            if len(ev_s.selection.rows) > 0:
                show_analysis_dialog(s.iloc[ev_s.selection.rows[0]], None, mode="job")

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
                    st.session_state.update({
                        'logged_in'    : True,
                        'user_name'    : info.get('name', '소장님'),
                        'user_license' : info.get('license', ''),
                        'user_phone'   : info.get('phone', ''),
                        'localId'      : user['localId'],
                        'idToken'      : user['idToken']
                    })
                    st.rerun()
                except Exception:
                    st.error("로그인 실패! 이메일 또는 비밀번호를 확인해주세요.")
        with t2:
            re_email = st.text_input("이메일 가입")
            re_pw    = st.text_input("비번 (6자 이상)", type="password")
            re_name  = st.text_input("성함")
            re_lic   = st.multiselect("보유 면허 (맞춤 매칭용)", ALL_LICENSES)
            if st.button("가입하기"):
                try:
                    u = auth.create_user_with_email_and_password(re_email.strip().lower(), re_pw)
                    db.child("users").child(u['localId']).set({
                        "name": re_name, "license": ", ".join(re_lic), "email": re_email
                    })
                    st.success("🎉 가입 성공!")
                except Exception:
                    st.error("가입 실패! 이미 사용 중인 이메일이거나 비밀번호가 6자 미만입니다.")
    else:
        # ★ 추가 2: 회원 정보 수정 + 탈퇴 기능 ★
        st.write(f"### {st.session_state['user_name']} 소장님 반갑습니다!")
        my_tab1, my_tab2 = st.tabs(["✏️ 정보 수정", "🗑️ 회원 탈퇴"])

        with my_tab1:
            st.markdown("**회원 정보를 수정합니다.**")
            cur_info = db.child("users").child(st.session_state['localId']).get().val() or {}
            new_name = st.text_input("성함 수정", value=cur_info.get('name', ''))
            new_phone = st.text_input("연락처 수정", value=cur_info.get('phone', ''))
            new_lic  = st.multiselect("보유 면허 수정", ALL_LICENSES,
                                      default=[l.strip() for l in cur_info.get('license', '').split(',') if l.strip() in ALL_LICENSES])
            if st.button("✅ 정보 저장"):
                try:
                    db.child("users").child(st.session_state['localId']).update({
                        "name"   : new_name,
                        "phone"  : new_phone,
                        "license": ", ".join(new_lic)
                    })
                    st.session_state['user_name']    = new_name
                    st.session_state['user_phone']   = new_phone
                    st.session_state['user_license'] = ", ".join(new_lic)
                    st.success("✅ 정보가 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

        with my_tab2:
            st.warning("⚠️ 탈퇴하면 모든 정보가 삭제되며 복구할 수 없습니다.")
            confirm_pw = st.text_input("탈퇴 확인용 비밀번호 입력", type="password", key="del_pw")
            if st.button("🗑️ 회원 탈퇴 확인", type="primary"):
                if not confirm_pw:
                    st.error("비밀번호를 입력해주세요.")
                else:
                    try:
                        cur_info2 = db.child("users").child(st.session_state['localId']).get().val() or {}
                        auth.sign_in_with_email_and_password(
                            cur_info2.get('email', ''), confirm_pw)
                        db.child("users").child(st.session_state['localId']).remove()
                        st.session_state.clear()
                        st.success("탈퇴 완료. 이용해 주셔서 감사합니다.")
                        time.sleep(2)
                        st.rerun()
                    except Exception:
                        st.error("비밀번호가 틀렸거나 탈퇴에 실패했습니다.")

        st.markdown("---")
        if st.button("🚪 로그아웃"):
            st.session_state.clear()
            st.rerun()

elif menu == "📁 K-건설 자료실":
    # ★ 추가 3: 게시판 수정/삭제 기능 ★
    st.subheader("📁 K-건설 자료실")
    if st.session_state['logged_in']:
        with st.expander("✏️ 새 자료 등록"):
            t_title   = st.text_input("제목", key="post_title")
            t_content = st.text_area("내용", key="post_content")
            if st.button("등록") and t_title and t_content:
                db.child("posts").push({
                    "author" : st.session_state['user_name'],
                    "title"  : t_title, "content": t_content,
                    "time"   : datetime.now(KST).strftime("%Y-%m-%d %H:%M")
                })
                st.rerun()

    posts = db.child("posts").get().val()
    if posts:
        for k, v in reversed(list(posts.items())):
            with st.expander(f"📢 {v['title']} (작성자: {v['author']})"):
                st.write(v['content'])
                st.caption(f"작성: {v.get('time', '')}")
                # 본인 글만 수정/삭제 가능
                if st.session_state['logged_in'] and v['author'] == st.session_state['user_name']:
                    col_e, col_d = st.columns([1, 1])
                    with col_e:
                        if st.button("✏️ 수정", key=f"edit_{k}"):
                            st.session_state[f'editing_{k}'] = True
                    with col_d:
                        if st.button("🗑️ 삭제", key=f"del_{k}"):
                            db.child("posts").child(k).remove()
                            st.toast("삭제되었습니다.")
                            time.sleep(0.5)
                            st.rerun()
                    if st.session_state.get(f'editing_{k}'):
                        new_t = st.text_input("제목 수정", value=v['title'],  key=f"et_{k}")
                        new_c = st.text_area("내용 수정", value=v['content'], key=f"ec_{k}")
                        if st.button("💾 저장", key=f"save_{k}"):
                            db.child("posts").child(k).update({"title": new_t, "content": new_c})
                            st.session_state.pop(f'editing_{k}', None)
                            st.toast("수정되었습니다.")
                            time.sleep(0.5)
                            st.rerun()

elif menu == "💬 K건설챗":
    st.subheader("💬 실시간 현장 소통")
    if st.session_state['logged_in']:
        chat_box   = st.container(height=400)
        chats_data = db.child("k_chat").get().val()
        if chats_data:
            for v in list(chats_data.values())[-20:]:
                chat_box.write(f"**{v['author']}**: {v['message']}")
        if msg := st.chat_input("메시지 입력"):
            db.child("k_chat").push({
                "author" : st.session_state['user_name'],
                "message": msg,
                "time"   : datetime.now(KST).strftime("%H:%M")
            })
            st.rerun()
    else:
        st.info("로그인 후 이용 가능합니다.")