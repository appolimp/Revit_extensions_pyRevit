import sys
sys.path.append("C:\Program Files (x86)\IronPython 2.7\Lib")
import time


def timeit(func):
    def wrapper(*arg, **kw):
        '''source: http://www.daniweb.com/code/snippet368.html'''
        t1 = time.time()
        res = func(*arg, **kw)
        t2 = time.time()
        print('\nt: {}'.format(t2 - t1))
        return res
    return wrapper


class ListValueDict(dict):
    def __setitem__(self, key, value):
        if key in self:
            self[key].append(value)
        else:
            super(ListValueDict, self).__setitem__(key, [value])