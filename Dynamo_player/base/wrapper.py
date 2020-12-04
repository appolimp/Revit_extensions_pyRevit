import clr

clr.AddReference('RevitAPI')
import Autodesk.Revit.DB as DB

clr.AddReference('RevitAPIUI')
import Autodesk.Revit.UI as UI

import Autodesk.Revit.Exceptions as Ex

clr.AddReference("RevitNodes")

import Revit

clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)

clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = uiapp.ActiveUIDocument

import sys

sys.path.append(r"C:\Program Files (x86)\IronPython 2.7\Lib")


def transaction(f=None, doc=doc, msg="Dynamo Transaction"):
    if f is None:
        return lambda f: transaction(f, msg=msg)

    def wrapped(*args, **kwargs):
        # t = DB.Transaction(doc, msg)
        # t.Start()
        # r = f(*args, **kwargs)
        # t.Commit()

        TransactionManager.Instance.EnsureInTransaction(doc)
        r = f(*args, **kwargs)
        TransactionManager.Instance.TransactionTaskDone()
        return r

    return wrapped


def UnwrapElement(item):
    if item is None:
        return None

    if hasattr(item, '__iter__'):
        return [UnwrapElement(x) for x in item]
    elif hasattr(item, 'InternalElement'):
        return item.InternalElement
    else:
        return item
