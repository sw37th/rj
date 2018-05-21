# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from subprocess import Popen, PIPE, TimeoutExpired
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

        tsfile = self.recdir + '/{}.{}.`date +%Y%m%d_%H%M.%S`.$$$.ts'.format(
            title,
            ch,
        )

        # ジョブコマンド作成
        c = [
            self.recpt1_path,
            '--b25',
            '--strip',
            ch,
            str(int(rectime.total_seconds())),
            tsfile,
        ]
        if lnb:
            c.insert(3, lnb)
        command = ' '.join(c)

        # systemd.timer登録用コマンド作成
        at = begin.strftime('%Y-%m-%d %H:%M:%S')
        timer_date = "--on-calendar={}".format(at)
        timer_name = "--unit=RJ.{}_{}.{}".format(ch, title, tuner)
        timer = [
            self.systemdrun,
            '--user',
            '--collect',
            '--timer-property=AccuracySec=1s',
            timer_date,
            timer_name,
            '/bin/bash',
            '-c',
            command
        ]
        print(timer_date)
        print(timer_name)
        print(timer)

        # systemd.timer登録
        try:
            with Popen(
                timer,
                universal_newlines=True,
                stdout=PIPE,
                stderr=PIPE
            ) as submit:
                # waiting for complete of job submit
                submit.wait(timeout=self.comm_timeout)
                stdout_data, stderr_data = submit.communicate()
                if stdout_data:
                    print("STDOUT:", stdout_data)
                if stderr_data:
                    print("STDERR:", stderr_data)
        except (OSError, ValueError, TimeoutExpired) as err:
            print('cannot submit job: {}'.format(err))
