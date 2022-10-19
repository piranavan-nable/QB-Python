from setuptools import setup, find_packages


VERSION = (0, 1)
version = '.'.join(map(str, VERSION))

setup(
    name='quickbooks',
    version=version,
    author='Piranavan Sivanesan',
    author_email='piranavan@n-able.biz',
    description='A really simple, brute-force, Python class for accessing the Quickbooks API.',
    url='',
    license='N-able private ltd',

    install_requires=[
        'setuptools',
        'rauth',
        'simplejson',
        'python-dateutil',
    ],

    packages=find_packages(),
)