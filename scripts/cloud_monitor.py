#!/usr/bin/python

import htcondor
import json
import pickle
from pprint import pprint
import re
import socket
import struct
from subprocess import Popen, PIPE
import sys
import time
import urllib2

if sys.version_info <= (2, 6):
    json.loads = json.read


# Configuration ################################################################

GRIDNAME = ''

CARBON_SERVER      = ''
CARBON_WEB_PORT    = 80
CARBON_PICKLE_PORT = 2004


# Setup ########################################################################

CARBON_OTHER_PATH     = 'grids.%s.clouds.%s.%s'
CARBON_SLOTS_PATH     = 'grids.%s.clouds.%s.slots.%s.%s'
CARBON_IDLE_PATH      = 'grids.%s.clouds.%s.idle.%s'
CARBON_JOBS_PATH      = 'grids.%s.jobs.%s.%s'
CARBON_VMTYPE_PATH    = 'grids.%s.clouds.%s.vms.%s.%s'
CARBON_LIVE_PATH      = 'util.live_hosts.%s.%s'
CARBON_HEARTBEAT_PATH = 'grids.%s.heartbeat.%s'

RE_HOSTNAME = re.compile(r'^([a-z0-9\-]+)')

CARBON_METRIC_PATHS = [
    CARBON_SLOTS_PATH  % (GRIDNAME, '*', '*', '*'),
    CARBON_IDLE_PATH   % (GRIDNAME, '*', '*'),
    CARBON_JOBS_PATH   % (GRIDNAME, '*', '*'),
    CARBON_VMTYPE_PATH % (GRIDNAME, '*', '*', '*'),
]
CARBON_METRIC_PARAMS = '?format=json&from=-1min&end=now&target=' + '&target='.join(CARBON_METRIC_PATHS)

CONDOR_JOB_STATUSES = {
    0: 'unexpanded',
    1: 'idle',
    2: 'running',
    3: 'removed',
    4: 'completed',
    5: 'held',
    6: 'error',
}

heartbeats = {
    'cloud_monitor':   1,
    'cloud_scheduler': 0,
    'condor':          0,
}
metrics = {}
clouds  = {}
jobs    = {
    'all': dict((status, 0) for status in CONDOR_JOB_STATUSES.values())
}
jobs['all']['total'] = 0

timestamp = int(time.time())


# Get Metrics ##################################################################

# Query Condor to get jobs and slots
try:
    condor_coll   = htcondor.Collector()
    condor_schedd = htcondor.Schedd()
    condor_slots  = condor_coll.query(htcondor.AdTypes.Startd, 'True', ['Name', 'Mips', 'Kflops'])
    condor_jobs   = condor_schedd.query('True', ['JobStatus', 'TargetClouds', 'AccountingGroup'])
    heartbeats['condor'] = 1
except:
    condor_slots = []
    condor_jobs  = []

# Query Cloud Scheduler to get VMs
try:
    cloudscheduler_clouds = Popen(['cloud_status', '-aj'], stdout=PIPE).communicate()[0]
    cloudscheduler_clouds = json.loads(cloudscheduler_clouds)['resources']
    heartbeats['cloud_scheduler'] = 1
except:
    cloudscheduler_clouds = []

# Query Graphite to get list of metrics
graphite_metrics = urllib2.urlopen('http://' + CARBON_SERVER + '/render' + CARBON_METRIC_PARAMS)
graphite_metrics = graphite_metrics.read()
graphite_metrics = json.loads(graphite_metrics)

for metric in graphite_metrics:
    metrics[metric['target']] = 0


# Process CloudSchduler VMs ####################################################

for cloud in cloudscheduler_clouds:
    cloud_name = cloud['name']
    clouds.setdefault(cloud_name, {
        'enabled': 0,
        'quota':   cloud['max_slots'],
        'vms':     {},
        'slots':   {},
        'vmtypes': {},
        'mips':    0,
        'kflops':  0,
    })

    if cloud['enabled']:
        clouds[cloud_name]['enabled'] = 1

    for vm in cloud['vms']:
        if vm['override_status']:
            status = vm['override_status'].lower()
        else:
            status = vm['status'].lower()

        hostname = vm['hostname'].split('.')[0]

        clouds[cloud_name]['vms'][hostname] = {
            'status': status,
            'vmtype': vm['vmtype'],
            'count':  0,
        }

        vmtype = vm['vmtype']

        if vmtype not in clouds[cloud_name]['vmtypes']:
            clouds[cloud_name]['vmtypes'][vmtype] = {
                'total':    0,
                'starting': 0,
                'running':  0,
                'retiring': 0,
                'error':    0,
                'shutdown': 0,
            }

        clouds[cloud_name]['vmtypes'][vmtype]['total'] += 1
        clouds[cloud_name]['vmtypes'][vmtype][status]  += 1


# Process Condor Slots #########################################################

for slot in condor_slots:
    (slot_name, machine) = slot['Name'].split('@')

    if '_' not in slot_name:
        continue

    machine = machine.split('.')[0]

    for cloud_name, cloud in clouds.iteritems():
        if machine in cloud['vms']:
            vmtype = cloud['vms'][machine]['vmtype']

            cloud['vms'][machine]['count'] += 1

            if vmtype not in cloud['slots']:
                cloud['slots'][vmtype] = {}

            if slot_name in cloud['slots'][vmtype]:
                cloud['slots'][vmtype][slot_name] += 1
            else:
                cloud['slots'][vmtype][slot_name] = 1

            cloud['mips']   += slot.get('Mips', 0)
            cloud['kflops'] += slot.get('Kflops', 0)


# Process Condor Jobs ##########################################################

for job in condor_jobs:
    status = CONDOR_JOB_STATUSES[job['JobStatus']]

    jobs['all']['total'] += 1
    jobs['all'][status]  += 1

    jobtype = None

    if 'TargetClouds' in job:
        if job['TargetClouds'] == 'IAAS':
            jobtype = '1_Core'
        elif job['TargetClouds'] == 'IAAS_MCORE':
            jobtype = '8_Core'
        elif job['TargetClouds'] == 'Alberta':
            jobtype = 'Alberta'
        elif job['TargetClouds'] == 'CERNClouds':
            if job['AccountingGroup'] == 'group_mcore':
                jobtype = 'MCore'
            elif job['AccountingGroup'] == 'group_himem':
                jobtype = 'Himem'
            elif job['AccountingGroup'] == 'group_analysis':
                jobtype = 'Analy'
        elif job['TargetClouds'] == 'cern-preservation':
            jobtype = 'DPHEP'

    if jobtype:
        if jobtype not in jobs:
            jobs[jobtype] = dict((status, 0) for status in CONDOR_JOB_STATUSES.values())
            jobs[jobtype]['total'] = 0

        jobs[jobtype]['total'] += 1
        jobs[jobtype][status]  += 1


# Generate Metrics #############################################################

for cloud_name, cloud in clouds.iteritems():
    for metric in ['enabled', 'quota', 'mips', 'kflops']:
        path = CARBON_OTHER_PATH % (GRIDNAME, cloud_name, metric)
        metrics[path] = cloud[metric]

    for vmtype, slots in cloud['slots'].iteritems():
        for slot, count in slots.iteritems():
            path = CARBON_SLOTS_PATH % (GRIDNAME, cloud_name, vmtype, slot)
            metrics[path] = count
    
    idle = dict((vmtype, 0) for vmtype in cloud['vmtypes'].keys())
    idle['total'] = 0

    if len(cloud['vms']):
        for vm_id, vm in cloud['vms'].iteritems():
            if vm['status'] == 'running' and vm['count'] == 0:
                idle['total'] += 1
                idle[vm['vmtype']] += 1

    for vmtype, count in idle.iteritems():
        path = CARBON_IDLE_PATH % (GRIDNAME, cloud_name, vmtype)
        metrics[path] = count

    for vmtype, statuses in cloud['vmtypes'].iteritems():
        for status, count in statuses.iteritems():
            path = CARBON_VMTYPE_PATH % (GRIDNAME, cloud_name, vmtype, status)
            metrics[path] = count

    for vm in cloud['vms'].keys():
        if cloud['vms'][vm]['status'] == 'running' or cloud['vms'][vm]['status'] == 'retiring':
            vm_hostname = RE_HOSTNAME.findall(vm)[0]
            path = CARBON_LIVE_PATH % (GRIDNAME, vm_hostname)
            metrics[path] = 1

for jobtype, statuses in jobs.iteritems():
    for status, count in statuses.iteritems():
        path = CARBON_JOBS_PATH % (GRIDNAME, jobtype, status)
        metrics[path] = count


# Send Metrics #################################################################

graphite_metrics = []
for path, count in metrics.iteritems():
    graphite_metrics.append((path, (timestamp, count)))

for heartbeat in heartbeats:
    path = CARBON_HEARTBEAT_PATH % (GRIDNAME, heartbeat)
    graphite_metrics.append((path, (timestamp, heartbeats[heartbeat])))

try:
    sock = socket.socket()
    sock.connect((CARBON_SERVER, CARBON_PICKLE_PORT))
except socket.error:
    raise SystemExit("Couldn't connect to {} on port {}, is carbon-cache.py running?".format(CARBON_SERVER, CARBON_PICKLE_PORT))

package = pickle.dumps(graphite_metrics, 1)
length  = struct.pack('!L', len(package))

# pprint(metrics)
print "[%s] %d metrics sent" % (time.strftime('%Y-%m-%d %H:%M:%S'), len(graphite_metrics))

sock.sendall(length + package)
sock.close()
