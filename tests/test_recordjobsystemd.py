from unittest import TestCase, mock
from recordjob import RecordJobSystemd as rjs
from io import StringIO
from unittest.mock import mock_open, patch
from datetime import datetime, timedelta


begin = datetime(2018, 6, 30, 00, 00, 00)

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
        timer = """\
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
        mopen = mock_open()
        with patch('recordjob.RecordJobSystemd.open', mopen, create=True):
            for rep, cal in repeats.items():
                self.rec._create_timer('test', 'dummytimer', begin, rep)

                f = mopen()
                f.write.assert_any_call(
                    timer.format(_repeat=rep, _calendar=cal)
                )

            # no repeat flag
            self.rec._create_timer('test', 'dummytimer', begin)
            f = mopen()
            f.write.assert_any_call(
                timer.format(_repeat='ONESHOT', _calendar=repeats['ONESHOT'])
            )

            # invalid repeat flag
            self.rec._create_timer('test', 'dummytimer', begin, 'invalid')
            f = mopen()
            f.write.assert_any_call(
                timer.format(_repeat='ONESHOT', _calendar=repeats['ONESHOT'])
            )

    def test_create_service_calendar(self):
        """
        _create_timer()で作成されるtimerユニットファイルの
        repeatフラグとOnCalendarフォーマットのペアが適正か
        """
        unit = self.rec.unitdir + '/test.service'
        rectime = timedelta(seconds=1770)
        service_bs_repeat = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip --lnb 15 $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.211.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"

""".format(_recdir=self.rec.recdir)

        service_bs_once = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip --lnb 15 $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.211.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable test.timer"
""".format(_recdir=self.rec.recdir)

        service_tt_repeat = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=15" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.15.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"

""".format(_recdir=self.rec.recdir)

        service_tt_once = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=15" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.15.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable test.timer"
""".format(_recdir=self.rec.recdir)

        mopen = mock_open()
        with patch('recordjob.RecordJobSystemd.open', mopen, create=True):
            self.rec._create_service(unit, '211', 'dummyservice', rectime)
            f = mopen()
            #print(f.write.call_args)
            f.write.assert_any_call(service_bs_once)

            self.rec._create_service(unit, '211', 'dummyservice', rectime, 'ONESHOT')
            f = mopen()
            f.write.assert_any_call(service_bs_once)

            self.rec._create_service(unit, '211', 'dummyservice', rectime, 'WEEKLY')
            f = mopen()
            f.write.assert_any_call(service_bs_repeat)

            self.rec._create_service(unit, '15', 'dummyservice', rectime)
            f = mopen()
            f.write.assert_any_call(service_tt_once)

            self.rec._create_service(unit, '15', 'dummyservice', rectime, 'ONESHOT')
            f = mopen()
            f.write.assert_any_call(service_tt_once)

            self.rec._create_service(unit, '15', 'dummyservice', rectime, 'WEEKLY')
            f = mopen()
            f.write.assert_any_call(service_tt_repeat)

    def test_is_bs(self):
        # 64~  ... expect True
        # 1-63 ... expect False
        self.assertTrue(self.rec._is_bs(64))
        self.assertFalse(self.rec._is_bs(63))

    def test_gen_unitname_jobid(self):
        unit, rj_id_long = self.rec._gen_unitname_jobid('15', 'test', begin)
        expect_unit = 'RJ.15.test.20180630000000.tt'
        expect_id = '6728ed28435be863a9ee453ecc391f2f6415aada2dc01d61643c2f25dac9f095'
        self.assertEqual(expect_unit, unit)
        self.assertEqual(expect_id, rj_id_long)
