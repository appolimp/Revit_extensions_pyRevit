# coding=utf-8
import os.path
import sys
import logging

stack_path = os.path.split(sys.path[0])[0]
sys.path.append(stack_path)


from visible_rebar import unobscured_all_rebars_on_view, transaction, ScriptError, doc


@transaction(msg='Change visible all rebar on view')
def main():
    visible = solid = True
    if __shiftclick__:
        visible = solid = False

    unobscured_all_rebars_on_view(doc.ActiveView, visible, solid)


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
