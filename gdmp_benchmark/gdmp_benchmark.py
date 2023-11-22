"""
Module that can be used to run benchmarks against an instance of the Gaia Data Mining Platform
"""
# pylint: disable-msg=too-many-locals
# pylint: disable-msg=too-many-arguments

import sys
import subprocess
import time
import string
import random
import hashlib
from enum import Enum
import argparse
import logging
from datetime import datetime
from multiprocessing import Pool, current_process
from typing import List, Dict, Protocol
from dataclasses import dataclass, field, fields
import simplejson as json
from simplejson.errors import JSONDecodeError
import requests


class InvalidConfigurationError(Exception):
    """Exception to be raised when the configuration passed in is invalid"""

    __module__ = Exception.__module__

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def validate_not_empty(val):
    """
    Args:
        val: The value to validate
    Raises:
         ValueError: If value is empty
    """

    if not val:
        msg = "Value is empty"
        raise ValueError(msg)


def validate_positive(val):
    """
    Args:
        val: The value to validate
    Raises:
         ValueError: If value is not positive
         TypeError: If value is not an int
    """
    if not isinstance(val, int):
        msg = f"Value is not an int: {val}"
        raise TypeError(msg)

    if val < 0:
        msg = f"Value is not positive: {val}"
        raise ValueError(msg)


def validate(instance):
    """
    Validate the parameter types of a class instance
    Args:
        instance: The instance of a class
    Raises:
         TypeError: If type does not match Type hint
    """
    for fld in fields(instance):
        attr = getattr(instance, fld.name)
        if not isinstance(attr, fld.type):
            msg = f"Field {fld.name} is of type {type(attr)}, should be {fld.type}"
            raise TypeError(msg)


class Status(str, Enum):
    """Status of the timing for a notebook run"""

    SLOW = "SLOW"
    FAST = "FAST"
    PASS = "PASS"
    ERROR = "ERROR"
    FAIL = "FAIL"
    SUCCESS = "SUCCESS"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def to_json(self):
        """Return as json"""
        return self.value


@dataclass
class Timing:
    """
    Stores the Timing info of Notebook run.
    Attributes:
        result (Status): The result of the operation.
        totaltime (int): The total execution time
        start (str): The start time of the notebook run
        finish (str): The end time of the notebook run
        expected (str): The expected execution time
    """

    result: Status
    totaltime: int
    start: str
    finish: str
    expected: int = 0

    def __post_init__(self):
        validate(self)
        validate_positive(self.totaltime)

    @property
    def percent_change(self) -> str:
        """
        Get percentage change (Total time - expected time) / expected_time
        Returns:
            str: Percentage change
        """
        if self.expected and self.totaltime > 0:
            return f"{((self.totaltime - self.expected) / self.expected) * 100:.2f}"
        return "0"

    def __str__(self):
        return str(
            {
                "result": self.result,
                "elapsed": f"{self.totaltime:.2f}",
                "percent": self.percent_change,
                "start": self.start,
                "finish": self.finish,
            }
        )

    def __repr__(self):
        """Return repr view"""
        return str(
            {
                "result": self.result,
                "elapsed": f"{self.totaltime:.2f}",
                "percent": self.percent_change,
                "start": self.start,
                "finish": self.finish,
            }
        )

    def to_json(self):
        """Return as json"""
        return {
            "result": self.result.to_json(),
            "elapsed": f"{self.totaltime:.2f}",
            "percent": self.percent_change,
            "start": self.start,
            "finish": self.finish,
        }

    def to_dict(self):
        """Return as dictionary"""
        dict_view = self.__dict__
        dict_view["percent_change"] = self.percent_change
        return dict_view


@dataclass
class Results:
    # pylint: disable=too-many-instance-attributes
    # Need to refactor this
    """
    Stores Results Info.

    Attributes:
        result (Status): The result of the operation.
        msg (str): A message describing the result.
        output (List[str]): A list of output strings.
        notebookid (str): The ID of the notebook.
        user_config (str): The user configuration in JSON format.
        messages (List[str]): A list of messages.
        logs (str): Additional logs.
        time (Timing): The timing information.
        outputs (dict): Additional outputs.
        name (str): A name attribute.
    """

    result: Status
    msg: str
    output: list
    notebookid: str
    user_config: str
    messages: list
    logs: str = ""
    time: Timing = field(default_factory=Timing)
    outputs: dict = field(default_factory=dict)
    name: str = ""

    def __post_init__(self):
        """post_init method"""
        validate(self)

    def to_dict(self):
        """Return as dictionary"""
        return {
            "result": self.result,
            "msg": self.msg,
            "output": self.output,
            "notebookid": self.notebookid,
            "user_config": self.user_config,
            "messages": self.messages,
            "logs": self.logs,
            "time": self.time.__dict__,
            "outputs": self.outputs,
            "name": self.name,
        }

    def __str__(self):
        return str(
            {
                "name": self.name,
                "result": str(self.result),
                "outputs": self.outputs,
                "messages": self.messages,
                "time": self.time,
                "logs": self.msg,
            }
        )

    def __repr__(self):
        return str(
            {
                "name": self.name,
                "result": str(self.result),
                "outputs": self.outputs,
                "messages": self.messages,
                "time": self.time,
                "logs": self.msg,
            }
        )

    def to_json(self) -> str:
        """Convert to JSON"""

        return json.dumps(str(
            {
                "name": self.name,
                "result": str(self.result),
                "outputs": self.outputs,
                "messages": self.messages,
                "time": self.time.to_json(),
                "logs": self.logs,
            }
        ))


class AlertStrategies(Enum):
    """
    Alerting Strategies
    """

    ONLY_ON_ERROR = "ONLY_ON_ERROR"
    SLOW_AND_ERROR = "SLOW_AND_ERROR"
    ALLWAYS = "ALLWAYS"


ALERT_STRATEGIES_MAP = {
    AlertStrategies.ONLY_ON_ERROR: (Status.ERROR, Status.FAIL),
    AlertStrategies.SLOW_AND_ERROR: (Status.ERROR, Status.FAIL, Status.SLOW),
    AlertStrategies.ALLWAYS: (
        Status.ERROR,
        Status.FAIL,
        Status.SLOW,
        Status.FAST,
        Status.PASS,
    ),
}


class SlackAlerter:
    """Slack Alerter Class, used to send out alerts to slack channels"""

    def __init__(self, webhook):
        self.webhook = webhook

    @staticmethod
    def send_http(msg: str, url: str):
        """Send an http request with msg as a 'text' parameter"""
        response = requests.post(
            url,
            json={"text": msg},
            headers={"Content-Type": "application/json"},
            timeout=300,
        )

        if response.status_code == 200:
            logging.info("Message sent successfully to Slack!")
        else:
            logging.warning(
                "Failed to send message. Status code: %s", response.status_code
            )

    def send_alert(self, content: list, alert_strategy: AlertStrategies) -> None:
        """Send an alert"""
        for test in content:
            if test.result in ALERT_STRATEGIES_MAP.get(
                alert_strategy, True
            ) or test.time.result in ALERT_STRATEGIES_MAP.get(alert_strategy, True):
                self.send_http(self.format_message(test), self.webhook)
                return

    @staticmethod
    def format_message(content: Results) -> str:
        """Format a message"""
        return json.dumps(content, default=str)


@dataclass
class Notebook:
    """
    Stores Notebook info
    Attributes:
         name (str): The name of the notebook
         filepath (str): The filepath of the notebook
         totaltime (int): The totaltime of the notebook
         results (list):  The results of the notebook
    """

    name: str
    filepath: str
    totaltime: int
    results: list

    def __post_init__(self):
        validate(self)
        validate_positive(self.totaltime)
        validate_not_empty(self.name)
        self.expected_output = self.results
        self.expectedtime = self.totaltime


class NotebookHandler(Protocol):
    """Protocol for a Notebook handling Class"""

    @staticmethod
    def create_notebook(config: str, filepath: str, messages: list) -> str:
        """Create a notebook"""
        # pylint: disable=W0107
        pass

    @staticmethod
    def execute_notebook(
        config: str, notebookid: str, filepath: str, messages: list
    ) -> tuple:
        """Execute a notebook"""
        # pylint: disable=W0107
        pass

    @staticmethod
    def print_notebook(notebookid: str, config: str) -> dict:
        """Print a notebook"""
        # pylint: disable=W0107
        pass

    @staticmethod
    def delete_notebook(notebookid: str, config: str) -> None:
        """
        Args:
            notebookid (str): The ID of the notebook to delete
            config (str): The configuration for the user
        Returns:
            None
        """
        # pylint: disable=W0107
        pass


class ZDairiNotebookHandler:
    """
    Implementation of the Notebook Handler Protocol.cProvides methods for creating, executing,
    printing and deleting notebooks
    """

    @staticmethod
    def delete_notebook(notebookid: str, config: str) -> None:
        """
        Args:
            notebookid (str): The ID of the notebook to delete
            config (str): The configuration for the user
        """

        batcmd = (
            "zdairi --config " + config + " notebook delete --notebook " + notebookid
        )
        with subprocess.Popen(
            batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        ):
            pass

    @staticmethod
    def create_notebook(config: str, filepath: str, messages: list) -> str:
        """
        Args:
            config (str): The configuration for the user
            filepath (str): The path for the notebook to create
            messages (list): The list of messages to append to
        Returns:
            notebookid: The ID for the new notebook
        """

        try:
            # Make notebook
            batcmd = (
                "zdairi --config " + config + " notebook create --filepath " + filepath
            )
            with subprocess.Popen(
                batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
            ) as pipe:
                zdairi_result = pipe.communicate()[0]
                result = zdairi_result.decode().split("\n")
                text = result[0]
                notebookid = text.split(": ")[1]

        except JSONDecodeError as json_err:
            logging.exception(json_err)
            messages.append(
                "Exception encountered while trying to create a notebook: "
                + filepath
                + " for user in config: "
                + config
            )
            messages.append(zdairi_result.decode())

        return notebookid

    @staticmethod
    def print_notebook(notebookid: str, config: str) -> dict:
        """
        Print notebook
        Args:
            notebookid: ID of the notebook
            config: User configuration file
        Returns:
            dict: JSON dictionary of notebook
        """
        batcmd = (
            "zdairi --config " + config + " notebook print --notebook " + notebookid
        )
        with subprocess.Popen(
            batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        ) as pipe:
            zdairi_output = pipe.communicate()[0]
            json_notebook = json.loads(
                "".join(zdairi_output.decode().split("\n")), strict=False
            )
        return json_notebook

    @staticmethod
    def execute_notebook(
        config: str, notebookid: str, filepath: str, messages: list
    ) -> tuple:
        """
        Execute a notebook
        Args:
            config (str): The configuration for the user
            notebookid (str): The notebook ID
            filepath (str): The path for the notebook to create
            messages (list): The list of messages to append to
        Returns:
            output: A list of output, each element being a single cell output
            msg: Result message
            status: Status message
        """

        output = []
        msg = ""
        status = ""
        try:
            # Run notebook
            batcmd = (
                "zdairi --config " + config + " notebook run --notebook " + notebookid
            )
            with subprocess.Popen(
                batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
            ) as pipe:
                _ = pipe.communicate()[0].decode()

            json_notebook = ZDairiNotebookHandler.print_notebook(
                notebookid=notebookid, config=config
            )

            for cell in json_notebook["paragraphs"]:
                if len(cell.get("results", [])) > 0:
                    status = Status[cell["results"]["code"].upper()]
                    if cell["results"]["code"] == Status.SUCCESS.value:
                        status = Status.SUCCESS
                    elif len(cell["results"].get("msg")) > 0:
                        result_msg = cell["results"]["msg"][0]["data"].strip()
                        output.append(result_msg)
                        if status == "ERROR":
                            msg = result_msg
                            break

        except JSONDecodeError as json_err:
            logging.exception(json_err)
            status = Status.FAIL
            messages.append(
                "Exception encountered while trying to create a notebook: "
                + filepath
                + " for user in config: "
                + config
            )
            messages.append(output)

        return output, msg, status


class GDMPBenchmarker:
    """Class used to run benchmarks for the Gaia Data Mining platform"""

    DEFAULT_DIR = "/tmp/"
    DEFAULT_USER_CONFIG = "user1.yml"

    def __init__(
        self,
        userconfig: str = "",
        zeppelin_url: str = "",
        verbose: bool = False,
        notebook_handler: NotebookHandler = ZDairiNotebookHandler,
    ):
        self.verbose = verbose
        self.zeppelin_url = zeppelin_url.strip("/")
        self.userconfig = userconfig
        self.notebooks = []
        self.default_userconfig = self.DEFAULT_USER_CONFIG
        self.total_users = self.generate_zdairi_user_configs()
        self.notebook_handler = notebook_handler

    @staticmethod
    def get_note(path: str) -> Dict[str, str]:
        """Get the json file given a path (URL or file), and return as a json object"""
        if path.startswith("http"):
            res = requests.get(path, timeout=30).text
            data = json.loads(res, strict=False)
        else:
            with open(path, encoding="utf-8") as config_file:
                data = json.load(config_file)
        return data

    def generate_zdairi_user_configs(self) -> int:
        """
        Generate the user configurations that can be used by the zdairi lib
        These need to be yml files with the following format:
            zeppelin_url:
            zeppelin_auth:
            zeppelin_user:
            zeppelin_password:
        Returns:
             int: Number of users
        Raises:
            InvalidConfigurationError: If User configuration is not a valid Json file
        """
        counter = 1
        if not self.userconfig:
            return 0
        try:
            with open(self.userconfig, encoding="utf-8") as user_file:
                user_dictionary = json.load(user_file)
        except JSONDecodeError as exc:
            raise InvalidConfigurationError(
                "User configuration is not a valid json file!"
            ) from exc

        user_list = user_dictionary.get("users", [])
        for user in user_list:
            shiro_user = user.get("shirouser", {})
            if shiro_user:
                with open(
                    self.DEFAULT_DIR + "user" + str(counter) + ".yml",
                    "w",
                    encoding="utf-8",
                ) as user_file:
                    user_file.write("zeppelin_url: " + self.zeppelin_url + "\n")
                    user_file.write("zeppelin_auth: true\n")
                    user_file.write("zeppelin_user: " + shiro_user.get("name") + "\n")
                    user_file.write(
                        "zeppelin_password: " + shiro_user.get("password") + "\n"
                    )
                counter += 1

        return len(user_list)

    def _get_user_config(self, concurrent: bool) -> str:
        """
        Args:
            concurrent (bool): Whether this is a concurrent test
        Returns:
            config (str): The user config path
        """

        if concurrent:
            cur_process = current_process()
            # pylint: disable=protected-access
            counter = cur_process._identity[0]
            config = self.DEFAULT_DIR + "user" + str(counter) + ".yml"
        else:
            config = self.DEFAULT_DIR + self.default_userconfig
        return config

    @staticmethod
    def _write_data_to_file(data: dict, filepath: str) -> None:
        """
        Write some data to a file
        Args:
            data: Dictionary of the data
            filepath: The file to write to
        """
        data["name"] = filepath
        with open(filepath, "w+", encoding="utf-8") as cred:
            json.dump(data, cred)

    def run_notebook(
        self, filepath: str, name: str, concurrent: bool = False
    ) -> Results:
        """
        Run a Zeppelin notebook, given a path and name for it.
        Return the status of the job and how long it took to execute
        Args:
            filepath: String with the filepath
            name: Name of the notebooks
            concurrent: Whether the notebook is part of a concurrent run
        Returns:
            Results: The results
        """

        tmpfile = self.DEFAULT_DIR + name + ".json"
        messages = []
        start = time.time()
        starttime_iso = datetime.now()

        config = self._get_user_config(concurrent)
        data = self.get_note(path=filepath)
        self._write_data_to_file(data=data, filepath=tmpfile)

        # Create Notebook
        notebookid = self.notebook_handler.create_notebook(
            config=config, filepath=tmpfile, messages=messages
        )

        # Run Notebook
        output, msg, status = self.notebook_handler.execute_notebook(
            config=config, notebookid=notebookid, filepath=tmpfile, messages=messages
        )

        end = time.time()
        endtime_iso = datetime.now()

        timing = Timing(
            result=Status.PASS,
            totaltime=int(end - start),
            start=starttime_iso.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            finish=endtime_iso.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        )

        return Results(
            result=status,
            msg=msg,
            output=output,
            time=timing,
            notebookid=notebookid,
            user_config=config,
            messages=messages,
        )

    def run(
        self,
        usercount: int = 1,
        notebook_config: str = "",
        delay_start: int = 0,
        delay_notebook: int = 0,
        delete: bool = True,
    ) -> list:
        """
        Wrapper method to run a notebook test, either as a concurrent benchmark or as a single one
        Args:
            usercount: Number of users
            notebook_config: Notebook configuration file,
            delay_start: Number of seconds to delay start of test
            delay_notebook: Number of seconds to delay each notebook
            delete: Whether to delete the notebooks after the test
        Returns:
            List of Results
        """

        def parse_notebook_config(note_config: str):
            """
            Parse the notebook configuration
            Args:
                note_config: Notebook config as string
            Returns:
                list: Notebook list
            """
            notebook_list = []
            notebook_json = self.get_note(path=note_config)["notebooks"]
            for notebook in notebook_json:
                notebook_list.append(Notebook(**notebook))
            return notebook_list

        notebooks = parse_notebook_config(notebook_config)
        if usercount > 1:
            results = self._run_parallel(
                usercount=usercount,
                notebooks=notebooks,
                delay_start=delay_start,
                delay_notebook=delay_notebook,
                delete=delete,
            )
        else:
            results = self._run_single(
                0, notebooks, False, delay_start, delay_notebook, delete
            )
        return results

    def _run_parallel(
        self,
        usercount: int = 1,
        notebooks: List = None,
        delay_start: int = 0,
        delay_notebook: int = 0,
        delete: bool = True,
    ):
        """
        Run the benchmarks in the given configuration as a parallel test
        with multiple concurrent users
        Args:
            usercount: Number of users
            notebooks: Notebook List
            delay_start: Delay start in seconds
            delay_notebook: Delay to start of notebook in seconds
            delete: Whether to delete the notebooks after the run
        Returns:
            dict: The results
        Raises:
            ValueError: If User count exceeds maximum
        """
        if usercount > self.total_users:
            err_msg = """
            User count exceeds the number of users that 
            were passed in the configuration!
            """
            raise ValueError(err_msg)
        with Pool(processes=usercount) as pool:
            results = pool.starmap(
                self._run_single,
                list(
                    zip(
                        range(1, usercount + 1),
                        [notebooks] * usercount,
                        [True] * usercount,
                        [delay_start] * usercount,
                        [delay_notebook] * usercount,
                        [delete] * usercount,
                    )
                ),
            )
        pool.close()
        pool.join()
        return results

    @staticmethod
    def _validate_output(actual, expected, cell_number):
        """
        Validate actual vs expected output
        Args:
            actual: Actual output
            expected: Expected output
            cell_number: Cell number
        Returns:
             bool: Whether the output is valid
             Status: Result Status
             str: Output message
        """
        out_valid = True
        result_status_msg = Status.PASS
        output_msg = ""

        if actual != expected:
            if expected != "":
                out_valid = False
                result_status_msg = Status.FAIL
                output_msg = (
                    f"Expected/Actual output missmatch " f"of cell #{cell_number}!"
                )

        return out_valid, result_status_msg, output_msg

    def _run_single(
        self,
        iterable: int = 0,
        notebooks: List = None,
        concurrent: bool = False,
        delay_start: int = 0,
        delay_notebook: int = 0,
        delete: bool = True,
    ) -> list:
        """
        Run a single instance of the benchmark test
        Args:
            iterable: Order of the user in a concurrent run
            notebooks: Notebook list
            concurrent: Whether this is part of a concurrent run
            delay_start: Delay ot the start of the run in seconds
            delay_notebook: Delay to the start of the notebook in seconds
            delete: Whether to delete the notebooks after the run
        Returns:
           list: The results
        """

        results = []
        time.sleep(delay_start * iterable)
        created_notebooks = []

        for notebook in notebooks:
            output_valid = True
            generated_name = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            )
            result = self.run_notebook(
                notebook.filepath, generated_name, concurrent
            )  # Results
            created_notebooks.append([result.notebookid, result.user_config])

            if len(notebook.expected_output) > 0 and result.result != Status.ERROR:
                for i, cell in enumerate(result.output):
                    actual_output = hashlib.md5(str(cell).encode("utf-8")).hexdigest()
                    expected_output = notebook.expected_output.get(str(i), "")
                    output_valid, result.result, res_message = self._validate_output(
                        actual_output, expected_output, i
                    )
                    if not output_valid:
                        result.messages.append(res_message)
                        result.logs += res_message
                        break

            # Add result data to Results object
            result.name = notebook.name
            result.outputs = {"valid": output_valid}

            if result.time.totaltime > notebook.expectedtime:
                result.time.result = Status.SLOW
            elif result.time.totaltime < (notebook.expectedtime / 2):
                result.time.result = Status.ERROR
            else:
                result.time.result = Status.FAST

            result.time.expected = notebook.expectedtime
            results.append(result)
            # Run Notebook delay here
            time.sleep(delay_notebook)

        if delete:
            for notebook in created_notebooks:
                self.notebook_handler.delete_notebook(
                    notebookid=notebook[0], config=notebook[1]
                )

        return [results]


def main(args: List[str] = None):
    """Main method"""
    user_config_docs = """The user configuration file in JSON format.
            { "users": [{    
                            "username": "user1",
                            "shirouser": {
                                "name": "user1",
                                "password": "pass1"
                            }          
                       }]
            }
    """

    notebook_config_docs = """The notebook configuration file in JSON format.
            { "notebooks" : [{
                               "name" : "GaiaDMPSetup",
                               "filepath" : "/path/GaiaDMP_validation.json",
                               "totaltime" : 50,
                               "results" : []
                            }] 
            }
    """
    parser = argparse.ArgumentParser(
        description="Gaia Data Mining Platform Benchmarking Tool"
    )

    parser.add_argument(
        "--zeppelin_url", required=True, type=str, default=1, help="Zeppelin URL"
    )
    parser.add_argument(
        "--usercount",
        type=int,
        required=True,
        default=1,
        help="Number of users (default: 1)",
    )
    parser.add_argument(
        "--notebook_config",
        type=str,
        required=True,
        default="",
        help=notebook_config_docs,
    )
    parser.add_argument(
        "--user_config", type=str, required=True, default="", help=user_config_docs
    )
    parser.add_argument(
        "--delay_start",
        type=int,
        default=0,
        help="Number of seconds to delay start of test (default: 0)",
    )
    parser.add_argument(
        "--delay_notebook",
        type=int,
        default=0,
        help="Number of seconds to delay each notebook (default: 0)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Whether to delete the notebooks after the test",
    )

    parser.add_argument(
        "--slack_webhook",
        type=str,
        required=False,
        default=None,
        help="Whether to delete the notebooks after the test",
    )
    args = parser.parse_args(args)
    zeppelin_url = args.zeppelin_url
    usercount = args.usercount
    notebook_config = args.notebook_config
    user_config = args.user_config
    delay_start = args.delay_start
    delay_notebook = args.delay_notebook
    alerter = SlackAlerter(args.slack_webhook) if args.slack_webhook else None

    print("{")
    print(
        f"""
        "config": {{
            "endpoint":   "{zeppelin_url}",
            "testconfig": "{notebook_config}",
            "userconfig":   "{user_config}",
            "usercount":  "{usercount}",
            "delaystart":  "{delay_start}",
            "delaynotebook":  "{delay_notebook}"
        }},
        """
    )
    print("}")

    print("---start---")

    results = GDMPBenchmarker(
        userconfig=user_config,
        zeppelin_url=zeppelin_url,
        verbose=False,
    ).run(
        usercount=usercount,
        notebook_config=notebook_config,
        delay_start=delay_start,
        delay_notebook=delay_notebook,
    )

    if alerter is not None:
        alerter.send_alert(
            content=results, alert_strategy=AlertStrategies.ONLY_ON_ERROR
        )
    print(json.dumps(results, default=lambda o: o.to_dict(), indent=4))
    print("---end---")


if __name__ == "__main__":
    main(sys.argv[1:])
