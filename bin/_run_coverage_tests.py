#!/usr/bin/env python
import unittest
import coverage

from _run_tests import TEST_MODULES

COVERAGE_MODULES = [
    'app',
    'handlers',
    'models',
]

def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)

if __name__ == '__main__':
    import tornado.testing

    cov = coverage.coverage()
    cov.use_cache(0) # Do not cache any of the coverage.py stuff
    cov.start()

    try:
        tornado.testing.main()
    except SystemExit, e:
        if e.code:
            # go ahead and raise the exit :(
            raise

    cov.stop()
    print ''
    print '----------------------------------------------------------------------'
    print ' Unit Test Code Coverage Results'
    print '----------------------------------------------------------------------'

    # Report code coverage metrics
    coverage_modules = []
    for module in COVERAGE_MODULES:
        coverage_modules.append(__import__(module, globals(), locals(), ['']))
    cov.report(coverage_modules, show_missing=1)
    cov.html_report(coverage_modules, directory='coverage_report')
    # Print code metrics footer
    print '----------------------------------------------------------------------'
