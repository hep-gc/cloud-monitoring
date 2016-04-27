#!/usr/bin/env python

import sys

from setuptools import setup

from cmon import __version__, __author__, __author_email__

setup(name='cmon',
      version=__version__,
      description="C'mon: monitor your clouds",
      author=__author__,
      author_email=__author_email__,
      url='https://github.com/hep-gc/cloud-monitoring',
      license='MIT',
      scripts=['bin/cmon'],
      packages=[
          'cmon',
          'cmon.web'
      ],
      package_data={
          'cmon.web': ['static/**/*', 'templates/**/*'],
      },
      data_files=[
          ('/usr/share/cmon/etc/cmon', ['config/cmon.yml.example']),
          ('/usr/share/cmon/etc/init', ['config/cmon.conf']),
          ('/usr/share/cmon', ['config/cmon.wsgi']),
          ('/usr/share/cmon/etc/apache2/sites-available', ['config/apache2-cmon.conf'])
      ],
      install_requires=[
          'elasticsearch',
          'flask',
          'pika',
          'pymongo'
      ],
      zip_safe=False)
