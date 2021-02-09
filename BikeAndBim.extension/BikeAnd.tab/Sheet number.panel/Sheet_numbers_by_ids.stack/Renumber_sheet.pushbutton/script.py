# coding=utf-8
from rpw import db, DB, UI, uidoc, doc, logger
from System.Collections.Generic import List
from rpw.ui.forms import FlexForm, Label, TextBox, Separator, Button
import functools


class ElemNotFound(Exception):
    pass


@db.Transaction.ensure('Renumber sheet')
def main():
    """
    Заменить символы в выделеных листах по шаблону

  - Выделить листы
  - Запустить скрипт
  - Ввести шаблон для замены и на что заменить
  - Наслаждаться

    """

    sheet_ids = get_selected_sheet_id()
    temp, new = get_from_win_form()

    data = change_sheets_name(sheet_ids, temp, new)

    task_dialog(type_mes='info',
                msg='{} Sheet was ReNumbered from {} to {}'.format(len(data), repr(temp), repr(new)),
                data=data)


def get_from_win_form():
    """
    Получить от пользователя значение шаблона и на что заменить

    :return: две строки
    :rtype: tuple[str, str]
    """

    components = [Label('Введите шаблон:'),
                  TextBox('Template', Text="A"),
                  Label('Заменить на:'),
                  TextBox('New_text', Text="Q"),
                  Separator(),
                  Button('Find and Replace')]
    form = FlexForm('Title', components)
    form.show()

    if 'Template' in form.values and 'New_text' in form.values:
        template = form.values['Template']
        new_text = form.values['New_text']
        logger.info('Get from user template {} and new text {}'.format(repr(template), repr(new_text)))
        return template, new_text

    raise ElemNotFound('User canceled form')


def refresh_project_browser(func):
    """
    Обновление ProjectBrowser

    Так как при изменении номеров листов, он не обновляется

    https://forums.autodesk.com/t5/revit-api-forum/refresh-projectbrowser-after-renaming-sheetnumber/td-p/6664487
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        dpId = UI.DockablePanes.BuiltInDockablePanes.ProjectBrowser
        pB = UI.DockablePane(dpId)
        r = func(*args, **kwargs)
        pB.Show()
        return r

    return wrapped


@refresh_project_browser
def change_sheets_name(sheet_ids, template, new):
    """
    Change sheet number to replace by template

    :param sheet_ids:
    :param template:
    :param new:
    :return:
    """

    data = []
    for sheet_id in sheet_ids:
        sheet = doc.GetElement(sheet_id)
        sheet_number = sheet.SheetNumber

        if template in sheet_number:
            new_sheet_number = sheet.SheetNumber.replace(template, new)
            sheet.SheetNumber = new_sheet_number

            data.append('OK [#{} Sheet {}]'.format(sheet_id, repr(new_sheet_number)))
            logger.debug('OK [#{} Sheet {}]'.format(sheet_id, repr(new_sheet_number)))
        else:
            data.append('PASS [#{} Sheet {}]'.format(sheet_id, repr(sheet_number)))
            logger.debug('PASS [#{} Sheet {}]'.format(sheet_id, repr(sheet_number)))

    logger.info('{} Sheets was ReNumbered'.format(len(data)))
    return data


def get_selected_sheet_id():
    """
    Получить id Выбранных пользовтелем листов

    :return: Id выбранных листов
    :rtype: List[DB.ElementId]
    """

    pre_selected = uidoc.Selection.GetElementIds()
    selected_views_id = List[DB.ElementId](pre_selected)

    if selected_views_id:
        logger.info('User select {} views'.format(len(selected_views_id)))
        return selected_views_id

    raise ElemNotFound('Please, select any sheet')


def task_dialog(type_mes, msg, data=None):
    """
    For create task dialog with error and message

    :param type_mes: info or error
    :type type_mes: str
    :param msg: Message for window
    :type msg: str
    :param data: Text for expanded content
    :type data: []
    """

    window = UI.TaskDialog('Export CAD')
    window.TitleAutoPrefix = False

    if type_mes == 'info':
        window.MainIcon = UI.TaskDialogIcon.TaskDialogIconInformation
        window.MainInstruction = 'Info'
        window.MainContent = msg
    else:
        window.MainIcon = UI.TaskDialogIcon.TaskDialogIconError
        window.MainInstruction = 'Error'
        window.MainContent = msg

    if data:
        window.ExpandedContent = '\n'.join(data)

    window.CommonButtons = UI.TaskDialogCommonButtons.Ok

    window.Show()


if __name__ == '__main__':
    logger.setLevel(60)

    try:
        main()

    except ElemNotFound as err:
        task_dialog(type_mes='error', msg=err.args[0])

    except Exception as err:
        task_dialog(type_mes='error', msg='Please, write Nikita', data=err.args)
