# -*- coding: utf-8 -*-

from unittest import TestCase
from recordjob import RecordJobSystemd as rjs
from unittest.mock import mock_open, patch, MagicMock, call
from datetime import datetime, timedelta
from subprocess import PIPE, STDOUT, DEVNULL


begin = datetime(2018, 6, 30, 00, 00, 00)
rectime = timedelta(seconds=1770)
unit_tt = 'RJ.15.test.20180630000000.tt'
unit_tt_id = '6728ed28435be863a9ee453ecc391f2f6415aada2dc01d61643c2f25dac9f095'
expect_sctl_start = [
    'systemctl',
    '--user',
    'start',
    unit_tt + '.timer'
]
expect_sctl_enable = [
    'systemctl',
    '--user',
    'enable',
    unit_tt + '.timer'
]
expect_timer_file = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ:{_repeat}: timer unit for dummytimer
CollectMode=inactive-or-failed

[Timer]
AccuracySec=1s
OnCalendar={_calendar}
RemainAfterElapse=no

[Install]
WantedBy=timers.target
"""
expect_service_file_bs_repeat = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip --lnb 15 $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.211.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"

"""
expect_service_file_bs_once = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip --lnb 15 $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.211.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable test.timer"
"""
expect_service_file_tt_repeat = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=15" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.15.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"

"""
expect_service_file_tt_once = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=15" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.15.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable test.timer"
"""
dummy_unitdir = '/home/dummy/.config/systemd/user/'
dummy_job_waiting_ids = ['d39bb99c', '6095bb27']
dummy_job_waiting = [
    {
        'tuner': 'tt',
        'timer': {
            'Names': 'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
            'NextElapseUSecRealtime': 'Tue 2018-07-10 01:38:50 JST',
            'Description': 'RJ:WEEKLY: timer unit for yamanosusume_3rd',
            'FragmentPath': dummy_unitdir + \
                'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
            },
        'service': {
            'Names': 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            'Environment': 'RJ_ch=15 RJ_walltime=960',
            'FragmentPath':dummy_unitdir + \
                'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            },
        'rec_begin': datetime(2018, 7, 10, 1, 38, 50),
        'channel': '15',
        'walltime': timedelta(0, 960),
        'rec_end': datetime(2018, 7, 10, 1, 54, 50),
        'user': 'autumn',
        'rj_title': 'yamanosusume_3rd',
        'rj_id_long': 'd39bb99c079baeffe9eb2c6e2f93a36401b37acec8bb4d4d0721f67cee5543ce',
        'rj_id': 'd39bb99c',
        'repeat': 'WEEKLY'},
    {
        'tuner': 'bs',
        'timer': {
            'Names': 'RJ.211.yamanosusume_3rd.20180703022850.bs.timer',
            'NextElapseUSecRealtime': 'Tue 2018-07-10 02:28:50 JST',
            'Description': 'RJ:WEEKLY: timer unit for yamanosusume_3rd',
            'FragmentPath': dummy_unitdir + \
                'RJ.211.yamanosusume_3rd.20180703022850.bs.timer',
            },
        'service': {
            'Names': 'RJ.211.yamanosusume_3rd.20180703022850.bs.service',
            'Environment': 'RJ_ch=211 RJ_walltime=960',
            'FragmentPath': dummy_unitdir + \
                'RJ.211.yamanosusume_3rd.20180703022850.bs.service',
            },
        'rec_begin': datetime(2018, 7, 10, 2, 28, 50),
        'channel': '211',
        'walltime': timedelta(0, 960),
        'rec_end': datetime(2018, 7, 10, 2, 44, 50),
        'user': 'autumn',
        'rj_title': 'yamanosusume_3rd',
        'rj_id_long': '6095bb2745368511247217865f47f09cd874f27eeda5a7c960c222bf8003e2c7',
        'rj_id': '6095bb27',
        'repeat': 'WEEKLY'}]
dummy_job_running = [
    {
        'tuner': 'tt',
        'timer': {
            'Names': 'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
            'LastTriggerUSec': 'Tue 2018-07-10 01:38:50 JST',
            'Description': 'RJ:WEEKLY: timer unit for yamanosusume_3rd',
            'FragmentPath': dummy_unitdir + \
                'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
            },
        'service': {
            'Names': 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            'Environment': 'RJ_ch=15 RJ_walltime=960',
            'MainPID': '8419',
            'FragmentPath':dummy_unitdir + \
                'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            },
        'record_state': 'Recording',
        'rec_begin': datetime(2018, 7, 10, 1, 38, 50),
        'channel': '15',
        'walltime': timedelta(0, 960),
        'rec_end': datetime(2018, 7, 10, 1, 54, 50),
        'user': 'autumn',
        'rj_title': 'yamanosusume_3rd',
        'rj_id_long': 'd39bb99c079baeffe9eb2c6e2f93a36401b37acec8bb4d4d0721f67cee5543ce',
        'rj_id': 'd39bb99c',
        'repeat': 'WEEKLY'}]
expect_sctl_stop = [
    'systemctl',
    '--user',
    'stop',
    'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
    'RJ.211.yamanosusume_3rd.20180703022850.bs.timer',
    'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
    'RJ.211.yamanosusume_3rd.20180703022850.bs.service',]
expect_sctl_disable = [
    'systemctl',
    '--user',
    'disable',
    'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
    'RJ.211.yamanosusume_3rd.20180703022850.bs.timer',]
expect_sctl_reload = [
    'systemctl',
    '--user',
    'daemon-reload',]

class RecordJobSystemdTest(TestCase):
    def setUp(self):
        super(RecordJobSystemdTest, self).setUp()
        self.rec = rjs.RecordJobSystemd()

    def tearDown(self):
        super(RecordJobSystemdTest, self).tearDown()

    def test_classname(self):
        self.assertEqual(str(self.rec), 'RecordJobSystemd')

    def test_create_timer_calendar(self):
        """
        _create_timer()で作成されるtimerユニットファイルの
        repeatフラグとOnCalendarフォーマットのペアが適正か
        """
        repeats = {
            'WEEKLY':  'Sat *-*-* 00:00:00',
            'DAILY':   '*-*-* 00:00:00',
            'WEEKDAY': 'Mon..Fri *-*-* 00:00:00',
            'ASADORA': 'Mon..Sat *-*-* 00:00:00',
            'ONESHOT': '2018-06-30 00:00:00',
        }
        mopen = mock_open()
        with patch('recordjob.RecordJobSystemd.open', mopen, create=True):
            for rep, cal in repeats.items():
                self.rec._create_timer('test', 'dummytimer', begin, rep)

                f = mopen()
                f.write.assert_any_call(
                    expect_timer_file.format(_repeat=rep, _calendar=cal)
                )

            # no repeat flag
            self.rec._create_timer('test', 'dummytimer', begin)
            f = mopen()
            f.write.assert_any_call(
                expect_timer_file.format(
                    _repeat='ONESHOT', _calendar=repeats['ONESHOT'])
            )

            # invalid repeat flag
            self.rec._create_timer('test', 'dummytimer', begin, 'invalid')
            f = mopen()
            f.write.assert_any_call(
                expect_timer_file.format(
                    _repeat='ONESHOT', _calendar=repeats['ONESHOT'])
            )

    def test_create_service_calendar(self):
        """
        _create_timer()で作成されるtimerユニットファイルの
        repeatフラグとOnCalendarフォーマットのペアが適正か
        """
        unit = self.rec.unitdir + '/test.service'
        recdir = self.rec.recdir
        mopen = mock_open()
        repeats = ('WEEKLY', 'DAILY', 'WEEKDAY', 'ASADORA')
        with patch('recordjob.RecordJobSystemd.open', mopen, create=True):
            # BS without repeat flag (the same behavior as ONESHOT)
            self.rec._create_service(
                unit, '211', 'dummyservice', rectime)
            f = mopen()
            f.write.assert_any_call(
                expect_service_file_bs_once.format(_recdir=recdir))

            # BS with ONESHOT flag 
            self.rec._create_service(
                unit, '211', 'dummyservice', rectime, 'ONESHOT')
            f = mopen()
            f.write.assert_any_call(
                expect_service_file_bs_once.format(_recdir=recdir))

            # BS with invalid flag (the same behavior as ONESHOT)
            self.rec._create_service(
                unit, '211', 'dummyservice', rectime, 'XXXXXXXX')
            f = mopen()
            f.write.assert_any_call(
                expect_service_file_bs_once.format(_recdir=recdir))

            # BS with each repeat flag
            for rep in repeats:
                self.rec._create_service(
                    unit, '211', 'dummyservice', rectime, rep)
                f = mopen()
                f.write.assert_any_call(
                    expect_service_file_bs_repeat.format(_recdir=recdir))

            # Terrestrial without repeat flag (the same behavior as ONESHOT)
            self.rec._create_service(
                unit, '15', 'dummyservice', rectime)
            f = mopen()
            f.write.assert_any_call(
                expect_service_file_tt_once.format(_recdir=recdir))

            # Terrestrial with ONESHOT flag
            self.rec._create_service(
                unit, '15', 'dummyservice', rectime, 'ONESHOT')
            f = mopen()
            f.write.assert_any_call(
                expect_service_file_tt_once.format(_recdir=recdir))

            # Terrestrial with ONESHOT flag (the same behavior as ONESHOT)
            self.rec._create_service(
                unit, '15', 'dummyservice', rectime, 'XXXXXXXX')
            f = mopen()
            f.write.assert_any_call(
                expect_service_file_tt_once.format(_recdir=recdir))

            # Terrestrial with each repeat flag
            for rep in repeats:
                self.rec._create_service(
                    unit, '15', 'dummyservice', rectime, rep)
                f = mopen()
                f.write.assert_any_call(
                    expect_service_file_tt_repeat.format(_recdir=recdir))

    def test_is_bs(self):
        """
        64~  ... expect True
        1-63 ... expect False
        """
        self.assertTrue(self.rec._is_bs(64))
        self.assertFalse(self.rec._is_bs(63))

    def test_gen_unitname_jobid(self):
        unit, rj_id_long = self.rec._gen_unitname_jobid('15', 'test', begin)
        expect_unit = unit_tt
        expect_id = unit_tt_id
        self.assertEqual(expect_unit, unit)
        self.assertEqual(expect_id, rj_id_long)

    @patch('recordjob.RecordJobSystemd.run')
    def test_add(self, m_run):
        expect_unit_timer = self.rec.unitdir + '/' + unit_tt + '.timer'
        expect_unit_service = self.rec.unitdir + '/' + unit_tt + '.service'
        expect_calls_run = [
            call(
                expect_sctl_start,
                check=True,
                stderr=STDOUT,
                stdout=DEVNULL),
            call(
                expect_sctl_enable,
                check=True,
                stderr=STDOUT,
                stdout=DEVNULL),
        ]

        self.rec._create_timer = MagicMock()
        self.rec._create_service = MagicMock()

        self.rec.add('15', 'test', begin, rectime, 'WEEKLY')

        self.rec._create_timer.assert_called_with(
            expect_unit_timer, 'test', begin, 'WEEKLY')
        self.rec._create_service.assert_called_with(
            expect_unit_service, '15', 'test', rectime, 'WEEKLY')
        m_run.assert_has_calls(expect_calls_run)

    @patch('recordjob.RecordJobSystemd.run')
    @patch('recordjob.RecordJobSystemd.print')
    def test_remove(self, m_print, m_run):
        self.rec.get_job_info = MagicMock()
        self.rec.get_job_info.return_value = dummy_job_waiting
        expect_calls_run = [
            call(
                expect_sctl_stop,
                check=True,
                stderr=STDOUT,
                stdout=DEVNULL),
            call(
                expect_sctl_disable,
                check=True,
                stderr=STDOUT,
                stdout=DEVNULL),
        ]
        self.rec.remove(dummy_job_waiting_ids)
        m_run.assert_has_calls(expect_calls_run)

        m_run.reset_mock()

        # 存在しないジョブIDが渡された場合
        # FIXME returnで返しているが、例外で処理したい
        self.rec.get_job_info.return_value = []
        self.rec.remove(dummy_job_waiting_ids)
        self.assertFalse(m_run.called)

    @patch('recordjob.RecordJobSystemd.run')
    def test_unit_reload(self, m_run):
        self.rec._unit_reload()
        m_run.assert_called_with(expect_sctl_reload, check=True)

    def test_change_begin(self):
        self.rec._change_timer = MagicMock()
        self.rec._unit_reload = MagicMock()

        job = dummy_job_waiting[0]

        self.rec.change_begin(job, begin)

        self.rec._change_timer.assert_called_with(
            job, begin)
        self.assertTrue(self.rec._unit_reload.called)

    def test_change_begin_delta(self):
        self.rec._change_timer = MagicMock()
        self.rec._unit_reload = MagicMock()

        delta = timedelta(seconds=300)
        job = dummy_job_waiting[0]
        expect_begin = datetime(2018, 7, 10, 1, 38, 50) + delta

        self.rec.change_begin_delta(job, delta)

        self.rec._change_timer.assert_called_with(
            job, expect_begin)
        self.assertTrue(self.rec._unit_reload.called)

    def test_change_rec(self):
        self.rec._change_service = MagicMock()
        self.rec._unit_reload = MagicMock()

        job = dummy_job_waiting[0]

        self.rec.change_rec(job, rectime)

        self.rec._change_service.assert_called_with(
            job, rectime=rectime)
        self.assertTrue(self.rec._unit_reload.called)

    def test_extend_rec(self):
        self.rec._change_service = MagicMock()
        self.rec._unit_reload = MagicMock()

        delta = timedelta(seconds=300)
        job = dummy_job_waiting[0]
        expect_rectime = timedelta(seconds=960) + delta

        self.rec.extend_rec(job, delta)

        self.rec._change_service.assert_called_with(
            job, rectime=expect_rectime)
        self.assertTrue(self.rec._unit_reload.called)

    def test_change_channel(self):
        self.rec._change_service = MagicMock()
        self.rec._unit_reload = MagicMock()

        job = dummy_job_waiting[0]

        self.rec.change_channel(job, '25')

        self.rec._change_service.assert_called_with(
            job, ch='25')
        self.assertTrue(self.rec._unit_reload.called)

    def test_change_repeat(self):
        self.rec._change_timer = MagicMock()
        self.rec._change_service = MagicMock()
        self.rec._unit_reload = MagicMock()

        job = dummy_job_waiting[0]

        self.rec.change_repeat(job, 'ONESHOT')

        self.rec._change_timer.assert_called_with(
            job, datetime(2018, 7, 10, 1, 38, 50), repeat='ONESHOT')
        self.rec._change_service.assert_called_with(
            job, repeat='ONESHOT')
        self.assertTrue(self.rec._unit_reload.called)

    @patch('recordjob.RecordJobSystemd.run')
    @patch('recordjob.RecordJobSystemd.print')
    def test_change_running_recpt1(self, m_print, m_run):
        expect_command = [
            'recpt1ctl', '--pid', '8419', '--channel', '15', '--time', '1770']

        self.rec._change_running_recpt1('8419', '15', rectime)

        m_run.assert_called_with(
            expect_command,
            check=True,
            stdout=PIPE,
            stderr=STDOUT,
            universal_newlines=True)

    @patch('recordjob.RecordJobSystemd.print')
    def test_change_service(self, m_print):
        self.rec._create_service = MagicMock()
        self.rec._change_running_recpt1 = MagicMock()

        # 待機中のジョブに対する変更
        job = dummy_job_waiting[0]

        # チャンネル変更
        self.rec._change_service(job, ch='20')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '20',
            'yamanosusume_3rd',
            timedelta(seconds=960),
            'WEEKLY')
        self.rec._change_running_recpt1.assert_not_called()
        self.rec._change_running_recpt1.reset_mock()


        # 録画時間変更
        self.rec._change_service(job, rectime=timedelta(seconds=1770))
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '15',
            'yamanosusume_3rd',
            timedelta(seconds=1770),
            'WEEKLY')
        self.rec._change_running_recpt1.assert_not_called()
        self.rec._change_running_recpt1.reset_mock()

        # リピートフラグ変更
        self.rec._change_service(job, repeat='DAILY')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '15',
            'yamanosusume_3rd',
            timedelta(seconds=960),
            'DAILY')
        self.rec._change_running_recpt1.assert_not_called()
        self.rec._change_running_recpt1.reset_mock()

        # 録画中のジョブに対する変更
        job = dummy_job_running[0]

        # チャンネル変更
        self.rec._change_service(job, ch='20')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '20',
            'yamanosusume_3rd',
            timedelta(seconds=960),
            'WEEKLY')
        self.rec._change_running_recpt1.assert_called_with(
            '8419',
            '20',
            timedelta(seconds=960))
        self.rec._change_running_recpt1.reset_mock()

        # 録画時間変更
        self.rec._change_service(job, rectime=timedelta(seconds=1770))
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '15',
            'yamanosusume_3rd',
            timedelta(seconds=1770),
            'WEEKLY')
        self.rec._change_running_recpt1.assert_called_with(
            '8419',
            '15',
            timedelta(seconds=1770))
        self.rec._change_running_recpt1.reset_mock()

        # リピートフラグのみ変更
        # このケースでは_change_running_recpt1()は呼ばれない
        self.rec._change_service(job, repeat='DAILY')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '15',
            'yamanosusume_3rd',
            timedelta(seconds=960),
            'DAILY')
        self.rec._change_running_recpt1.assert_not_called()
        self.rec._change_running_recpt1.reset_mock()

        # チャンネルとリピートフラグ変更
        self.rec._change_service(job, ch='20', repeat='DAILY')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '20',
            'yamanosusume_3rd',
            timedelta(seconds=960),
            'DAILY')
        self.rec._change_running_recpt1.assert_called_with(
            '8419',
            '20',
            timedelta(seconds=960))
        self.rec._change_running_recpt1.reset_mock()

        # 録画時間とリピートフラグ変更
        self.rec._change_service(
            job, rectime=timedelta(seconds=1770), repeat='DAILY')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '15',
            'yamanosusume_3rd',
            timedelta(seconds=1770),
            'DAILY')
        self.rec._change_running_recpt1.assert_called_with(
            '8419',
            '15',
            timedelta(seconds=1770))
        self.rec._change_running_recpt1.reset_mock()

        # チャンネルと録画時間とリピートフラグ変更
        self.rec._change_service(
            job, ch='20', rectime=timedelta(seconds=1770), repeat='DAILY')
        self.rec._create_service.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.service',
            '20',
            'yamanosusume_3rd',
            timedelta(seconds=1770),
            'DAILY')
        self.rec._change_running_recpt1.assert_called_with(
            '8419',
            '20',
            timedelta(seconds=1770))
        self.rec._change_running_recpt1.reset_mock()

    def test_change_timer(self):
        self.rec._create_timer = MagicMock()
        job = dummy_job_waiting[0]

        # 開始時刻変更
        self.rec._change_timer(job, begin)
        self.rec._create_timer.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
            'yamanosusume_3rd',
            begin,
            'WEEKLY')

        # 開始時刻とリピートフラグ変更
        self.rec._change_timer(job, begin, repeat='DAILY')
        self.rec._create_timer.assert_called_with(
            dummy_unitdir + 'RJ.15.yamanosusume_3rd.20180703013850.tt.timer',
            'yamanosusume_3rd',
            begin,
            'DAILY')

    def test_get_job_info(self):
        self.rec._get_systemd_job_info = MagicMock()
        self.rec._get_systemd_job_info.return_value = dummy_job_waiting
        self.maxDiff = None
        jid_tt = (
            'd39bb99c079baeffe9eb2c6e2f93a36401b37acec8bb4d4d0721f67cee5543ce',
            'd39bb99c',)
        jid_bs = (
            '6095bb2745368511247217865f47f09cd874f27eeda5a7c960c222bf8003e2c7',
            '6095bb27',)

        # 引数無指定でジョブ情報を取得
        jobinfo = self.rec.get_job_info()
        self.assertEqual(dummy_job_waiting, jobinfo)

        # ジョブIDを指定してジョブ情報を取得
        expect_jobinfo = [dummy_job_waiting[0]]
        for i in jid_tt:
            jobinfo = self.rec.get_job_info(jid=i)
            self.assertEqual(expect_jobinfo, jobinfo)
        expect_jobinfo = [dummy_job_waiting[1]]
        for i in jid_bs:
            jobinfo = self.rec.get_job_info(jid=i)
            self.assertEqual(expect_jobinfo, jobinfo)
