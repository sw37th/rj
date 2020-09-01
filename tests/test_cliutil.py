from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import mock_open, patch, MagicMock
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
        FIXME
        """
        return True

    def test_parse_date(self):
        """
        'YYYY/MM/DD'
        """
        datestr1 = '2020/09/01'
        expect1 = datetime(year=2020, month=9, day=1)
        result1 = cliutil.parse_date(datestr1)
        self.assertEqual(result1, expect1)

        """
        'MM/DD'
        """
        datestr2 = '09/01'
        expect2 = datetime(year=2020, month=9, day=1)
        result2 = cliutil.parse_date(datestr2)
        self.assertEqual(result2, expect2)

        with freeze_time("2020-12-01"):
            """
            年またぎ録画予約
            """
            datestr3 = '01/01'
            expect3 = datetime(year=2021, month=1, day=1)
            result3 = cliutil.parse_date(datestr3)
            self.assertEqual(result3, expect3)

        """
        'sun|mon|tue|wed|thu|fri|sat'
        """
        with freeze_time("2020-09-01"):
            """
            日付を2020/09/01 火曜日に固定
            """
            datestr4 = 'tue'
            expect4 = datetime(year=2020, month=9, day=1)
            result4 = cliutil.parse_date(datestr4)
            self.assertEqual(result4, expect4)

            datestr6 = 'WED'
            expect6 = datetime(year=2020, month=9, day=2)
            result6 = cliutil.parse_date(datestr6)
            self.assertEqual(result6, expect6)

            datestr7 = 'tHU'
            expect7 = datetime(year=2020, month=9, day=3)
            result7 = cliutil.parse_date(datestr7)
            self.assertEqual(result7, expect7)

            datestr8 = 'frI'
            expect8 = datetime(year=2020, month=9, day=4)
            result8 = cliutil.parse_date(datestr8)
            self.assertEqual(result8, expect8)

            datestr9 = 'sAt'
            expect9 = datetime(year=2020, month=9, day=5)
            result9 = cliutil.parse_date(datestr9)
            self.assertEqual(result9, expect9)

            datestr10 = 'SUn'
            expect10 = datetime(year=2020, month=9, day=6)
            result10 = cliutil.parse_date(datestr10)
            self.assertEqual(result10, expect10)

            datestr11 = 'Mon'
            expect11 = datetime(year=2020, month=9, day=7)
            result11 = cliutil.parse_date(datestr11)
            self.assertEqual(result11, expect11)

        """
        'today'
        """
        with freeze_time("2020-09-01"):
            """
            日付を2020/09/01 火曜日に固定
            """
            datestr12 = 'today'
            expect12 = datetime(year=2020, month=9, day=1)
            result12 = cliutil.parse_date(datestr12)
            self.assertEqual(result12, expect12)

            datestr13 = 'TODAY'
            expect13 = datetime(year=2020, month=9, day=1)
            result13 = cliutil.parse_date(datestr13)
            self.assertEqual(result13, expect13)

        """
        '+n'
        """
        with freeze_time("2020-09-01"):
            """
            日付を2020/09/01 火曜日に固定
            """
            datestr14 = '+7'
            expect14 = datetime(year=2020, month=9, day=8)
            result14 = cliutil.parse_date(datestr14)
            self.assertEqual(result14, expect14)

        """
        invalid value
        """
        datestr15 = ''
        result15 = cliutil.parse_date(datestr15)
        self.assertIsNone(result15)

        datestr16 = '1'
        result16 = cliutil.parse_date(datestr16)
        self.assertIsNone(result16)

        datestr17 = '2020/2020/2020'
        result17 = cliutil.parse_date(datestr17)
        self.assertIsNone(result17)

        datestr18 = '2020/09/01/02'
        result18 = cliutil.parse_date(datestr18)
        self.assertIsNone(result18)

        datestr19 = '2020/20/40'
        result19 = cliutil.parse_date(datestr19)
        self.assertIsNone(result19)

    def test_parse_time(self):
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

        """
        '秒数'
        """
        timestr = '1770'
        expect = timedelta(minutes=29, seconds=30)
        result = cliutil.parse_time(timestr)
        self.assertEqual(result, expect)

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

    def test_parse_time_delta(self):
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
