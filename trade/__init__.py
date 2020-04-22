# -*- coding : uft-8 -*-

class AlgorithmSimulator(object):
    EMISSION_TO_PERF_KEY_MAP = {
        'minute': 'minute_perf',
        'daily': 'daily_perf'
    }

    def __init__(self, algo, sim_params, data_portal, clock, benchmark_source,
                 restrictions, universe_func):

        self.sim_params = sim_params
        self.data_portal = data_portal
        self.restrictions = restrictions
        self.algo = algo
        # This object is the way that user algorithms interact with OHLCV data,
        # fetcher data, and some API methods like `data.can_trade`.
        self.current_data = self._create_bar_data(universe_func)

        # We don't have a datetime for the current snapshot until we
        # receive a message.
        self.simulation_dt = None

        self.clock = clock

        # =============
        # Logging Setup
        # =============

        # Processor function for injecting the algo_dt into
        # user prints/logs.
        def inject_algo_dt(record):
            if 'algo_dt' not in record.extra:
                record.extra['algo_dt'] = self.simulation_dt

        self.processor = Processor(inject_algo_dt)

    def get_simulation_dt(self):
        return self.simulation_dt

    # 获取交易日数据，封装为一个API(fetch process flush other api)
    def _create_bar_data(self, universe_func):
        return BarData(
            data_portal=self.data_portal,
            simulation_dt_func=self.get_simulation_dt,
            data_frequency=self.sim_params.data_frequency,
            trading_calendar=self.algo.trading_calendar,
            restrictions=self.restrictions,
            universe_func=universe_func
        )

    def transform(self):
        """
        Main generator work loop.
        """
        algo = self.algo
        metrics_tracker = algo.metrics_tracker
        emission_rate = metrics_tracker.emission_rate

        # 生成器yield方法 ，返回yield 生成的数据，next 执行yield 之后的方法
        def every_bar(dt_to_use, current_data=self.current_data,
                      handle_data=algo.event_manager.handle_data):
            for capital_change in calculate_minute_capital_changes(dt_to_use):
                yield capital_change

            self.simulation_dt = dt_to_use
            # called every tick (minute or day).
            algo.on_dt_changed(dt_to_use)

            blotter = algo.blotter

            # handle any transactions and commissions coming out new orders
            # placed in the last bar
            new_transactions, new_commissions, closed_orders = \
                blotter.get_transactions(current_data)

            blotter.prune_orders(closed_orders)

            for transaction in new_transactions:
                metrics_tracker.process_transaction(transaction)

                # since this order was modified, record it
                order = blotter.orders[transaction.order_id]
                metrics_tracker.process_order(order)

            for commission in new_commissions:
                metrics_tracker.process_commission(commission)

            handle_data(algo, current_data, dt_to_use)

            # grab any new orders from the blotter, then clear the list.
            # this includes cancelled orders.
            new_orders = blotter.new_orders
            blotter.new_orders = []

            # if we have any new orders, record them so that we know
            # in what perf period they were placed.
            for new_order in new_orders:
                metrics_tracker.process_order(new_order)

        def once_a_day(midnight_dt, current_data=self.current_data,
                       data_portal=self.data_portal):
            # process any capital changes that came overnight
            for capital_change in algo.calculate_capital_changes(
                    midnight_dt, emission_rate=emission_rate,
                    is_interday=True):
                yield capital_change

            # set all the timestamps
            self.simulation_dt = midnight_dt
            algo.on_dt_changed(midnight_dt)

            metrics_tracker.handle_market_open(
                midnight_dt,
                algo.data_portal,
            )

            # handle any splits that impact any positions or any open orders.
            assets_we_care_about = (
                    viewkeys(metrics_tracker.positions) |
                    viewkeys(algo.blotter.open_orders)
            )

            if assets_we_care_about:
                splits = data_portal.get_splits(assets_we_care_about,
                                                midnight_dt)
                if splits:
                    algo.blotter.process_splits(splits)
                    metrics_tracker.handle_splits(splits)

        def on_exit():
            # Remove references to algo, data portal, et al to break cycles
            # and ensure deterministic cleanup of these objects when the
            # simulation finishes.
            self.algo = None
            self.benchmark_source = self.current_data = self.data_portal = None

        with ExitStack() as stack:
            stack.callback(on_exit)
            stack.enter_context(self.processor)
            stack.enter_context(ZiplineAPI(self.algo))

            if algo.data_frequency == 'minute':
                def execute_order_cancellation_policy():
                    algo.blotter.execute_cancel_policy(SESSION_END)

                def calculate_minute_capital_changes(dt):
                    # process any capital changes that came between the last
                    # and current minutes
                    return algo.calculate_capital_changes(
                        dt, emission_rate=emission_rate, is_interday=False)
            else:
                def execute_order_cancellation_policy():
                    pass

                def calculate_minute_capital_changes(dt):
                    return []

            for dt, action in self.clock:
                if action == BAR:
                    for capital_change_packet in every_bar(dt):
                        yield capital_change_packet
                elif action == SESSION_START:
                    for capital_change_packet in once_a_day(dt):
                        yield capital_change_packet
                elif action == SESSION_END:
                    # End of the session.
                    positions = metrics_tracker.positions
                    position_assets = algo.asset_finder.retrieve_all(positions)
                    self._cleanup_expired_assets(dt, position_assets)

                    execute_order_cancellation_policy()
                    algo.validate_account_controls()

                    yield self._get_daily_message(dt, algo, metrics_tracker)
                elif action == BEFORE_TRADING_START_BAR:
                    self.simulation_dt = dt
                    algo.on_dt_changed(dt)
                    algo.before_trading_start(self.current_data)
                elif action == MINUTE_END:
                    minute_msg = self._get_minute_message(
                        dt,
                        algo,
                        metrics_tracker,
                    )

                    yield minute_msg

            risk_message = metrics_tracker.handle_simulation_end(
                self.data_portal,
            )
            yield risk_message

    def _cleanup_expired_assets(self, dt, position_assets):
        """
        Clear out any assets that have expired before starting a new sim day.

        Performs two functions:

        1. Finds all assets for which we have open orders and clears any
           orders whose assets are on or after their auto_close_date.

        2. Finds all assets for which we have positions and generates
           close_position events for any assets that have reached their
           auto_close_date.
        """

        def past_auto_close_date(asset):
            acd = asset.auto_close_date
            return acd is not None and acd <= dt

        # Remove positions in any sids that have reached their auto_close date.
        assets_to_clear = \
            [asset for asset in position_assets if past_auto_close_date(asset)]
        metrics_tracker = algo.metrics_tracker
        data_portal = self.data_portal
        for asset in assets_to_clear:
            metrics_tracker.process_close_position(asset, dt, data_portal)

        # Remove open orders for any sids that have reached their auto close
        # date. These orders get processed immediately because otherwise they
        # would not be processed until the first bar of the next day.
        blotter = algo.blotter
        assets_to_cancel = [
            asset for asset in blotter.open_orders
            if past_auto_close_date(asset)
        ]
        for asset in assets_to_cancel:
            blotter.cancel_all_orders_for_asset(asset)

        # Make a copy here so that we are not modifying the list that is being
        # iterated over.
        for order in copy(blotter.new_orders):
            if order.status == ORDER_STATUS.CANCELLED:
                metrics_tracker.process_order(order)
                blotter.new_orders.remove(order)