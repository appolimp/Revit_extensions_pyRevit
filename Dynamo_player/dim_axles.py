# coding=utf-8
from base.wrapper import transaction, doc, DB, clr, uidoc
from base.exeption import ScriptError
from base.selection import get_selected_by_cat
from Autodesk.Revit.UI.Selection import ISelectionFilter
import logging


SECTION_TYPE = [DB.ViewType.Section, DB.ViewType.Elevation]


class MySelectionFilter(ISelectionFilter):
    def __init__(self, cat, elem):
        ISelectionFilter.__init__(self)
        self.cat = cat
        self.valid_direction = self._calc_valid_direction_or_none(elem)

    def AllowElement(self, elem):
        if type(elem) is self.cat:
            if self.valid_direction is None or self._is_valid_direction(elem):
                return True

        return False

    def _calc_valid_direction_or_none(self, axis):
        """
        Calc direction of first axis

        :param axis: DB.Grid
        :return: DB.XYZ
        """

        if type(axis) is self.cat:
            curve = axis.GetCurvesInView(DB.DatumExtentType.ViewSpecific, doc.ActiveView)[0]
            direction = curve.Direction

            return direction

    def _is_valid_direction(self, axis):
        """
        Identity is collinear axis or not

        :param axis: DB.Grid
        :return: Is collinear
        :rtype: bool
        """

        curve = axis.GetCurvesInView(DB.DatumExtentType.ViewSpecific, doc.ActiveView)[0]
        direction = curve.Direction

        prod = self.valid_direction.CrossProduct(direction)
        return prod.IsAlmostEqualTo(DB.XYZ.Zero, 0.001)

    def AllowReference(self, reference, position):
        return False


class OutLineDim:
    """
    Class for get many outline in certain normal at origin with step

    First is uniq, next is equal
    """

    FIRST_OFFSET_1 = 15
    NEXT_OFFSET_1 = 10

    def __init__(self, origin, normal):
        """
        Creator outlines with offset and step by origin and normal

        :param origin: DB.XYZ
        :param normal: DB.XYZ
        """
        self.origin = origin
        self.normal = normal

        self.scale = doc.ActiveView.Scale
        self.__offset = self._offset_coroutine()

    @classmethod
    def create_by_two_point_and_normal(cls, normal):
        """
        Create instance by normal and invited user to select origin and side

        :param normal: DB.XYZ
        :return: Instance
        :rtype: OutLineDim
        """

        point = get_user_point()
        side_point = get_user_point()

        sign_normal = cls._calc_direction_by_side(normal, side_point - point)

        return cls(point, sign_normal)

    @staticmethod
    def _calc_direction_by_side(normal, side):
        """
        Calculate direction normal by side in section or plane

        :param normal: DB.XYZ
        :param side: DB.XYZ
        :return: DB.XYZ
        """

        if doc.ActiveView.ViewType in SECTION_TYPE:
            normal = normal if side.Z > 0 else -normal
        else:
            dir_norm = normal.CrossProduct(DB.XYZ.BasisZ)
            side_z = dir_norm.CrossProduct(side).Z
            normal = normal if side_z > 0 else -normal

        logging.debug('Normal calculated {}'.format(normal))
        return normal

    def get_outline(self):
        """
        Get new outline, which have offset of previous

        :return: DB.Line
        """

        view_normal = doc.ActiveView.ViewDirection
        direction = self.normal.CrossProduct(view_normal)

        origin = self.origin + self.normal * self._offset

        out_line = DB.Line.CreateUnbound(origin, direction)

        logging.debug('Outline created: origin {}; direction {}'.format(origin, direction))
        return out_line

    @property
    def _offset(self):
        """
        Get new offset value at origin

        :return: Offset value
        :rtype: float
        """
        return next(self.__offset)

    def _offset_coroutine(self):
        """
        Coroutine for sum offset value: first is uniq

        Next with equal step
        """
        total_sum = self._calc_offset_by_value(self.FIRST_OFFSET_1)

        while True:
            yield total_sum
            total_sum += self._calc_offset_by_value(self.NEXT_OFFSET_1)

    def _calc_offset_by_value(self, value):
        """
        Convert value offset to current scale and ft

        :param value: base value
        :type value: int or float
        :return: value[ft]
        :rtype: float
        """

        new_value = value * self.scale / 304.8

        logging.debug('Calc offset value {} mm for scale 1:{} == {} ft'.format(value, self.scale, new_value))
        return new_value


class AxlesDim:
    """
    Class for get axles reference, corner axles and modify it

    Maybe update is unnecessary in current class
    """

    def __init__(self, axles):
        """


        :param axles: List of grid
        :type axles: list[DB.Grid]
        """

        self.axles = axles

        one_curve = axles[0].GetCurvesInView(DB.DatumExtentType.ViewSpecific, doc.ActiveView)[0]
        self.direction = one_curve.Direction

    @property
    def as_ref_arr(self):
        """
        Return axles as ReferenceArray

        :return: DB.ReferenceArray
        """

        ref_arr = DB.ReferenceArray()
        for axis in self.axles:
            ref_arr.Append(DB.Reference(axis))
        logging.debug('ReferenceArray for {} grid was created'.format(len(self.axles)))
        return ref_arr

    @classmethod
    def get_by_user(cls):
        """
        Create instanse by axles.

        Axles pre-selected users or invite user to select it

        :return: Instanse of current class
        :rtype: AxlesDim
        """

        axles = get_selected_by_cat(DB.BuiltInCategory.OST_Grids, as_list=True)
        logging.info('User pre-selected {} axles'.format(len(axles)))

        if len(axles) < 2:
            elem = axles[0] if len(axles) == 1 else None
            axles = user_selection_by_cat_and_elem(DB.Grid, elem)

        return AxlesDim(axles)

    def update_crop_and_bubble(self, crop_line, crop_modify=True, bubble_modify=True):
        """
        Update axles len and bubbles visible on view by crop line

        :param crop_line: DB.Line
        :param crop_modify: is crop axis line on view
        :type crop_modify: bool
        :param bubble_modify: is bubbles update on view
        :type bubble_modify: bool
        """

        for axis in self.axles:
            AxisCrop(axis).modify_axis(crop_line, crop_modify, bubble_modify)

        logging.info(
            '{} axles {}was cropped and {}updated bubbles'.format(
                len(self.axles),
                '' if crop_modify else 'not ',
                '' if bubble_modify else 'not '))

    def get_corners(self):
        """
        Get instance of current class with corners axis



        :return: Instance with corner axis
        :rtype: AxlesDim
        """

        corners = self._get_corners()
        if len(corners) < 2:
            raise ScriptError('Cant found 2 corner axles')

        logging.debug('Get {} corner axles'.format(len(corners)))
        return AxlesDim(corners)

    def _get_corners(self):
        """
        Find corners axis

        Находит все оси, перемножение направления которых с остальными имеет одинаковый знак

        :return:
        :rtype: list[DB.Grid]
        """

        def side(cur_axis, other_axis):
            """
            Calculate side other at current axis.

            If '-' left, '+' right

            :param cur_axis: DB.Grid
            :param other_axis: DB.Grid
            :return: left or right
            :rtype: bool
            """

            dir_to_other = other_axis.Curve.Origin - cur_axis.Curve.Origin
            product = cur_axis.Curve.Direction.CrossProduct(dir_to_other)
            return product.Z > 0

        corners = []
        for axis in self.axles:
            z_vectors = [side(axis, other) for other in self.axles if axis is not other]

            if all(z_vectors) or not any(z_vectors):
                logging.debug('Get corner axis "{}"'.format(axis.Name))
                corners.append(axis)

        return corners

    def __len__(self):
        return len(self.axles)


class AxisCrop:
    """
    Class for crop axis and change visible bubbles by crop line
    """

    def __init__(self, axis):
        self.axis = axis
        self.curve = self.axis.GetCurvesInView(DB.DatumExtentType.ViewSpecific, doc.ActiveView)[0]

    def modify_axis(self, crop_line, crop_modify=True, bubble_modify=True):
        """
        Main function to modify axis: crop and change bubbles visible

        :param crop_line: DB.Line
        :param crop_modify: Is modify len axis
        :type crop_modify: bool
        :param bubble_modify: Is modify bubbles visible
        :type bubble_modify: bool
        """

        new_curve, is_start = self.crop_curve_by_line(crop_line)
        if crop_modify:
            self.axis.SetCurveInView(DB.DatumExtentType.ViewSpecific, doc.ActiveView, new_curve)
            logging.debug('Axis {} curve: crop in view'.format(self.axis.Name))

        if bubble_modify:
            self._modify_bubble(is_start)

    def crop_curve_by_line(self, crop_line):
        """
        Crop curve in depend on ActiveView.ViewType

        :param crop_line: DB.Line
        :return: DB.Line and is_start parameter
        :rtype: tuple[DB.Line, bool]
        """

        if doc.ActiveView.ViewType in SECTION_TYPE:
            logging.debug('Line crop in section')
            return self._crop_curve_by_line_on_section(crop_line)
        else:
            logging.debug('Line crop in plane')
            return self._crop_curve_by_line_on_plane(crop_line)

    def _crop_curve_by_line_on_plane(self, crop_line):
        """
        Crop len current axis on plane and return it

        :param crop_line: DB.Line
        :return: DB.Line and is_start parameter
        :rtype: tuple[DB.Line, bool]
        """

        flatten_curve = self._make_flatten_and_extend(self.curve)
        flatten_crop_line = self._make_flatten_and_extend(crop_line)

        intersect = clr.StrongBox[DB.IntersectionResultArray]()
        is_intersect = flatten_curve.Intersect(flatten_crop_line, intersect)

        if is_intersect == DB.SetComparisonResult.Overlap:
            point = intersect.Value[0].XYZPoint
            h_point = point + DB.XYZ.BasisZ * self.curve.Origin.Z
            height_curve, is_start = self._create_line_by_closest_point(h_point)

            return height_curve, is_start

        raise ScriptError('Line not intersect')

    def _crop_curve_by_line_on_section(self, crop_line):
        """
        Crop len current axis on section and return it

        :param crop_line: DB.Line
        :return: DB.Line and is_start parameter
        :rtype: tuple[DB.Line, bool]
        """

        origin = self.curve.Origin
        height = crop_line.Origin
        h_point = DB.XYZ(origin.X, origin.Y, height.Z)

        height_curve, is_start = self._create_line_by_closest_point(h_point)
        return height_curve, is_start

    def _create_line_by_closest_point(self, point):
        """
        Create new line by point on line and delete part with min len

        Identity is_start parameter

        :param point: DB.XYZ
        :return: DB.Line and is_start parameter
        :rtype: tuple[DB.Line, bool]
        """

        start = self.curve.GetEndPoint(0)
        end = self.curve.GetEndPoint(1)

        if start.DistanceTo(point) > end.DistanceTo(point):
            is_start = False
            line = DB.Line.CreateBound(start, point)
        else:
            is_start = True
            line = DB.Line.CreateBound(point, end)

        logging.debug('Cropped line created, is_start == {}'.format(is_start))
        return line, is_start

    @staticmethod
    def _up_line_to_height(line, height):
        """
        Set start and end point to certain height(Z)

        :param line: DB.Line
        :param height: New height (Z) of line
        :type height: int or float
        :return: DB.Line
        """

        start_point = line.GetEndPoint(0)
        new_start = DB.XYZ(start_point.X, start_point.Y, height)

        end_point = line.GetEndPoint(1)
        new_end = DB.XYZ(end_point.X, end_point.Y, height)

        height_line = DB.Line.CreateBound(new_start, new_end)

        logging.debug('Line moved to height == {}'.format(height))
        return height_line

    def _make_flatten_and_extend(self, curve):
        """
        Extend line for BORDER value, then set it to 0 height

        :param curve: DB.Line
        :return: DB.Line
        """

        BORDER = 10000

        temp_curve = curve.Clone()
        if temp_curve.IsBound:
            temp_curve.MakeUnbound()
        temp_curve.MakeBound(-BORDER, BORDER)

        flatten_line = self._up_line_to_height(temp_curve, 0)

        logging.debug('Flatten line create')
        return flatten_line

    def _modify_bubble(self, is_start):
        """
        Modify bubbles visible on start and end

        :param is_start: Which side we crop
        :type is_start: bool
        """

        if is_start:
            self.axis.ShowBubbleInView(DB.DatumEnds.End0, doc.ActiveView)
            self.axis.HideBubbleInView(DB.DatumEnds.End1, doc.ActiveView)
        else:
            self.axis.ShowBubbleInView(DB.DatumEnds.End1, doc.ActiveView)
            self.axis.HideBubbleInView(DB.DatumEnds.End0, doc.ActiveView)

        temp = ('show', 'hide') if is_start else ('hide', 'show')
        logging.debug('Axis {} bubble: start - {}, end - {}'.format(self.axis.Name, *temp))


@transaction
def main():
    """
    Crete dimension, corner dimension, crop axles and update bubbles

    Get input from dynamo:

    - CREATE_DIM: type(bool), Create or not main dimension
    - CREATE_DIM_ALL: type(bool), Create or not corner axles dimension
    - CROP_AXLES: type(bool), Crop or not axles by outline
    - EDIT_BUBBLE: type(bool), Update or not bubbles on end and start of axis

    Get pre-selected axles or invite user to select it.
    Then invite user to select origin and side point to outline
    """

    CREATE_DIM = IN[0]
    CREATE_DIM_ALL = IN[1]
    CROP_AXLES = IN[2]
    EDIT_BUBBLE = IN[3]

    axles = AxlesDim.get_by_user()
    outline = OutLineDim.create_by_two_point_and_normal(axles.direction)

    if CREATE_DIM:
        dim_line = outline.get_outline()
        create_dim_by_reference_and_outline(axles.as_ref_arr, dim_line)

    if CREATE_DIM_ALL and len(axles) > 2:
        corner_axles = axles.get_corners()
        corner_line = outline.get_outline()
        create_dim_by_reference_and_outline(corner_axles.as_ref_arr, corner_line)

    if CROP_AXLES or EDIT_BUBBLE:
        crop_line = outline.get_outline()
        axles.update_crop_and_bubble(crop_line, crop_modify=CROP_AXLES, bubble_modify=EDIT_BUBBLE)


def create_dim_by_reference_and_outline(refs, outline):
    """
    Create dimension on active view by references and outline

    :param refs: DB.ReferenceArray
    :param outline: DB.Line
    """

    doc.Create.NewDimension(doc.ActiveView, outline, refs)
    logging.info('Dim created for {} axles'.format(refs.Size))


def user_selection_by_cat_and_elem(cat, elem):
    """
    Invite user to select elems by certain category, and look like element

    :param cat: DB
    :param elem: DB.Element
    :return: List of elements
    :rtype: list[DB.Element]
    """

    elem_filter = MySelectionFilter(cat, elem)
    elems = uidoc.Selection.PickElementsByRectangle(elem_filter, 'select elements {}'.format(cat))

    logging.info('User select {}'.format(len(elems)))
    if len(elems) < 2:
        raise ScriptError('Please select 2 or more axles')
    return elems


def get_user_point():
    """
    Invite user to select point in active view

    :return: DB.XYZ
    """

    if doc.ActiveView.ViewType in SECTION_TYPE:
        update_work_plane_on_view(doc.ActiveView)

    point = uidoc.Selection.PickPoint('Select point')
    return point


def update_work_plane_on_view(view):
    """
    Create work plane on view by view origin and view direction

    :param view: DB.View
    """

    if view.SketchPlane is not None:
        logging.debug('WorkPlane already exist: #{}'.format(view.Id))

    plane = DB.Plane.CreateByNormalAndOrigin(view.ViewDirection, view.Origin)
    sketch_plane = DB.SketchPlane.Create(doc, plane)
    view.SketchPlane = sketch_plane
    view.HideActiveWorkPlane()
    logging.debug('WorkPlane was updated on view: #{}'.format(view.Id))


if __name__ == '__main__':
    logging.basicConfig(
        filename=None, level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s <example>: %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    try:
        main()
    except ScriptError as e:
        logging.error(e)
    except Exception as err:
        logging.exception('Critical error')
