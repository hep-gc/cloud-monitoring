# C'mon: Monitor your clouds

C'mon uses status data from multiple instances of Cloud Scheduler and HTCondor
to generate an overall summary and history. C'mon conveniently works alongside
Sensu to provide monitoring of compute clouds.

Included is a simple Flask application to display a high-level status summary.
Clicking any value will open a plot which can be expanded to any time window and
exported. It can also display detailed information about running VMs and jobs
and pull log data from Elasticsearch.

## Dependencies

C'mon is built on MongoDB and RabbitMQ, so these servers need to be running
somewhere. The application itself requires the following Python packages:

  * elasticsearch
  * flask
  * pika
  * pymongo

## Quickstart

Install the package:

```bash
$ sudo python setup.py install
```

Install the configuration:

```bash
$ sudo mkdir -pv /etc/cmon
$ sudo cp config/cmon.yml.example /etc/cmon/cmon.yml
```

An Upstart script is provided:

```bash
$ sudo cp config/cmon.conf /etc/init
$ sudo start cmon
```

Then you can run the Flask application:

```bash
$ ./bin/cmon_web
```

## Production

The simplest solution is to run Cloud Monitor with WSGI. Here's an example configuration for Apache:

```apache
<VirtualHost *:80>
    SetEnv CMON_CONFIG_FILE /etc/cmon/cmon.yml

    WSGIDaemonProcess cmon processes=5 threads=5 display-name='%{GROUP}' inactivity-timeout=120 user=www-data group=www-data
    WSGIProcessGroup cmon
    WSGIImportScript /usr/share/cmon/cmon.wsgi process-group=cmon application-group=%{GLOBAL}
    WSGIScriptAlias / /usr/share/cmon/cmon.wsgi

    <Directory /usr/share/cmon>
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/cmon_error.log
    LogLevel warn
    CustomLog ${APACHE_LOG_DIR}/cmon_access.log combined
</VirtualHost>
```

This assumes that `config/cmon.wsgi` is installed at `/usr/share/cmon/cmon.wsgi`.

## Collector

`scripts/cmon_collect_status.py` is the data collection script that runs on each
grid's Cloud Scheduler server. It queries HTCondor using the `htcondor` Python
package and Cloud Scheduler using the `cloud_status` command. It pushes this
data over AMQP to the C'mon server. This script is typically run once a minute
by sensu or cron.
