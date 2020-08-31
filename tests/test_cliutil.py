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
