# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired
import re
import recordjob

# Systemd commands
systemctl_path = '/bin/systemctl'
systemdrun_path = '/usr/bin/systemd-run'

class RecordJobSystemd(recordjob.RecordJob):
    def __init__(self):
        super().__init__()
        self.sytemctl = systemctl_path
        self.systemdrun = systemdrun_path
        self.systemctlshow = [
            systemctl_path,
            '--user',
            '--no-pager',
            'show',
        ]
        self.name = 'RecordJobSystemd'

    def __str__(self):
        return self.name

    def add(self, ch, title, begin, rectime):
        """
        ジョブスケジューラに録画ジョブを追加する
        """
        jid = ''
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
            c.insert(1, lnb)
        command = ' '.join(c)

        # systemd.timer登録用コマンド作成
        at = begin.strftime('%Y-%m-%d %H:%M:%S')
        timer_date = "--on-calendar={}".format(at)
        timer_name = "--unit=RJ.{}.{}.{}.{}".format(
            ch, title, begin.strftime('%Y%m%d%H%M%S'), tuner)
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

        # systemd.timer登録
        try:
            with Popen(
                timer,
                universal_newlines=True,
                stdout=PIPE,
                stderr=STDOUT
            ) as submit:
                # waiting for complete of job submit
                submit.wait(timeout=self.comm_timeout)
                stdout_data = submit.communicate()[0]
                if stdout_data:
                    re_jid = re.compile('Running timer as unit: (.*)')
                    m =  re.match(re_jid, stdout_data)
                    if m:
                        jid = m.group(1)
                    else:
                        print(stdout_data)
        except (OSError, ValueError, TimeoutExpired) as err:
            print('cannot submit job:', err)

        return jid


    def get_job_info(self, date=None, jid=None):
        """
        録画ジョブ情報を取得して配列として返す
        """

        jobinfo = self._get_torque_job_info(jid)

        if date:
            # dateで指定された日のジョブのみを配列に詰め直す
            nextday = date + timedelta(days=1)
            jobinfo = [
                i for i in jobinfo
                    if i['rec_begin'] >= date and i['rec_begin'] < nextday
            ]

        return jobinfo

    def get_systemd_job_info(self, target_jid=None):
        """
        systemctl --user --no-pager --all list-timersの出力から
        ジョブ毎の情報を取得し配列として返す
        """
        jobs = {}

        if not target_jid:
            target_jid = '*.timer'

        self.systemctlshow.append(target_jid)

        try:
            with Popen(self.systemctlshow,
                universal_newlines=True,
                stdout=PIPE,
                stderr=STDOUT,
            ) as timers:
                # Thu 2018-05-24 01:34:50 JST RJ.15.test.20180524013450.tt.timer
                re_line = re.compile(
                    '(\w{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*' +
                    'RJ\.(\w.+)\.timer'
                )
                # 15.test.20180524013450.tt
                re_job = re.compile(
                    '(\d.+)\.(\w.+)\.(\d{14})\.(\w{2})'
                )

                for i in timers.stdout:
                    print(i)
                """
                    l = re.match(re_line, i)
                    if l:
                        jid = l.group(2)
                        jobs[jid] = {}

                        j = re.match(re_job, jid)
                        if not j:
                            continue

                        ch, name, tuner = j.group(1, 2, 4)
                        jobs[jid]['ch'] = ch
                        jobs[jid]['name'] = name
                        jobs[jid]['queue'] = tuner

                        # Thu 2018-05-24 01:34:50
                        jobs[jid]['rec_begin'] = datetime.strptime(
                            l.group(1), "%a %Y-%m-%d %H:%M:%S"
                        )
                print(jobs)

                """


        except (OSError, ValueError) as err:
            print('cannot get job information: ', err)
            return []

        return []

