# coding=utf-8
from wrapper import doc, uidoc, DB


def for_each(f):
    selection = uidoc.Selection.GetElementIds()
    for e_id in selection:
        element = doc.GetElement(e_id)
        f(element)


def get_selected(as_list=False):
    if as_list:
        return list(_get_selected())
    return _get_selected()


def _get_selected():
    selection = uidoc.Selection.GetElementIds()
    for e_id in selection:
        element = doc.GetElement(e_id)
        yield element


def get_selected_by_cat(cat, as_list=False):
    """
    Получить элементы в пользовательском выборе определенной категории

    :param cat: BuiltInCategory
    :type cat: DB.BuiltInCategory
    :param as_list: Вернуть лист или генератор
    :type as_list: bool
    :return: Элементы опр. категории выбранные пользователем
    :rtype: DB.Element
    """

    if as_list:
        return list(_get_selected_by_cat(cat))
    return _get_selected_by_cat(cat)


def _get_selected_by_cat(cat):
    """
    Генератор. Получить элементы в пользовательском выборе определенной категории

    :param cat: BuiltInCategory
    :type cat: DB.BuiltInCategory
    :return: Элементы опр. категории выбранные пользователем
    :rtype: DB.Element
    """

    for elem in get_selected():
        if elem.Category.Id == DB.Category.GetCategory(doc, cat).Id:
            yield elem
