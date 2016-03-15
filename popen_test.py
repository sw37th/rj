#!/usr/bin/env python3

import subprocess

qstat = "/usr/local/torque/bin/qstat"

cmd = [qstat, "-f"]
#jobs = subprocess.check_output(cmd, universal_newlines=True)
#print(jobs)

#pjob = subprocess.Popen(cmd, universal_newlines=True)
pjob = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#pjob1 = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE)
#pjob2 = subprocess.Popen(["egrep", "^Job"], universal_newlines=True, stdin=pjob1.stdout, stdout=subprocess.PIPE)
#pjob = pjob2.stdout
#job = subprocess.check_output(cmd)
#print(pjob)
#stdout_data, stderr_data = pjob.communicate()
#for jobinfo in pjob.stdout:
for jobinfo in pjob.stdout:
    print(jobinfo.rstrip())
    
