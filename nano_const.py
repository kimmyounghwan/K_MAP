import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib3
import streamlit as st
import concurrent.futures
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"
KST = timezone(timedelta(hours=9))


@st.cache_data(ttl=600)
def fetch_monster_announcements():
    all_raw = []

    # 📅 딱 3일 전부터 오늘까지! (타임아웃 방지용 가벼운 세팅)
    end_date = datetime.now(KST).date()
    start_date = end_date - timedelta(days=3) # 🚨 <--- 딱 이 부분만 60에서 3으로 수정했어!
    delta = end_date - start_date
    dates = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(delta.days + 1)]

    # 🚨 [엔진 업그레이드] 조달청 전용(PPSSrch) 꼬리표를 떼고,
    # 국토부 등 모든 국가/공공기관의 건설 공고를 가져오는 '통합 마스터 주소'로 변경!
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'

    def fetch_per_day(dt):
        params = {
            'inqryDiv': '1', 'inqryBgnDt': f'{dt}0000', 'inqryEndDt': f'{dt}2359',
            'pageNo': '1', 'numOfRows': '999', 'bidNtceNm': '공사',
            'type': 'json', 'serviceKey': API_KEY
        }

        # 🚨 [끈기 모드] 데이터가 많아져서 서버가 튕겨내면 0.5초 쉬고 재도전!
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

    # 🚨 일꾼 15명 유지 (안전 주행)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_per_day, dates))
        for res in results:
            if res: all_raw.extend(res)

    return pd.DataFrame(all_raw)