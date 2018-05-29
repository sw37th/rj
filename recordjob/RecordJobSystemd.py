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
            '--all',
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

    def get_systemd_job_info(self, unit='RJ.*'):
        """
        ジョブ毎のtimerユニット/serviceユニット情報を取得し、
        補足情報を追加して配列に詰めて返す
        """
        jobinfo = {}

        # timerユニット情報を取得
        jobs = self._systemctl_show(unit + '.timer')
        for i in jobs:
            name = i.get('Names')
            name = name.rsplit('.', 1)[0]
            rec_begin = i.get('NextElapseUSecRealtime')

            jobinfo[name] = {'timer': i}

            # 開始時刻のdatetimeオブジェクトを追加
            jobinfo[name]['rec_begin'] = datetime.strptime(
                # WDY YYYY-MM-DD HH:MM:SS TZN
                rec_begin, "%a %Y-%m-%d %H:%M:%S %Z"
            )
            # 終了時刻のdatetimeオブジェクトを追加
            #FIXME

        # serviceユニット情報を取得
        jobs = self._systemctl_show(unit + '.service')
        for i in jobs:
            name = i.get('Names')
            name = name.rsplit('.', 1)[0]
            # timerユニットとserviseユニットはペアで存在するはず
            if name not in jobinfo:
                print(name + '.timer not exist. skiped.')
                continue

            jobinfo[name]['service'] = i

            # チャンネルを追加
            #FIXME

            # キューを追加
            #FIXME

        # DEBUG
        for i in jobinfo.keys():
            print('### timer')
            for k, v in jobinfo[i]['timer'].items():
                print(k, ':', v)
            print('### service')
            for k, v in jobinfo[i]['service'].items():
                print(k, ':', v)
            print()

        # 開始時間で昇順にソート
        job_array = sorted(jobinfo.items(), key=lambda x:x[1]['rec_begin'])

        # DEBUG
        for i in job_array:
            print(i[0])

        return job_array


    def _systemctl_show(self, unit):
        """
        systemctl --user --all --no-pager showの出力を
        ジョブ毎にDictにまとめ、配列に詰めて返す
        """
        command = self.systemctlshow
        command.append(unit)
        jobarr = []
        try:
            with Popen(
                command, universal_newlines=True, stdout=PIPE, stderr=STDOUT,
            ) as J:
                job = {}
                for i in J.stdout:
                    i = i.strip()
                    if not i:
                        jobarr.append(job)
                        job = {}
                        continue
                    k, v = i.split('=', 1)
                    job[k] = v
                # append last job
                if job:
                    jobarr.append(job)
        except (OSError, ValueError) as err:
            print('cannot get job information: ', err)
            return []

        return jobarr
