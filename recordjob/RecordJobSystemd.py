# -*- coding: utf-8 -*-

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

    def get_self(self):
        return self
