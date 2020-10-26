# coding=utf-8
from rpw import revit, db, ui, doc, logger, DB
from rpw.exceptions import RpwException
from rpw.utils.dotnet import List

# Get config
import ConfigParser as configparser
import os

this_folder = os.path.dirname(os.path.abspath(__file__))
init_file = os.path.join(this_folder, 'config.ini')
config = configparser.ConfigParser()
config.read(init_file)

SHEET_TITLE_FAMILY_NAME = config.get("Sheet", "title_family_name").decode('utf-8')
SECOND_SHEET_TITLE_FAMILY_NAME = config.get("Sheet", "second_title_family_name").decode('utf-8')
SHEET_NUMBER_ON_STAMP_NAME = config.get("Sheet", "number_on_stamp_name").decode('utf-8')

KEYPLAN_FAMILY_NAME = config.get("Keyplan", "family_name").decode('utf-8')


def main():
    sheets = get_sheet()
    with db.TransactionGroup('Copy Sheet'):
        for sheet in sheets:
            new_sheet = copy_sheet(sheet)
    return new_sheet


@db.Transaction.ensure('Ololo2222')
def copy_sheet(sheet):
    # logger.info('Start')
    # Get next number for sheet
    next_number = get_next_number(sheet)

    # Get TitleBlock
    title_block = get_elem_by_cat_and_family_name_on_view(category=DB.BuiltInCategory.OST_TitleBlocks,
                                                          block_name=SHEET_TITLE_FAMILY_NAME,
                                                          view=sheet)

    # Create new sheet and set number
    new_sheet = create_sheet(title_block)
    # logger.info('Create sheet')

    new_title_block = get_elem_by_cat_and_family_name_on_view(category=DB.BuiltInCategory.OST_TitleBlocks,
                                                              block_name=SHEET_TITLE_FAMILY_NAME,
                                                              view=new_sheet)

    new_sheet.parameters.builtins[DB.BuiltInParameter.SHEET_NUMBER] = next_number
    new_sheet.parameters[SHEET_NUMBER_ON_STAMP_NAME] = next_number.rpartition('-')[-1]
    # logger.info('Set number parameter')

    # TODO add Подпись2 as current user in pyRevit and Комаристов
    # Copy parameters by TitleBlock and Sheet
    fill_param_on_elem_from_old_elem_by_name(new=new_title_block,
                                             old=title_block,
                                             names=('Подпись3', 'Подпись4', 'Подпись5'))
    fill_param_on_elem_from_old_elem_by_name(new=new_sheet,
                                             old=sheet,
                                             names=('Наим. объекта', 'Марка', 'Доп. шифр'))
    # logger.info('Fill signs')

    # Create legend
    # FIXME 20201016 RevitAPI cant move title of viewport, one solution in revit 2020. just copy legend
    legend = get_legend_on_view(sheet)
    new_legend = DB.Viewport.Create(doc, new_sheet.Id, legend.ViewId, legend.GetBoxCenter())
    new_legend.ChangeTypeId(legend.GetTypeId())
    # logger.info('Create legend')

    # Copy annotation
    stamp = get_elem_by_cat_and_family_name_on_view(category=DB.BuiltInCategory.OST_TitleBlocks,
                                                    block_name=SECOND_SHEET_TITLE_FAMILY_NAME,
                                                    view=sheet)
    keyplan = get_elem_by_cat_and_family_name_on_view(category=DB.BuiltInCategory.OST_GenericAnnotation,
                                                      block_name=KEYPLAN_FAMILY_NAME,
                                                      view=sheet)

    text_notes = db.Collector(view=sheet, of_category='TextNotes').get_elements()

    copy_elements = [stamp] + [keyplan] + text_notes
    copy_element_ids = List[DB.ElementId]([elem.Id for elem in copy_elements])
    # logger.info('Get elements:{}'.format(len(copy_elements)))

    DB.ElementTransformUtils.CopyElements(sheet.unwrap(),
                                          copy_element_ids,
                                          new_sheet.unwrap(),
                                          None, None)


def get_sheet():
    """
    Get selected sheet or active view if sheet

    :return: Sheet
    :rtype: list[db.ViewSheet]
    """

    selection = ui.Selection()
    if selection:
        sheets = db.Collector(elements=selection, of_class=DB.ViewSheet)
        return sheets.get_elements()
    else:
        sheet = revit.active_view
        if sheet.ViewType != DB.ViewType.DrawingSheet:
            raise RpwException("ActiveView is not sheet")  # FIXME
        return [sheet]


def get_elem_by_cat_and_family_name_on_view(category, block_name, view):
    """
    Get elem by category and family name on view

    :param category: DB.BuiltInCategory
    :type category: DB.BuiltInCategory
    :param block_name: Family name
    :type block_name: str
    :param view: Sheet
    :type view: DB.ViewSheet
    :return: instanse of TitleBlock
    :rtype: DB.FamilyInstance
    """

    blocks = db.Collector(view=view, of_category=category, where=lambda block: block.Symbol.Family.Name == block_name)
    if blocks:
        return blocks.get_first()
    raise RpwException('{} on sheet not found'.format(category))


def get_legend_on_view(view):
    """
    Get legend view on view. Need for revit2020, which can copy legend

    :param view: View
    :type view: DB.View
    :return: View of Legend
    :rtype: DB.View
    """

    view_ports = db.Collector(view=view, of_category=DB.BuiltInCategory.OST_Viewports)
    for view_port in view_ports:
        view = doc.GetElement(view_port.ViewId)
        if view.ViewType == DB.ViewType.Legend:
            return view_port

    raise RpwException('Legend on sheet not found')


def create_sheet(title_block):
    """
    Create new sheet on current document by TitleBlock

    :param title_block: instanse of TitleBlock
    :type title_block: db.FamilyInstance
    :return: New Sheet
    :rtype: db.ViewSheet
    """

    return db.Element(DB.ViewSheet.Create(doc, title_block.Symbol.Id))


def fill_param_on_elem_from_old_elem_by_name(new, old, names):
    """
    Скопировать значения параметра из одного элемента в другой по имени

    :param new: Element which will fill
    :type new: db.Element
    :param old: Element for parameters
    :type old: db.Element
    :param names: Name parameters
    :type names: tuple[str]
    """

    for name in names:
        new.parameters[name] = old.parameters[name].value


def get_next_number(sheet):
    """
    Получить следующий номер листа

    :param sheet: Sheet
    :type sheet: DB.SheetView
    :return: <Марка>-<Номер листа>
    :rtype: str
    """

    num_value = sheet.get_Parameter(DB.BuiltInParameter.SHEET_NUMBER).AsString()
    mark, _, number = num_value.rpartition('-')
    max_number = int(number)

    collector = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).WhereElementIsNotElementType().ToElements()
    for temp_sheet in collector:
        temp_value = temp_sheet.get_Parameter(DB.BuiltInParameter.SHEET_NUMBER).AsString()
        temp_mark, _, temp_number = temp_value.rpartition('-')
        if temp_mark == mark:
            if temp_number.isdigit() and int(temp_number) > max_number:
                max_number = int(temp_number)

    return mark + '-' + str(max_number + 1).rjust(len(number), '0')


if __name__ == '__main__':
    main()
