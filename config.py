from collections import OrderedDict


# Graphite render API endpoint
GRAPHITE_HOST = 'localhost'

# Metrics to query for the summary view
SUMMARY_METRICS = [
    'grids.*.clouds.*.enabled',
    'grids.*.clouds.*.idle.*',
    'grids.*.clouds.*.quota',
    'grids.*.clouds.*.slots.*.*',
    'grids.*.clouds.*.jobs.*.*',
    'grids.*.clouds.*.vms.*.*',
    'grids.*.heartbeat.*',
    'grids.*.jobs.*.*',
]

# Heartbeats to display
HEARTBEATS = {
    'cloud_monitor': 'Monitor',
    'cloud_scheduler': 'CS',
    'condor': 'HTCondor',
}

# These grids won't be shown at all
HIDE_GRIDS = [
]

# Specify a list of clouds to show for each grid (or show all by default)
GRID_CLOUDS = {
}

# Date ranges for the drop-down menu
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
