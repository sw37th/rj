from copy import deepcopy
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
        self.maxDiff = None

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
        """
        ジョブスクリプトのフォーマットチェック
        """
        tt_name_expected = '/home/autumn/jobsh/tt_test.202008120134.30.1597071600.0.sh'
        tt_body_expected = dedent('''\
            #PBS -N 15.tt_test
            #PBS -a 202008120134.30
            #PBS -l walltime=1770
            #PBS -l tt=1
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
            #PBS -l bs=1
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

    """
    現在時刻を2020年08月16日 20時03分00秒(1597575780)に固定
    """
    @freeze_time('2020-08-16 20:03:00')
    def test_get_job_info_all(self):
        """
        qstatコマンドの出力から内部的なジョブ情報リストに変換されることを確認
        """
        # qstatコマンド出力のダミー
        # 2020年08月16日 20時03分00秒(1597575780)の時点で
        #   68: 衛星放送 待機中(W)
        #   69: 衛星放送 録画中(R)
        #   70: 地上波 待機中(W)
        #   71: 地上波 録画中(R)
        qstat_out = dedent("""\
            {
                "Jobs":{
                    "68.openpbs":{
                        "Job_Name":"181.bs_wait",
                        "job_state":"W",
                        "ctime":"Sun Aug 16 17:11:02 2020",
                        "Execution_Time":"Tue Aug 18 23:59:50 2020",
                        "mtime":"Sun Aug 16 17:11:02 2020",
                        "qtime":"Sun Aug 16 17:11:02 2020",
                        "Resource_List":{
                            "bs":"1",
                            "walltime":"00:29:30"},
                        "euser":"autumn",
                        "egroup":"autumn"},
                    "69.openpbs":{
                        "Job_Name":"181.bs_run",
                        "job_state":"R",
                        "ctime":"Sun Aug 16 20:01:16 2020",
                        "exec_host":"openpbs/0",
                        "mtime":"Sun Aug 16 20:03:24 2020",
                        "qtime":"Sun Aug 16 20:01:16 2020",
                        "Resource_List":{
                            "bs":"1",
                            "walltime":"00:29:30"},
                        "stime":"Sun Aug 16 20:01:50 2020",
                        "euser":"autumn",
                        "egroup":"autumn",
                        "etime":"Sun Aug 16 20:01:50 2020"},
                    "70.openpbs":{
                        "Job_Name":"25.tt_wait",
                        "job_state":"W",
                        "ctime":"Sun Aug 16 17:11:02 2020",
                        "Execution_Time":"Tue Aug 18 23:59:50 2020",
                        "mtime":"Sun Aug 16 17:11:02 2020",
                        "qtime":"Sun Aug 16 17:11:02 2020",
                        "Resource_List":{
                            "tt":"1",
                            "walltime":"00:29:30"},
                        "euser":"autumn",
                        "egroup":"autumn"},
                    "71.openpbs":{
                        "Job_Name":"25.tt_run",
                        "job_state":"R",
                        "ctime":"Sun Aug 16 20:01:16 2020",
                        "exec_host":"openpbs/0",
                        "mtime":"Sun Aug 16 20:03:24 2020",
                        "qtime":"Sun Aug 16 20:01:16 2020",
                        "Resource_List":{
                            "tt":"1",
                            "walltime":"00:29:30"},
                        "stime":"Sun Aug 16 20:01:50 2020",
                        "euser":"autumn",
                        "egroup":"autumn",
                        "etime":"Sun Aug 16 20:01:50 2020"}}}""")
        joblist_expected = [
            {
                'rj_id': '69',
                'channel': '181',
                'rj_title': 'bs_run',
                'walltime': timedelta(0, 1770),
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50),
                'elapse': timedelta(0, 70, 0),
                'exec_host': 'openpbs',
                'rec_end': datetime(2020, 8, 16, 20, 31, 20),
                'record_state': 'Recording',
                'tuner': 'bs',
                'user': 'autumn',
                'group': 'autumn',
                'qtime': datetime(2020, 8, 16, 20, 1, 16),
                'ctime': datetime(2020, 8, 16, 20, 1, 16),
                'mtime': datetime(2020, 8, 16, 20, 3, 24),
                'alert': ''},
            {
                'rj_id': '71',
                'channel': '25',
                'rj_title': 'tt_run',
                'walltime': timedelta(0, 1770),
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50),
                'elapse': timedelta(0, 70, 0),
                'exec_host': 'openpbs',
                'rec_end': datetime(2020, 8, 16, 20, 31, 20),
                'record_state': 'Recording',
                'tuner': 'tt',
                'user': 'autumn',
                'group': 'autumn',
                'qtime': datetime(2020, 8, 16, 20, 1, 16),
                'ctime': datetime(2020, 8, 16, 20, 1, 16),
                'mtime': datetime(2020, 8, 16, 20, 3, 24),
                'alert': ''},
            {
                'rj_id': '68',
                'channel': '181',
                'rj_title': 'bs_wait',
                'walltime': timedelta(0, 1770),
                'rec_begin': datetime(2020, 8, 18, 23, 59, 50),
                'rec_end': datetime(2020, 8, 19, 0, 29, 20),
                'record_state': 'Waiting',
                'tuner': 'bs',
                'user': 'autumn',
                'group': 'autumn',
                'qtime': datetime(2020, 8, 16, 17, 11, 2),
                'ctime': datetime(2020, 8, 16, 17, 11, 2),
                'mtime': datetime(2020, 8, 16, 17, 11, 2),
                'alert': ''},
            {
                'rj_id': '70',
                'channel': '25',
                'rj_title': 'tt_wait',
                'walltime': timedelta(0, 1770),
                'rec_begin': datetime(2020, 8, 18, 23, 59, 50),
                'rec_end': datetime(2020, 8, 19, 0, 29, 20),
                'record_state': 'Waiting',
                'tuner': 'tt',
                'user': 'autumn',
                'group': 'autumn',
                'qtime': datetime(2020, 8, 16, 17, 11, 2),
                'ctime': datetime(2020, 8, 16, 17, 11, 2),
                'mtime': datetime(2020, 8, 16, 17, 11, 2),
                'alert': ''}]
        proc = MagicMock()
        proc.stdout = qstat_out
        self.rec._run_command = MagicMock(return_value=proc)

        self.rec._get_job_info_all()
        self.assertEqual(self.rec.joblist, joblist_expected)

    def test_get_job_info(self):
        """
        get_job_info()の引数に応じたジョブ情報のリストが返ってくることを確認
        """
        joblist_all = [
            {
                'rj_id': '69',
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50)},
            {
                'rj_id': '71',
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50)},
            {
                'rj_id': '68',
                'rec_begin': datetime(2020, 8, 18, 23, 59, 50)},
            {
                'rj_id': '70',
                'rec_begin': datetime(2020, 8, 18, 23, 59, 50)}]
        expected_jid69 = [
            {
                'rj_id': '69',
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50)}]
        expected_jid72 = []
        expected_aug16 = [
            {
                'rj_id': '69',
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50)},
            {
                'rj_id': '71',
                'rec_begin': datetime(2020, 8, 16, 20, 1, 50)}]
        expected_aug17 = []
        expected_aug18 = [
            {
                'rj_id': '68',
                'rec_begin': datetime(2020, 8, 18, 23, 59, 50)},
            {
                'rj_id': '70',
                'rec_begin': datetime(2020, 8, 18, 23, 59, 50)}]

        self.rec._get_job_info_all = MagicMock()
        self.rec._check_tuner_resource = MagicMock()
        self.rec.joblist = joblist_all

        # ジョブID指定
        joblist = self.rec.get_job_info(jid='69')
        self.assertEqual(joblist, expected_jid69)
        joblist = self.rec.get_job_info(jid='72')
        self.assertEqual(joblist, expected_jid72)

        # 日付指定
        joblist = self.rec.get_job_info(date=datetime(2020, 8, 16, 0, 0, 0))
        self.assertEqual(joblist, expected_aug16)
        joblist = self.rec.get_job_info(date=datetime(2020, 8, 17, 0, 0, 0))
        self.assertEqual(joblist, expected_aug17)
        joblist = self.rec.get_job_info(date=datetime(2020, 8, 18, 0, 0, 0))
        self.assertEqual(joblist, expected_aug18)

        # 指定なし
        joblist = self.rec.get_job_info()
        self.assertEqual(joblist, joblist_all)

    def test_get_tuner_num(self):
        """
        pbsnodesコマンドの出力に応じてカスタムリソース'bs'、'tt'が
        集計されることを確認
        """
        proc = MagicMock()
        self.rec._run_command = MagicMock(return_value=proc)

        # 録画ノードが1台
        pbsnodes_single = dedent("""\
            {
                "nodes":{
                    "node1":{
                        "state":"free",
                        "resources_available":{
                            "bs":2,
                            "tt":2}}}}""")
        expected_single = {'bs': 2, 'tt': 2}
        with patch.dict(self.rec.tuners, {'tt': 0, 'bs': 0}, clear=True):
            proc.stdout = pbsnodes_single
            self.rec._get_tuner_num()
            self.assertEqual(self.rec.tuners, expected_single)

        # 録画ノードが複数台
        pbsnodes_multi = dedent("""\
            {
                "nodes":{
                    "node1":{
                        "state":"free",
                        "resources_available":{
                            "bs":2,
                            "tt":2}},
                    "node2":{
                        "state":"free",
                        "resources_available":{
                            "bs":4,
                            "tt":4}}}}""")
        expected_multi = {'bs': 6, 'tt': 6}
        with patch.dict(self.rec.tuners, {'tt': 0, 'bs': 0}, clear=True):
            proc.stdout = pbsnodes_multi
            self.rec._get_tuner_num()
            self.assertEqual(self.rec.tuners, expected_multi)

        # 録画ノードが複数台、チューナー数が異なる
        pbsnodes_multi_hetero = dedent("""\
            {
                "nodes":{
                    "node1":{
                        "state":"free",
                        "resources_available":{
                            "bs":3,
                            "tt":1}},
                    "node2":{
                        "state":"free",
                        "resources_available":{
                            "bs":2,
                            "tt":6}}}}""")
        expected_multi_hetero = {'bs': 5, 'tt': 7}
        with patch.dict(self.rec.tuners, {'tt': 0, 'bs': 0}, clear=True):
            proc.stdout = pbsnodes_multi_hetero
            self.rec._get_tuner_num()
            self.assertEqual(self.rec.tuners, expected_multi_hetero)

        # 録画ノードが複数台、free/job-busy以外の状態のノードが含まれる
        pbsnodes_include_offline = dedent("""\
            {
                "nodes":{
                    "node1":{
                        "state":"free",
                        "resources_available":{
                            "bs":4,
                            "tt":1}},
                    "node2":{
                        "state":"offline",
                        "resources_available":{
                            "bs":2,
                            "tt":2}},
                    "node3":{
                        "state":"free",
                        "resources_available":{
                            "bs":2,
                            "tt":6}}}}""")
        expected_include_offline = {'bs': 6, 'tt': 7}
        with patch.dict(self.rec.tuners, {'tt': 0, 'bs': 0}, clear=True):
            proc.stdout = pbsnodes_include_offline
            self.rec._get_tuner_num()
            self.assertEqual(self.rec.tuners, expected_include_offline)

        # 録画ノードが複数台、free/job-busy状態のノードのみ
        pbsnodes_include_jobbusy = dedent("""\
            {
                "nodes":{
                    "node1":{
                        "state":"free",
                        "resources_available":{
                            "bs":2,
                            "tt":3}},
                    "node2":{
                        "state":"free",
                        "resources_available":{
                            "bs":4,
                            "tt":4}},
                    "node3":{
                        "state":"job-busy",
                        "resources_available":{
                            "bs":3,
                            "tt":1}}}}""")
        expected_include_jobbusy = {'bs': 9, 'tt': 8}
        with patch.dict(self.rec.tuners, {'tt': 0, 'bs': 0}, clear=True):
            proc.stdout = pbsnodes_include_jobbusy
            self.rec._get_tuner_num()
            self.assertEqual(self.rec.tuners, expected_include_jobbusy)

    def test_check_tuner_resource(self):
        """
        同時録画数がチューナー数を超えた場合に
        当該ジョブのalert属性に警告文がつくことを確認
        """
        message = 'Out of Tuners. Max: 2'
        self.rec._get_tuner_num = MagicMock()
        self.rec.tuners = {'tt': 2, 'bs': 2}

        # 'tt'、'bs'ともに同時録画数がチューナー数以内
        joblist_no_exceeded = [
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 23, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 23, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 23, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 23, 59, 59),
                'tuner': 'bs',
                'alert': ''}]
        expected_no_exceeded = ['', '', '', '', '', '']

        self.rec.joblist = joblist_no_exceeded
        self.rec._check_tuner_resource()

        alerts = [i.get('alert') for i in self.rec.joblist]
        self.assertEqual(alerts, expected_no_exceeded)

        # 'tt'の同時録画数がチューナー数を超過
        joblist_exceeded_tt = [
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 23, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 23, 59, 59),
                'tuner': 'bs',
                'alert': ''}]
        expected_exceeded_tt = [message, message, message, '', '', '']

        self.rec.joblist = joblist_exceeded_tt
        self.rec._check_tuner_resource()

        alerts = [i.get('alert') for i in self.rec.joblist]
        self.assertEqual(alerts, expected_exceeded_tt)

        # 'bs'の同時録画数がチューナー数を超過
        joblist_exceeded_bs = [
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 23, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 23, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'bs',
                'alert': ''}]
        expected_exceeded_bs = ['', '', '', message, message, message]

        self.rec.joblist = joblist_exceeded_bs
        self.rec._check_tuner_resource()

        alerts = [i.get('alert') for i in self.rec.joblist]
        self.assertEqual(alerts, expected_exceeded_bs)

        # 境界値チェック。チューナー数以内
        joblist_boundary_no_exceeded = [
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 29, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 29, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 30, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 30, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''}]
        expected_boundary_no_exceeded = ['', '', '', '']

        self.rec.joblist = joblist_boundary_no_exceeded
        self.rec._check_tuner_resource()

        alerts = [i.get('alert') for i in self.rec.joblist]
        self.assertEqual(alerts, expected_boundary_no_exceeded)

        # 境界値チェック。チューナー数を超過
        joblist_boundary_exceeded = [
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 30, 00),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 00, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 30, 00),
                'tuner': 'tt',
                'alert': ''},
            {
                'rec_begin': datetime(2020, 8, 16, 22, 30, 00),
                'rec_end':   datetime(2020, 8, 16, 22, 59, 59),
                'tuner': 'tt',
                'alert': ''}]
        expected_boundary_exceeded = [message, message, message]

        self.rec.joblist = joblist_boundary_exceeded
        self.rec._check_tuner_resource()

        alerts = [i.get('alert') for i in self.rec.joblist]
        self.assertEqual(alerts, expected_boundary_exceeded)
