import unittest
from gdmp_benchmark import GDMPBenchmarker, Results, Timing, Notebook, Status
import unittest.mock as mock

"""
Main functionalities:
The GDMPBenchmarker class is responsible for running Zeppelin notebooks and benchmarking their performance. It can run notebooks in parallel for multiple users, compare their output to expected output, and delete the notebooks after they have been run. It also generates user configuration files for Zeppelin authentication.

Methods:
- get_note: retrieves a Zeppelin notebook from a URL and returns it as a dictionary
- generate_zdairi_user_configs: generates user configuration files for Zeppelin authentication based on a user configuration file
- _delete_notebook: deletes a Zeppelin notebook using the zdairi command-line tool
- _create_notebook: creates a Zeppelin notebook using the zdairi command-line tool and returns its ID
- _run_notebook: runs a Zeppelin notebook using the zdairi command-line tool and returns its output, status, and messages
- _get_user_config: returns the path to a user configuration file based on whether the method is being run concurrently or not
- run_notebook: runs a Zeppelin notebook and returns its results, including output, status, and timing
- run: runs Zeppelin notebooks for multiple users, either in parallel or sequentially, and returns their results

Fields:
- DEFAULT_DIR: the default directory for user configuration files
- DEFAULT_USER_CONFIG: the default user configuration file
- verbose: whether to print verbose output
- zeppelin_url: the URL of the Zeppelin instance
- userconfig: the path to the user configuration file
- notebooks: a list of Notebook objects
- default_userconfig: the default user configuration file
- expected_output: the expected output of the notebook
- expectedtime: the expected time for the notebook to run
- total_users: The total users 
"""

class TestGDMPBenchmarker(unittest.TestCase):

    #  Tests that a single notebook can be run with expected output and timing.
    def test_run_single_notebook_with_expected_output_and_timing(self):
        # create a mock notebook with expected output and timing
        notebook = Notebook(name="test_notebook", filepath="test_filepath", totaltime=10, results=[])
        # create a mock result with actual output and timing
        result = Results(result=Status.PASS, msg="", output=["expected_output"], time=Timing(result=Status.FAST, totaltime=9, start="", finish=""), notebookid="", user_config="", messages=[])
        # create a mock GDMPBenchmarker object
        benchmarker = GDMPBenchmarker()
        benchmarker.run_notebook = lambda x, y, z: result
        # run the test
        actual_result = benchmarker._run_single(notebooks=[notebook])
        # assert that the actual result matches the expected result
        expected_result = [result]
        self.assertEqual(actual_result, expected_result)

    #  Tests that multiple notebooks can be run with expected output and timing.
    def test_run_multiple_notebooks_with_expected_output_and_timing(self):
        # create mock notebooks with expected output and timing
        notebook1 = Notebook(name="test_notebook1", filepath="test_filepath1", totaltime=10, results=[])
        notebook2 = Notebook(name="test_notebook2", filepath="test_filepath2", totaltime=5, results=[])
        # create mock results with actual output and timing
        result1 = Results(result=Status.PASS, msg="", output=["expected_output1"], time=Timing(result=Status.FAST, totaltime=9, start="", finish=""), notebookid="", user_config="", messages=[])
        result2 = Results(result=Status.PASS, msg="", output=["expected_output2"], time=Timing(result=Status.FAST, totaltime=4, start="", finish=""), notebookid="", user_config="", messages=[])
        # create a mock GDMPBenchmarker object
        benchmarker = GDMPBenchmarker()
        benchmarker.run_notebook = lambda x, y, z: result1 if x == "test_filepath1" else result2
        # run the test
        actual_result = benchmarker._run_single(notebooks=[notebook1, notebook2])
        # assert that the actual result matches the expected result
        expected_result = [result1, result2]
        self.assertEqual(actual_result, expected_result)

    #  Tests that a notebook can be run with no expected output.
    def test_run_notebook_with_no_expected_output(self):
        # create a mock notebook with no expected output
        notebook = Notebook(name="test_notebook", filepath="test_filepath", totaltime=10, results=[])
        # create a mock result with actual output and timing
        result = Results(result=Status.PASS, msg="", output=["actual_output"], time=Timing(result=Status.FAST, totaltime=9, start="", finish=""), notebookid="", user_config="", messages=[])
        # create a mock GDMPBenchmarker object
        benchmarker = GDMPBenchmarker()
        benchmarker.run_notebook = lambda x, y, z: result
        # run the test
        actual_result = benchmarker._run_single(notebooks=[notebook])
        # assert that the actual result matches the expected result
        expected_result = [result]
        self.assertEqual(actual_result, expected_result)

    #  Tests that a notebook can be run with no expected timing.
    def test_run_notebook_with_no_expected_timing(self):
        # create a mock notebook with no expected timing
        notebook = Notebook(name="test_notebook", filepath="test_filepath", totaltime=0, results=[])
        # create a mock result with actual output and timing
        result = Results(result=Status.PASS, msg="", output=["expected_output"], time=Timing(result=Status.FAST, totaltime=9, start="", finish=""), notebookid="", user_config="", messages=[])
        # create a mock GDMPBenchmarker object
        benchmarker = GDMPBenchmarker()
        benchmarker.run_notebook = lambda x, y, z: result
        # run the test
        actual_result = benchmarker._run_single(notebooks=[notebook])
        # assert that the actual result matches the expected result
        expected_result = [result]
        self.assertEqual(actual_result, expected_result)


if __name__ == '__main__':
    unittest.main()