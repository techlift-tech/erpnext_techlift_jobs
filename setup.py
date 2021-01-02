# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in erpnext_techlift_jobs/__init__.py
from erpnext_techlift_jobs import __version__ as version

setup(
	name='erpnext_techlift_jobs',
	version=version,
	description='App to synch ERPNext Jobs',
	author='Techlift',
	author_email='palash@techlift.in',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
