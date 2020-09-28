import yaml

class RecordJob:
    def __init__(self, config):
        recpt1_path = config.get('recpt1_path')
        recpt1ctl_path = config.get('recpt1ctl_path')
        self.recdir = config.get('recdir')
        self.channel_file = config.get('channel_file')
        self.recpt1 = [recpt1_path, '--b25', '--strip']
        self.recpt1ctl = [recpt1ctl_path]
        self.comm_timeout = 10
        self.job_state = {
            'C': "Completed",
            'E': "Exiting",
            'H': "on Hold",
            'Q': "Queued",
            'R': "Recording",
            'T': "Moved",
            'W': "Waiting",
            'S': "Suspend",
        }
        self.queuename = {
            'satellite': 'bs',
            'terrestrial': 'tt',
        }

    def _is_bs(self, ch):
        if int(ch) > 63:
            return True
        else:
            return False

    def get_channel_list(self):
        """
        チャンネル番号と局名の対応表をYAMLファイルから取得して返す
        """
        try:
            with open(self.channel_file) as f:
                chinfo = yaml.load(f)
        except (PermissionError, FileNotFoundError, yaml.YAMLError) as err:
            print('channel information cannot load: {}'.format(err))
            return {}

        return {str(i): str(j) for i, j in chinfo.items()}

    def change_repeat(self, job, repeat):
        """
        リピート設定変更用クラスメソッド
        Systemd以外のスケジューラーではこれが呼ばれる
        """
        return []
