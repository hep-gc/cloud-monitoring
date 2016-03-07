# Cloud Monitor

A simple Flask application for monitoring compute clouds that run Cloud Scheduler and HTCondor and push monitoring data to Graphite. Cloud Monitor polls Graphite's render API every minute to retreive a high-level status summary. Clicking any value will open a plot which can be expanded to any time window and exported.

## Quickstart

Using `virtualenv`, intall the dependencies:

```bash
$ virtualenv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
```

Then, run the Flask web server:

```bash
$ python run.py
```

## Metrics

Cloud Monitor currently queries the following Graphite metric paths:

```bash
"grids.$GRID.clouds.$CLOUD.enabled"
"grids.$GRID.clouds.$CLOUD.idle.$TYPE"
"grids.$GRID.clouds.$CLOUD.quota"
"grids.$GRID.clouds.$CLOUD.slots.$TYPE.$STATUS"
"grids.$GRID.clouds.$CLOUD.vms.$TYPE.$STATUS"
"grids.$GRID.heartbeat.$SERVICE"
"grids.$GRID.jobs.$TYPE.$STATUS"
```
