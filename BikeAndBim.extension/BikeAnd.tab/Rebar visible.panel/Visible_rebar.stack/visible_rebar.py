# coding=utf-8
import os.path
import sys

stack_path = os.path.split(sys.path[0])[0]
panel_path = os.path.split(stack_path)[0]
tab_path = os.path.split(panel_path)[0]
ext_path = os.path.split(tab_path)[0]
base_path = os.path.join(ext_path, 'base')
sys.path.append(base_path)


from wrapper import DB, UI, doc, uidoc, transaction, ScriptError, SheetsNotSelected, ElemNotFound
from selection import get_selected_by_cat

import logging


@transaction
def main():
    # rebar = UnwrapElement(IN[4])
    # rebar.SetUnobscuredInView(doc.ActiveView, False)
    unobscured_all_rebars_on_view(doc.ActiveView, True, solid=True)
    # unobscured_all_selected_rebars_on_view(doc.ActiveView, True)
    return


'--------------------First----------------------------'


def unobscured_all_rebars_on_view(view, visible=True, solid=None):
    """
    Переопределить видимость всей арматуры на виде

    :param view: Вид, на котором нужно переопределить видимость
    :type view: DB.View
    :param visible: Видимость
    :type visible: bool
    :param solid: Показать как тело
    :type solid: bool
    """

    count = 0
    rebars = get_all_rebar_on_view(view.Id)
    for rebar in rebars:
        unobscured_rebar_on_view(rebar, view, visible=visible)

        if view.ViewType == DB.ViewType.ThreeD and solid is not None:
            solid_rebar_on_view(rebar, view, solid=solid)

        count += 1

    logging.info('У {} арматурных элементов теперь видимость <{}> на виде "{}" #{}'.format(
        count, visible, view.Name, view.Id))


def get_all_rebar_on_view(view_id):
    """
    Получить всю арматуру на виде. Генератор

    :param view_id: id Вида
    :type view_id: DB.ElementId
    :return: Экземпляры арматуры
    :rtype: DB.Structure.Rebar
    """

    collector = DB.FilteredElementCollector(doc, view_id).OfClass(DB.Structure.Rebar)
    collector.WhereElementIsNotElementType().ToElements()
    for rebar in collector:
        yield rebar


def unobscured_rebar_on_view(rebar, view, visible=True):
    """
    Изменяет параметра <Показать неперекрытым> в свойстве <Состояние видимости вида> для арматуры

    Если видимость арматуры совпадает с visible пропускает

    :param rebar: Экземпляр арматуры
    :type rebar: DB.Structure.Rebar
    :param view: Вид, на котором нужно переопределить
    :type view: DB.View
    :param visible: Видимость
    :type visible: bool
    """

    if rebar.IsUnobscuredInView(view) is not visible:
        rebar.SetUnobscuredInView(view, visible)
        logging.debug('Арматура #{} изменила видимость на <{}> на виде "{}" #{}'.format(
            rebar.Id, visible, view.Name, view.Id))
    else:
        logging.debug('Арматура #{} уже имеет видимость <{}> на виде "{}" #{}'.format(
            rebar.Id, visible, view.Name, view.Id))


def solid_rebar_on_view(rebar, view, solid=True):
    """
    Изменяет параметра <Показать как тело> в свойстве <Состояние видимости вида> для арматуры на 3D виде

    Если вид не 3D - пропускает

    Если видимость арматуры совпадает с solid пропускает

    :param rebar: Экземпляр арматуры
    :type rebar: DB.Structure.Rebar
    :param view: 3D Вид, на котором нужно переопределить
    :type view: DB.View3D
    :param solid: Показать как тело
    :type solid: bool
    """

    if rebar.IsSolidInView(view) is not solid:
        rebar.SetSolidInView(view, solid)
        logging.debug('Арматура #{} изменила видимость тела на <{}> на виде "{}" #{}'.format(
            rebar.Id, solid, view.Name, view.Id))
    else:
        logging.debug('Арматура #{} уже имеет видимость тела <{}> на виде "{}" #{}'.format(
            rebar.Id, solid, view.Name, view.Id))


'--------------------Second----------------------------'


def unobscured_all_selected_rebars_on_view(view, visible=False, solid=None):
    """
    Переопределить видимость всей выбранной пользователем арматуры на виде

    :param view: Вид, на котором нужно переопределить видимость
    :type view: DB.View
    :param visible: Видимость
    :type visible: bool
    :param solid: Показать как тело
    :type solid: bool
    """

    count = 0
    rebars = get_selected_by_cat(DB.BuiltInCategory.OST_Rebar)
    for rebar in rebars:
        unobscured_rebar_on_view(rebar, view, visible=visible)

        if view.ViewType == DB.ViewType.ThreeD and solid is not None:
            solid_rebar_on_view(rebar, view, solid=solid)

        count += 1

    logging.info('У {} арматурных элементов теперь видимость <{}> на виде "{}" #{}'.format(
        count, visible, view.Name, view.Id))


if __name__ == '__main__':
    logging.basicConfig(
        filename=None, level=logging.DEBUG,
        format='[%(asctime)s] %(levelname).1s <example>: %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    try:
        OUT = main()
    except ScriptError as e:
        logging.error(e)
    except Exception as err:
        logging.exception('Critical error')
