# coding=utf-8
from rpw import db, DB, UI, uidoc, doc, logger


def task_dialog(msg):
    """
    For create task dialog with error and message

    :param msg: Message for window
    :type msg: str
    """

    window = UI.TaskDialog('Edit crop')
    window.TitleAutoPrefix = False

    window.MainIcon = UI.TaskDialogIcon.TaskDialogIconError
    window.MainInstruction = 'Error'
    window.MainContent = msg

    window.CommonButtons = UI.TaskDialogCommonButtons.Ok
    window.Show()


def box_selection():
    """
    Get two points by user rectangle selection

    :returns (DB.XYZ, DB.XYZ)
    :rtype tuple
    """

    style = UI.Selection.PickBoxStyle.Enclosing
    data = uidoc.Selection.PickBox(style, 'select two point')
    return data.Min, data.Max


@db.Transaction.ensure('Edit crop view')
def set_view_crop_by_point(view, down_left, up_right):
    """
    Set view crop of view by min and max point

    :param view: DB.View
    :param down_left: DB.XYZ
    :param up_right: DB.XYZ
    """

    box = view.CropBox

    box.Min = down_left + box.Min.Z * DB.XYZ.BasisZ
    box.Max = up_right + box.Max.Z * DB.XYZ.BasisZ

    doc.ActiveView.CropBox = box


def calc_x_y_plan(view, point):
    """
    Calculate point coordinate in plane of plane view

    - Calculate offset of view origin
    - Rotate point to angle between view.UpDirection and DB.XYZ.BasisY

    :param view: DB.ViewPlan
    :param point: DB.XYZ
    :return: DB.XYZ in plane view
    """

    normal_val = point - view.Origin - (point - view.Origin).Z * DB.XYZ.BasisZ

    angle = calc_angle(view.UpDirection, DB.XYZ.BasisY)
    rot_point = rotate_by_point_and_angle(normal_val, DB.XYZ.Zero, angle)

    return rot_point


def calc_angle(main_vector, second_vector):
    """
    Calculate angle between two vectors

    :param main_vector: DB.XYZ
    :param second_vector: DB.XYZ
    :return: Angle with sign
    :rtype: float
    """
    angle = main_vector.AngleTo(second_vector)
    sign = 1 if main_vector.CrossProduct(second_vector).Z >= 0 else -1
    return sign * angle


def rotate_by_point_and_angle(vector, origin, angle):
    """
    Rotate vector at origin to angle

    :param vector: DB.XYZ
    :param origin: DB.XYZ of origin
    :param angle: Angle to rotate
    :type angle: float
    :return: DB.XYZ
    """

    transform = DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, angle, origin)
    rot_vector = transform.OfPoint(vector)

    return rot_vector


def calc_x_y_section(view, point):
    """
    Calculate point coordinate in plane of section view

    - Calculate offset of view origin
    - Get shift in plane of view
    - Transform Z value to Y

    :param view: DB.ViewSection
    :param point: DB.XYZ
    :return: DB.XYZ in plane view
    """

    height = (point - view.Origin).Z
    normal_val = point - view.Origin - height * DB.XYZ.BasisZ

    length = normal_val.GetLength()
    sign = 1 if view.ViewDirection.CrossProduct(normal_val).Z >= 0 else -1

    new_point = DB.XYZ(sign * length, height, 0)

    return new_point


def calc_up_down(p_first, p_second):
    """
    Convert point for up_right and down_left

    :param p_first: DB.XYZ
    :param p_second: DB.XYZ
    :return: (DB.XYZ, DB.XYZ)
    :rtype: tuple
    """

    p_left = DB.XYZ(min(p_first.X, p_second.X),
                    min(p_first.Y, p_second.Y),
                    0)

    p_right = DB.XYZ(max(p_first.X, p_second.X),
                     max(p_first.Y, p_second.Y),
                     0)

    return p_left, p_right


def calc_point_by_handler(view, first, second, handler):
    """
    Calculate points for box by handler

    - Calculate in plane
    - Modify to up_right and down_left

    :param view: DB.View
    :param first: DB.XYZ
    :param second: DB.XYZ
    :param handler: Func for transform point for view
    :type handler: lambda view, point: pass
    :return: (DB.XYZ, DB.XYZ)
    :rtype: tuple
    """

    p_first, p_second = handler(view, first), handler(view, second)

    p_min, p_max = calc_up_down(p_first, p_second)

    return p_min, p_max


def edit_crop(view):
    """
    Edit crop view

    :param view:
    :type view:
    :return:
    :rtype:
    """

    if view.ViewType in VALID_VIEW_TYPE:
        handler = VALID_VIEW_TYPE[view.ViewType]
    else:
        raise NotImplementedError('View type "{}" not designed'.format(doc.ActiveView.ViewType))

    first, second = box_selection()
    p_min, p_max = calc_point_by_handler(view, first, second, handler)
    set_view_crop_by_point(view, p_min, p_max)


VALID_VIEW_TYPE = {
    DB.ViewType.Section: calc_x_y_section,
    DB.ViewType.Elevation: calc_x_y_section,
    DB.ViewType.EngineeringPlan: calc_x_y_plan,
    DB.ViewType.FloorPlan: calc_x_y_plan,
}


def main():
    view = doc.ActiveView
    edit_crop(view)


if __name__ == '__main__':
    logger.setLevel(50)

    try:
        main()
    except Exception as err:
        task_dialog(msg=str(err.args[0]) + '\nPlease, write Nikita')
