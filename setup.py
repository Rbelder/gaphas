
VERSION = '0.4.0'

from ez_setup import use_setuptools

use_setuptools()

from setuptools import setup, find_packages
from distutils.cmd import Command

class build_doc(Command):
    description = 'Builds the documentation'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        epydoc_conf = 'epydoc.conf'

        try:
            import sys
            from epydoc import cli
            old_argv = sys.argv[1:]
            sys.argv[1:] = [
                '--config=%s' % epydoc_conf,
                '--no-private', # epydoc bug, not read from config
                '--simple-term',
                '--verbose'
            ]
            cli.cli()
            sys.argv[1:] = old_argv

        except ImportError:
            print 'epydoc not installed, skipping API documentation.'

setup(
    name='gaphas',
    version=VERSION,
    description='Gaphas is a GTK+ based diagramming widget',
    long_description="""\
Gaphas is a MVC canvas that uses Cairo_ for rendering. One of the nicer things
of this widget is that the user (model) is not bothered with bounding box
calculations: this is all done through Cairo.

Some more features:

- Each item has it's own separate coordinate space (easy when items are
  rotated).
- Items on the canvas can be connected to each other. Connections are
  maintained by a linear constraint solver.
- Multiple views on one Canvas.
- What is drawn is determined by Painters. Multiple painters can be used and
  painters can be stacked.
- User interaction is handled by Tools. Tools can be stacked.
- Versatile undo/redo system

GTK+ and PyGTK_ are required.

.. _Cairo: http://cairographics.org/
.. _PyGTK: http://www.pygtk.org/
""",

    classifiers=[
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    keywords='',

    author="Arjan J. Molenaar",
    author_email='arjanmol@users.sourceforge.net',

    url='http://gaphor.devjavu.com/wiki/Subprojects/Gaphas',

    #download_url='http://cheeseshop.python.org/',

    license='GNU Library General Public License (LGPL, see COPYING)',

    packages=find_packages(exclude=['ez_setup']),

    setup_requires = 'nose >= 0.9.2',

    install_requires=[
     'decorator >= 2.2.0',
#    'PyGTK >= 2.8.0',
    ],

    zip_safe=False,

    package_data={
    # -*- package_data: -*-
    },

    entry_points = {
    },

    test_suite = 'nose.collector',

    cmdclass={'build_doc': build_doc },
    )
      
