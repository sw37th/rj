from copy import deepcopy
from unittest import TestCase
from rjsched import RecordJobOpenpbs as rjo
from unittest.mock import mock_open, patch, MagicMock
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

    def test_add(self):
        """
        録画予約ジョブ用qsubコマンドオプションと
        録画用recpt1コマンドオプションのチェック
        """
        proc = MagicMock()
        self.rec._run_command = MagicMock(return_value=proc)

        # 地上波
        expected_qsub_tt = [
            '/work/pbs/bin/qsub',
            '-N', 'test_tt.15',
            '-a', '202008192029.30',
            '-l', 'walltime=1770.0',
            '-l', 'tt=1',
            '-j', 'oe',
            '-o', '/home/autumn/log',
            '-W', 'umask=222',
            '-']
        expected_jobexec_tt = \
            '/usr/local/bin/recpt1 --b25 --strip '\
            '${PBS_JOBNAME##*.} - '\
            '/home/autumn/rec/${PBS_JOBNAME}.'\
            '$(date +%Y%m%d_%H%M.%S).${PBS_JOBID%.*}.ts'
        proc.stdout = '110.example.org'

        jid = self.rec.add('15', 'test_tt', datetime(2020, 8, 19, 20, 29, 30),
            timedelta(seconds=1770))

        self.rec._run_command.assert_called_with(
            command=expected_qsub_tt, _input=expected_jobexec_tt)
        self.assertEqual(jid, '110')

        # 衛星放送
        expected_qsub_tt = [
            '/work/pbs/bin/qsub',
            '-N', 'test_bs.211',
            '-a', '202008192029.30',
            '-l', 'walltime=1770.0',
            '-l', 'bs=1',
            '-j', 'oe',
            '-o', '/home/autumn/log',
            '-W', 'umask=222',
            '-']
        expected_jobexec_tt = \
            '/usr/local/bin/recpt1 --b25 --strip --lnb 15 '\
            '${PBS_JOBNAME##*.} - '\
            '/home/autumn/rec/${PBS_JOBNAME}.'\
            '$(date +%Y%m%d_%H%M.%S).${PBS_JOBID%.*}.ts'
        proc.stdout = '111.example.org'

        jid = self.rec.add('211', 'test_bs', datetime(2020, 8, 19, 20, 29, 30),
            timedelta(seconds=1770))

        self.rec._run_command.assert_called_with(
            command=expected_qsub_tt, _input=expected_jobexec_tt)
        self.assertEqual(jid, '111')

    def test_remove(self):
        """
        ジョブ削除の際のqdelコマンドと引数、戻り値を確認
        """
        self.rec._run_command = MagicMock()
        self.rec.get_job_info = MagicMock()
        jid = '1'

        # 引数のIDのジョブが存在する
        expected_joblist = [{'rj_id': jid}]
        expected_command = ['/work/pbs/bin/qdel', jid]

        self.rec.get_job_info.return_value = expected_joblist

        joblist = self.rec.remove(jid)
        self.rec._run_command.assert_called_with(expected_command)
        self.assertEqual(joblist, expected_joblist)

        # _run_commandのMagicMockをリセット
        self.rec._run_command.reset_mock()

        # 対象のジョブが存在しない場合は_run_command()を呼ばず空リストを返す
        self.rec.get_job_info.return_value = []

        joblist = self.rec.remove(jid)
        self.rec._run_command.assert_not_called()
        self.assertEqual(joblist, [])

    def test_change_begin(self):
        """
        録画開始時間変更の際のqalterコマンドと引数、戻り値を確認
        """
        self.rec._run_command = MagicMock()
        self.rec.get_job_info = MagicMock()
        jid = '1'

        begin = datetime(2020, 8, 16, 0, 0, 0)
        delta = timedelta(seconds=300)
        job = [{'rj_id': jid, 'rec_begin': begin}]

        expected_command = [
            '/work/pbs/bin/qalter', '-a', '202008160000.00', jid]

        expected_command_delta = [
            '/work/pbs/bin/qalter', '-a', '202008160005.00', jid]

        expected_job_exists = [
            {'rj_id': jid, 'rec_begin': begin},
            {'rj_id': jid, 'rec_begin': begin}]
        expected_job_notexists = []

        """
        引数のIDのジョブが存在する
        """
        # 開始時刻時刻指定
        self.rec.get_job_info.return_value = deepcopy(job)
        job_pair = self.rec.change_begin(jid, begin=begin)

        self.rec._run_command.assert_called_with(expected_command)
        self.assertEqual(job_pair, expected_job_exists)

        # 元の録画開始時間からの差分指定
        self.rec.get_job_info.return_value = deepcopy(job)
        job_pair = self.rec.change_begin(jid, delta=delta)

        self.rec._run_command.assert_called_with(expected_command_delta)
        self.assertEqual(job_pair, expected_job_exists)

        # _run_commandのMagicMockをリセット
        self.rec._run_command.reset_mock()

        """
        引数のIDのジョブが存在しない
        """
        self.rec.get_job_info.return_value = []

        # 開始時刻時刻指定
        job_pair = self.rec.change_begin(jid, begin=begin)

        self.rec._run_command.assert_not_called
        self.assertEqual(job_pair, expected_job_notexists)

        # 元の録画開始時間からの差分指定
        job_pair = self.rec.change_begin(jid, delta=delta)

        self.rec._run_command.assert_not_called
        self.assertEqual(job_pair, expected_job_notexists)

    def test_change_retime(self):
        """
        録画時間変更の際のqalterコマンドと引数、戻り値を確認
        """
        self.rec._run_command = MagicMock()
        self.rec.get_job_info = MagicMock()
        jid = '1'

        rectime = timedelta(seconds=1800)
        delta = timedelta(seconds=300)
        job = [{'rj_id': jid, 'walltime': timedelta(seconds=1770)}]

        expected_command = [
            '/work/pbs/bin/qalter', '-l', 'walltime=1800.0', jid]

        expected_command_delta = [
            '/work/pbs/bin/qalter', '-l', 'walltime=2070.0', jid]

        expected_job_exists = [
            {'rj_id': jid, 'walltime': timedelta(seconds=1770)},
            {'rj_id': jid, 'walltime': timedelta(seconds=1770)}]
        expected_job_notexists = []

        """
        引数のIDのジョブが存在する
        """
        # 録画時間指定
        self.rec.get_job_info.return_value = deepcopy(job)
        job_pair = self.rec.change_rectime(jid, rectime=rectime)

        self.rec._run_command.assert_called_with(expected_command)
        self.assertEqual(job_pair, expected_job_exists)

        # 元の録画開始時間からの差分指定
        self.rec.get_job_info.return_value = deepcopy(job)
        job_pair = self.rec.change_rectime(jid, delta=delta)

        self.rec._run_command.assert_called_with(expected_command_delta)
        self.assertEqual(job_pair, expected_job_exists)

        # _run_commandのMagicMockをリセット
        self.rec._run_command.reset_mock()

        """
        引数のIDのジョブが存在しない
        """
        self.rec.get_job_info.return_value = []

        # 開始時刻時刻指定
        job_pair = self.rec.change_rectime(jid, rectime=rectime)

        self.rec._run_command.assert_not_called
        self.assertEqual(job_pair, expected_job_notexists)

        # 元の録画開始時間からの差分指定
        job_pair = self.rec.change_rectime(jid, delta=delta)

        self.rec._run_command.assert_not_called
        self.assertEqual(job_pair, expected_job_notexists)

    """
    現在時刻を2020年08月16日 20時03分00秒(1597575780)に固定
    """
    @freeze_time('2020-08-16 20:03:00')
    def test_fetch_joblist(self):
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
                        "Job_Name":"bs_wait.181",
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
                        "Job_Name":"bs_run.181",
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
                        "Job_Name":"tt_wait.25",
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
                        "Job_Name":"tt_run.25",
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

        self.rec._fetch_joblist()
        self.assertEqual(self.rec.joblist, joblist_expected)

        # 同一インスタンスで2回呼んでも古いjoblistはクリアされている
        self.rec._fetch_joblist()
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

        self.rec._fetch_joblist = MagicMock()
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
        proc.stdout = pbsnodes_single
        tuners = self.rec._get_tuner_num()
        self.assertEqual(tuners, expected_single)

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
        proc.stdout = pbsnodes_multi
        tuners = self.rec._get_tuner_num()
        self.assertEqual(tuners, expected_multi)

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
        proc.stdout = pbsnodes_multi_hetero
        tuners = self.rec._get_tuner_num()
        self.assertEqual(tuners, expected_multi_hetero)

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
        proc.stdout = pbsnodes_include_offline
        tuners = self.rec._get_tuner_num()
        self.assertEqual(tuners, expected_include_offline)

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
        proc.stdout = pbsnodes_include_jobbusy
        tuners = self.rec._get_tuner_num()
        self.assertEqual(tuners, expected_include_jobbusy)

    def test_check_tuner_resource(self):
        """
        同時録画数がチューナー数を超えた場合に
        当該ジョブのalert属性に警告文がつくことを確認
        """
        message = 'Out of Tuners. Max: 2'
        self.rec._get_tuner_num = MagicMock(return_value={'tt': 2, 'bs': 2})

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
