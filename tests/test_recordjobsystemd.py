import unittest
from recordjob import RecordJobSystemd as rjs
from io import StringIO
from unittest.mock import mock_open, patch
from datetime import datetime, timedelta



class RecordJobSystemdTest(unittest.TestCase):
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
        timer = """# created programmatically via rj. Do not edit.
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
        """
        _create_timer()で作成されるtimerユニットファイルの
        repeatフラグとOnCalendarフォーマットのペアが適正か
        """
        service = """# created programmatically via rj. Do not edit.
[Unit]
Description=RJ: service unit for dummyservice
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch=211" "RJ_walltime=1770"
ExecStart=@/bin/bash "/bin/bash" "-c" "{_recpt1} $$RJ_ch $$RJ_walltime {_output}.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
{_execstop}
"""

