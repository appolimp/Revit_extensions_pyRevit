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
import logging


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


def transaction_group(f=None, msg="Dynamo Transaction"):
    if f is None:
        return lambda f: transaction_group(f, msg=msg)

    def wrapped(*args, **kwargs):
        tGroup = DB.TransactionGroup(doc, 'Place Families')
        tGroup.Start()

        r = f(*args, **kwargs)

        tGroup.Commit()
        return r

    return wrapped


def one_transaction_in_group(f=None, msg="Dynamo Transaction"):
    if f is None:
        return lambda f: one_transaction_in_group(f, msg=msg)

    def wrapped(*args, **kwargs):
        t = DB.Transaction(doc, msg)

        t.Start()
        r = f(*args, **kwargs)

        t.Commit()
        return r

    return wrapped


class Transaction:
    def __init__(self, msg=None):
        self.msg = msg or 'Dynamo Transaction'
        self.transaction = DB.Transaction(doc, msg)

    def __enter__(self):
        self.transaction.Start()

    def __exit__(self, exception, exception_msg, tb):
        if exception:
            self.transaction.RollBack()
            logging.error('Error in Transaction Context: has rolled back.')
            # traceback.print_tb(tb)
            # raise exception # Let exception through
        else:
            try:
                self.transaction.Commit()
            except Exception as exc:
                self.transaction.RollBack()
                logging.error('Error in Transaction Commit: has rolled back.')
                logging.error(exc)
                raise

    @staticmethod
    def ensure(name):
        """ Transaction Manager Decorator

        Decorate any function with ``@Transaction.ensure('Transaction Name')``
        and the function will run within a Transaction Context.

        Args:
            name (str): Name of the Transaction

        """

        from functools import wraps

        def wrap(f):
            @wraps(f)
            def wrapped_f(*args, **kwargs):
                with Transaction(name):
                    return_value = f(*args, **kwargs)
                return return_value
            return wrapped_f
        return wrap
