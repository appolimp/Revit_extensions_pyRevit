# coding=utf-8
from dim_column import create_dim_for_column

import unittest
from pyrevit.unittests.runner import OutputWriter, PyRevitTestRunner, RESULT_TEST_SUITE_START
from rpw import revit, db, ui, doc, uidoc, logger, DB, UI


def run_suite_tests(test_suite, name):
    test_runner = PyRevitTestRunner(failfast=False)
    OutputWriter().write(RESULT_TEST_SUITE_START.format(suite=name))
    return test_runner.run(test_suite)


class TestDimColumn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.column = doc.GetElement(DB.ElementId(553068))
        cls.axis_horizontal = doc.GetElement(DB.ElementId(518439))
        cls.axis_vertical = doc.GetElement(DB.ElementId(519778))
        cls.view = doc.ActiveView

    def setUp(self):
        self.transaction = DB.Transaction(doc, self.__class__.__name__)
        self.transaction.Start()

    def tearDown(self):
        self.transaction.RollBack()

    def test_01_create_dim(self):
        dims = create_dim_for_column(self.column, view=self.view)
        self.assertTrue(dims, msg='Размеры не созданы')

    def test_02_count_dim(self):
        dims = create_dim_for_column(self.column, view=self.view)
        self.assertTrue(len(dims) == 2, msg='Количество созданных размеров не равно 2')

    def test_03_dims_on_view(self):
        dims = create_dim_for_column(self.column, view=self.view)
        self.assertTrue(all(dim.View.Id == self.view.Id for dim in dims), msg='Размеры созданы не на заданном виде')

    def test_04_count_segments(self):
        dims = create_dim_for_column(self.column, view=self.view)
        self.assertTrue(all(dim.Segments.Size == 2 for dim in dims), msg='Размеры состоят не из двух сегментов')

    def test_99_number_two(self):
        self.assertTrue(True, "this is all wrong")


def main():
    logger.title('Start testing')
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDimColumn)
    run_suite_tests(suite, name=TestDimColumn.__name__)


if __name__ == '__main__':
    main()
