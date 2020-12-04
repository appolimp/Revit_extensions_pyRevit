from base.wrapper import doc, DB
from abc import ABCMeta, abstractproperty
from . import my_view
from base.wrapper import Transaction
import logging


class MySectionCreatorBase:
    __metaclass__ = ABCMeta

    OFFSET_HEIGHT = 2
    OFFSET_WIDTH = 2
    OFFSET_DEPTH = 2
    OFFSET_CUT_LINE = 2

    ViewFamilyType = None

    def __init__(self, element):
        """

        :param element: Elem with geom prop
        :type element: MyElementGeom
        """
        self.element = element

        self.origin = element.origin
        self.height_up = element.height_up
        self.height_down = element.height_down

    @abstractproperty
    def width(self):
        return self.element.length

    @abstractproperty
    def thickness(self):
        return self.element.width

    @abstractproperty
    def direction(self):
        return self.element.orientation

    @Transaction.ensure('Create section')
    def create_section(self, template_view=None, section_family=None, flip=False):
        if section_family is None:
            section_family = self._get_section_view_family_type()

        line = (1 if not flip else -1) * self.direction

        box = self.create_bounding_box(line)
        section = DB.ViewSection.CreateSection(doc, section_family.Id, box)
        logging.info('Section was created: {}'.format(section.Name))

        if template_view:
            my_view.set_template(section, template_view)

        my_view.set_visible_section_scale(section, 200)

        return section

    def create_bounding_box(self, direction):
        t = DB.Transform.Identity
        t.Origin = self.origin

        t.BasisX = direction
        t.BasisY = DB.XYZ.BasisZ
        t.BasisZ = t.BasisX.CrossProduct(t.BasisY)

        box = DB.BoundingBoxXYZ()
        box.Transform = t

        box.Max, box.Min = self._calc_points_to_box()
        return box

    def _calc_points_to_box(self):
        down = DB.XYZ(
            -self.width / 2 - self.OFFSET_WIDTH,  # length left
            self.height_down - self.OFFSET_HEIGHT,  # height down
            -self.thickness / 2 - self.OFFSET_CUT_LINE)  # offset of cut line

        up = DB.XYZ(
            self.width / 2 + self.OFFSET_WIDTH,  # length right
            self.height_up + self.OFFSET_HEIGHT,  # height up
            self.thickness / 2 + self.OFFSET_DEPTH)  # offset of far clip

        return up, down

    @classmethod
    def _get_section_view_family_type(cls):
        if cls.ViewFamilyType is None:
            logging.debug('Calc view family')
            collector = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
            for elem in collector:
                if elem.ViewFamily == DB.ViewFamily.Section:
                    MySectionCreatorBase.ViewFamilyType = elem

        return MySectionCreatorBase.ViewFamilyType


class MyAcrossSectionCreator(MySectionCreatorBase):

    @property
    def width(self):
        return self.element.width

    @property
    def thickness(self):
        return 0

    @property
    def direction(self):
        return DB.XYZ.BasisZ.CrossProduct(self.element.orientation)


class MyAlongSectionCreator(MySectionCreatorBase):

    @property
    def width(self):
        return self.element.length

    @property
    def thickness(self):
        return self.element.width

    @property
    def direction(self):
        return self.element.orientation
