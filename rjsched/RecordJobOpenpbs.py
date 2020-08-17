from datetime import datetime, timedelta
from subprocess import run, PIPE, STDOUT, DEVNULL, CalledProcessError, TimeoutExpired
import hashlib
import json
import os
import rjsched
import sys
import textwrap

class RecordJobOpenpbs(rjsched.RecordJob):
    def __init__(self):
        super().__init__()
        pbsexec = '/work/pbs/bin/'
        self.name = 'RecordJobOpenpbs'
        self.qstat = [pbsexec + 'qstat', '-f', '-F', 'json']
        self.pbsnodes = [pbsexec + 'pbsnodes', '-a']
        self.qsub = [pbsexec + 'qsub']
        self.qalter = [pbsexec + 'qalter', '-a' ]
        self.scriptdir = '/home/autumn/jobsh'
        self.logdir = '/home/autumn/log'
        self.joblist = []

    def __str__(self):
        return self.name

    def _get_job_info(self):
        """
        qstatコマンドの出力から、ジョブごとに下記の情報を取得し
        self.joblist[]に詰める

        'rj_id':        OpenPBSのジョブID (str)
        'channel':      チャンネル番号 (str)
        'rj_title':     番組名 (str)
        'record_state': ジョブの状態 (str)
        'tuner':        地上波(tt) or 衛星放送(bs) (str)
        'user':         ジョブのオーナー (str)
        'group':        ジョブのグループ (str)
        'exec_host':    実行中のジョブのみ。ジョブの実行ホスト (str)
        'rec_begin':    録画開始時刻 (datetime)
        'rec_end':      録画終了時刻 (datetime)
        'walltime':     録画時間 (timedelta)
        'elapse':       実行中のジョブのみ。録画開始からの経過時間 (timedelta)
        'qtime':        ジョブのキュー追加時刻 (datetime)
        'ctime':        ジョブの作成時刻 (datetime)
        'mtime':        ジョブをMoMが最後にモニタした時刻 (datetime)
        """
        current = datetime.now()

        proc = self._run_command(self.qstat)
        jobs = json.loads(proc.stdout).get('Jobs', {})
        for k, v in jobs.items():
            # ジョブID、チャンネル番号、番組名
            job = {'rj_id': k.split('.')[0]}
            job['channel'], job['rj_title'] = v.get('Job_Name').split('.', 1)

            # 録画時間
            wt_h, wt_m, wt_s = list(
                map(
                    int,
                    v.get('Resource_List').get('walltime').split(':')))
            job['walltime'] = timedelta(hours=wt_h, minutes=wt_m, seconds=wt_s)

            # ジョブの状態、録画開始時刻、録画終了時間、録画開始からの経過時間
            state = v.get('job_state')
            if state == "R":
                # running
                job['rec_begin'] = datetime.strptime(
                    v.get('etime'), "%a %b %d %H:%M:%S %Y")
                job['elapse'] = current - job['rec_begin']
                job['exec_host'] = v.get('exec_host').split('/')[0]
            else:
                # waiting
                job['rec_begin'] = datetime.strptime(
                    v.get('Execution_Time'), "%a %b %d %H:%M:%S %Y")
            job['rec_end'] = job['rec_begin'] + job['walltime']
            job['record_state'] = self.job_state.get(state)

            # 地上波(tt) or 衛星放送(bs)
            if 'bs' in v.get('Resource_List'):
                job['tuner'] = 'bs'
            else:
                job['tuner'] = 'tt'

            # ジョブのオーナー、ジョブのグループ、ジョブの実行ホスト
            job['user'] = v.get('euser')
            job['group'] = v.get('egroup')

            # qtime, ctime, mtime
            job['qtime'] = datetime.strptime(
                v.get('qtime'), "%a %b %d %H:%M:%S %Y")
            job['ctime'] = datetime.strptime(
                v.get('ctime'), "%a %b %d %H:%M:%S %Y")
            job['mtime'] = datetime.strptime(
                v.get('mtime'), "%a %b %d %H:%M:%S %Y")

            self.joblist.append(job)

        # 録画開始時刻で昇順にソート
        self.joblist = sorted(
            self.joblist, key=lambda x:x['rec_begin'])

    def get_job_info(self, date=None):
        self._get_job_info()
        return self.joblist

    def _create_jobscript(self, ch, title, begin, rectime, repeat=''):
        """
        ジョブスクリプトファイルを作成し、ファイル名を返す
        """
        command = self.recpt1[:]
        if self._is_bs(ch):
            command.append('--lnb 15')
            tuner = 'bs'
        else:
            tuner = 'tt'
        at = begin.strftime('%Y%m%d%H%M.%S')
        scriptname = '{}/{}.{}.{}.sh'.format(
                self.scriptdir,
                title,
                at,
                str(datetime.now().timestamp()),
                )
        try:
            with open(scriptname, 'w') as f:
                output = self.recdir + '/{}.{}'.format(title, ch)
                f.write(
                    textwrap.dedent('''\
                        #PBS -N {_ch}.{_title}
                        #PBS -a {_at}
                        #PBS -l walltime={_walltime}
                        #PBS -l {_tuner}=1
                        #PBS -j oe
                        #PBS -o {_logdir}
                        #PBS -e {_logdir}
                        umask 022
                        _jobid=`echo $PBS_JOBID | awk -F'.' '{{printf("%05d", $1)}}'`
                        {_command} {_ch} - {_recdir}/{_title}.{_ch}.`date +%Y%m%d_%H%M.%S`.${{_jobid}}.ts
                    ''').format(
                        _ch=ch,
                        _title=title,
                        _at=at,
                        _walltime=str(int(rectime.total_seconds())),
                        _tuner=tuner,
                        _logdir=self.logdir,
                        _recdir=self.recdir,
                        _command=' '.join(command),
                    )
                )
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create jobscript: {}'.format(err))
            sys.exit(1)

        return scriptname

    def _run_command(self, command):
        """
        コマンドを実行し、CompletedProcessオブジェクトを返す
        """
        try:
            proc = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                #universal_newlines=True,
                timeout=self.comm_timeout,
                check=True,)
        except (TimeoutExpired, CalledProcessError) as err:
            print('{} failed: {}'.format(command[0], err))
            sys.exit(1)
        return proc

    def add(self, ch, title, begin, rectime, repeat=''):
        """
        ch:      チャンネル番号(string)
        title:   番組名(string)
        begin:   開始時間(datetime.datetime)
        rectime: 録画時間(datetime.timedelta)
        repeat:  繰り返しフラグ(string)
        """
        scriptname = self._create_jobscript(ch, title, begin, rectime, repeat)

        qsub = self.qsub[:]
        qsub.append(scriptname)
        print(qsub)
        proc = self._run_command(qsub)
        print('{}'.format(proc.stdout))

        return None
