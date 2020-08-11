from unittest import TestCase
from rjsched import RecordJobOpenpbs as rjo
from unittest.mock import mock_open, patch, MagicMock, call
from datetime import datetime, timedelta
from subprocess import PIPE, STDOUT, DEVNULL
from textwrap import dedent
from freezegun import freeze_time

class RecordJobOpenpbsTest(TestCase):
    def setUp(self):
        super(RecordJobOpenpbsTest, self).setUp()
        self.rec = rjo.RecordJobOpenpbs()

    def tearDown(self):
        super(RecordJobOpenpbsTest, self).tearDown()

    def test_classname(self):
        self.assertEqual(str(self.rec), 'RecordJobOpenpbs')

    def test_is_bs(self):
        self.assertTrue(self.rec._is_bs(64))
        self.assertFalse(self.rec._is_bs(63))

    """
    現在時刻を2020年08月11日 00時00分00秒(1597071600)に固定
    """
    @freeze_time('2020-08-11 00:00:00')
    def test_create_jobscript(self):

        tt_name_expected = '/home/autumn/jobsh/tt_test.202008120134.30.1597071600.0.sh'
        tt_body_expected = dedent('''\
            #PBS -N 15.tt_test
            #PBS -a 202008120134.30
            #PBS -l walltime=1770
            #PBS -j oe
            #PBS -o /home/autumn/log
            #PBS -e /home/autumn/log
            umask 022
            _jobid=`echo $PBS_JOBID | awk -F'.' '{printf("%05d", $1)}'`
            /usr/local/bin/recpt1 --b25 --strip 15 - /home/autumn/rec/tt_test.15.`date +%Y%m%d_%H%M.%S`.${_jobid}.ts
            ''')
        bs_name_expected = '/home/autumn/jobsh/bs_test.202008120134.30.1597071600.0.sh'
        bs_body_expected = dedent('''\
            #PBS -N 103.bs_test
            #PBS -a 202008120134.30
            #PBS -l walltime=1770
            #PBS -j oe
            #PBS -o /home/autumn/log
            #PBS -e /home/autumn/log
            umask 022
            _jobid=`echo $PBS_JOBID | awk -F'.' '{printf("%05d", $1)}'`
            /usr/local/bin/recpt1 --b25 --strip --lnb 15 103 - /home/autumn/rec/bs_test.103.`date +%Y%m%d_%H%M.%S`.${_jobid}.ts
            ''')

        begin = datetime(2020, 8, 12, 1, 34, 30)
        rectime = timedelta(seconds=1770)

        # 地上波用ジョブスクリプト作成
        with patch('rjsched.RecordJobOpenpbs.open', mock_open()) as mopen:
            name = self.rec._create_jobscript('15', 'tt_test', begin, rectime)
            handle = mopen()
            handle.write.assert_called_once_with(tt_body_expected)
            self.assertEqual(name, tt_name_expected)

        # BS用ジョブスクリプト作成
        with patch('rjsched.RecordJobOpenpbs.open', mock_open()) as mopen:
            name = self.rec._create_jobscript('103', 'bs_test', begin, rectime)
            handle = mopen()
            handle.write.assert_called_once_with(bs_body_expected)
            self.assertEqual(name, bs_name_expected)
