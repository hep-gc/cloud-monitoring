from collections import OrderedDict
from flask import make_response, render_template, request
import json

import config
from cloud_monitor import app
from graphite import history, path_to_name, summary


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
