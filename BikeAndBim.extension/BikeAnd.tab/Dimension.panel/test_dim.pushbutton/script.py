# coding=utf-8
# Функция для тестирования
from dim_column import create_dim_for_column, is_need_shift

import unittest  # стандартный модуль библиотеки Python
# модули расширения PyRevit
from pyrevit.unittests.runner import (OutputWriter, PyRevitTestRunner,
                                      RESULT_TEST_SUITE_START)
from rpw import doc, logger, DB, db, ScriptError

# Собственные функции для создания объектов. В данной работе не приводятся
from creator import (create_axis, create_column,
                     get_view_project_browser, create_wall)


def run_suite_tests(test_suite, name):
    test_runner = PyRevitTestRunner(failfast=False)
    OutputWriter().write(RESULT_TEST_SUITE_START.format(suite=name))
    return test_runner.run(test_suite)


class TestDimColumn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.column = create_column(location=(0, 0, 0), height=3000)
        cls.axis = create_axis(origin=(0, 0, 0), direction=(0, 1, 0))
        cls.view = doc.ActiveView

    @classmethod
    def tearDownClass(cls):
        doc.Delete(cls.column.Id)
        doc.Delete(cls.axis.Id)

    def setUp(self):
        self.transaction = DB.Transaction(doc, 'Test')
        self.transaction.Start()

    def tearDown(self):
        self.transaction.RollBack()

    def test_01_create_dim(self):
        dim = create_dim_for_column(self.column, view=self.view)
        self.assertIsInstance(dim, DB.Dimension, msg='Размер не создан')

    def test_02_dim_on_view(self):
        dim = create_dim_for_column(self.column, view=self.view)
        self.assertEqual(dim.View.Id, self.view.Id, 'Ошибка с видом')

    def test_03_count_segments(self):
        dim = create_dim_for_column(self.column, view=self.view)
        self.assertEqual(dim.Segments.Size, 2, 'Ошибка с сегментами')

    def test_04_correct_column(self):
        dim = create_dim_for_column(self.column, view=self.view)
        depended_ids = [ref.ElementId for ref in dim.References]
        self.assertIn(self.column.Id, depended_ids, 'Ошибка с колонной')

    def test_05_correct_axis(self):
        dim = create_dim_for_column(self.column, view=self.view)
        depended_ids = [ref.ElementId for ref in dim.References]
        self.assertIn(self.axis.Id, depended_ids, 'Ошибка с осью')

    def test_06_check_is_shift_segments(self):
        self.assertTrue(False)
        dim = create_dim_for_column(self.column, view=self.view)

        for segment in dim.Segments:
            value = segment.ValueString
            dim_type = dim.DimensionType
            scale = self.view.Scale

            if is_need_shift(value, dim_type, scale):
                shift = segment.Origin.DistanceTo(segment.TextPosition)
                self.assertGreater(shift, 0.5, 'Сегмент не смещен')

    def test_07_error_with_not_column(self):
        wall = create_wall(origin=(0, 0, 0), direction=(1, 0, 0), level=0)
        with self.assertRaises(ScriptError):
            create_dim_for_column(wall, view=self.view)

    def test_08_error_non_valid_view(self):
        non_valid_view = get_view_project_browser()
        with self.assertRaises(ScriptError):
            create_dim_for_column(self.column, view=non_valid_view)


def main():
    # Общая транзакция для создания элементов
    with db.TransactionGroup(name='Test Column'):
        logger.title('Start testing')
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDimColumn)
        run_suite_tests(suite, name=TestDimColumn.__name__)


if __name__ == '__main__':
    main()
