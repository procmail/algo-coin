class TestBacktest:
    def setup(self):
        from config import BacktestConfig
        self.config = BacktestConfig()
        self.config.file = 'test'

        self.test_line = '1479272400,1,100'

    def teardown(self):
        pass
        # teardown() after each test method

    @classmethod
    def setup_class(cls):
        from callback import Callback

        class CallbackTester(Callback):
            def __init__(self):
                self._onMatch = True
                self._onReceived = True
                self._onOpen = True
                self._onDone = True
                self._onChange = True
                self._onError = True
                self._onAnalyze = True

            def onMatch(self, data):
                self._onMatch = True

            def onReceived(self, data):
                self._onReceived = True

            def onOpen(self, data):
                self._onOpen = True

            def onDone(self, data):
                self._onDone = True

            def onChange(self, data):
                self._onChange = True

            def onError(self, data):
                self._onError = True

            def onAnalyze(self, data):
                self._onAnalyze = True

        cls.demo_callback = CallbackTester

    @classmethod
    def teardown_class(cls):
        pass
        # teardown_class() after any methods in this class

    def test_init(self):
        from backtest import Backtest
        b = Backtest(self.config)
        assert b
        assert b._file == 'test'

    def test_receive(self):
        from backtest import Backtest

        b = Backtest(self.config)
        cb = self.demo_callback()

        b.registerCallback(cb)
        b._receive(self.test_line)
        assert cb._onMatch