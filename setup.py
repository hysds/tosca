from setuptools import setup, find_packages

setup(
    name='tosca',
    version='0.2.2',
    long_description='Advanced FacetView User Interface',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask', 'gunicorn', 'gevent', 'supervisor', 'requests',
                      'Flask-SQLAlchemy', 'Flask-WTF', 'Flask-DebugToolbar',
                      'Flask-Login', 'simpleldap', 'simplekml']
)
