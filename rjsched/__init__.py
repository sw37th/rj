from subprocess import run, PIPE, CalledProcessError, TimeoutExpired
import yaml
import syslog

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

    def _logger(self, priority, message):
        ident = 'recordjob'
        syslog.openlog(
            ident=ident, logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL7)
        syslog.syslog(priority, message)
        syslog.closelog()

    def _run_command(self, command, _input=None, log=True):
        """
        コマンドを実行し、CompletedProcessオブジェクトを返す
        """
        if log:
            self._logger(syslog.LOG_INFO, ' '.join(command))
        try:
            proc = run(
                command,
                input=_input,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=self.comm_timeout,
                check=True,)
        except (OSError, TimeoutExpired, CalledProcessError) as err:
            self._logger(syslog.LOG_ERR, str(err))
            raise
        return proc

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
