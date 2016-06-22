#!/usr/local/bin/python2.7
########################################################################
# This needs to be set to whichever Python has the cloudscheduler and
# pika packages installed.

import ConfigParser
import json
import pika
import sys
import time

from cloudscheduler.cloud_management import ResourcePool
from socket import gethostname

if sys.version_info <= (2, 6):
    json.loads = json.read
    json.dumps = json.write


# RabbitMQ configuration
RMQ_SERVER = 'SENSU RABBITMQ SERVER GOES HERE'
RMQ_PORT = 5672
RMQ_USER = 'sensu'
RMQ_SECRET = 'SENSU RABBITMQ SECRET GOES HERE'
RMQ_VHOST = '/sensu'


clouds = {}

timestamp = int(time.time())

config = ConfigParser.ConfigParser()
config.read('/etc/cloudscheduler/cloud_resources.conf')

for cloud_name in config.sections():
    cloud = ResourcePool._cluster_from_config(config, cloud_name)
    cloud_type = cloud.cloud_type.lower()

    if cloud_type == 'openstacknative':
        try:
            cloud_api = cloud._get_creds_nova()
            cloud_vms = cloud_api.servers.findall()
            print 'Connected to %s' % cloud_name
        except:
            print 'Unable to connect to %s' % cloud_name
            continue

        clouds[cloud_name] = []

        for vm in cloud_vms:
            vm_status = cloud.VM_STATES[vm.status].lower()
            
            clouds[cloud_name][vm_status] += 1
            clouds[cloud_name]['total'] += 1

    elif cloud_type in ['amazonec2', 'eucalyptus', 'openstack']:
        try:
            cloud_api = cloud._get_connection()
            cloud_vms = cloud_api.get_all_instances()
            print 'Connected to %s' % cloud_name
        except:
            print 'Unable to connect to %s' % cloud_name
            continue

        if cloud_name not in clouds:
            clouds[cloud_name] = dict([(status, 0) for status in STATUSES])

        for vm in cloud_vms:
            vm_status = cloud.VM_STATES[vm.instances[0].state].lower()

            clouds[cloud_name][vm_status] += 1
            clouds[cloud_name]['total'] += 1

    elif cloud_type == 'azure':
        try:
            cloud_api = cloud._get_service_connection()
            cloud_vms = cloud_api.list_hosted_services()
            print 'Connected to %s' % cloud_name
        except:
            print 'Unable to connect to %s' % cloud_name
            continue

        if cloud_name not in clouds:
            clouds[cloud_name] = dict([(status, 0) for status in STATUSES])

        for vm in cloud_vms:
            try:
                vm_details = cloud_api.get_hosted_service_properties(vm.service_name, True)
            except:
                continue

            if vm_details.deployments and vm_details.deployments[0].role_instance_list:
                vm_status = vm_details.deployments[0].role_instance_list[0].instance_status
                if vm_status in cloud.VM_STATES.keys():
                    vm_status = cloud.VM_STATES[vm_status]
                vm_status = vm_status.lower()

            else:
                vm_status = 'error'

            clouds[cloud_name][vm_status] += 1
            clouds[cloud_name]['total'] += 1

grid_name = sys.argv[1] if len(sys.argv) > 1 else gethostname()

payload = {
    'grid': grid_name,
    'resources': clouds,
}
payload = json.dumps(payload)

creds = pika.PlainCredentials(RMQ_USER, RMQ_SECRET)
params = pika.ConnectionParameters(RMQ_SERVER, RMQ_PORT, RMQ_VHOST, creds)
try:
    rmq = pika.BlockingConnection(params)

    props = pika.BasicProperties(
        delivery_mode=2,
        timestamp=int(time.time())
    )

    channel = rmq.channel()
    channel.exchange_declare(exchange='cmon', exchange_type='fanout')
    channel.basic_publish(exchange='cmon', routing_key='', body=payload, properties=props)
except Exception as e:
    print "ERROR: %s" % str(e)
    sys.exit(1)
finally:
    rmq.close()

print "OK: %d bytes of JSON sent for %s" % (len(payload), grid_name)
