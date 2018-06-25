import unittest
from recordjob import RecordJobSystemd as rjs
from io import StringIO
from unittest.mock import mock_open, patch
from datetime import datetime, timedelta



class RecordJobSystemdTest(unittest.TestCase):
    def test_classname(self):
        rec = rjs.RecordJobSystemd()
        self.assertEqual(str(rec), 'RecordJobSystemd')

    #@mock_open.patch('RecordJobSystemd._create_timer.open', m)
    def test_create_timer_onshot(self):
        rec = rjs.RecordJobSystemd()
        begin = datetime(2018, 6, 30, 00, 00, 00)
        timer = """# created programmatically via rj. Do not edit.
[Unit]
Description=RJ:ONESHOT: timer unit for oneshot_timer
CollectMode=inactive-or-failed

[Timer]
AccuracySec=1s
OnCalendar=2018-06-30 00:00:00
RemainAfterElapse=no

[Install]
WantedBy=timers.target
"""
        m = mock_open()
        with patch('recordjob.RecordJobSystemd.open', m, create=True):
            rec._create_timer('test', 'oneshot_timer', begin, '')
            #print(m.called)
            #print(m.call_args)
            mock = m()
            #print(mock.write.call_args)
            mock.write.assert_any_call(timer)

