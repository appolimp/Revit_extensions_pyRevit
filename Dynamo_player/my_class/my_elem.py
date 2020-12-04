# coding=utf-8
from base.wrapper import doc, DB

from abc import abstractmethod, ABCMeta
from my_geom import MyPoints, MyFace
from my_revit_geom import GeometryInRevit
import logging


class MyElementGeom:
    """MetaClass for Element Geometry. Need overrides:

    - _calc_origin_and_orientation
    - get_symbol_points

    """
    __metaclass__ = ABCMeta

    def __init__(self, element):
        self.element = element
        self._calc_some()

        self.origin = self._calc_origin()
        self.orientation = self._calc_orientation()
        self.rotation = self._calc_rotation()

        self._calc_up_down_height()

        self.width = self._calc_width()
        self.length = self._calc_length()

    @abstractmethod
    def _calc_some(self):
        pass

    @abstractmethod
    def _calc_origin(self):
        return DB.XYZ.Zero

    @abstractmethod
    def _calc_orientation(self):
        return DB.XYZ.BasisY

    def _calc_rotation(self):
        return self.orientation.AngleTo(DB.XYZ.BasisY) * MyPoints.calc_sign(self.orientation, DB.XYZ.BasisY)

    @abstractmethod
    def _calc_width(self):
        return 3

    @abstractmethod
    def _calc_length(self):
        return 5

    def _calc_up_down_height(self):

        # FIXME It is very bad, need think
        # Почему то на активном виде некорректные точки в BoundingBox
        solid = GeometryInRevit.get_geom_by_elem(self.element)
        box = solid.GetBoundingBox()

        self.height_up = box.Max.Z
        self.height_down = box.Min.Z
        self.origin = DB.XYZ(self.origin.X, self.origin.Y, solid.ComputeCentroid().Z)

        logging.debug('Calc up down height point')

    @abstractmethod
    def get_symbol_points(self):
        """
        Get up_right and left_down points of symbol geometry

        Need be overrides in subclasses

        :return: Points max and min of symbol geometry
        :rtype: MyPoints
        """

        up, down = DB.XYZ(), DB.XYZ()
        return MyPoints(up, down)

    def _get_symbol_points_as_solid(self):
        """
        Get corner points via getting symbol solid and get it BoundingBox

        :return: Points max and min of symbol solid
        :rtype: MyPoints
        """

        solid = GeometryInRevit.get_geom_by_elem(self.element.Symbol)
        box = solid.GetBoundingBox()

        logging.debug('Get symbol points as solid symbol')
        return MyPoints(box.Max, box.Min)

    @property
    def mark_for_sheet(self):
        parameter_mark = self.element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if parameter_mark and parameter_mark.AsString():
            mark_value = parameter_mark.AsString()
        else:
            mark_value = ''
        category_name = self.element.Category.Name
        return category_name + '_' + mark_value


class MyWallGeom(MyElementGeom):

    def _calc_some(self):
        pass

    def _calc_origin(self):
        first, second = self.element.Location.Curve.GetEndPoint(0), self.element.Location.Curve.GetEndPoint(1)
        return (first + second) / 2.0

    def _calc_orientation(self):
        return self.element.Location.Curve.Direction

    def _calc_width(self):
        return self.element.Width

    def _calc_length(self):
        return self.element.Location.Curve.Length

    def get_symbol_points(self):
        """
        Get points of symbol geometry to create callout: via curve location and width

        Overrides method in metaclass

        :return: Points max and min
        :rtype: MyPoints
        """

        width = self.width
        length = self.length

        up = DB.XYZ(width / 2.0, length / 2.0, self.height_up)
        down = DB.XYZ(-width / 2.0, -length / 2.0, self.height_down)

        return MyPoints(up, down)


class MyBeamGeom(MyWallGeom):

    def _calc_width(self):
        """
        Return width of beam via symbol point distance

        :return: Width
        :rtype: float
        """

        up, down = self._get_symbol_points_as_solid()
        return up.Y - down.Y


class MyColumnGeom(MyElementGeom):
    """Class for create callout to structural column"""
    def _calc_some(self):
        self.solid_symbol_point = self._get_symbol_points_as_solid()

    def _calc_origin(self):
        return self.element.Location.Point

    def _calc_orientation(self):
        return self.element.FacingOrientation

    def _calc_width(self):
        up, down = self.solid_symbol_point
        return up.X - down.X

    def _calc_length(self):
        up, down = self.solid_symbol_point
        return up.Y - down.Y

    def get_symbol_points(self):
        """
        Get points of symbol geometry to create callout: max and min

        Overrides method in metaclass

        :return: Points max and min
        :rtype: MyPoints
        """

        return self.solid_symbol_point


class MyFloorGeom(MyElementGeom):
    """Class for create callout to floor and foundation"""

    def _calc_some(self):
        up_face = GeometryInRevit.get_up_face(self.element, vector=DB.XYZ.BasisZ)
        self.up_face = MyFace(up_face).calc_param()
        self.solid_symbol_point = self.up_face.get_two_point()

    def _calc_origin(self):
        return self.up_face.origin

    def _calc_orientation(self):
        return self.up_face.orientation

    def _calc_width(self):
        up, down = self.solid_symbol_point
        return up.X - down.X

    def _calc_length(self):
        up, down = self.solid_symbol_point
        return up.Y - down.Y

    def get_symbol_points(self):
        """
        Get points of symbol geometry to create callout: via face

        Overrides method in metaclass

        :return: Points max and min
        :rtype: MyPoints
        """

        return self.solid_symbol_point


class MyAnyGeom(MyElementGeom):
    """Class for create callout to floor and foundation"""

    def _calc_some(self):
        view = doc.ActiveView
        box = self.element.get_BoundingBox(view)
        self.up, self.down = box.Max, box.Min
        pass

    def _calc_origin(self):
        return DB.XYZ.Zero

    def _calc_orientation(self):
        return doc.ActiveView.UpDirection

    def _calc_width(self):
        return (self.up - self.down).X

    def _calc_length(self):
        return (self.up - self.down).Y

    def _calc_up_down_height(self):
        self.height_up = self.up.Z
        self.height_down = self.down.Z
        self.origin = DB.XYZ(self.origin.X, self.origin.Y, (self.height_up + self.height_down) / 2)

    def get_symbol_points(self):
        """
        Get points of symbol geometry to create callout: via BoundingBox

        In this case get points of instance geometry

        Overrides method in metaclass

        :return: Points max and min
        :rtype: MyPoints
        """

        return MyPoints(self.up, self.down)


class MyElemFactory(object):
    """
    Factory to create element

    It check the category and selects the desired class or default

    Developed categories:

    - StructuralColumns
    - Walls
    - StructuralFraming (beams)
    - Floors
    - StructuralFoundation

    """

    VALID_CAT = {
        DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_StructuralColumns).Id: MyColumnGeom,
        DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Columns).Id: MyColumnGeom,
        DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Walls).Id: MyWallGeom,
        DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_StructuralFraming).Id: MyBeamGeom,
        DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Floors).Id: MyFloorGeom,
        DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_StructuralFoundation).Id: MyFloorGeom
    }
    DEFAULT = MyAnyGeom

    @classmethod
    def get_geom_to_element(cls, element):
        """
        Get callout creator instance depending on category

        :param element: DB.Element
        :return: instance of class callout
        :rtype: MyElementGeom
        """

        elem_cat = element.Category
        return cls.VALID_CAT.get(elem_cat.Id, cls.DEFAULT)(element)

    @classmethod
    def is_valid(cls, cat):
        valid = cat.Id in cls.VALID_CAT

        logging.info('Get {}valid category: {}'.format('' if valid else 'not ', cat.Name))
        return valid
