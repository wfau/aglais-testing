import unittest
from gdmp_benchmark import GDMPBenchmarker, Results, Timing, Notebook, Status

"""
The GDMPBenchmarker class is responsible for benchmarking Zeppelin notebooks. It allows users to run notebooks and compare their output against expected output. The class can run notebooks in parallel, and it can delete the notebooks after they have been run. The class also generates user configurations for Zeppelin, and it can validate the configuration passed in by the user.

Methods:
- __init__: Initializes the GDMPBenchmarker object with user configuration, Zeppelin URL, verbosity, notebook handler, and a list of notebooks.
- get_note: Sends a GET request to a Zeppelin notebook URL and returns the response as a dictionary.
- generate_zdairi_user_configs: Generates user configurations for Zeppelin based on a user configuration file.
- _get_user_config: Returns the path to the user configuration file for a given process.
- _write_data_to_file: Writes data to a file with a given filepath.
- run_notebook: Runs a Zeppelin notebook and returns the results.
- run: Runs a list of notebooks and returns the results.
- _run_parallel: Runs a list of notebooks in parallel and returns the results.
- _validate_output: Compares actual output to expected output and returns a tuple indicating whether the output is valid, the result status message, and the output message.
- _run_single: Runs a list of notebooks sequentially and returns the results.

Fields:
- DEFAULT_DIR: The default directory for user configuration files.
- DEFAULT_USER_CONFIG: The default user configuration file.
- verbose: Whether to print verbose output.
- zeppelin_url: The URL for the Zeppelin instance.
- userconfig: The path to the user configuration file.
- notebooks: A list of notebooks to run.
- default_userconfig: The default user configuration file.
- total_users: The total number of users generated from the user configuration file.
- notebook_handler: The notebook handler to use for running notebooks.
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
