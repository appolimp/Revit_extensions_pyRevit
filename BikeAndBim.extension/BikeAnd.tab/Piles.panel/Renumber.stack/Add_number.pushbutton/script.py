# coding=utf-8
from rpw import db, logger, DB, ui
from rpw.exceptions import RpwException
from pyrevit.forms import ask_for_string
import functools


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


class UserCancelOperation(Exception):
    pass


# ################# Основная логика #########################################
def get_mark_selected_or_none():
    if ui.Selection():
        element = ui.Selection()[0]
        start_number = int(element.parameters.builtins['DOOR_NUMBER'].value)

        logger.debug('Get start number [{}]'.format(start_number))
        return start_number


def add_number(element, adder_number):
    parameter = element.parameters.builtins['DOOR_NUMBER']

    new_number = int(parameter.value or 0) + adder_number
    parameter.value = new_number

    logger.debug('#{} element. Set number [{}]'.format(element.Id, new_number))


def get_adder_number_from_user(count):
    prompt = 'Выбрано [{}]. Введите число, которое нужно добавить к марке:'.format(count)
    user_number = ask_for_string(default='0', prompt=prompt, title='Add number to mark')
    if user_number is None:
        raise UserCancelOperation
    adder_number = int(user_number)

    logger.debug('Get adder number from user [{}]'.format(adder_number))
    return adder_number


@transaction_with_suppress(msg='Add number of piles', accessor=DuplicateMark())
def main():
    selection = ui.Selection()
    adder_number = get_adder_number_from_user(count=len(selection))

    for element in selection:
        add_number(element, adder_number)

    logger.debug('End Script')


if __name__ == '__main__':
    # logger.setLevel(10)

    try:
        main()
    except UserCancelOperation:
        logger.debug('User cancel operation')

    except RpwException as e:
        logger.error(e)

    except Exception as err:
        logger.error('Critical error')
        raise
