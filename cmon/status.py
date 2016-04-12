from datetime import datetime, timedelta


def parse(status, db):
    grid_name = status['grid']

    # Fetch Current VMs and Jobs ###############################################

    db_vms = {}
    cursor = db.vms.find({'grid': grid_name, 'last_updated': {'$gte': datetime.now() - timedelta(hours=1)}})
    for vm in cursor:
        db_vms[vm['_id']] = vm

    db_jobs = {}
    cursor = db.jobs.find({'grid': grid_name, 'last_updated': {'$gte': datetime.now() - timedelta(hours=1)}})
    for job in cursor:
        db_jobs[job['_id']] = job

    current_vms = []
    current_jobs = []

    for cloud in status['clouds']:
        cloud_name = cloud['name']

        cloud_vms = []

        for vm in cloud['vms']:
            vm_id = vm['hostname']
            if not vm_id:
                continue

            cloud_vms.append(vm_id)

            db_vm = db_vms.get(vm_id)
            if db_vm:
                db_vm_status = db_vm['status']
                vm_doc = db_vm
            else:
                vm_doc = {
                    '_id': vm_id,
                    'first_updated': datetime.now(),
                    'grid': grid_name,
                    'cloud': cloud_name,
                    'hostname': vm['hostname'],
                    'id': vm['id'],
                    'type': vm['vmtype'],
                    'alt_hostname': vm['alt_hostname'],
                    'initialize_time': datetime.fromtimestamp(vm['initialize_time']),
                }

            vm_doc['last_updated'] = datetime.now()

            vm_status = vm['status'].lower()
            if vm['override_status']:
                vm_status = vm['override_status'].lower()

            if vm_status == 'provisioningtimeout':
                vm_status = 'error'

            vm_doc['status'] = vm_status
            
            if db_vm:
                vm_status_history = db_vm.get('status_history', [])
                if vm_status != db_vm_status:
                    print '%s:%s:%s %s -> %s' % (grid_name, cloud_name, vm_id, db_vm_status, vm_status)
                    vm_status_history.append([datetime.now(), vm_status])
            else:
                print '%s:%s:%s %s' % (grid_name, cloud_name, vm_id, vm_status)
                vm_status_history = [[datetime.now(), vm_status]]

            vm_doc['status_history'] = vm_status_history

            db.vms.replace_one({'_id': vm_id}, vm_doc, upsert=True)

            current_vms.append(vm_id)

        cloud_id = '.'.join((grid_name, cloud_name))
        cloud_doc = {
            '_id': cloud_id,
            'grid': grid_name,
            'cloud': cloud_name,
            'type': cloud['cloud_type'],
            'enabled': cloud['enabled'],
            'quota': cloud['max_slots'],
            'cloudscheduler_vms': cloud_vms,
        }
        
        db.clouds.replace_one({'_id': cloud_id}, cloud_doc, upsert=True)

    for vm_id, db_vm in db_vms.iteritems():
        if vm_id not in current_vms and db_vm['status'] != 'gone':
            vm_doc = db_vm
            vm_doc['status'] = 'gone'
            vm_doc['status_history'].append([datetime.now(), 'gone'])

            print '%s:%s:%s %s' % (grid_name, db_vm['cloud'], vm_id, 'gone')
            db.vms.replace_one({'_id': vm_id}, vm_doc, upsert=True)

    for job in status['jobs']:
        job_id = job['id']
        if not job_id:
            continue

        job_host = job.get('remote_host')
        job_last_host = job.get('last_remote_host')

        db_job = db_jobs.get(job_id)
        if db_job:
            db_job_status = db_job['status']
            db_job_host = db_job.get('host')
            job_doc = db_job
        else:
            job_doc = {
                '_id': job_id,
                'first_updated': datetime.now(),
                'grid': grid_name,
                'queue_date': datetime.fromtimestamp(job['queue_date'])
            }

        job_doc['last_updated'] = datetime.now()

        job_doc['status'] = job['status']
        job_doc['last_host'] = job_last_host
        job_doc['host'] = job_host

        if job_host or job_last_host:
            if job_host and job_host in db_vms:
                job_doc['cloud'] = db_vms[job_host]['cloud']
            elif job_last_host and job_last_host in db_vms:
                job_doc['cloud'] = db_vms[job_last_host]['cloud']
        else:
            if not db_job or not db_job.get('cloud'):
                job_doc['cloud'] = None

        if db_job:
            job_status_history = db_job.get('status_history', [])
            job_host_history = db_job.get('host_history', [])

            if job['status'] != db_job_status:
                print '%s:%s %s -> %s' % (grid_name, job_id, db_job_status, job['status'])
                job_status_history.append([datetime.now(), job['status']])

            if job_host != db_job_host:
                print '%s:%s %s -> %s' % (grid_name, job_id, db_job_host, job_host)
                job_host_history.append([datetime.now(), job_host])
        else:
            print '%s:%s %s %s' % (grid_name, job_id, job['status'], job_host)
            job_status_history = [[datetime.now(), job['status']]]
            job_host_history = [[datetime.now(), job_host]]

        job_doc['status_history'] = job_status_history
        job_doc['host_history'] = job_host_history

        db.jobs.replace_one({'_id': job_id}, job_doc, upsert=True)

        current_jobs.append(job_id)

    for job_id, db_job in db_jobs.iteritems():
        if job_id not in current_jobs and db_job['status'] != 'gone':
            job_doc = db_job
            job_doc['status'] = 'gone'
            job_doc['status_history'].append([datetime.now(), 'gone'])

            print '%s:%s %s' % (grid_name, job_id, 'gone')
            db.jobs.replace_one({'_id': job_id}, job_doc, upsert=True)

    for slot in status['slots']:
        continue
        slot_id = slot['id']
        if not slot_id:
            continue
