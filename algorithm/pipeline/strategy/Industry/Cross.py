# -*- coding : utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""

from gateWay import Event,GateReq,Quandle

quandle = Quandle()

class CrossReverse:
    """
        跨行业（横截面）均值回归 ---- 相对收益率的反转，即为回归
        具体逻辑实现：
            1、筛选出强势的行业
            2、基于强势行业计算一定时间内行业的每天收益率均值（横截面收益率）
            3、横截面收益率与行业中最低的收益率之差，计算均值、标准差
            4、当天价格基于3中均值、标准差计算zscore ,如果zscore大于1或者N，买入对应标的
        关键：
            1、周期 --- 存在实效性 ，如果周期太大序列不平稳，而且容易发生异常事件到时价格偏离不会反转；当
            短周期的价格反弹的概率变大（由于行业的急剧效应，滞后的股票上涨）
            2、计算行业的强度
    """
    def __init__(self,window):
        self.period = window

    def _construct_power(self,dt):
        """
            1、基于Composite.IndusComposite.Initialize模块对应的时间点行业权重
            2、构建不同行业的指数强度，并筛选出最强的行业
        """
        pass

    def _cross_ret(self,dt):
        """
            1、对应的行业的过去每天收益率均值以及相对于最低的超额收益率序列
            2、计算当前时点数据的zscore
        """
        pass

    def run(self,dt):
        self._cross_ret(dt)


if __name__ == '__main__':

    reverse = CrossReverse(10)