#!/usr/bin/env python

from datetime import datetime, timedelta
import json
import pika
from pymongo import MongoClient
import socket
import sys
from xml.etree import ElementTree

RMQ_SERVER = 'monitor.heprc.uvic.ca'
RMQ_PORT = 5672
RMQ_USER = 'sensu'
RMQ_SECRET = '95f5c326975623f9e2c1ef3cfa6eae2920dce88add83731533b8dc06402fafae'
RMQ_VHOST = '/sensu'

db = MongoClient().cloud_status

def vm_update(vm_id, status):
    pass

if __name__ == '__main__':
    creds = pika.PlainCredentials(RMQ_USER, RMQ_SECRET)
    params = pika.ConnectionParameters(RMQ_SERVER, RMQ_PORT, RMQ_VHOST, creds)
    rmq = pika.BlockingConnection(params)

    channel = rmq.channel()
    channel.exchange_declare(exchange='status', exchange_type='fanout')
    result = channel.queue_declare(queue='status', durable=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='status', queue=queue_name)

    try:
        def callback(ch, method, props, body):
            parse_cloud_status(json.loads(body))

            # Acknowledge message to prevent re-queueing
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(callback, queue=queue_name)
        channel.start_consuming()

    except KeyboardInterrupt:
        print 'Shutting down'

    finally:
        rmq.close()
