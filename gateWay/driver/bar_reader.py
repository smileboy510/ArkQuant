# Copyright 2016 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from abc import ABC, abstractmethod

class BarReader(ABC):

    @property
    def data_frequency(self):
        return 'daily'

    @property
    def trading_calendar(self):
        """
        Returns the zipline.utils.calendar.trading_calendar used to read
        the data.  Can be None (if the writer didn't specify it).
        """
        return self._trading_calendar

    def _window_size_to_dt(self,date,window):
        shift_date = self.trading_calendar.shift_calendar(date, window)
        return shift_date

    @abstractmethod
    def get_value(self, asset, dt, field):
        """
        Retrieve the value at the given coordinates.

        Parameters
        ----------
        asset : Asset
            The asset identifier.
        dt : pd.Timestamp
            The timestamp for the desired data point.
        field : string
            The OHLVC name for the desired data point.

        Returns
        -------
        value : float|int
            The value at the given coordinates, ``float`` for OHLC, ``int``
            for 'volume'.

        Raises
        ------
        NoDataOnDate
            If the given dt is not a valid market minute (in minute mode) or
            session (in daily mode) according to this reader's tradingcalendar.
        """
        raise NotImplementedError()

    @abstractmethod
    def load_raw_arrays(self, date, window,columns,assets):
        """
        Parameters
        ----------
        columns : list of str
           'open', 'high', 'low', 'close', or 'volume'
        start_date: Timestamp
           Beginning of the window range.
        end_date: Timestamp
           End of the window range.
        assets : list of int
           The asset identifiers in the window.

        Returns
        -------
        list of np.ndarray
            A list with an entry per field of ndarrays with shape
            (minutes in range, sids) with a dtype of float64, containing the
            values for the respective field over start and end dt range.
        """
        raise NotImplementedError()


#reader
class AssetSessionReader(BarReader):
    """
    Reader for raw pricing data from mysql.
    return different asset types : etf bond symbol
    """
    AssetsTypes = frozenset(['symbol','bond','etf','dual'])

    def __init__(self,
                 metadata,
                 engine,
                 trading_calendar,
                ):
        self.metadata = metadata
        self.engine = engine
        self._trading_calendar = trading_calendar

    def get_value(self, asset,dt):
        table_name = '%s_price'%asset.asset_type
        tbl = self.metadata[table_name]
        orm = select([cast(tbl.c.open, Numeric(10, 2)).label('open'),
                      cast(tbl.c.close, Numeric(12, 2)).label('close'),
                      cast(tbl.c.high, Numeric(10, 2)).label('high'),
                      cast(tbl.c.low, Numeric(10, 3)).label('low'),
                      cast(tbl.c.volume, Numeric(15, 0)).label('volume'),
                      cast(tbl.c.amount, Numeric(15, 2)).label('amount')])\
            .where(and_(tbl.c.trade_dt == dt,tbl.c.sid == asset.sid))
        rp = self.engine.execute(orm)
        arrays = [[r.trade_dt, r.code, r.open, r.close, r.high, r.low, r.volume] for r in
                  rp.fetchall()]
        kline = pd.DataFrame(arrays,
                             columns=['open', 'close', 'high', 'low', 'volume',
                                      'amount'])
        return kline

    def _retrieve_asset_type(self,table,sids,fields,start_date,end_date):
        tbl = self.metadata['%s_price' & table]
        orm = select([tbl.c.trade_dt, tbl.c.sid,
                      cast(tbl.c.open, Numeric(10, 2)).label('open'),
                      cast(tbl.c.close, Numeric(12, 2)).label('close'),
                      cast(tbl.c.high, Numeric(10, 2)).label('high'),
                      cast(tbl.c.low, Numeric(10, 3)).label('low'),
                      cast(tbl.c.volume, Numeric(15, 0)).label('volume'),
                      cast(tbl.c.amount, Numeric(15, 2)).label('amount')]). \
            where(tbl.c.trade_dt.between(start_date, end_date))
        rp = self.engine.execute(orm)
        arrays = [[r.trade_dt, r.code, r.open, r.close, r.high, r.low, r.volume] for r in
                  rp.fetchall()]
        raw = pd.DataFrame(arrays,
                             columns=['trade_dt', 'code', 'open', 'close', 'high', 'low', 'volume',
                                      'amount'])
        raw.set_index('code', inplace=True)
        # 基于code
        _slice = raw.loc[sids]
        # 基于fields 获取数据
        kline = _slice.loc[:, fields]
        unpack_kline = unpack_df_to_component_dict(kline)
        return unpack_kline

    def load_raw_arrays(self,end_date,window,columns,assets):
        start_date = self._window_size_to_dt(end_date,window)
        _get_source = partial(self._retrieve_asset_type(fields= columns,
                                                           start_date= start_date,
                                                           end_date = end_date
                                                           ))
        sid_groups = {}
        for asset in assets:
            sid_groups[asset.asset_type].append(asset.sid)
        #验证
        assert set(sid_groups) in self.AssetsTypes,('extra asset types %r'%
                                                    (set(sid_groups) - self.AssetsTypes))
        #获取数据
        batch_arrays = {}
        for _name,sids in sid_groups.items():
            raw = _get_source(table = _name,sids = sids)
            batch_arrays.update(raw)
        return batch_arrays
