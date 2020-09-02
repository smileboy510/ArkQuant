# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import pandas as pd, numpy as np
from gateway.driver.client import tsclient

# 过于过滤frame 防止入库报错
EquityNullFields = ['sid', 'first_traded']

_rename_equity_cols = {
    '代码': 'sid',
    '港股': 'dual_sid',
    '上市市场': 'exchange',
    '上市日期': 'first_traded',
    '发行价格': 'initial_price',
    '主承销商': 'broker',
    # '公司名称': 'company_symbol',
    '公司名称': 'asset_name',
    '成立日期': 'establish_date',
    '注册资本': 'register_capital',
    '组织形式': 'organization',
    '邮政编码': 'district',
    '经营范围': 'business_scope',
    '公司简介': 'brief',
    '证券简称更名历史': 'history_name',
    '注册地址': 'register_area',
    '办公地址': 'office_area',
    # 'delist_date': 'last_traded'
}


frame = pd.read_csv('equity_basics.csv', dtype={'代码': str})
frame.set_index('代码', drop=False, inplace=True)
print('ength 1', len(frame))
# replace null -- Nan
# # replace null -- Nan
frame.replace(to_replace='null', value=pd.NA, inplace=True)
frame.set_index('代码', drop=False, inplace=True)
print('length 2', len(frame))

frame['上市日期'].replace('--', None, inplace=True)
print('length 3', len(frame))

frame['发行价格'].replace('', None, inplace=True)
print('length 4', len(frame))

frame.rename(columns=_rename_equity_cols, inplace=True)
print('length 5', len(frame))


print(frame.loc['000003', :])
frame.dropna(axis=0, how='any', subset=EquityNullFields, inplace=True)
print('length 6', len(frame))


frame['initial_price'] = frame['initial_price'].astype(np.float)
print('length 7', len(frame))

frame.loc[:, 'asset_type'] = 'equity'
frame.fillna('', inplace=True)
print('length 8', len(frame))

stats = tsclient.to_ts_status()
print(len(stats), stats)
print(len(set(stats['sid'].values)))

union = set(stats['sid'].values) & set(frame.index)
print('common', len(union))

#
# print('test', stats.loc['000003',:])
# print('test', stats.loc['600018',:])

# @staticmethod
# def set_isolation_level(conn, level="READ COMMITTED"):
#     connection = conn.execution_options(
#         isolation_level=level
#     )
#     return connection

# con = self.set_isolation_level(conn)

# def check_version_info(conn, version_table, expected_version):
#     """
#     Checks for a version value in the version table.
#
#     Parameters
#     ----------
#     conn : sa.Connection
#         The connection to use to perform the check.
#     version_table : sa.Table
#         The version table of the asset database
#     expected_version : int
#         The expected version of the asset database
#
#     Raises
#     ------
#     AssetDBVersionError
#         If the version is in the table and not equal to ASSET_DB_VERSION.
#     """
#
#     # Read the version out of the table
#     version_from_table = conn.execute(
#         sa.select(version_table.c.version),
#     ).scalar()
#
#     # A db without a version is considered v0
#     if version_from_table is None:
#         version_from_table = 0
#
#     # Raise an error if the versions do not match
#     if version_from_table != expected_version:
#         # raise AssetDBVersionError(db_version=version_from_table,
#         #                           expected_version=expected_version)
#         raise ValueError('db_version != version_from_table')
#
#
# def write_version_info(conn, version_table, version_value):
#     """
#     Inserts the version value in to the version table.
#
#     Parameters
#     ----------
#     conn : sa.Connection
#         The connection to use to execute the insert.
#     version_table : sa.Table
#         The version table of the asset database
#     version_value : int
#         The version to write in to the database
#
#     """
#     conn.execute(sa.insert(version_table, values={'version': version_value}))

# print('full equities', len(equities))
# print('asset_router', len(existing_assets.get('equity', [])))
# print('asset_router convertible', len(existing_assets.get('convertible', [])))
# print('asset_router funds', len(existing_assets.get('fund', [])))
# status = status.reindex(index=frame.index)
# frame = pd.concat([frame, status], axis=1)

# # replace null -- Nan
# frame.replace(to_replace='null', value=pd.NA, inplace=True)
# frame.set_index('代码', drop=False, inplace=True)
