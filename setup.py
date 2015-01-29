#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='latexpmk',
      version='0.1',
      description='A simple script for real-time latex compilation.',
      author='Roman Yurchak',
      author_email='rth@crans.org',
      packages=['latexpmk'],
      entry_points = {
          'console_scripts': ['latexpmk = latexpmk.main:cli']
        }
     )

