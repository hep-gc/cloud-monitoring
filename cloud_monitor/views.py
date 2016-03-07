from collections import OrderedDict
from datetime import datetime
from flask import make_response, render_template, request
import json
import requests


import config
from cloud_monitor import app


@app.route('/')
def index():
    return render_template('index.html', grids=summary(), config=config)


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


def path_to_name(path):
    name = path.split('.')[1:]
    name[0] = name[0].split('_')[0]

    return name


def graphite(target, start='-2min', end='now'):
    """Query Graphite for metric data.

    Args:
        targets (str|List[str]): Graphite path, or list of paths.
        start (Optional[str]): Start of date range. Defaults to two minutes ago.
        end (Optional[str]): End of date range. Defaults to now.

    Returns:
        JSON response from the Graphite render API.
    """

    params = {
        'format': 'json',
        'target': target,
        'from':   start,
        'until':  end,
    }
    response = requests.get('http://{}/render'.format(config.GRAPHITE_HOST), params=params).text
    
    return response


def summary():
    """Retrieve a summary of Cloud Scheduler VMs and Condor jobs and slots.

    Returns:
        A hierarchical dict of metric values organized by grid and cloud.
    """

    metrics = json.loads(graphite(config.SUMMARY_METRICS))
    grids   = metrics_to_dict(metrics)['grids']

    for grid in grids:
        if grid in config.HIDE_GRIDS:
            grids[grid]['hide'] = True

        # Hide clouds with no VMs
        for cloud in grids[grid]['clouds']:
            if 'vms' not in grids[grid]['clouds'][cloud]:
                grids[grid]['clouds'][cloud]['hide'] = True
                continue

            for vmtype in grids[grid]['clouds'][cloud]['vms']:
                if grids[grid]['clouds'][cloud]['vms'][vmtype]['total'] == 0:
                    grids[grid]['clouds'][cloud]['vms'][vmtype]['hide'] = True

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

    metrics = graphite(targets, start, end)

    try:
        metrics = json.loads(metrics)[0]['datapoints']
    except:
        return []

    # Convert unix timestamps to plot.ly's required date format
    for metric in metrics:
        timestamp = datetime.fromtimestamp(metric[1])
        metric[1] = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    return metrics


def metrics_to_dict(metrics_list, metrics_dict={}):
    """Convert a list of Graphite metrics to a dict by path.

    Takes a list of metrics returned by Graphite's render API (in JSON format)
    and returns a multi-level dict. For example the metric value at the path
    ``a.b.c.d`` would accessed at the dict key ``['a']['b']['c']['d']``. This
    allows a flat list of metrics to be iterated in useful ways.

    Args:
        metrics_list (List[dict]): List of Graphite metrics.
        metrics_dict (Optional[dict]): Add metrics to this dict. Defaults to an
            empty dict.

    Returns:
        Metrics arranged into a dict by path.
    """

    for metric in metrics_list:
        path = metric['target']
        parts = path.split('.')
        len_parts = len(parts)

        subdict = metrics_dict

        for i, part in enumerate(parts):
            if i == len_parts - 1:
                if metric['datapoints'][0][0] is None:
                    subdict[part] = None
                else:    
                    subdict[part] = int(metric['datapoints'][0][0])
            else:
                if part not in subdict:
                    subdict[part] = {}

                subdict = subdict[part]

    return metrics_dict



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
