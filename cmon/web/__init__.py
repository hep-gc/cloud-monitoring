import json
import os
import yaml
from collections import OrderedDict
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
from flask import Flask, make_response, render_template, request
from pymongo import MongoClient
from time import strftime

from graphite import query, metrics_to_dict, path_to_name


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
    'grids.*.clouds.*.lost.*',
    'grids.*.clouds.*.unreg.*',
    'grids.*.clouds.*.quota',
    'grids.*.clouds.*.slots.*.*',
    'grids.*.clouds.*.jobs.*.*',
    'grids.*.clouds.*.vms.*.*',
    'grids.*.clouds.*.api-vms.*',
    'grids.*.heartbeat.*',
    'grids.*.jobs.*.*',
    'grids.*.sysinfo.*',
]


app = Flask(__name__)

with open(os.environ.get('CMON_CONFIG_FILE', DEFAULT_CONFIG_FILE), 'r') as config_file:
    config = yaml.load(config_file)

db = MongoClient(config['mongodb']['server'], config['mongodb']['port'])[config['mongodb']['db']]
es = Elasticsearch()

graphite.GRAPHITE_HOST = config['graphite']['server']
graphite.GRAPHITE_PORT = config['graphite']['web_port']


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'refresh' in request.values:
        return render_grids()
    else:
        return render_template('pages/index.html.j2', grids=get_grids(), links=config['links'], date_ranges=DATE_RANGES)


@app.route('/clouds/<grid_name>/<cloud_name>', methods=['GET', 'POST'])
def cloud(grid_name, cloud_name):
    if 'refresh' in request.values:
        return render_cloud(grid_name, cloud_name)
    else:
        return render_template('pages/cloud.html.j2', cloud=get_cloud(grid_name, cloud_name), links=config['links'], date_ranges=DATE_RANGES)


@app.route('/clouds/<grid_name>/<cloud_name>/vms/<vm_hostname>', methods=['GET', 'POST'])
def vm(grid_name, cloud_name, vm_hostname):
    if 'refresh' in request.values:
        return render_vm(grid_name, vm_hostname)
    else:
        vm = get_vm(grid_name, vm_hostname)
        logs = get_logs('"{0}" "{1}"'.format(vm['id'], vm['hostname']))
        return render_template('pages/vm.html.j2', back='/clouds/{0}/{1}'.format(grid_name, cloud_name), vm=vm, logs=logs, links=config['links'], date_ranges=DATE_RANGES)


@app.route('/clouds/<grid_name>/<cloud_name>/jobs/<job_id>', methods=['GET', 'POST'])
def jobs(grid_name, cloud_name, job_id):
    if 'refresh' in request.values:
        return render_job(grid_name, job_id)
    else:
        job = get_job(grid_name, job_id)
        logs = get_logs('"{0}"'.format(job_id))
        return render_template('pages/job.html.j2', back='/clouds/{0}/{1}'.format(grid_name, cloud_name), job=job, logs=logs, links=config['links'], date_ranges=DATE_RANGES)


@app.route('/json', methods=['GET', 'POST'])
def data():
    if 'paths[]' in request.values:
        paths = request.values.getlist('paths[]')
        (range_from, range_end) = date_range()

        traces = []

        for path in paths:
            name = path_to_name(path)
            trace = plotly(get_history(path, range_from, range_end), name=' '.join(name))
            traces.append(trace)

        return json.dumps(traces, indent=4, separators=(',', ': '))
    else:
        return '{}'

@app.route('/export', methods=['GET', 'POST'])
def export():
    if 'paths[]' in request.values:
        paths = request.values.getlist('paths[]')
        (range_from, range_end) = date_range()
        timestamps = OrderedDict({})

        traces = {}
        for path in paths:
            name  = path_to_name(path)
            trace = get_history(path, range_from, range_end)
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


def render_grids():
    return render_template('partials/grids.html.j2', grids=get_grids())


def render_cloud(grid_name, cloud_name):
    return render_template('partials/cloud.html.j2', cloud=get_cloud(grid_name, cloud_name))


def render_vm(grid_name, vm_hostname):
    vm = get_vm(grid_name, vm_hostname)
    logs = get_logs('"{0}" "{1}"'.format(vm['id'], vm['hostname']))

    return render_template('partials/vm.html.j2', vm=vm, logs=logs)


def render_job(grid_name, job_id):
    job = get_job(grid_name, job_id)
    logs = get_logs('"{0}"'.format(job_id))

    return render_template('partials/job.html.j2', job=job, logs=logs)


def get_grids():
    grids = {}
    cursor = db.grids.find()
    for grid in cursor:
        grids[grid['_id']] = grid
        grids[grid['_id']]['data_valid'] = grids[grid['_id']]['last_updated'] > datetime.now() + timedelta(minutes=-10)
        grids[grid['_id']]['last_updated_str'] = grids[grid['_id']]['last_updated'].strftime('%H:%M:%S %d-%b')
    return grids


def get_cloud(grid_name, cloud_name):
    """Query status database for 
    """
    cursor = db.vms.find({
        'grid': grid_name,
        'cloud': cloud_name,
        'last_updated': {'$gte': datetime.now() - timedelta(hours=1)}
    })
    vms = []
    for vm in cursor.sort('status', -1):
        vms.append(vm)

    cursor = db.jobs.find({
        'grid': grid_name,
        'cloud': cloud_name,
        'last_updated': {'$gte': datetime.now() - timedelta(hours=1)}
    })
    jobs = []
    for job in cursor.sort('queue_date', 1):
        jobs.append(job)

    cloud = {
        'grid': grid_name,
        'name': cloud_name,
        'vms': vms,
        'jobs': jobs,
    }
    return cloud


def get_vm(grid_name, vm_hostname):
    vm = db.vms.find_one({
        'grid': grid_name,
        'hostname': vm_hostname,
    })

    cursor = db.jobs.find({
        '$and': [
            { 'grid': grid_name },
            {
                '$or': [
                    { 'host': vm_hostname },
                    { '$and': [ {'last_host': vm_hostname}, {'host': None} ] },
                ]
            }
        ]
    })
    jobs = []
    for job in cursor.sort('status', -1):
        jobs.append(job)

    vm['jobs'] = jobs

    return vm


def get_job(grid_name, job_id):
    job = db.jobs.find_one({
        'grid': grid_name,
        '_id': job_id,
    })

    return job


def get_logs(terms):
    response = es.search(index='logstash-*', size=200, body={
        'query': {
            'filtered': {
                'query': {
                    'query_string': {
                        'analyze_wildcard': True,
                        'query': terms
                    }
                }
            }
        },
        'sort': {
            '@timestamp': 'desc'
        }
    })

    return response['hits']['hits']


def get_history(targets, start='-1h', end='now'):
    """Retrieve the time series data for one or more metrics.

    Args:
        targets (str|List[str]): Graphite path, or list of paths.
        start (Optional[str]): Start of date range. Defaults to one hour ago.
        end (Optional[str]): End of date range. Defaults to now.

    Returns:
        A list of metric values.
    """

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


@app.template_filter('status_label')
def status_label(status):
    if status == 'running' or status == 'completed':
        return 'success'
    elif status == 'gone':
        return 'disabled'
    elif status == 'held':
        return 'warning'
    elif status == 'error':
        return 'danger'

    return 'info'
