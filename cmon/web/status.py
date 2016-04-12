from datetime import datetime, timedelta
import json
import requests


def summary(db):
    paths = {}

    cursor = db.vms.aggregate([
        { '$match': { 'status': { '$ne': 'gone' } } },
        { '$group': { '_id': { 'grid': '$grid', 'cloud': '$cloud', 'type': '$type', 'status': '$status' },
            'count': { '$sum': 1 } } } ])

    for group in cursor:
        path = 'grids.{0}.clouds.{1}.vms.{2}.{3}'.format(group['_id']['grid'], group['_id']['cloud'], group['_id']['type'], group['_id']['status'])
        paths[path] = group['count']

    cursor = db.jobs.aggregate([
        { '$match': { 'status': { '$ne': 'gone' } } },
        { '$group': { '_id': { 'grid': '$grid', 'cloud': '$cloud', 'status': '$status' },
            'count': { '$sum': 1 } } } ])

    for group in cursor:
        if group['_id']['cloud']:
            path = 'grids.{0}.clouds.{1}.jobs.all.{2}'.format(group['_id']['grid'], group['_id']['cloud'], group['_id']['status'])
            paths[path] = group['count']

        path = 'grids.{0}.jobs.all.{1}'.format(group['_id']['grid'], group['_id']['status'])
        paths[path] = group['count']

    return paths


def cloud(db, grid_name, cloud_name):
    """Query status database for 
    """
    cursor = db.vms.find({
        'grid': grid_name,
        'cloud': cloud_name,
        'last_updated': {'$gte': datetime.now() - timedelta(hours=1)}
    })
    vms = []
    for vm in cursor.sort('status', -1):
        vms.append(vm)

    cursor = db.jobs.find({
        'grid': grid_name,
        'cloud': cloud_name,
        'last_updated': {'$gte': datetime.now() - timedelta(hours=1)}
    })
    jobs = []
    for job in cursor.sort('queue_date', 1):
        jobs.append(job)

    cloud = {
        'grid': grid_name,
        'name': cloud_name,
        'vms': vms,
        'jobs': jobs,
    }
    return cloud

def vm(db, grid_name, vm_hostname):
    vm = db.vms.find_one({
        'grid': grid_name,
        'hostname': vm_hostname,
    })

    cursor = db.jobs.find({
        '$and': [
            { 'grid': grid_name },
            {
                '$or': [
                    { 'host': vm_hostname },
                    { '$and': [ {'last_host': vm_hostname}, {'host': None} ] },
                ]
            }
        ]
    })
    jobs = []
    for job in cursor.sort('status', -1):
        jobs.append(job)

    vm['jobs'] = jobs

    return vm

def job(db, grid_name, job_id):
    job = db.jobs.find_one({
        'grid': grid_name,
        '_id': job_id,
    })

    return job

def logs(es, terms):
    response = es.search(index='logstash-*', size=200, body={
        'query': {
            'filtered': {
                'query': {
                    'query_string': {
                        'analyze_wildcard': True,
                        'query': terms
                    }
                }
            }
        },
        'sort': {
            '@timestamp': 'desc'
        }
    })

    return response['hits']['hits']
