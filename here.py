import site, os.path as op
ROOT = op.abspath(op.dirname(__file__))
path = lambda *a: op.join(ROOT, *a)
site.addsitedir(path('vendor'))
