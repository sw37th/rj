from unittest import TestCase
from recordjob import RecordJobSystemd as rjs
from io import StringIO
from unittest.mock import mock_open, patch
from datetime import datetime, timedelta



class RecordJobSystemdTest(TestCase):
    def test_classname(self):
        rec = rjs.RecordJobSystemd()
        self.assertEqual(str(rec), 'RecordJobSystemd')

    def test_create_timer_calendar(self):
        """
        _create_timer()で作成されるtimerユニットファイルの
        repeatフラグとOnCalendarフォーマットのペアが適正か
        """
        begin = datetime(2018, 6, 30, 00, 00, 00)
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
        rec = rjs.RecordJobSystemd()
        mopen = mock_open()
        with patch('recordjob.RecordJobSystemd.open', mopen, create=True):
            for rep, cal in repeats.items():
                rec._create_timer('test', 'dummytimer', begin, rep)

                f = mopen()
                f.write.assert_any_call(
                    timer.format(_repeat=rep, _calendar=cal)
                )

            # no repeat flag
            rec._create_timer('test', 'dummytimer', begin)
            f = mopen()
            f.write.assert_any_call(
                timer.format(_repeat='ONESHOT', _calendar=repeats['ONESHOT'])
            )

            # invalid repeat flag
            rec._create_timer('test', 'dummytimer', begin, 'invalid')
            f = mopen()
            f.write.assert_any_call(
                timer.format(_repeat='ONESHOT', _calendar=repeats['ONESHOT'])
            )

    def test_create_service_calendar(self):
        #@mock.patch('recordjob.RecordJobSystemd')
        """
        _create_timer()で作成されるtimerユニットファイルの
        repeatフラグとOnCalendarフォーマットのペアが適正か
        """
        rec = rjs.RecordJobSystemd()
        unit = rec.unitdir + '/test.service'
        rectime = timedelta(seconds=1770)
        service_bs_repeat = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip --lnb 15 $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.211.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"

""".format(_recdir=rec.recdir)

        service_bs_once = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip --lnb 15 $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.211.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable test.timer"
""".format(_recdir=rec.recdir)

        service_tt_repeat = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=15" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.15.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"

""".format(_recdir=rec.recdir)

        service_tt_once = """\
# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=15" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "recpt1 --b25 --strip $$RJ_ch $$RJ_walltime {_recdir}/dummyservice.15.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable test.timer"
""".format(_recdir=rec.recdir)

        mopen = mock_open()
        with patch('recordjob.RecordJobSystemd.open', mopen, create=True):
            rec._create_service(unit, '211', 'dummyservice', rectime)
            f = mopen()
            #print(f.write.call_args)
            f.write.assert_any_call(service_bs_once)

            rec._create_service(unit, '211', 'dummyservice', rectime, 'ONESHOT')
            f = mopen()
            f.write.assert_any_call(service_bs_once)

            rec._create_service(unit, '211', 'dummyservice', rectime, 'WEEKLY')
            f = mopen()
            f.write.assert_any_call(service_bs_repeat)

            rec._create_service(unit, '15', 'dummyservice', rectime)
            f = mopen()
            f.write.assert_any_call(service_tt_once)

            rec._create_service(unit, '15', 'dummyservice', rectime, 'ONESHOT')
            f = mopen()
            f.write.assert_any_call(service_tt_once)

            rec._create_service(unit, '15', 'dummyservice', rectime, 'WEEKLY')
            f = mopen()
            f.write.assert_any_call(service_tt_repeat)
