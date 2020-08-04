import yaml
import os

homedir = os.path.expanduser('~')
confdir = homedir + '/.rj'
channel_file = confdir + '/channel.yml'
recdir = homedir + '/rec'
recpt1_path = 'recpt1'
recpt1ctl_path = 'recpt1ctl'
comm_timeout = 10

class RecordJob(object):
    def __init__(self):
        self.channel_file = channel_file
        self.recpt1_path = recpt1_path
        self.recpt1ctl_path = recpt1ctl_path
        self.recdir = recdir
        self.comm_timeout = comm_timeout

    def get_channel_info(self):
        """
        チャンネル番号と局名の対応表をYAMLファイルから取得して返す
        """
        try:
            with open(self.channel_file) as f:
                chinfo = yaml.load(f)
        except (PermissionError, FileNotFoundError) as err:
            return None
        return chinfo

    def get_job_info(self):
        return []

    def add(self):
        return ''

    def mod_begintime(self):
        return
