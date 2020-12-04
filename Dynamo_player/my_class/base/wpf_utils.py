# -*- coding: utf-8 -*-
# http://www.voidspace.org.uk/ironpython/presentation.html
import sys
sys.path.append(r"C:\Program Files (x86)\IronPython 2.7\Lib")
sys.path.append("C:\Program Files (x86)\IronPython 2.7\DLLs")
import clr
clr.AddReference('System')

clr.AddReference("IronPython.Wpf")
import wpf

# Add references to WPF assemblies
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
from System.Windows import Application, Window
# from System.Windows.Markup import XamlReader
# from System.Windows.Shapes import Polygon, Path
# from System.Windows.Media import PathGeometry, PathFigure, LineSegment,\
#     PathSegmentCollection, CombinedGeometry, GeometryCombineMode, GeometryGroup,\
#     GeometryCollection
# from System.IO import File
from System.Windows.Controls import Label, ListBox, ListBoxItem, CheckBox


class WPFWindow(Window):
    # todo fix xaml file selection (copy from pyrevit)
    # todo fix crash on using .Show() instead .ShowDialog()

    def __init__(self, xaml_source):
        wpf.LoadComponent(self, xaml_source)
