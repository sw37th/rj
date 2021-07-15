from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import mock_open, patch, MagicMock, DEFAULT
from freezegun import freeze_time
import cliutil

class CliUtilTest(TestCase):
    def setUp(self):
        super(CliUtilTest, self).setUp()
        self.maxDiff = None

    def tearDown(self):
        super(CliUtilTest, self).tearDown()

    """
    現在時刻を2020年09月01日 00時00分00秒に固定
    """
    @freeze_time('2020-09-01 00:00:00')
    def test_is_future(self):
        """
        現在時刻より未来のdatetimeオブジェクトはTrue
        過去のdatetimeオブジェクトはFalseを返す
        """
        # true case
        future_begin = datetime(
            year=2020, month=9, day=2, hour=0, minute=0, second=0)
        self.assertTrue(cliutil.is_future(future_begin))

        boundary_future_begin = datetime(
            year=2020, month=9, day=1, hour=0, minute=0, second=1)
        self.assertTrue(cliutil.is_future(boundary_future_begin))

        # false case
        past_begin = datetime(
            year=2020, month=8, day=31, hour=0, minute=0, second=0)
        self.assertFalse(cliutil.is_future(past_begin))

        sametime_begin = datetime(
            year=2020, month=9, day=1, hour=0, minute=0, second=0)
        self.assertFalse(cliutil.is_future(sametime_begin))

    def test_parse_start_time(self):
        """
        parse_date(), parse_time()が適切な引数で呼ばれることを確認
        wormup_sec秒分だけ前倒しされていることを確認
        """
        datestr = '2020/09/01'
        timestr = '01:00:00'

        """
        without wormup_sec, day_change_hour
        """
        with patch.multiple(
            'cliutil',
            parse_date=DEFAULT,
            parse_time=DEFAULT) as functions:

            functions['parse_date'].return_value = datetime(
                year=2020, month=9, day=1)
            functions['parse_time'].return_value = timedelta(hours=1)

            result = cliutil.parse_start_time(datestr, timestr)
            expect = datetime(year=2020, month=9, day=1, hour=1)

            functions['parse_date'].assert_called_once_with(datestr, 0)
            functions['parse_time'].assert_called_once_with(timestr)
            self.assertEqual(result, expect)

        """
        with wormup_sec=30, without day_change_hour
        """
        with patch.multiple(
            'cliutil',
            parse_date=DEFAULT,
            parse_time=DEFAULT) as functions:

            functions['parse_date'].return_value = datetime(
                year=2020, month=9, day=1)
            functions['parse_time'].return_value = timedelta(hours=1)

            result = cliutil.parse_start_time(datestr, timestr, wormup_sec=30)
            expect = datetime(
                year=2020, month=9, day=1, hour=0, minute=59, second=30)

            functions['parse_date'].assert_called_once_with(datestr, 0)
            functions['parse_time'].assert_called_once_with(timestr)
            self.assertEqual(result, expect)

        """
        with day_change_hour=2, without wormup_sec
        """
        with patch.multiple(
            'cliutil',
            parse_date=DEFAULT,
            parse_time=DEFAULT) as functions:

            functions['parse_date'].return_value = datetime(
                year=2020, month=9, day=1)
            functions['parse_time'].return_value = timedelta(hours=1)

            result = cliutil.parse_start_time(
                datestr, timestr, day_change_hour=2)
            expect = datetime(year=2020, month=9, day=1, hour=1)

            functions['parse_date'].assert_called_once_with(datestr, 2)
            functions['parse_time'].assert_called_once_with(timestr)
            self.assertEqual(result, expect)

        """
        with wormup_sec=30, day_change_hour=2
        """
        with patch.multiple(
            'cliutil',
            parse_date=DEFAULT,
            parse_time=DEFAULT) as functions:

            functions['parse_date'].return_value = datetime(year=2020, month=9, day=1)
            functions['parse_time'].return_value = timedelta(hours=1)

            result = cliutil.parse_start_time(
                    datestr, timestr, wormup_sec=30, day_change_hour=2)
            expect = datetime(
                year=2020, month=9, day=1, hour=0, minute=59, second=30)

            functions['parse_date'].assert_called_once_with(datestr, 2)
            functions['parse_time'].assert_called_once_with(timestr)
            self.assertEqual(result, expect)

    def test_parse_date_yyyymmdd(self):
        """
        YYYY/MM/DD or MM/DD
        """
        with patch('cliutil._yyyymmdd') as mock:
            datestr = '2020/09/01'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '2020/9/01'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '2020/09/1'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '2020/9/1'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '09/01'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '9/01'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '09/1'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

        with patch('cliutil._yyyymmdd') as mock:
            datestr = '9/1'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr)

    def test_parse_date_weekday(self):
        """
        'sun|mon|tue|wed|thu|fri|sat'
        """
        with patch('cliutil._weekday') as mock:
            datestr = 'Sun'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'mOn'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'tuE'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'wed'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'THu'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'fRI'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'SAT'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(datestr, 0)

        with patch('cliutil._weekday') as mock:
            datestr = 'sun'
            cliutil.parse_date(datestr, day_change_hour=5)
            mock.assert_called_once_with(datestr, 5)

        with patch('cliutil._weekday') as mock:
            datestr = 'MON'
            cliutil.parse_date(datestr, 2)
            mock.assert_called_once_with(datestr, 2)

    def test_parse_date_today(self):
        """
        'today'
        """
        with patch('cliutil._today') as mock:
            datestr = 'today'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(0)

        with patch('cliutil._today') as mock:
            datestr = 'TODAY'
            cliutil.parse_date(datestr, day_change_hour=5)
            mock.assert_called_once_with(5)

    def test_parse_date_plusN(self):
        """
        '+N'
        """
        with patch('cliutil._days_from_today') as mock:
            datestr = '+1'
            cliutil.parse_date(datestr)
            mock.assert_called_once_with(1, 0)

        with patch('cliutil._days_from_today') as mock:
            datestr = '+3'
            cliutil.parse_date(datestr, day_change_hour=5)
            mock.assert_called_once_with(3, 5)

    def test_parse_date_invalid(self):
        """
        invalid value
        """
        with patch.multiple(
            'cliutil',
            _yyyymmdd=DEFAULT,
            _weekday=DEFAULT,
            _today=DEFAULT,
            _days_from_today=DEFAULT) as functions:

            result = cliutil.parse_date('')
            functions['_yyyymmdd'].assert_not_called()
            functions['_weekday'].assert_not_called()
            functions['_today'].assert_not_called()
            functions['_days_from_today'].assert_not_called()
            self.assertIsNone(result)

            result = cliutil.parse_date('1')
            functions['_yyyymmdd'].assert_not_called()
            functions['_weekday'].assert_not_called()
            functions['_today'].assert_not_called()
            functions['_days_from_today'].assert_not_called()
            self.assertIsNone(result)

            result = cliutil.parse_date('2020/2020/2020')
            functions['_yyyymmdd'].assert_not_called()
            functions['_weekday'].assert_not_called()
            functions['_today'].assert_not_called()
            functions['_days_from_today'].assert_not_called()
            self.assertIsNone(result)

            result = cliutil.parse_date('2020/09/01/02')
            functions['_yyyymmdd'].assert_not_called()
            functions['_weekday'].assert_not_called()
            functions['_today'].assert_not_called()
            functions['_days_from_today'].assert_not_called()
            self.assertIsNone(result)

    def test_yyyymmdd_yyyymmdd(self):
        """
        'YYYY/MM/DD'
        """
        datestr = '2020/09/01'
        expect = datetime(year=2020, month=9, day=1)
        result = cliutil._yyyymmdd(datestr)
        self.assertEqual(result, expect)

    def test_yyyymmdd_mmdd(self):
        """
        'MM/DD'
        """
        with freeze_time("2020-09-01"):
            datestr = '09/01'
            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._yyyymmdd(datestr)
            self.assertEqual(result, expect)

    def test_yyyymmdd_nextyear(self):
        """
        年またぎ録画予約
        """
        with freeze_time("2020-12-01"):
            datestr = '01/01'
            expect = datetime(year=2021, month=1, day=1)
            result = cliutil._yyyymmdd(datestr)
            self.assertEqual(result, expect)

    def test_yyyymmdd_invalid_date(self):
        """
        Invalid Date
        """
        datestr = '2020/20/40'
        result = cliutil._yyyymmdd(datestr)
        self.assertIsNone(result)

    def test_weekday(self):
        """
        'sun|mon|tue|wed|thu|fri|sat'
        """
        with freeze_time("2020-09-01 00:00:00"):
            """
            現在時刻を2020/09/01 00:00:00 火曜日に固定
            """
            datestr = 'tue'
            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

            datestr = 'WED'
            expect = datetime(year=2020, month=9, day=2)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

            datestr = 'tHU'
            expect = datetime(year=2020, month=9, day=3)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

            datestr = 'frI'
            expect = datetime(year=2020, month=9, day=4)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

            datestr = 'sAt'
            expect = datetime(year=2020, month=9, day=5)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

            datestr = 'SUn'
            expect = datetime(year=2020, month=9, day=6)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

            datestr = 'Mon'
            expect = datetime(year=2020, month=9, day=7)
            result = cliutil._weekday(datestr)
            self.assertEqual(result, expect)

    def test_weekday_2am(self):
        """
        day_change_hour=2
        """
        with freeze_time("2020-09-01 00:00:00"):    # 8/31 Mon 24:00
            datestr = 'Mon'
            expect = datetime(year=2020, month=8, day=31)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-02 00:00:00"):    # 9/1 Tue 24:00
            datestr = 'Tue'
            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-03 00:00:00"):    # 9/2 Wed 24:00
            datestr = 'Wed'
            expect = datetime(year=2020, month=9, day=2)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-04 00:00:00"):    # 9/3 Thu 24:00
            datestr = 'Thu'
            expect = datetime(year=2020, month=9, day=3)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-05 00:00:00"):    # 9/4 Fri 24:00
            datestr = 'Fri'
            expect = datetime(year=2020, month=9, day=4)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-06 00:00:00"):    # 9/5 Sat 24:00
            datestr = 'Sat'
            expect = datetime(year=2020, month=9, day=5)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-07 00:00:00"):    # 9/6 Sun 24:00
            datestr = 'Sun'
            expect = datetime(year=2020, month=9, day=6)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 00:00:00"):    # 8/31 Mon 24:00
            datestr = 'Tue'
            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 01:59:59"):    # 8/31 Mon 25:59:59
            """
            現在時刻がday_change_hour=2未満なので前曜日扱い
            """
            datestr = 'Mon'
            expect = datetime(year=2020, month=8, day=31)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 02:00:00"):    # 9/1 Tue 02:00:00
            """
            現在時刻がday_change_hour=2を過ぎたので翌週曜日扱い
            """
            datestr = 'Mon'
            expect = datetime(year=2020, month=9, day=7)
            result = cliutil._weekday(datestr, day_change_hour=2)
            self.assertEqual(result, expect)

    def test_today(self):
        """
        'today'
        """
        with freeze_time("2020-09-01 00:00:00"):
            """
            現在時刻を2020/09/01 00:00:00 火曜日に固定
            """
            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._today()
            self.assertEqual(result, expect)

            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._today()
            self.assertEqual(result, expect)

    def test_today_2am(self):
        """
        day_change_hour=2
        """
        with freeze_time("2020-09-01 00:00:00"):
            """
            現在時刻を2020/09/01 00:00:00 火曜日に固定
            """
            expect = datetime(year=2020, month=8, day=31)
            result = cliutil._today(day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 01:00:00"):
            """
            現在時刻を2020/09/01 01:00:00 火曜日に固定
            """
            expect = datetime(year=2020, month=8, day=31)
            result = cliutil._today(day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 01:59:59"):
            """
            現在時刻を2020/09/01 01:59:59 火曜日に固定
            """
            expect = datetime(year=2020, month=8, day=31)
            result = cliutil._today(day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 02:00:00"):
            """
            現在時刻を2020/09/01 02:00:00 火曜日に固定
            """
            expect = datetime(year=2020, month=9, day=1)
            result = cliutil._today(day_change_hour=2)
            self.assertEqual(result, expect)

    def test_days_from_today(self):
        """
        '+n'
        """
        with freeze_time("2020-09-01 00:00:00"):
            """
            現在時刻を2020/09/01 00:00:00 火曜日に固定
            """
            days = 7

            expect = datetime(year=2020, month=9, day=8)
            result = cliutil._days_from_today(days)
            self.assertEqual(result, expect)

            """
            day_change_hour=2
            """
            expect = datetime(year=2020, month=9, day=7)
            result = cliutil._days_from_today(days, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 01:59:59"):
            """
            現在時刻を2020/09/01 01:59:59 火曜日に固定
            """
            expect = datetime(year=2020, month=9, day=7)
            result = cliutil._days_from_today(days, day_change_hour=2)
            self.assertEqual(result, expect)

        with freeze_time("2020-09-01 02:00:00"):
            """
            現在時刻を2020/09/01 02:00:00 火曜日に固定
            """
            expect = datetime(year=2020, month=9, day=8)
            result = cliutil._days_from_today(days, day_change_hour=2)
            self.assertEqual(result, expect)

    def test_parse_time_hhmmss(self):
        """
        HH:MM:SS
        """
        timestr = '01:00:00'
        expect = timedelta(hours=1)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

        timestr = '00:01:00'
        expect = timedelta(minutes=1)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

        timestr = '00:00:01'
        expect = timedelta(seconds=1)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

        timestr = '01:01:01'
        expect = timedelta(hours=1, minutes=1, seconds=1)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

        timestr = '23:59:59'
        expect = timedelta(hours=23, minutes=59, seconds=59)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

        timestr = '00:120:00'
        expect = timedelta(hours=2)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

    def test_parse_time_hhmm(self):
        """
        HH:MM
        """
        timestr = '01:10'
        expect = timedelta(hours=1, minutes=10)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

        timestr = '00:120'
        expect = timedelta(hours=2)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

    def test_parse_time_sec(self):
        """
        '秒数'
        """
        timestr = '1770'
        expect = timedelta(minutes=29, seconds=30)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

    def test_parse_time_invalid(self):
        """
        invalid strings
        """
        timestr = '00:hoge:00'
        result = cliutil.parse_time(timestr)
        self.assertIsNone(result)

        timestr = '00:hoge'
        result = cliutil.parse_time(timestr)
        self.assertIsNone(result)

        timestr = 'hoge:00'
        result = cliutil.parse_time(timestr)
        self.assertIsNone(result)

        timestr = 'hoge'
        result = cliutil.parse_time(timestr)
        self.assertIsNone(result)

        timestr = '01:01:01:01'
        result = cliutil.parse_time(timestr)
        self.assertIsNone(result)

    def test_parse_time_delta_hhmmss(self):
        """
        HH:MM:SS[+-]
        """
        timestr = '01:00:00+'
        expect = timedelta(hours=1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '01:00:00-'
        expect = timedelta(hours=-1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '00:01:00+'
        expect = timedelta(minutes=1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '00:01:00-'
        expect = timedelta(minutes=-1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '00:00:01+'
        expect = timedelta(seconds=1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '00:00:01-'
        expect = timedelta(seconds=-1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

    def test_parse_time_delta_hhmm(self):
        """
        HH:MM[+-]
        """
        timestr = '01:00+'
        expect = timedelta(hours=1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '01:00-'
        expect = timedelta(hours=-1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '00:01+'
        expect = timedelta(minutes=1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '00:01-'
        expect = timedelta(minutes=-1)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

    def test_parse_time_delta_sec(self):
        """
        seconds[+-]
        """
        timestr = '1770+'
        expect = timedelta(minutes=29, seconds=30)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

        timestr = '1770-'
        expect = timedelta(minutes=-29, seconds=-30)
        result = cliutil.parse_time_delta(timestr)
        self.assertEqual(result, expect)

    def test_parse_time_delta_invalid(self):
        """
        invalid strings
        """
        timestr = '01:01:01'
        result = cliutil.parse_time_delta(timestr)
        self.assertIsNone(result)

        timestr = '01:01:01*'
        result = cliutil.parse_time_delta(timestr)
        self.assertIsNone(result)

        timestr = '01:01'
        result = cliutil.parse_time_delta(timestr)
        self.assertIsNone(result)

        timestr = '1770'
        result = cliutil.parse_time_delta(timestr)
        self.assertIsNone(result)

        timestr = '01:01:01:01+'
        result = cliutil.parse_time_delta(timestr)
        self.assertIsNone(result)

        timestr = '01:01:01:01-'
        result = cliutil.parse_time_delta(timestr)
        self.assertIsNone(result)
