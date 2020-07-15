# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  1 11:27:02 2018

@author: hengxinliu
"""

import json,pandas as pd

from .tools import _parse_url
from ._config import  BENCHMARK_URL


def request_benchmark():
    raw = json.loads(_parse_url(BENCHMARK_URL['benchmark'], encoding='utf-8', bs=False))
    index_sids = raw['data']['diff']
    return index_sids

def request_periphera_kline(c_name,dt):
    """
        dt --- 1990-01-01
    """
    index = BENCHMARK_URL['periphery'][c_name]
    url = BENCHMARK_URL['periphera_kline'] % (index, dt)
    text = _parse_url(url, bs=False, encoding='utf-8')
    raw = json.loads(text)
    df = pd.DataFrame(raw['data'][index]['day'],
                      columns=['trade_dt', 'open', 'close',
                                'high', 'low', 'turnvoer'])
    df.index = df.loc[:, 'trade_dt']
    df.sort_index(inplace=True)
    return df

def attach_prefix(sid):
    if sid.startswith('0'):
        prefix = '1.' + sid
    else:
        prefix = '0.' + sid
    return prefix

def request_native_kline(sid,date):
    """
        date --- 19900101
    """
    url = BENCHMARK_URL['kline'].format(attach_prefix(sid),date)
    obj = _parse_url(url,bs = False)
    data = json.loads(obj)
    raw = data['data']
    if raw and len(raw['klines']):
        raw = [item.split(',') for item in raw['klines']]
        benchmark = pd.DataFrame(raw,
                                 columns = ['trade_dt','open','close','high',
                                            'low','turnover','volume','amount'])
    return benchmark

def get_benchmark_returns(sid,dts):
    try:
        kline = request_native_kline(sid,dts)
    except Exception as e:
        kline = request_periphera_kline(sid,dts)
    returns = kline['close'] / kline['close'].shift(1) - 1
    return returns