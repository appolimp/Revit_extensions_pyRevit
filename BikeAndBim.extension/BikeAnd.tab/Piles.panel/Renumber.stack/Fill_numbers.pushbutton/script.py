# coding=utf-8
from rpw import db, logger, DB, ui
from pyrevit.revit.selection import pick_element_by_category
from rpw.exceptions import RpwException
import functools
import itertools


# ################# Вспомогательные функции #################################
class DuplicateMark(DB.IFailuresPreprocessor):
    """

    https://stackoverflow.com/questions/23833674/can-you-suppress-the-duplicate-mark-prompt-in-revit-during-c-sharp-program
    """

    @staticmethod
    def PreprocessFailures(failures_accessor):
        failures = failures_accessor.GetFailureMessages()
        for fail in failures:
            if fail.GetFailureDefinitionId() == DB.BuiltInFailures.GeneralFailures.DuplicateValue:
                failures_accessor.DeleteWarning(fail)
                logger.debug('Suppress duplicate mark error')
        return DB.FailureProcessingResult.Continue


def transaction_with_suppress(func=None, msg='', accessor=None):
    """

    :type func: Callable
    :type msg: str
    :type accessor: DB.IFailuresPreprocessor

    :rtype: Any
    """

    if func is None:
        return functools.partial(transaction_with_suppress, msg=msg, accessor=accessor)

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        with db.Transaction(msg) as trans:
            failure_options = trans.GetFailureHandlingOptions()
            failure_options.SetFailuresPreprocessor(accessor)
            trans.SetFailureHandlingOptions(failure_options)

            res = func(*args, **kwargs)
        return res

    return wrapped


# ################# Основная логика #########################################
def get_mark_selected_or_none():
    if ui.Selection():
        element = ui.Selection()[0]
        start_number = int(element.parameters.builtins['DOOR_NUMBER'].value)

        logger.debug('Get start number [{}]'.format(start_number))
        return start_number


@transaction_with_suppress(msg='Number Element', accessor=DuplicateMark())
def renumber(element, number):
    element.parameters.builtins['DOOR_NUMBER'] = number
    logger.debug('#{} Element. Set number [{}]'.format(element.Id, number))


def main():
    start_number = (get_mark_selected_or_none() or 0) + 1

    with db.TransactionGroup('Fill number of piles', assimilate=True):
        for number in xrange(start_number, 10**5):
            element = pick_element_by_category(DB.BuiltInCategory.OST_StructuralColumns,
                                               message='Next number [{}]'.format(number))

            if element is None:
                logger.debug('User aborted pick operation')
                break
            else:
                renumber(db.Element(element), number)

    logger.debug('End Script')


if __name__ == '__main__':
    # logger.setLevel(10)

    try:
        main()

    except RpwException as e:
        logger.error(e)

    except Exception as err:
        logger.error('Critical error')
        raise
