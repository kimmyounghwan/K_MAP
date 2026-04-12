import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import urllib3
import streamlit as st
import concurrent.futures
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"
KST = timezone(timedelta(hours=9))


def fetch_front_door(days=7):
    """[앞문] 조달청 홈페이지 직접 크롤링 (명환이 사진 참고!)"""
    all_bids = []
    end_date = datetime.now(KST).strftime('%Y/%m/%d')
    start_date = (datetime.now(KST) - timedelta(days=days)).strftime('%Y/%m/%d')

    url = "https://www.g2b.go.kr:8101/ep/tbid/tbidList.do"
    params = {
        "taskClCds": "3",  # 3: 공사 (건설)
        "searchDtType": "1",
        "fromBidDt": start_date,
        "toBidDt": end_date,
        "regYn": "Y",
        "bidSearchType": "1",
        "searchType": "1"
    }

    try:
        encoded_params = urllib.parse.urlencode(params, encoding='euc-kr')
        res = requests.get(f"{url}?{encoded_params}", verify=False, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        rows = soup.select('table.table_list tr')[1:]  # 맨 위 제목(헤더) 줄 제외

        for row in rows:
            cols = row.select('td')
            if len(cols) >= 5:
                all_bids.append({
                    'bidNtceNo': cols[1].text.strip()[:11],
                    'bidNtceDt': cols[4].text.strip(),
                    'bidNtceNm': cols[2].text.strip(),
                    'ntceInsttNm': cols[3].text.strip(),
                    'bdgtAmt': "0"  # 크롤링 목록에는 예산이 안 나와서 0으로 임시 처리
                })
    except Exception as e:
        print(f"크롤링 에러 발생: {e}")

    return pd.DataFrame(all_bids)


@st.cache_data(ttl=600)
def fetch_monster_announcements():
    """[뒷문+앞문 통합] API 먼저 시도하고, 실패하면 크롤링 가동"""
    all_raw = []

    # 📅 딱 2개월(60일) 전부터 오늘까지!
    end_date = datetime.now(KST).date()
    start_date = end_date - timedelta(days=60)
    delta = end_date - start_date
    dates = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(delta.days + 1)]

    # 🚨 [엔진 업그레이드] 국토부 등 모든 공공기관 통합 API
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

    # 🚨 일꾼 15명으로 병렬 수집
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_per_day, dates))
        for res in results:
            if res: all_raw.extend(res)

    df = pd.DataFrame(all_raw)

    # 🚨 API(뒷문)가 막혀서 데이터가 하나도 없다면? -> 앞문(크롤링) 열어라!
    if df.empty:
        return fetch_front_door(days=7)  # 크롤링은 속도를 위해 최근 7일치만!

    return df