# coding=utf-8
import os.path
import sys


panel_path = os.path.split(sys.path[0])[0]
tab_path = os.path.split(panel_path)[0]
ext_path = os.path.split(tab_path)[0]
base_path = os.path.join(ext_path, 'base')
sys.path.append(base_path)


from wrapper import DB, doc, uidoc, transaction, ScriptError
from Autodesk.Revit.UI.Selection import PickBoxStyle

import logging


@transaction(msg='Edit crop view')
def main():
    edit_view_crop()


def edit_view_crop():

    box = DB.BoundingBoxXYZ()
    user_select_rect = box_selection()
    box.Min, box.Max = convert_two_point(*user_select_rect)

    doc.ActiveView.CropBox = box
    return box


def box_selection():
    """
        Get two points by user rectangle selection

        :returns (DB.XYZ, DB.XYZ)
        """
    data = uidoc.Selection.PickBox(PickBoxStyle.Enclosing, 'select two point')
    return data.Min, data.Max


def transform_point_for_section(first, second, side, flip_direction):
    """
    Convert point for section
    Using origin shaft and view direction

    :param first: DB.XYZ
    :param second: DB.XYZ
    :param side: str
    :param flip_direction: bool

    :returns (DB.XYZ, DB.XYZ)
    """
    origin = doc.ActiveView.Origin

    point_x = [getattr(elem, side) for elem in (first, second)]
    point_z = [getattr(elem, 'Z') for elem in (first, second)]

    point_left = DB.XYZ(min(point_x) - getattr(origin, side), min(point_z) - origin.Z, 0)
    point_right = DB.XYZ(max(point_x) - getattr(origin, side), max(point_z) - origin.Z, 0)

    if flip_direction:  # Need for flip section
        left_x, right_x = point_left.X, point_right.X
        point_left = DB.XYZ(-right_x, point_left.Y, 0)
        point_right = DB.XYZ(-left_x, point_right.Y, 0)

    return point_left, point_right


def convert_two_point(first, second):
    """
        Convert point for BoundingBoxXYZ
        return left_down and right_up points

        :param first: DB.XYZ
        :param second: DB.XYZ

        :returns (DB.XYZ, DB.XYZ)
        """
    direction = doc.ActiveView.ViewDirection

    if round(direction.X - direction.Y, 5) == 0:  # View plane
        point_left = DB.XYZ(min(first.X, second.X), min(first.Y, second.Y), 0)
        point_right = DB.XYZ(max(first.X, second.X), max(first.Y, second.Y), 0)

    elif round(direction.Y - direction.Z, 5) == 0:  # Section in X
        point_left, point_right = transform_point_for_section(
            first, second, side='Y',
            flip_direction=int(direction.X) == -1)

    elif round(direction.X - direction.Z, 5) == 0:  # Section in Y
        point_left, point_right = transform_point_for_section(
            first, second, side='X',
            flip_direction=int(direction.Y) == 1)

    else:
        raise NotImplemented("3D and slope section doesn't work")  # FIXME
    return point_left, point_right


if __name__ == '__main__':
    logging.basicConfig(
        filename=None, level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s <example>: %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    try:
        OUT = main()
    except ScriptError as e:
        logging.error(e)
    except Exception as err:
        logging.exception('Critical error')
