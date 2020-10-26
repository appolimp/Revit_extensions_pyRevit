# coding=utf-8
import os.path
import sys

stack_path = os.path.split(sys.path[0])[0]
sys.path.append(stack_path)

from reload_number import reload_number, db, logger


@db.Transaction.ensure('Fill id sheet on text note')
def main():
    logger.disable()
    reload_number()


if __name__ == '__main__':
    main()
