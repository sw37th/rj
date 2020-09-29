from textwrap import dedent
from unittest import TestCase
from unittest.mock import mock_open, patch, MagicMock
import rjsched

class RecordJobTest(TestCase):
    def setUp(self):
        super(RecordJobTest, self).setUp()
        config = {
            'recpt1_path':    '/usr/local/bin/recpt1',
            'recpt1ctl_path': '/usr/local/bin/recpt1ctl',
            'recdir':         '/home/dummy/rec',
            'channel_file':   '/home/dummy/.rj/channel.yml',}
        self.rec = rjsched.RecordJob(config)
        self.maxDiff = None

    def tearDown(self):
        super(RecordJobTest, self).tearDown()

    def test_is_bs(self):
        self.assertTrue(self.rec._is_bs(64))
        self.assertFalse(self.rec._is_bs(63))

    def test_get_channel_list(self):
        yaml_channel = dedent("""\
            15:       MX
            211:      BS11
        """)
        expected = {'15': 'MX', '211': 'BS11'}
        mopen = mock_open(read_data=yaml_channel)
        with patch('rjsched.open', mopen):
            result = self.rec.get_channel_list()
            self.assertEqual(result, expected)
