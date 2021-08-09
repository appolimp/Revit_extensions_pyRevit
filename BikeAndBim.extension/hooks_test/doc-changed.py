from pyrevit import EXEC_PARAMS

import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference("RevitServices")

import Autodesk.Revit.DB as DB


doc = EXEC_PARAMS.event_args.GetDocument()  # type: DB.Document

rebar_filer = DB.ElementClassFilter(DB.Structure.Rebar)
added_rebar_id = EXEC_PARAMS.event_args.GetAddedElementIds(rebar_filer)

if added_rebar_id:
    print 777, doc.IsReadOnly

    active_view = doc.ActiveView
    value = active_view.LookupParameter('Sheet Number').AsString()

    for el_id in added_rebar_id:
        rebar = doc.GetElement(el_id)
        param = rebar.LookupParameter('Comments')
        param.Set(value)

        print '#{} rebar. Comments == [{}]'.format(el_id, value)
