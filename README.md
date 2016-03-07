# Cloud Monitor

A simple Flask application for monitoring compute clouds that run Cloud
Scheduler and HTCondor and push monitoring data to Graphite. Cloud Monitor polls
Graphite's render API every minute to retreive a high-level status summary.
Clicking any value will open a plot which can be expanded to any time window and
exported.

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

## Production

The simplest solution is to run Cloud Monitor with WSGI. Here's an example configuration for Apache:

```apache
<VirtualHost *:5000>
	Define CLOUD_MONITOR_USER user
	Define CLOUD_MONITOR_GROUP group
	Define CLOUD_MONITOR_PATH /path/to/cloud_monitor/root

    WSGIDaemonProcess cloud_monitor processes=5 threads=5 display-name='%{GROUP}' inactivity-timeout=120 user=${CLOUD_MONITOR_USER} group=${CLOUD_MONITOR_GROUP}
    WSGIProcessGroup cloud_monitor
    WSGIImportScript ${CLOUD_MONITOR_PATH}/cloud_monitor.wsgi process-group=cloud_monitor application-group=%{GLOBAL}
    WSGIScriptAlias / ${CLOUD_MONITOR_PATH}/cloud_monitor.wsgi

    <Directory ${CLOUD_MONITOR_PATH}>
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/cloud_monitor_error.log
    LogLevel warn
    CustomLog ${APACHE_LOG_DIR}/cloud_monitor_access.log combined
</VirtualHost>
```

## Metrics

Cloud Monitor currently queries the following Graphite metric paths:

```bash
"grids.$GRID.clouds.$CLOUD.enabled"
"grids.$GRID.clouds.$CLOUD.idle.{$TYPE,total}"
"grids.$GRID.clouds.$CLOUD.quota"
"grids.$GRID.clouds.$CLOUD.slots.$TYPE.$SLOT"
"grids.$GRID.clouds.$CLOUD.vms.$TYPE.{$STATUS,total}"
"grids.$GRID.heartbeat.$SERVICE"
"grids.$GRID.jobs.{$TYPE,all}.$STATUS"
```

## Collector

`scripts/cloud_monitor.py` is the data collection script that runs on each
grid's Cloud Scheduler server. It queries HTCondor using the `htcondor` Python
package and Cloud Scheduler using the `cloud_status` command. It generates a
list of metrics describing the current status of the grid. These metrics are
then pushed to the Graphite paths listed above on the monitoring server using
the pickle interface. This script is typically run once a minute by `cron`.

Be sure to set `GRIDNAME` and `CARBON_SERVER`!
