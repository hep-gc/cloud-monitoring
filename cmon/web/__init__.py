from collections import OrderedDict
from elasticsearch import Elasticsearch
from flask import Flask, make_response, render_template, request
import json
import os
from pymongo import MongoClient
import yaml

import graphite
from graphite import query, metrics_to_dict
import status


DEFAULT_CONFIG_FILE = '/etc/cmon/cmon.yml'

DATE_RANGES = [
    OrderedDict([
        ('Last 7 days',   ('-7d' ,  'now')),
        ('Last 30 days',  ('-30d',  'now')),
        ('Last 60 days',  ('-60d',  'now')),
        ('Last 90 days',  ('-90d',  'now')),
        ('Last 6 months', ('-6mon', 'now')),
        ('Last 1 year',   ('-1y',   'now')),
        ('Last 2 years',  ('-2y',   'now')),
        ('Last 5 years',  ('-5y',   'now')),
    ]),
    OrderedDict([
        ('Yesterday',            ('-2d',   '-1d')),
        ('Day before yesterday', ('-3d',   '-2d')),
        ('This day last week',   ('-8d',   '-7d')),
        ('Previous week',        ('-14d',  '-7d')),
        ('Previous month',       ('-2mon', '-1mon')),
        ('Previous year',        ('-2y',   '-1y')),
    ]),
    OrderedDict([
        ('Last 5 minutes',  ('-5min' , 'now')),
        ('Last 15 minutes', ('-15min', 'now')),
        ('Last 30 minutes', ('-30min', 'now')),
        ('Last 1 hour',     ('-1h',    'now')),
        ('Last 3 hours',    ('-3h',    'now')),
        ('Last 6 hours',    ('-6h',    'now')),
        ('Last 12 hours',   ('-12h',   'now')),
        ('Last 24 hours',   ('-24h',   'now')),
    ]),
]

SUMMARY_METRICS = [
    'grids.*.clouds.*.enabled',
    'grids.*.clouds.*.idle.*',
    'grids.*.clouds.*.quota',
    'grids.*.clouds.*.slots.*.*',
    'grids.*.clouds.*.jobs.*.*',
    'grids.*.clouds.*.vms.*.*',
    'grids.*.clouds.*.api-vms.*',
    'grids.*.heartbeat.*',
    'grids.*.jobs.*.*',
]

HEARTBEATS = {
    'cloud_monitor': 'Monitor',
    'cloud_scheduler': 'CS',
    'condor': 'HTCondor',
}


app = Flask(__name__)

with open(os.environ.get('CMON_CONFIG_FILE', DEFAULT_CONFIG_FILE), 'r') as config_file:
    config = yaml.load(config_file)

db = MongoClient(config['mongodb']['server'], config['mongodb']['port'])[config['mongodb']['db']]
es = Elasticsearch()

@app.route('/')
def index():
    return render_template('index.html', grids=summary(), config=config, heartbeats=HEARTBEATS, date_ranges=DATE_RANGES)


@app.route('/clouds/<grid_name>/<cloud_name>')
def cloud(grid_name, cloud_name):
    cloud = status.cloud(db, grid_name, cloud_name)
    return render_template('cloud.html', cloud=cloud)


@app.route('/clouds/<grid_name>/<cloud_name>/vms/<vm_hostname>')
def vm(grid_name, cloud_name, vm_hostname):
    vm = status.vm(db, grid_name, vm_hostname)
    logs = status.logs(es, '"{0}" "{1}"'.format(vm['id'], vm['hostname']))
    return render_template('vm.html', back='/clouds/{0}/{1}'.format(grid_name, cloud_name), vm=vm, logs=logs)


@app.route('/clouds/<grid_name>/<cloud_name>/jobs/<job_id>')
def jobs(grid_name, cloud_name, job_id):
    job = status.job(db, grid_name, job_id)
    logs = status.logs(es, '"{0}"'.format(job_id))
    return render_template('job.html', back='/clouds/{0}/{1}'.format(grid_name, cloud_name), job=job, logs=logs)


@app.route('/json', methods=['GET', 'POST'])
def data():
    if 'paths[]' in request.values:
        paths = request.values.getlist('paths[]')
        (range_from, range_end) = date_range()

        traces = []

        for path in paths:
            name = path_to_name(path)
            trace = plotly(history(path, range_from, range_end), name=' '.join(name))
            traces.append(trace)

        return json.dumps(traces, indent=4, separators=(',', ': '))
    elif 'mongo' in request.values:
        return json.dumps(status.summary(), indent=4, separators=(',', ': '))
    else:
        return json.dumps(summary(), indent=4, separators=(',', ': '))


@app.route('/export', methods=['GET', 'POST'])
def export():
    if 'paths[]' in request.values:
        paths = request.values.getlist('paths[]')
        (range_from, range_end) = date_range()
        timestamps = OrderedDict({})

        traces = {}
        for path in paths:
            name  = path_to_name(path)
            trace = history(path, range_from, range_end)
            traces[path] = dict([(point[1], point[0]) for point in trace])

            for point in trace:
                timestamp = point[1]
                value = point[0]

                if timestamp not in timestamps:
                    timestamps[timestamp] = []

                timestamps[timestamp].append(str(value))

        string = "timestamp\t" + "\t".join(paths) + "\n"
        for timestamp, values in timestamps.iteritems():
            string += timestamp + "\t" + "\t".join(values) + "\n"

        response = make_response(string)
        response.headers["Content-Disposition"] = "attachment; filename=data.tsv"

        return response
    else:
        return 'No Data'


def plotly(metrics=[], name='', color=None):
    """Convert a list of metric values to a Plot.ly object.
    """
    values, timestamps = zip(*metrics)
    trace = {
        'type': 'scatter',
        'x': timestamps,
        'y': values,
        'name': name,
    }

    if color:
        trace['marker'] = { color: color }

    return trace


def date_range():
    """Ensure the requested date range is in a format Graphite will accept.
    """
    
    range_from = request.values.get('from', '-1h')
    range_end  = request.values.get('end', 'now')

    try:
        # Try to coerce date range into integers
        range_from = int(float(range_from) / 1000)
        range_end  = int(float(range_end) / 1000)
    except:
        # ... or pass string directly to Graphite
        pass

    return (range_from, range_end)


def summary():
    """Retrieve a summary of Cloud Scheduler VMs and Condor jobs and slots.

    Returns:
        A hierarchical dict of metric values organized by grid and cloud.
    """

    metrics = json.loads(query(SUMMARY_METRICS))
    grids   = metrics_to_dict(metrics)['grids']

    for grid in grids:
        # if grid in HIDE_GRIDS:
        #     grids[grid]['hide'] = True

        # Hide clouds with no VMs
        for cloud_name, cloud in grids[grid]['clouds'].iteritems():
            if 'vms' not in cloud:
                cloud['hide'] = True
                continue

            hide = True
            for vmtype in cloud['vms']:
                if cloud['vms'][vmtype]['total'] != 0:
                    hide = False
                    
            cloud['hide'] = hide

            if 'jobs' in cloud and cloud['jobs']['all']['held'] > 0:
                cloud['hide'] = False

            if 'api-vms' in cloud:
                api_vms = [cloud['api-vms'].get('error', 0), cloud['api-vms'].get('starting', 0), cloud['api-vms'].get('running', 0)]
                cloud['lost'] = sum(filter(None, api_vms)) - sum([vmtype['total'] for vmtype in cloud['vms'].values()])
                if cloud['lost'] < 0:
                    cloud['lost'] = 0

    return grids


def history(targets, start='-1h', end='now'):
    """Retrieve the time series data for one or more metrics.

    Args:
        targets (str|List[str]): Graphite path, or list of paths.
        start (Optional[str]): Start of date range. Defaults to one hour ago.
        end (Optional[str]): End of date range. Defaults to now.

    Returns:
        A list of metric values.
    """

    print targets
    metrics = query(targets, start, end)

    try:
        metrics = json.loads(metrics)[0]['datapoints']
    except:
        return []

    # Convert unix timestamps to plot.ly's required date format
    for metric in metrics:
        timestamp = datetime.fromtimestamp(metric[1])
        metric[1] = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    return metrics
