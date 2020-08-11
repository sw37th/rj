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

    def __str__(self):
        return self.name

    def _qstat(self):
        try:
            ret = run(
                self.qstat,
                timeout=self.comm_timeout,
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
            )
            self.jobs = json.loads(ret.stdout)
        except (CalledProcessError, TimeoutExpired) as err:
            print('cannot get job information: {}'.format(err))

    def _create_jobscript(self, ch, title, begin, rectime, repeat=''):
        """
        ジョブスクリプトファイルを作成し、ファイル名を返す
        """
        command = self.recpt1[:]
        if self._is_bs(ch):
            command.append('--lnb 15')
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
                        _logdir=self.logdir,
                        _recdir=self.recdir,
                        _command=' '.join(command),
                    )
                )
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create jobscript: {}'.format(err))
            sys.exit(1)

        return scriptname

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

        return None
