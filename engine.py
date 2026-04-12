import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import urllib3
import time
import streamlit as st

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))
API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"

def fetch_via_api(days=15):
    all_raw = []
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk'
    end_date = datetime.now(KST).date()
    start_date = end_date - timedelta(days=days)
    delta = end_date - start_date
    dates = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range(delta.days + 1)]
    for dt in dates:
        params = {'inqryDiv': '1', 'inqryBgnDt': f'{dt}0000', 'inqryEndDt': f'{dt}2359', 'pageNo': '1', 'numOfRows': '999', 'bidNtceNm': '공사', 'type': 'json', 'serviceKey': API_KEY}
        try:
            res = requests.get(url, params=params, verify=False, timeout=8)
            if res.status_code == 200:
                items = res.json().get('response', {}).get('body', {}).get('items', [])
                if items: all_raw.extend(items)
        except: return pd.DataFrame()
        time.sleep(0.1)
    if not all_raw: return pd.DataFrame()
    df = pd.DataFrame(all_raw)
    return df.rename(columns={'bidNtceNo': '공고번호', 'bidNtceNm': '공고명', 'ntceInsttNm': '발주기관', 'bidNtceDt': '공고일시', 'bdgtAmt': '예산금액'})

def fetch_via_crawling(days=7):
    all_bids = []
    end_date = datetime.now(KST).strftime('%Y/%m/%d')
    start_date = (datetime.now(KST) - timedelta(days=7)).strftime('%Y/%m/%d')
    base_url = "https://www.g2b.go.kr:8101/ep/tbid/tbidList.do"
    params = {"taskClCds": "3", "searchDtType": "1", "fromBidDt": start_date, "toBidDt": end_date, "regYn": "Y", "bidSearchType": "1", "searchType": "1"}
    try:
        encoded_params = urllib.parse.urlencode(params, encoding='euc-kr')
        response = requests.get(f"{base_url}?{encoded_params}", verify=False, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.select('table.table_list tr')[1:]
        for row in rows:
            cols = row.select('td')
            if len(cols) >= 5:
                no = cols[1].text.strip()
                all_bids.append({'공고번호': no, '공고명': cols[2].text.strip(), '발주기관': cols[3].text.strip(), '공고일시': cols[4].text.strip(), '예산금액': "0"})
    except: pass
    return pd.DataFrame(all_bids)

@st.cache_data(ttl=600)
def get_final_data():
    df = fetch_via_api(days=15)
    if df.empty:
        df = fetch_via_crawling(days=7)
    return df