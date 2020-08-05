from datetime import datetime, timedelta
from subprocess import run, PIPE, STDOUT, DEVNULL, CalledProcessError, TimeoutExpired
import hashlib
import json
import os
import rjsched
import sys

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

    def add(self, ch, title, begin, rectime, repeat=''):
        print()

