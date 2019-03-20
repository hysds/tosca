from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from setuptools import setup, find_packages

setup(
    name='tosca',
    version='0.3.0',
    long_description='Advanced FacetView User Interface',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask', 'gunicorn', 'gevent', 'requests',
                      'Flask-SQLAlchemy', 'Flask-WTF', 'Flask-DebugToolbar',
                      'Flask-Login', 'simpleldap', 'simplekml',
                      'future>=0.17.1']
)
