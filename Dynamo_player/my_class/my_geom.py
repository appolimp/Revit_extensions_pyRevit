# coding=utf-8
from base.wrapper import DB, doc

from math import pi
from System.Collections.Generic import List

import logging


class MyPoints(object):
    def __init__(self, *points):
        if points and isinstance(points[0], (list, tuple)):
            self.points = points[0]
        else:
            self.points = points

    @classmethod
    def create_rectangle(cls, up, down):
        left_up = DB.XYZ(down.X, up.Y, up.Z)
        right_down = DB.XYZ(up.X, down.Y, up.Z)
        return MyPoints(down, left_up, up, right_down)

    def rot_by_point_and_angle(self, origin, angle):
        transform = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, origin)
        new_points = [transform.OfPoint(point) for point in self.points]

        return MyPoints(new_points)

    def get_curve_loop(self):
        loop_list = List[DB.Curve]()

        for first, second in zip(self.points, self.points[1:] + [self.points[0]]):
            loop_list.Add(DB.Line.CreateBound(first, second))

        loop = DB.CurveLoop.Create(loop_list)
        logging.debug('CurveLoop was created')
        return loop

    def move_by_vector(self, vector):
        self.points = [point + vector for point in self.points]
        return self

    def set_height(self, height):
        self.points = [DB.XYZ(point.X, point.Y, height) for point in self.points]
        return self

    def displace_two_point_to_vector(self, vector):
        first, second = self.points
        self.points = [first + vector, second - vector]
        return self

    def transform_symbol_point_for_callout(self, origin, offset):
        self.move_by_vector(origin)
        self.set_height(doc.ActiveView.Origin.Z)
        self.displace_two_point_to_vector(DB.XYZ(offset, offset, 0))

    @staticmethod
    def calc_sign(main_v, second):
        prod = main_v.CrossProduct(second)
        return 1 if prod.Z >= 0 else -1

    def compute_min_max(self):
        max_x = max_y = float('-inf')
        min_x = min_y = float('inf')

        for point in self.points:
            max_x = max(point.X, max_x)
            max_y = max(point.Y, max_y)
            min_x = min(point.X, min_x)
            min_y = min(point.Y, min_y)

        up = DB.XYZ(max_x, max_y, 0)
        down = DB.XYZ(min_x, min_y, 0)

        return MyPoints(up, down)

    def __str__(self):
        return 'Point: ' + str(self.points)

    def __format__(self, format_spec):
        return '\nPoints:\n' + '\n'.join(
            '{:.2f}, {:.2f}, {:.2f}'.format(point.X, point.Y, point.Z) for point in self.points)

    def __iter__(self):
        return iter(self.points)

    def __getattr__(self, item):
        return getattr(self.points, item)

    def __getitem__(self, item):
        return self.points[item]


class MyFace:
    def __init__(self, face):
        self.face = face

    def calc_param(self):
        self._find_corner()
        self._compute_center()
        self.orientation = self.face.YVector
        self.rotation = -self.orientation.AngleTo(DB.XYZ.BasisY) * MyPoints.calc_sign(self.orientation, DB.XYZ.BasisY)
        return self

    def get_two_point(self):
        if 0.02 < abs(self.rotation) < pi - 0.02:
            rot_point = self.corner_polygon.rot_by_point_and_angle(self.origin, -self.rotation)
        else:
            rot_point = self.corner_polygon

        rot_point.move_by_vector(-self.origin)
        return rot_point.compute_min_max()

    def _find_corner(self):
        loops = self.face.EdgeLoops
        bounds = self._get_bounds(loops)

        area = []
        for f_bounds in self.flatten_polygons(bounds):
            area.append(self.get_signed_polygon_area(f_bounds))

        self._area = min(area)
        self.corner_polygon = MyPoints(bounds[area.index(self._area)])

        logging.debug('Calc area: {}'.format(self._area))
        # logging.debug('{}'.format(self.corner_polygon))

        return self.corner_polygon

    def _compute_center(self):
        g_x_sum = 0
        g_y_sum = 0

        for first, second in zip(self.corner_polygon, self.corner_polygon[1:] + [self.corner_polygon[0]]):
            sec_br = first.X * second.Y - second.X * first.Y
            g_x_sum += (first.X + second.X) * sec_br
            g_y_sum += (first.Y + second.Y) * sec_br

        g_x_sum /= 6 * -self._area
        g_y_sum /= 6 * -self._area

        self.origin = DB.XYZ(g_x_sum, g_y_sum, 0)
        # logging.debug('Calc origin: {:.3}, {:.3}, {:.3}'.format(self.origin.X, self.origin.Y, self.origin.Z))
        return self.origin

    @staticmethod
    def _get_bounds(loops):
        polygons = []
        for loop in loops:
            polygon = []
            for edge in loop:
                points = list(edge.Tessellate())
                if polygon:
                    assert not polygon[-1].IsAlmostEqualTo(points[0])
                polygon.extend(points[:-1])
            polygons.append(polygon)
        return polygons

    def flatten_polygons(self, polygons):
        """
        Спроецировать список полигонов на горизонтальную плоскость

        :param polygons: Список полигонов
        :type polygons: list[list[DB.XYZ]]
        :return: Лист плоских точек
        :rtype: list[list[DB.UV]]
        """

        return List[List[DB.UV]](self.flatten_polygon(polygon) for polygon in polygons)

    def flatten_polygon(self, polygon):
        """
        Спроецировать список точек на горизонтальную плоскость

        :param polygon: Лист точек
        :type polygon: list[DB.XYZ]
        :return: Лист плоских точек
        :rtype: list[DB.UV]
        """

        return List[DB.UV](self.flatten_point(point) for point in polygon)

    @staticmethod
    def flatten_point(point):
        """
        Спроецировать точку на горизонтальную плоскость как вектор в двумерном пространстве

        :param point: Point
        :type point: DB.XYZ
        :return: new DB.UV
        :rtype: DB.UV
        """

        return DB.UV(point.X, point.Y)

    @staticmethod
    def get_signed_polygon_area(points):
        """
        Get area 2d polygon

        :param points: list[DB.UV]
        :type points: list[DB.UV]
        :return: Area
        :rtype: float
        """

        area = 0
        j = points[len(points) - 1]

        for i in points:
            area += (j.U + i.U) * (j.V - i.V)
            j = i

        return area / 2
