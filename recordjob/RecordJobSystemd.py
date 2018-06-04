# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from subprocess import run, Popen, PIPE, STDOUT, CalledProcessError
import hashlib
import os
import recordjob
import sys

class RecordJobSystemd(recordjob.RecordJob):
    def __init__(self):
        super().__init__()
        self.name = 'RecordJobSystemd'
        self.prefix = 'RJ'
        self.unitdir = os.path.expanduser('~') + '/.config/systemd/user'
        self.systemctl = 'systemctl'
        self.systemctlstart = [
            self.systemctl,
            '--user',
            'start',
        ]
        self.systemctlshow = [
            self.systemctl,
            '--user',
            '--all',
            '--no-pager',
            'show',
        ]
        self.systemctlshowenv = [
            self.systemctl,
            '--user',
            '--all',
            '--no-pager',
            'show-environment',
        ]
        self.recpt1 = [self.recpt1_path, '--b25', '--strip']
        self.template_timer = """# created programmatically via rj. Do not edit.
[Unit]
Description={_suffix}: timer unit for {_title}
CollectMode=inactive-or-failed

[Timer]
AccuracySec=1s
OnCalendar={_begin}
RemainAfterElapse=no
"""
        self.template_service = """# created programmatically via rj. Do not edit.
[Unit]
Description={_suffix}: service unit for {_title}

[Service]
Environment="RJ_ch={_ch}" "RJ_walltime={_walltime}"
ExecStart=@/bin/bash "/bin/bash" "-c" "{_recpt1} $$RJ_ch $$RJ_walltime {_output}.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
"""

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
        else:
            # for broadcasting satellite
            tuner = 'bs'
            self.recpt1.append('--lnb 15')


        # RJ.211.goldenkamui.20180529005950.bs.service
        unit = '{}.{}.{}.{}.{}'.format(
            self.prefix,
            ch,
            title,
            begin.strftime('%Y%m%d%H%M%S'),
            tuner,
        )
        unit_timer = unit + '.timer'
        unit_service = unit + '.service'

        try:
            # timerユニットファイル作成
            with open(self.unitdir + '/' + unit_timer, 'w') as f:
                f.write(
                    self.template_timer.format(
                        _suffix=self.prefix,
                        _title=title,
                        _begin=begin.strftime('%Y-%m-%d %H:%M:%S'),
                    )
                )
            # serviceユニットファイル作成
            with open(self.unitdir + '/' + unit_service, 'w') as f:
                output = self.recdir + '/{}.{}'.format(title, ch)
                f.write(
                    self.template_service.format(
                        _suffix=self.prefix,
                        _title=title,
                        _ch=ch,
                        _walltime=str(int(rectime.total_seconds())),
                        _recpt1=' '.join(self.recpt1),
                        _output=output,
                    )
                )
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create unit file:', err)
            return ''

        # timer開始
        self.systemctlstart.append(unit_timer)
        try:
           run(self.systemctlstart, check=True)
        except (CalledProcessError) as err:
            print('cannot submit job:', err)
            return ''

        rj_id_long = hashlib.sha256(unit.encode('utf-8')).hexdigest()
        return rj_id_long

    def get_job_info(self, date=None, jid=None):
        """
        録画ジョブ情報を取得して配列として返す
        """

        jobinfo = self._get_systemd_job_info()

        if jid:
            if len(jid) == 8:
                jobinfo = [i for i in jobinfo if i['rj_id'] == jid]
            else:
                jobinfo = [i for i in jobinfo if i['rj_id_long'] == jid]
        elif date:
            # dateで指定された日のジョブのみを配列に詰め直す
            nextday = date + timedelta(days=1)
            jobinfo = [
                i for i in jobinfo
                    if i['rec_begin'] >= date and i['rec_begin'] < nextday
            ]

        return jobinfo

    def _get_systemd_job_info(self):
        """
        全ジョブのtimerユニット/serviceユニット情報を取得し、
        補足情報を追加して配列に詰めて返す
        """
        jobinfo = {}
        jobarray = []
        current = datetime.now()

        unit = self.prefix + '.*'

        # 環境変数を取得
        user_env = self._systemctl_show(None, showenv=True)[0]

        # ユニット情報を取得
        jobs = self._systemctl_show(unit)
        for i in jobs:
            name = i.get('Names')
            name, suffix = name.rsplit('.', 1)

            if name not in jobinfo:
                jobinfo[name] = {}
                jobinfo[name]['tuner'] = name.rsplit('.', 1)[1]

            jobinfo[name][suffix] = i

        # ユニット情報から録画管理に必要な情報を取得、追加
        for name in jobinfo.keys():
            # 録画開始時刻
            rec_begin = jobinfo[name]['timer'].get('NextElapseUSecRealtime')
            if not rec_begin:
                # ジョブ実行中(録画中)
                rec_begin = jobinfo[name]['timer'].get('LastTriggerUSec')

            if rec_begin:
                # 開始時刻のdatetimeオブジェクトを追加
                jobinfo[name]['rec_begin'] = datetime.strptime(
                    # WDY YYYY-MM-DD HH:MM:SS TZN
                    rec_begin, "%a %Y-%m-%d %H:%M:%S %Z"
                )
                if jobinfo[name]['rec_begin'] < current:
                    # 録画中
                    elapse = current - jobinfo[name]['rec_begin']
                    jobinfo[name]['elapse'] = elapse
                    jobinfo[name]['record_state'] = 'Recording'

            # チャンネル、録画時間、録画終了時刻
            rec_env = jobinfo[name]['service'].get('Environment')
            if rec_env:
                ch, walltime = rec_env.split()
                ch = ch.split('=')[1]
                walltime = walltime.split('=')[1]

                jobinfo[name]['channel'] = ch
                jobinfo[name]['walltime'] = timedelta(seconds=int(walltime))
                jobinfo[name]['rec_end'] = (
                    jobinfo[name]['rec_begin'] + jobinfo[name]['walltime'] 
                )
            jobinfo[name]['user'] = user_env.get('USER')
            title = name.rsplit('.', 2)[0]
            jobinfo[name]['rj_title'] = title.split('.', 2)[2]
            jobinfo[name]['rj_id_long'] = hashlib.sha256(
                name.encode('utf-8')
            ).hexdigest()
            jobinfo[name]['rj_id'] = jobinfo[name]['rj_id_long'][0:8]

        # DEBUG
        #for i in jobinfo.keys():
        #    print(i)
        #    print('### timer')
        #    for k, v in jobinfo[i]['timer'].items():
        #        print(k, ':', v)
        #    print('### service')
        #    for k, v in jobinfo[i]['service'].items():
        #        print(k, ':', v)
        #    print()

        # 開始時間で昇順にソート
        jobarray = [
            jobinfo[k] for k, v in sorted(
                jobinfo.items(), key=lambda x:x[1]['rec_begin']
            )
        ]

        return jobarray

    def _systemctl_show(self, unit, timer=True, service=True, showenv=False):
        """
        systemctl --user --all --no-pager showの出力を
        ジョブ毎にDictにまとめ、配列に詰めて返す
        """
        if showenv:
            command = self.systemctlshowenv
        else:
            command = self.systemctlshow
            if timer:
                command.append(unit + '.timer')
            if service:
                command.append(unit + '.service')


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
