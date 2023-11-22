"""
Tests for Classes of gdmp_benchmark
"""
import unittest
from gdmp_benchmark import Results, Timing, Notebook, Status

class TestResults(unittest.TestCase):
    #  Tests that a Results object can be created with all required attributes.
    def test_create_results_object(self):
        result = Results(result=Status.PASS, msg="Test successful", output=["test output"], notebookid="1234",
                         user_config="test config", messages=["test message"], logs="test logs",
                         time=Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00",
                                      finish="2022-01-01 00:00:10"), outputs={"test": "output"}, name="test name")
        self.assertEqual(result.result, Status.PASS)
        self.assertEqual(result.msg, "Test successful")
        self.assertEqual(result.output, ["test output"])
        self.assertEqual(result.notebookid, "1234")
        self.assertEqual(result.user_config, "test config")
        self.assertEqual(result.messages, ["test message"])
        self.assertEqual(result.logs, "test logs")
        self.assertEqual(result.time.result, Status.PASS)
        self.assertEqual(result.time.totaltime, 10)
        self.assertEqual(result.time.start, "2022-01-01 00:00:00")
        self.assertEqual(result.time.finish, "2022-01-01 00:00:10")
        self.assertEqual(result.outputs, {"test": "output"})
        self.assertEqual(result.name, "test name")

    #  Tests that the to_dict() method returns a dictionary with all attributes.
    def test_results_to_dict(self):
        result = Results(result=Status.PASS, msg="Test successful", output=["test output"], notebookid="1234",
                         user_config="test config", messages=["test message"], logs="test logs",
                         time=Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00",
                                      finish="2022-01-01 00:00:10"), outputs={"test": "output"}, name="test name")
        result_dict = result.to_dict()
        self.assertEqual(result_dict["result"], Status.PASS)
        self.assertEqual(result_dict["msg"], "Test successful")
        self.assertEqual(result_dict["output"], ["test output"])
        self.assertEqual(result_dict["notebookid"], "1234")
        self.assertEqual(result_dict["user_config"], "test config")
        self.assertEqual(result_dict["messages"], ["test message"])
        self.assertEqual(result_dict["logs"], "test logs")
        self.assertEqual(result_dict["time"]["result"], Status.PASS)
        self.assertEqual(result_dict["time"]["totaltime"], 10)
        self.assertEqual(result_dict["time"]["start"], "2022-01-01 00:00:00")
        self.assertEqual(result_dict["time"]["finish"], "2022-01-01 00:00:10")
        self.assertEqual(result_dict["outputs"], {"test": "output"})
        self.assertEqual(result_dict["name"], "test name")

    #  Tests that a Results object cannot be created with invalid values for attributes.
    def test_results_invalid_attributes(self):
        with self.assertRaises(TypeError):
            Results(result="success", msg="Test successful", output=["test output"], notebookid="1234",
                             user_config="test config", messages=["test message"], logs="test logs",
                             time=Timing(result="success", totaltime="10s", start="2022-01-01 00:00:00",
                                          finish="2022-01-01 00:00:10"), outputs={"test": "output"}, name=1234)


    #  Tests that the __str__() method returns a string representation of the object.
    def test_results_to_str(self):
        result = Results(result=Status.PASS, msg="Test successful", output=["test output"], notebookid="1234",
                         user_config="test config", messages=["test message"], logs="test logs",
                         time=Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00",
                                      finish="2022-01-01 00:00:10"), outputs={"test": "output"}, name="test name")
        result_str = str(result)
        self.assertIn("name", result_str)
        self.assertIn("result", result_str)
        self.assertIn("outputs", result_str)
        self.assertIn("messages", result_str)
        self.assertIn("time", result_str)
        self.assertIn("logs", result_str)

    #  Tests that the __repr__() method returns a string representation of the object.
    def test_results_to_repr(self):
        result = Results(result=Status.PASS, msg="Test successful", output=["test output"], notebookid="1234",
                         user_config="test config", messages=["test message"], logs="test logs",
                         time=Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00",
                                      finish="2022-01-01 00:00:10"), outputs={"test": "output"}, name="test name")
        result_repr = repr(result)
        self.assertIn("name", result_repr)
        self.assertIn("result", result_repr)
        self.assertIn("outputs", result_repr)
        self.assertIn("messages", result_repr)
        self.assertIn("time", result_repr)
        self.assertIn("logs", result_repr)

class TestTiming(unittest.TestCase):
    #  Tests creating a Timing object with all required attributes.
    def test_create_timing_object(self):
        timing = Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00", finish="2022-01-01 00:00:10")
        self.assertEqual(timing.result, Status.PASS)
        self.assertEqual(timing.totaltime, 10)
        self.assertEqual(timing.start, "2022-01-01 00:00:00")
        self.assertEqual(timing.finish, "2022-01-01 00:00:10")

    #  Tests converting a Timing object to a string.
    def test_timing_to_string(self):
        timing = Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00", finish="2022-01-01 00:00:10")
        self.assertEqual(str(timing),
                         "{'result': "  + str(Status.PASS) + ", 'elapsed': '10.00', 'percent': '0', 'start': '2022-01-01 00:00:00', 'finish': '2022-01-01 00:00:10'}")

    #  Tests creating a Timing object with a negative totaltime.
    def test_timing_negative_totaltime(self):
        with self.assertRaises(ValueError):
            Timing(result=Status.PASS, totaltime=-10, start="2022-01-01 00:00:00", finish="2022-01-01 00:00:10")

    #  Tests that the percent_change attribute is calculated correctly based on expected and actual totaltime.
    def test_percent_change(self):
        timing = Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00", finish="2022-01-01 00:00:10",
                        expected=5)
        self.assertEqual(timing.percent_change, "100.00")

    #  Tests converting a Timing object to a dictionary.
    def test_timing_to_dict(self):
        timing = Timing(result=Status.PASS, totaltime=10, start="2022-01-01 00:00:00", finish="2022-01-01 00:00:10")
        expected_dict = {
            "result": Status.PASS,
            "totaltime": 10,
            "start": "2022-01-01 00:00:00",
            "finish": "2022-01-01 00:00:10",
            "expected": 0,
            "percent_change": "0"
        }
        self.assertEqual(timing.to_dict(), expected_dict)


class TestNotebook(unittest.TestCase):
    #  Tests that a Notebook object can be created with valid input parameters.
    def test_create_notebook_valid_input(self):
        notebook = Notebook(name="test_notebook", filepath="/path/to/notebook", totaltime=10, results=[1, 2, 3])
        self.assertEqual(notebook.name, "test_notebook")
        self.assertEqual(notebook.filepath, "/path/to/notebook")
        self.assertEqual(notebook.totaltime, 10)
        self.assertEqual(notebook.results, [1, 2, 3])

    #  Tests that the attributes of a Notebook object can be accessed.
    def test_access_notebook_attributes(self):
        notebook = Notebook(name="test_notebook", filepath="/path/to/notebook", totaltime=10, results=[1, 2, 3])
        self.assertEqual(notebook.name, "test_notebook")
        self.assertEqual(notebook.filepath, "/path/to/notebook")
        self.assertEqual(notebook.totaltime, 10)
        self.assertEqual(notebook.results, [1, 2, 3])

    #  Tests that a Notebook object cannot be created with an empty name.
    def test_create_notebook_empty_name(self):
        with self.assertRaises(ValueError):
            Notebook(name="", filepath="/path/to/notebook", totaltime=10, results=[1, 2, 3])

    #  Tests that a Notebook object cannot be created with a negative totaltime.
    def test_create_notebook_negative_totaltime(self):
        with self.assertRaises(ValueError):
            Notebook(name="test_notebook", filepath="/path/to/notebook", totaltime=-10, results=[1, 2, 3])


if __name__ == '__main__':
    unittest.main()