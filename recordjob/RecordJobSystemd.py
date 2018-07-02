# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from subprocess import run, Popen, PIPE, STDOUT, DEVNULL, CalledProcessError
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
        self.tuner_tt_num = 2
        self.tuner_bs_num = 2
        self.sctl = ['systemctl', '--user']
        self.sctl_start = self.sctl + ['start']
        self.sctl_stop = self.sctl + ['stop']
        self.sctl_enable = self.sctl + ['enable']
        self.sctl_disable = self.sctl + ['disable']
        self.sctl_show = self.sctl + ['--all', '--no-pager', 'show']
        self.sctl_showenv = self.sctl + [
            '--all',
            '--no-pager',
            'show-environment',
        ]
        self.sctl_reload = self.sctl + ['daemon-reload']
        self.recpt1 = [self.recpt1_path, '--b25', '--strip']
        self.recpt1ctl = [self.recpt1ctl_path]
        self.execstop = 'ExecStop=@/bin/bash "/bin/bash" "-c" "systemctl --user disable {}"'
        self.template_timer = """# created programmatically via rj. Do not edit.
[Unit]
Description={_suffix}:{_repeat}: timer unit for {_title}
CollectMode=inactive-or-failed

[Timer]
AccuracySec=1s
OnCalendar={_begin}
RemainAfterElapse=no

[Install]
WantedBy=timers.target
"""
        self.template_service = """# created programmatically via rj. Do not edit.
[Unit]
Description={_suffix}: service unit for {_title}
CollectMode=inactive-or-failed

[Service]
Environment="RJ_ch={_ch}" "RJ_walltime={_walltime}"
ExecStart=@/bin/bash "/bin/bash" "-c" "{_recpt1} $$RJ_ch $$RJ_walltime {_output}.`date +%%Y%%m%%d_%%H%%M.%%S`.$$$.ts"
{_execstop}
"""

    def __str__(self):
        return self.name

    def _is_bs(self, ch):
        if int(ch) > 63:
            return True
        else:
            return False

    def _create_timer(self, unit, title, begin, repeat=''):
        """
        timerユニットファイル作成
        """
        repeat = repeat.upper()
        if repeat == 'WEEKLY':
            str_begin = begin.strftime('%a *-*-* %H:%M:%S')
        elif repeat == 'DAILY':
            str_begin = begin.strftime('*-*-* %H:%M:%S')
        elif repeat == 'WEEKDAY':
            str_begin = begin.strftime('Mon..Fri *-*-* %H:%M:%S')
        elif repeat == 'ASADORA':
            str_begin = begin.strftime('Mon..Sat *-*-* %H:%M:%S')
        else:
            str_begin = begin.strftime('%Y-%m-%d %H:%M:%S')
            repeat = 'ONESHOT'

        with open(unit, 'w') as f:
            f.write(
                self.template_timer.format(
                    _suffix=self.prefix,
                    _repeat=repeat,
                    _title=title,
                    _begin=str_begin,
                )
            )

    def _create_service(self, unit, ch, title, rectime, repeat=''):
        """
        # serviceユニットファイル作成
        """
        if repeat and repeat.upper() != 'ONESHOT':
            execstop = ''
        else:
            # for ONESHOT
            # serviceユニット実行後、ExecStopからsystemctl disable
            # で当該ジョブのtimerユニットを無効化する
            timer = unit.rsplit('/', maxsplit=1)[1]
            timer = timer.rsplit('.', maxsplit=1)[0] + '.timer'
            execstop = self.execstop.format(timer)

        recpt1 = self.recpt1[:]
        if self._is_bs(ch):
            recpt1.append('--lnb 15')

        with open(unit, 'w') as f:
            output = self.recdir + '/{}.{}'.format(title, ch)
            f.write(
                self.template_service.format(
                    _suffix=self.prefix,
                    _title=title,
                    _ch=ch,
                    _walltime=str(int(rectime.total_seconds())),
                    _recpt1=' '.join(recpt1),
                    _output=output,
                    _execstop=execstop,
                )
            )

    def _gen_unitname_jobid(self, ch, title, begin):
        """
        チャンネル、タイトル、開始時間から
        ユニット名を生成する
        """
        if self._is_bs(ch):
            # for broadcasting satellite
            tuner = 'bs'
        else:
            # for terrestrial television
            tuner = 'tt'

        # RJ.ch.title.YYYYMMDDhhmmss.tuner
        unit = '{}.{}.{}.{}.{}'.format(
            self.prefix,
            ch,
            title,
            begin.strftime('%Y%m%d%H%M%S'),
            tuner,
        )
        # ユニット名のsha256ハッシュをジョブIDとする
        rj_id_long = hashlib.sha256(unit.encode('utf-8')).hexdigest()

        return unit, rj_id_long

    def add(self, ch, title, begin, rectime, repeat=''):
        """
        recpt1コマンドを実行するserviceユニットファイルと
        そのserviceを指定時刻に実行するtimerユニットファイル
        を作成する。

        timerユニットはsystemd startで有効化する。
        また、OS再起動後も自動的に有効化されるよう
        systemd enableする。
        """
        unit, rj_id_long = self._gen_unitname_jobid(ch, title, begin)

        try:
            # timer/serviceユニットファイル作成
            timer_file = self.unitdir + '/' + unit + '.timer'
            service_file = self.unitdir + '/' + unit + '.service'

            self._create_timer(timer_file, title, begin, repeat)
            self._create_service(service_file, ch, title, rectime, repeat)

            # timerユニットをsystemctl start, enabled
            sctl_start = self.sctl_start[:]
            sctl_enable = self.sctl_enable[:]
            sctl_start.append(unit + '.timer')
            sctl_enable.append(unit + '.timer')

            run(sctl_start, check=True, stdout=DEVNULL, stderr=STDOUT)
            run(sctl_enable, check=True, stdout=DEVNULL, stderr=STDOUT)
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create unit file:', err)
            rj_id_long = ''
        except CalledProcessError as err:
            print('cannot submit job:', err)
            rj_id_long = ''

        return rj_id_long

    def remove(self, jid=[]):
        """
        録画ジョブを削除する
        """
        jobinfo = self.get_job_info(jid=jid)
        timers = []
        services = []
        for i in jobinfo:
            timers.append(i['timer']['Names'])
            services.append(i['service']['Names'])

        # timer停止(ジョブ削除)
        sctl_stop = self.sctl_stop[:]
        sctl_disable = self.sctl_disable[:]

        sctl_stop.extend(timers)
        sctl_stop.extend(services)
        sctl_disable.extend(timers)
        try:
           run(sctl_stop, check=True, stdout=DEVNULL, stderr=STDOUT)
           run(sctl_disable, check=True, stdout=DEVNULL, stderr=STDOUT)
        except (CalledProcessError) as err:
            print('cannot delete job:', err)

    def _unit_reload(self):
        """
        ユニットファイルを再読込する
        """
        try:
           run(self.sctl_reload, check=True)
        except (CalledProcessError) as err:
            print('cannot reload unit:', err)

    def change_begin(self, job, begin):
        """
        録画ジョブの開始時刻を指定時刻に変更
        """
        repeat = job.get('repeat')
        self._change_timer(job, begin=begin, repeat=repeat)
        self._unit_reload()

    def change_begin_delta(self, job, delta):
        """
        録画ジョブの開始時刻を相対的に変更
        """
        repeat = job.get('repeat')
        begin = job.get('rec_begin') + delta
        self._change_timer(job, begin=begin, repeat=repeat)
        self._unit_reload()

    def change_rec(self, job, rectime):
        """
        録画時間を指定時間に変更
        """
        repeat = job.get('repeat')
        self._change_service(job, rectime=rectime, repeat=repeat)
        self._unit_reload()

    def extend_rec(self, job, delta):
        """
        録画時間を相対的に延長 or 短縮
        """
        repeat = job.get('repeat')
        rectime = job.get('walltime') + delta
        self._change_service(job, rectime=rectime, repeat=repeat)
        self._unit_reload()

    def change_channel(self, job, ch):
        """
        チャンネルを変更
        """
        repeat = job.get('repeat')
        self._change_service(job, ch=ch, repeat=repeat)
        self._unit_reload()

    def change_repeat(self, job, repeat):
        """
        リピート設定を変更
        """
        begin = job.get('rec_begin')
        self._change_timer(job, begin, repeat=repeat)
        self._change_service(job, repeat=repeat)
        self._unit_reload()

    def _change_service(self, job, ch=None, rectime=None, repeat=''):
        """
        録画ジョブのserviceユニットファイルを変更する
        """
        unit = job.get('service',{}).get('FragmentPath')
        title = job.get('rj_title')

        if not ch:
            ch = job.get('channel')
        if not rectime:
            rectime = job.get('walltime')

        state = job.get('record_state', '')
        if state == 'Recording':
            # すでにrecpt1コマンドを実行中の場合は
            # recpt1ctlコマンドにて録画時間とチャンネルを
            # 変更する
            pid = job.get('service').get('MainPID')
            args = [
                '--pid', pid,
                '--time', str(int(rectime.total_seconds())),
                '--channel', ch,
            ]
            recpt1ctl = self.recpt1ctl[:]
            recpt1ctl.extend(args)
            try:
                ret = run(
                    recpt1ctl, check=True, stdout=PIPE, stderr=STDOUT,
                    universal_newlines=True
                )
                print(ret.stdout)

            except (CalledProcessError) as err:
                print('cannot change recording time:', err)
                return

        try:
            # serviceユニットファイル再作成
            # recpt1ctlで録画時間を変更した場合でも、
            # systemctl showの出力に録画時間とチャンネルを
            # 反映させるため、ここで再作成する
            self._create_service(unit, ch, title, rectime, repeat)
        except (PermissionError, FileNotFoundError) as err:
            print('cannot change recording parameter:', err)

    def _change_timer(self, job, begin, repeat=''):
        """
        録画ジョブのtimerユニットファイルを変更する
        """
        unit = job.get('timer',{}).get('FragmentPath')
        title = job.get('rj_title')

        try:
            # timerユニットファイル再作成
            self._create_timer(unit, title, begin, repeat)
        except (PermissionError, FileNotFoundError) as err:
            print('cannot change start time:', err)

    def get_job_info(self, date=None, jid=[]):
        """
        録画ジョブ情報を取得して返す
        """
        jobinfo = self._get_systemd_job_info()

        if jid:
            # 指定のIDのジョブのみ抽出
            # jidで渡された配列の文字列は
            # すべて同じ長さであると想定する
            if len(jid[0]) == 8:
                key = 'rj_id'
            else:
                key = 'rj_id_long'
            jobinfo = [i for i in jobinfo if i[key] in jid]
        elif date:
            # dateで指定された日のジョブのみ抽出
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
        job = {}
        jobarray = []
        current = datetime.now()

        unit = self.prefix + '.*'

        # 環境変数を取得
        user_env = self._systemctl_show(None, showenv=True)[0]

        # ユニット情報を取得
        for i in self._systemctl_show(unit):
            name = i.get('Names')
            name, suffix = name.rsplit('.', 1)

            if name not in job:
                job[name] = {}
                job[name]['tuner'] = name.rsplit('.', 1)[1]

            job[name][suffix] = i

        # ユニット情報から録画管理に必要な情報を取得、追加
        for name in list(job.keys()):
            # timerユニット情報、serviceユニット情報の
            # どちらか一方しかないジョブは削除する
            J = job.get(name)
            if 'timer' not in J:
                print(J['service'].get('Names'), 'is orphaned')
                del job[name]
                continue
            if 'service' not in J:
                print(J['timer'].get('Names'), 'is orphaned')
                del job[name]
                continue

            # 録画開始時刻
            rec_begin = J['timer'].get('NextElapseUSecRealtime')
            if not rec_begin:
                # ジョブ実行中(録画中)
                rec_begin = J['timer'].get('LastTriggerUSec')

            if rec_begin:
                # 開始時刻のdatetimeオブジェクトを追加
                J['rec_begin'] = datetime.strptime(
                    # WDY YYYY-MM-DD HH:MM:SS TZN
                    rec_begin, "%a %Y-%m-%d %H:%M:%S %Z"
                )
                if J['rec_begin'] < current:
                    # 録画中
                    elapse = current - J['rec_begin']
                    J['elapse'] = elapse
                    J['record_state'] = 'Recording'

            # チャンネル、録画時間、録画終了時刻
            rec_env = J['service'].get('Environment')
            if rec_env:
                ch, walltime = rec_env.split()
                ch = ch.split('=')[1]
                walltime = walltime.split('=')[1]

                J['channel'] = ch
                J['walltime'] = timedelta(seconds=int(walltime))
                J['rec_end'] = (
                    J['rec_begin'] + J['walltime'] 
                )
            J['user'] = user_env.get('USER')
            title = name.rsplit('.', 2)[0]
            J['rj_title'] = title.split('.', 2)[2]
            J['rj_id_long'] = hashlib.sha256(
                name.encode('utf-8')
            ).hexdigest()
            J['rj_id'] = J['rj_id_long'][0:8]
            J['repeat'] = J['timer'].get('Description').split(':')[1]

        # 開始時間で昇順にソート
        jobarray = [
            job[k] for k, v in sorted(
                job.items(), key=lambda x:x[1]['rec_begin']
            )
        ]

        self._check_channel_resource(jobarray)

        return jobarray

    def _systemctl_show(self, unit, timer=True, service=True, showenv=False):
        """
        systemctl --user --all --no-pager showの出力を
        ユニット毎にDictにまとめ、配列に詰めて返す
        """
        if showenv:
            command = self.sctl_showenv[:]
        else:
            command = self.sctl_show[:]
            if timer:
                command.append(unit + '.timer')
            if service:
                command.append(unit + '.service')


        unitarray = []
        try:
            with Popen(
                command, universal_newlines=True, stdout=PIPE, stderr=STDOUT,
            ) as J:
                unit = {}
                for i in J.stdout:
                    i = i.strip()
                    if not i:
                        unitarray.append(unit)
                        unit = {}
                        continue
                    k, v = i.split('=', 1)
                    unit[k] = v
                # append last unit information
                if unit:
                    unitarray.append(unit)
        except (OSError, ValueError) as err:
            print('cannot get unit information: ', err)
            return []

        return unitarray


    def _check_channel_resource(self, jobarray):
        """
        チャンネルリソースの空き具合をチェックする
        """
        tuner = {
            'tt': {'jobs': [], 'max': self.tuner_tt_num},
            'bs': {'jobs': [], 'max': self.tuner_bs_num},
        }
        message = 'Not enough tuners'

        for job in jobarray:
            t = job.get('tuner')
            if len(tuner[t]['jobs']) < tuner[t]['max']:
                # チャンネルの空きがある
                tuner[t]['jobs'].append(job)
            else:
                # ガベージコレクト
                for overlap in tuner[t]['jobs']:
                    # tuner[t]['jobs']のジョブから
                    # 録画終了しているものを削除
                    if job['rec_begin'] > overlap['rec_end']:
                        tuner[t]['jobs'].remove(overlap)

                # 改めてチャンネルの空き確認
                if (len(tuner[t]['jobs']) < tuner[t]['max']):
                    # チャンネルの空きがある
                    tuner[t]['jobs'].append(job)
                else:
                    # 警告を追加
                    job['alert'] = message
                    for i in tuner[t]['jobs']:
                        i['alert'] = message
