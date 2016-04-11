from collections import OrderedDict
from flask import make_response, render_template, request
import json

import config
from cloud_monitor import app
from graphite import history, path_to_name, summary
import status


@app.route('/')
def index():
    return render_template('index.html', grids=summary(), config=config)


@app.route('/clouds/<grid_name>/<cloud_name>')
def cloud(grid_name, cloud_name):
    cloud = status.cloud(grid_name, cloud_name)
    return render_template('cloud.html', cloud=cloud, config=config)


@app.route('/clouds/<grid_name>/<cloud_name>/vms/<vm_hostname>')
def vm(grid_name, cloud_name, vm_hostname):
    vm = status.vm(grid_name, vm_hostname)
    logs = status.logs('"{0}" "{1}"'.format(vm['id'], vm['hostname']))
    return render_template('vm.html', back='/clouds/{0}/{1}'.format(grid_name, cloud_name), vm=vm, logs=logs, config=config)


@app.route('/clouds/<grid_name>/<cloud_name>/jobs/<job_id>')
def jobs(grid_name, cloud_name, job_id):
    job = status.job(grid_name, job_id)
    logs = status.logs('"{0}"'.format(job_id))
    return render_template('job.html', back='/clouds/{0}/{1}'.format(grid_name, cloud_name), job=job, logs=logs, config=config)


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
