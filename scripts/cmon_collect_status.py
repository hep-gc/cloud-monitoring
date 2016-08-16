#!/usr/bin/python2.6
########################################################################
# This needs to be set to whichever Python has the htcondor and pika
# packages installed.

import htcondor
import logging
import json
import pika
import sys
import time

from socket import gethostname
from subprocess import Popen, PIPE

if sys.version_info <= (2, 6):
    json.loads = json.read
    json.dumps = json.write


# RabbitMQ configuration
RMQ_SERVER = 'SENSU RABBITMQ SERVER GOES HERE'
RMQ_PORT = 5672
RMQ_USER = 'sensu'
RMQ_SECRET = 'SENSU RABBITMQ SECRET GOES HERE'
RMQ_VHOST = '/sensu'

CONDOR_JOB_STATUSES = {
    0: 'unexpanded',
    1: 'idle',
    2: 'running',
    3: 'removed',
    4: 'completed',
    5: 'held',
    6: 'error',
}


# Query Condor to get jobs and slots
condor_coll   = htcondor.Collector()
condor_schedd = htcondor.Schedd()
condor_slots  = condor_coll.query(htcondor.AdTypes.Startd, 'True', ['Name', 'Mips', 'Kflops'])
condor_jobs   = condor_schedd.query('True', [
    'JobStatus',
    'ClusterID',
    'ProcID',
    'RemoteUserCpu',
    'RequestCpus',
    'RemoteHost',
    'LastRemoteHost',
    'TargetClouds',
    'AccountingGroup',
    'NumJobStarts',
    'QDate',
    'LastJobStatus',
    'EnteredCurrentStatus'])

# Query Cloud Scheduler to get VMs
clouds = Popen(['/usr/local/bin/cloud_status -aj'], shell=True, stdout=PIPE).communicate()[0]
clouds = json.loads(clouds)['resources']

jobs = []
for condor_job in condor_jobs:
    job = {
        'status': CONDOR_JOB_STATUSES[condor_job['JobStatus']],
        'id': '%d.%d' % (condor_job['ClusterID'], condor_job['ProcID']),
        'target_clouds': condor_job.get('TargetClouds'),
        'accounting_group': condor_job.get('AccountingGroup'),
        'queue_date': condor_job.get('QDate'),
        'status_time': condor_job.get('EnteredCurrentStatus'),
        'remote_host': None,
        'last_remote_host': None,
        'last_status': None,
    }

    if 'RemoteHost' in condor_job:
        job['remote_host'] = condor_job['RemoteHost'].split('@')[1]
    if 'LastRemoteHost' in condor_job:
        job['last_remote_host'] = condor_job['LastRemoteHost'].split('@')[1]
    if 'LastJobStatus' in condor_job:
        job['last_status'] = CONDOR_JOB_STATUSES[condor_job['LastJobStatus']]

    jobs.append(job)

slots = []
for condor_slot in condor_slots:
    slot = {
        'name': condor_slot['Name'],
        'mips': condor_slot.get('Mips'),
        'kflops': condor_slot.get('Kflops'),
    }

    slots.append(slot)


grid_name = sys.argv[1] if len(sys.argv) > 1 else gethostname()

payload = {
    'grid': grid_name,
    'clouds': clouds,
    'jobs': jobs,
    'slots': slots,
}
payload = json.dumps(payload)

creds = pika.PlainCredentials(RMQ_USER, RMQ_SECRET)
params = pika.ConnectionParameters(RMQ_SERVER, RMQ_PORT, RMQ_VHOST, creds)
try:
    rmq = pika.BlockingConnection(params)

    props = pika.BasicProperties(
        delivery_mode=2,
        timestamp=int(time.time())
    )

    channel = rmq.channel()
    channel.exchange_declare(exchange='cmon', type='fanout')
    channel.basic_publish(exchange='cmon', routing_key='', body=payload, properties=props)
except Exception as e:
    print "ERROR: %s" % str(e)
    sys.exit(1)
finally:
    rmq.close()

print "OK: %d bytes of JSON sent for %s" % (len(payload), grid_name)
