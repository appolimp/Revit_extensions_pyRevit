# coding=utf-8
from dim_column import create_dim_for_column

import unittest
from pyrevit.unittests.runner import OutputWriter, PyRevitTestRunner, RESULT_TEST_SUITE_START
from rpw import revit, db, ui, doc, uidoc, logger, DB, UI


def run_suite_tests(test_suite):
    test_runner = PyRevitTestRunner()
    OutputWriter().write(RESULT_TEST_SUITE_START.format(suite=test_suite.__class__.__name__))
    return test_runner.run(test_suite)


class TestClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.column = doc.GetElement(DB.ElementId(553068))
        print cls.column
        cls.axis_horizontal = doc.GetElement(DB.ElementId(518439))
        cls.axis_vertical = doc.GetElement(DB.ElementId(519778))
        cls.view = doc.ActiveView

    def setUp(self):
        print 'start transaction'
        self.transaction = DB.Transaction(doc, self.__class__.__name__)
        self.transaction.Start()

    def tearDown(self):
        print 'end transaction'
        self.transaction.Commit()
        # self.transaction.RollBack()

    def test_count_dim(self):
        print 'start test'
        with self.transaction:
            print 'in transaction'
            create_dim_for_column(self.column)
            self.assertTrue(True)

    def test_number_two(self):
        self.assertTrue(True, "this is all wrong")


def main():
    logger.title('Start testing')
    suite = unittest.TestLoader().loadTestsFromTestCase(TestClass)
    run_suite_tests(suite)


if __name__ == '__main__':
    main()
