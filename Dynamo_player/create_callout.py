# coding=utf-8
from my_class.base.wrapper import doc, DB, transaction_group
from my_class.base.exeption import ScriptError

from my_class.my_callout import MyCalloutCreator
from my_class.my_elem import MyElemFactory
from my_class.my_section import MyAlongSectionCreator, MyAcrossSectionCreator
from my_class.my_selection import get_preselected_elems_or_invite
from my_class.my_view import get_or_create_template_by_name_and_type, set_template

from my_class import my_sheet

import logging


@transaction_group(msg='Create callout')
def main():
    """
    Create Callout to selected elements

    Get pre-selected elements or invite user to select it

    Get input from dynamo:

    - OFFSET: type(float), Offset value to callout
    - ROTATED: type(bool), Rotate or not callout view
    """

    OFFSET = IN[0]
    ROTATED = IN[1]

    IS_CREATE_ALONG_1 = IN[2]
    IS_CREATE_ALONG_2 = IN[3]
    IS_CREATE_ACROSS_1 = IN[4]

    VIEW_TEMPLATE_NAME = IN[5]
    SECTION_TEMPLATE_NAME = IN[6]

    IS_CREATE_SHEET = IN[7]

    callout_view_template = get_or_create_template_by_name_and_type(
        template_name=VIEW_TEMPLATE_NAME,
        view_type=DB.ViewType.EngineeringPlan)

    section_view_template = get_or_create_template_by_name_and_type(
        template_name=SECTION_TEMPLATE_NAME,
        view_type=DB.ViewType.Section)

    elems = get_preselected_elems_or_invite()
    for elem in elems:
        my_elem = MyElemFactory.get_geom_to_element(elem)
        need_update = MyElemFactory.is_valid(elem.Category)

        callout = MyCalloutCreator(my_elem, need_update).create_callout_on_view(
            doc.ActiveView,
            template_view=callout_view_template,
            rotated=ROTATED, offset=OFFSET)

        sections = []
        if IS_CREATE_ALONG_1:
            along_one = MyAlongSectionCreator(my_elem).create_section(template_view=section_view_template)
            # along_one.Name = 'EXP_SECT_' + along_one.Name
            sections.append(along_one)

        if IS_CREATE_ALONG_2:
            along_two = MyAlongSectionCreator(my_elem).create_section(flip=True, template_view=section_view_template)
            # along_two.Name = 'EXP_SECT_' + along_two.Name
            sections.append(along_two)

        if IS_CREATE_ACROSS_1:
            across_one = MyAcrossSectionCreator(my_elem).create_section(template_view=section_view_template)
            # across_one.Name = 'EXP_SECT_' + across_one.Name
            sections.append(across_one)

        if IS_CREATE_SHEET:
            sheet = my_sheet.create_sheet_by_views(
                views=[callout.callout] + sections,
                name='EXP_Elem_'+my_elem.mark_for_sheet)


if __name__ == '__main__':
    logging.basicConfig(
        filename=None, level=logging.DEBUG,
        format='[%(asctime)s] %(levelname).1s: %(message)s',
        datefmt='%H:%M:%S')

    try:
        main()
    except ScriptError as e:
        logging.error(e)
    except Exception as err:
        logging.exception('Critical error')
