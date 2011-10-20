import re
import tornado.web

def thousands_commas(v):
    thou=re.compile(r"([0-9])([0-9][0-9][0-9]([,.]|$))").search
    v=str(v)
    vl=v.split('.')
    if not vl: return v
    v=vl[0]
    del vl[0]
    if vl: s='.'+'.'.join(vl)
    else: s=''
    mo=thou(v)
    while mo is not None:
        l = mo.start(0)
        v=v[:l+1]+','+v[l+1:]
        mo=thou(v)
    return v+s

class Thousands(tornado.web.UIModule):

    def render(self, number):
        return thousands_commas(number)
