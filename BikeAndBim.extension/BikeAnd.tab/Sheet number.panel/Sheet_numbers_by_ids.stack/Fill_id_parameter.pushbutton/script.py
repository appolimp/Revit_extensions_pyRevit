# coding=utf-8
import os.path
import sys

stack_path = os.path.split(sys.path[0])[0]
sys.path.append(stack_path)

from reload_number import fill_id_in_text_note, db, logger


@db.Transaction.ensure('Fill id sheet on text note')
def main():
    logger.disable()
    fill_id_in_text_note()


if __name__ == '__main__':
    main()
