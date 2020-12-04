from my_view import MyView
from my_geom import MyPoints
from base.wrapper import Transaction


class MyCalloutCreator:
    """
    MetaClass for Callout. Need overrides:

    - _calc_origin_and_orientation
    - _get_symbol_points

    _need_update determines whether to rotate and crop
    """

    def __init__(self, element, need_update=True):
        """
        Initialization of instance

        :param element:
        :type element: MyElementGeom
        """

        self.element = element
        self.need_update = need_update

        self.callout = None

    @Transaction.ensure('Create callout on view')
    def create_callout_on_view(self, view, template_view=None,  rotated=True, offset=2.0):
        """
        Create callout on given view, offset and rotate if it needed

        :param view: view on which the callout will be created
        :param rotated: Is rotated view or not
        :param template_view: DB.View, template view
        :type rotated: bool
        :param offset: Value of offset at geometry
        :type offset: float
        :return: MyCallout instance
        :rtype: MyCalloutCreator
        """

        points = self._get_up_down_points(offset)
        self.callout = MyView.create_callout(view.Id, view.GetTypeId(), *points)

        if self.need_update:
            self._update(symbol_point=points, rotated=rotated)

        if template_view:
            self.callout.ApplyViewTemplateParameters(template_view)

        return self

    def _update(self, symbol_point, rotated):
        """
        Rotate view if is need and set correct crop border

        :param symbol_point: Max and min point of instance geometry
        :type symbol_point: MyPoints
        :param rotated: Is rotated view or not
        :type rotated: bool
        """

        if rotated:
            self.callout.calc_and_rotate(self.element.orientation, self.element.origin)

        border = self.create_border(symbol_point)
        self.callout.set_crop(border)

    def create_border(self, points):
        """
        Create CurveLoop rectangle by two point in main coord system and then rotate it

        :param points: Max and min point
        :type points: MyPoints
        :return: DB.CurveLoop
        """

        points_list = MyPoints.create_rectangle(*points)
        rotated_points = points_list.rot_by_point_and_angle(self.element.origin, -self.element.rotation)

        loop = rotated_points.get_curve_loop()
        return loop

    def _get_up_down_points(self, offset):
        """
        Get up_right and left_down points of instance geometry with offset without rotation

        :param offset: Value of offset at geometry
        :type offset: float
        :return: Points max and min of instance geometry
        :rtype: MyPoints
        """

        points = self.element.get_symbol_points()
        points.transform_symbol_point_for_callout(self.element.origin, offset)
        return points
