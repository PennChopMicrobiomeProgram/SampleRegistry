#!/usr/bin/env python

from distutils.core import setup
from glob import glob

setup(
    name='SampleRegistry',
    version='0.1',
    description='PennCHOP Microbiome Program Sample Registry',
    author='Kyle Bittinger',
    author_email='kylebitinger@gmail.com',
    url='http://github.com/PennChopMicrobiomeProgram/SampleRegistry',
    packages=['sample_registry'],
    entry_points = {'console_scripts': [
        'register_run = sample_registry.register:register_run',
        'register_run_file = sample_registry.register:register_illumina_file',
        'unregister_samples = sample_registry.register:unregister_samples',
        'register_samples = sample_registry.register:register_samples',
        'register_annotations = sample_registry.register:register_annotations',
        'register_host_species = sample_registry.register:register_host_species',
        'register_sample_types = sample_registry.register:register_sample_types',
        'export_samples = sample_registry.export:export_samples',
        ]},
    )

