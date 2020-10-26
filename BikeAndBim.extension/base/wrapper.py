import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI as UI
import Autodesk.Revit.Exceptions as Ex
from System.Collections.Generic import List

from pyrevit.revit.db.transaction import Transaction


class ScriptError(Exception):
    pass


class SheetsNotSelected(ScriptError):
    pass


class ElemNotFound(ScriptError):
    pass


class ParamNotFound(ScriptError):
    pass


uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def transaction(f=None, msg="Dynamo Transaction"):
    if f is None:
        return lambda f: transaction(f, msg=msg)

    def wrapped(*args, **kwargs):
        with Transaction(msg):
            r = f(*args, **kwargs)
        return r

    return wrapped
