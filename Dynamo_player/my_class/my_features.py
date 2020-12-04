import logging

from math import pi
from .my_geom import MyPoints


def calc_angle_to_ver_or_hor_side(main_vector, second_vector):
    """
    Calc angle between main and second

    Then transform it to main vector or it perpendicular and make angle less than 90

    :param main_vector: DB.XYZ
    :param second_vector: DB.XYZ, for example UpDirection of view
    :return: Angle between main and second < 90
    :rtype: float
    """

    angle = main_vector.AngleTo(second_vector)
    logging.debug('Calc first rotation angle: {:.2f}'.format(angle * 180 / pi))

    if pi / 4 < angle <= pi / 2:
        angle -= pi / 2
    elif pi / 2 < angle <= 3 * pi / 4:
        angle += pi / 2 - pi
    elif 3 * pi / 4 < angle <= pi:
        angle -= pi

    logging.debug('Calc change rotation angle: {:.2f}'.format(angle * 180 / pi))
    sign_angle = MyPoints.calc_sign(main_vector, second_vector) * angle

    logging.debug('Calc sign rotation angle: {:.2f}'.format(sign_angle * 180 / pi))
    return sign_angle