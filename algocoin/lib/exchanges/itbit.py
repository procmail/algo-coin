import json
# import os
# import pprint
# import websocket
import threading
import queue
# import time
from websocket import create_connection
from datetime import datetime
from ..callback import Callback
from ..config import ExchangeConfig
from ..enums import TradingType, ExchangeType, TickType
from ..exchange import Exchange
from ...manual import manual
from ..structs import TradeRequest, TradeResponse, MarketData, Account
from ..utils import trade_req_to_params_gdax, parse_date, get_keys_from_environment, str_to_currency_type, str_to_side, str_to_order_type
from ..logging import LOG as log


class ItBitExchange(Exchange):
    def __init__(self, options: ExchangeConfig) -> None:
        super(ItBitExchange, self).__init__(options)
        self._type = ExchangeType.ITBIT
        self._last = None

        if options.trading_type == TradingType.LIVE:
            self._key, self._secret, self._passphrase = get_keys_from_environment('ITBIT')
            # self._client = GeminiSession(api_key=self._key, api_secret=self._secret, sandbox=False)

        val = self._client.get_balances() if hasattr(self, '_client') else ['BACKTEST']

        self._accounts = []
        for i, jsn in enumerate(val):
            currency = str_to_currency_type(jsn.get('currency'))
            balance = float(jsn.get('available', 'inf'))
            id = str(i)
            account = Account(id=id, currency=currency, balance=balance)
            self._accounts.append(account)

        # self._subscription = json.dumps({"type": "subscribe",
        #                                  "product_id": "BTC-USD"})
        # self._heartbeat = json.dumps({"type": "heartbeat",
        #                               "on": True})

        self._seqnum_enabled = False

    def run(self, engine) -> None:
        # DEBUG
        # websocket.enableTrace(True)

        while True:
            if not self._running and not self._manual:
                # startup and redundancy
                log.info('Starting....')
                self.ws = create_connection(self._md_url)
                log.info('Connected!')

                # self.ws.send(self._subscription)
                # log.info('Sending Subscription %s' % self._subscription)
                # self.ws.send(self._heartbeat)
                # log.info('Sending Heartbeat %s' % self._subscription)

                self._running = True

                t, inqueue, outqueue = None, None, None

                log.info('')
                log.info('Starting algo trading')
            try:
                while True:
                    self.receive()
                    engine.tick()
                    if self._manual and t and t.is_alive():
                        try:
                            x = outqueue.get(block=False)
                            if x:
                                if x[0] == 'c':
                                    if not self._running:
                                        log.warn('Continuing algo trading')

                                    self._running = True
                                    engine.continueTrading()

                                elif x[0] == 'h':
                                    if self._running:
                                        log.warn('Halting algo trading')

                                    self._running = False
                                    engine.haltTrading()

                                elif x[0] == 'q':
                                    log.critical('Terminating program')

                                    self.close()
                                    inqueue.put(1)

                                    self._manual = False

                                    t.join()
                                    t = None
                                    return

                                elif x[0] == 'r':
                                    log.critical('leaving manual')

                                    inqueue.put(1)

                                    self._manual = False

                                    t.join()
                                    t = None
                                elif x[0] == 'b':
                                    self.buy(x[1])
                                elif x[0] == 's':
                                    self.sell(x[1])
                                else:
                                    log.critical('manual override error')
                        except queue.Empty:
                            pass

                    elif self._manual and t:
                        log.critical('leaving manual')
                        self._manual = False

                        t.join()
                        t = None

            except KeyboardInterrupt:
                # x = manual(self)
                if not self._manual:
                    self._manual = True
                    inqueue = queue.Queue()
                    outqueue = queue.Queue()
                    t = threading.Thread(target=manual, args=(self, inqueue, outqueue,))
                    t.start()
                else:
                    log.critical('Terminating program')
                    inqueue.put(1)
                    t.join()
                    return

            # except Exception as e:
            #     log.critical(e)

            #     self.callback(TickType.ERROR, e)
            #     self.close()

            #     return

    def accounts(self) -> list:
        # return pprint.pformat(self._client.getAccounts()) if hasattr(self, '_client') else 'BACKTEST'
        return self._accounts

    def sendOrder(self, callback: Callback):
        '''send order to exchange'''

    def orderResponse(self, response):
        '''parse the response'''

    def orderBook(self, level=1):
        '''get order book'''
        return self._client.getProductOrderBook(level=level)

    def buy(self, req: TradeRequest) -> TradeResponse:
        '''execute a buy order'''
        params = trade_req_to_params_gdax(req)
        log.warn(str(params))
        # self._client.buy(params)

    def sell(self, req: TradeRequest) -> TradeResponse:
        '''execute a sell order'''
        params = trade_req_to_params_gdax(req)
        log.warn(str(params))
        # self._client.sell(params)

    def tickToData(self, jsn: dict) -> MarketData:
        print(jsn)
        time = datetime.now()
        price = float(jsn.get('price', 'nan'))
        reason = jsn.get('reason', '')
        volume = float(jsn.get('amount', 'nan'))
        typ = self.strToTradeType(jsn.get('type'))

        if typ == TickType.CHANGE and not volume:
            delta = float(jsn.get('delta', 'nan'))
            volume = delta
            typ = self.reasonToTradeType(reason)

        side = str_to_side(jsn.get('side', ''))
        remaining_volume = float(jsn.get('remaining', 'nan'))

        sequence = -1
        currency = str_to_currency_type('BTC')

        ret = MarketData(time=time,
                         volume=volume,
                         price=price,
                         type=typ,
                         currency=currency,
                         remaining=remaining_volume,
                         reason=reason,
                         side=side,
                         sequence=sequence)
        print(ret)
        return ret

    @staticmethod
    def strToTradeType(s: str) -> TickType:
        if s == 'trade':
            return TickType.TRADE
        elif s == 'change':
            return TickType.CHANGE
        elif s == 'heartbeat':
            return TickType.HEARTBEAT
        else:
            return TickType.ERROR
