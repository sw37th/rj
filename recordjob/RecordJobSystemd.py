# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import recordjob

# Systemd commands
systemctl_path = '/bin/systemctl'
systemdrun_path = '/usr/bin/systemd-run'

class RecordJobSystemd(recordjob.RecordJob):
    def __init__(self):
        super().__init__()
        self.sytemctl = systemctl_path
        self.systemdrun = systemdrun_path
        self.name = 'RecordJobSystemd'
        self.args_base = '--user --timer-property=AccuracySec=1s '

    def __str__(self):
        return self.name

    def add(self, ch, title, begin, rectime):
        """
        ジョブスケジューラに録画ジョブを追加する
        """
        if int(ch) < 100:
            # for terrestrial television
            tuner = 'tt'
            lnb = ''
        else:
            # for broadcasting satellite
            tuner = 'bs'
            lnb = '--lnb 15'

        current = datetime.now()

        # ジョブスクリプト作成
        jobsh_name = self.scriptdir + '/' + '{}.{}.{}-{}.sh'.format(
            title,
            ch,
            begin.strftime('%Y%m%d%H%M%S'),
            current.strftime('%Y%m%d%H%M%S'))
        jobsh_body = """umask 022
{} {} --b25 --strip {} - {}/{}.{}.`date +%Y%m%d_%H%M.%S`.$$.ts
""".format(self.recpt1_path, lnb, ch, self.recdir, title, ch)

        try:
            with open(jobsh_name, 'w') as f:
                f.write(jobsh_body)
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create jobscript: {}'.format(err))
            return ''

        # systemd.timer登録
        at = begin.strftime('%Y-%m-%d %H:%M:%S')
        sr_arg_date = "--on-calendar='{}'".format(at)
        sr_arg_name = "--unit='rj_{}_{}'".format(ch, title)
        command = '/bin/bash ' + jobsh_name
        print(sr_arg_date)
        print(sr_arg_name)
        print(command)

