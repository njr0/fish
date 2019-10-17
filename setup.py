# -*- coding: utf-8 -*-
from distutils.core import setup

setup(name='fish',
      version='4.34',
      description='The Fluidinfo Shell',
      author='Nicholas J. Radcliffe',
      author_email='njr@StochasticSolutions.com',
      packages=['fish'],
      url="http://github.com/njr0/fish/",
      download_url="https://github.com/njr0/fish",
      scripts=['scripts/fish'],
      keywords=[
          'fluidinfo',
          'fluiddb',
          'abouttag',
          'about',
          'tag',
          'shell',
          'normalization',
          'canonicalization',
          'standardarization'
      ],
      classifiers = [
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Development Status :: 5 - Production/Stable',
          'License :: OSI Approved :: MIT License',
          'Environment :: Other Environment',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Internet',
      ],
      install_requires = ['urlnorm>=1.1.2', 'requests==2.20.0'],
      long_description = '''\
The Fluidinfo shell provides a shell for Fluidinfo, modelled
fairly closely on a Unix shell.

Fluidinfo is a hosted, online database based on the notion of tagging.
For more information on FluidDB, visit http://fluidinfo.com.

The full documentation is hosted in Fluidinfo and may be accessed
in an ordinary browser at

    http://fluiddb.fluidinfo.com/about/fish/fish/index.html



INSTALLATION

    python setup.py install

DEPENDENCIES

    urlnorm
    abouttag
    requests (or httplib2)
'''
      
     )
