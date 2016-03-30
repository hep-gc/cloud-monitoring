from datetime import datetime
import json
import requests

import config


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
    response = requests.get('http://{}/render'.format(config.GRAPHITE_HOST), params=params).text

    return response


def summary():
    """Retrieve a summary of Cloud Scheduler VMs and Condor jobs and slots.

    Returns:
        A hierarchical dict of metric values organized by grid and cloud.
    """

    metrics = json.loads(query(config.SUMMARY_METRICS))
    grids   = metrics_to_dict(metrics)['grids']

    for grid in grids:
        if grid in config.HIDE_GRIDS:
            grids[grid]['hide'] = True

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
                cloud['lost'] = cloud['api-vms'].get('error', 0) + cloud['api-vms'].get('starting', 0) + cloud['api-vms'].get('running', 0) - sum([vmtype['total'] for vmtype in cloud['vms'].values()])
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
