from datetime import datetime
import json
import requests


GRAPHITE_HOST = 'localhost'
GRAPHITE_PORT = '80'


def query(target, start='-2min', end='now'):
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
    response = requests.get('http://{}:{}/render'.format(GRAPHITE_HOST, GRAPHITE_PORT), params=params).text

    return response


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


def path_to_name(path):
    name = path.split('.')[1:]
    name[0] = name[0].split('_')[0]

    return name
