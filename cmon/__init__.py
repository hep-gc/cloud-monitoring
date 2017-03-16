__version__ = '0.2'
__author__ = 'Darryl Ring'
__author_email__ = 'ringda@uvic.ca'

CARBON_PATHS = {
    'cloud_other': 'grids.{}.clouds.{}.{}',
    'cloud_slots': 'grids.{}.clouds.{}.slots.{}.{}',
    'cloud_jobs': 'grids.{}.clouds.{}.jobs.{}.{}',
    'cloud_idle': 'grids.{}.clouds.{}.idle.{}',
	'cloud_lost': 'grids.{}.clouds.{}.lost.{}',
    'cloud_unreg': 'grids.{}.clouds.{}.unreg.{}',
    'jobs': 'grids.{}.jobs.{}.{}',
    'sysinfo': 'grids.{}.sysinfo.{}',
    'cloud_vms': 'grids.{}.clouds.{}.vms.{}.{}',
}

# class Parser():

#     def __init__(self):
#         self.db = None
#         self.config = None
