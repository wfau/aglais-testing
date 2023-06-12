# GDMPBenchmarker

GDMPBenchmarker is a class used to run benchmarks for the Gaia Data Mining platform. It provides functionality to run Zeppelin notebooks, collect and validate their results, and generate benchmark reports.

## Installation

### Requirements Installation

To use the GDMPBenchmarker, first install the requirements:

        pip install -r pip-requirements
        
###  GDMPBenchmarker Install

Optionally, you can install the GDMPBenchmarker:
        
        python3 setup.py install
        
Or you can use it by just running the gdmp_benchmark.py module

## Usage

To use the GDMPBenchmarker class, follow these steps:

1. Import the class:

       from gdmp_benchmark import GDMPBenchmarker

2. Create an instance of the GDMPBenchmarker class, providing the necessary parameters:

        benchmarker = GDMPBenchmarker(userconfig="user_config.json", zeppelin_url="http://localhost:8080")


        Parameters:
        -----------
        userconfig (optional): Path to the user configuration file in JSON format. If not provided, a default configuration will be used.
        zeppelin_url (required): The URL of the Zeppelin instance.

3. Run the benchmark:

        results = benchmarker.run(usercount=1, notebook_config="notebook_config.json", delay_start=0, delay_notebook=0)


        Parameters:
        -----------
        usercount (optional): Number of users to simulate in the benchmark. Default is 1.
        notebook_config (required): Path to the notebook configuration file in JSON format.
        delay_start (optional): Number of seconds to delay the start of the benchmark. Default is 0.
        delay_notebook (optional): Number of seconds to delay the execution of each notebook. Default is 0.

## Command Line Interface

You can also run it via the cli as:

      python gdmp_benchmark.py --zeppelin_url http://localhost:8080 --usercount 1 --notebook_config notebook_config.json --user_config user_config.json --delay_start 0 --delay_notebook 0

### Arguments

        --zeppelin_url (required): URL of the Zeppelin instance.
        --usercount (required): Number of users.
        --notebook_config (required): Path to the notebook configuration file in JSON format.
        --user_config (required): Path to the user configuration file in JSON format.
        --delay_start (optional): Number of seconds to delay the start of the test. Default is 0.
        --delay_notebook (optional): Number of seconds to delay each notebook. Default is 0.
        --delete (optional): Whether to delete the notebooks after the test.

## Configuration Files

The GDMPBenchmarker class relies on two configuration files: the user configuration file and the notebook configuration file.

###  User Configuration File

The user configuration file should be in JSON format and specify the users' credentials for the Zeppelin instance. Example configuration:

        {
          "users": [
            {
              "username": "user1",
              "shirouser": {
                "name": "user1",
                "password": "pass1"
              }
            }
          ]
        }

###  Notebook Configuration File

The notebook configuration file should also be in JSON format, and specifies the list of notebooks to be tested, along with the expected execution duration, and optionally hashes of the expected output. Example configuration:

        {
        "notebooks" : [
                           {
                              "name" : "GaiaDMPSetup",
                              "filepath" : "https://raw.githubusercontent.com/wfau/aglais-testing/bc9b9787b5b6225e11df5a4ef0272bcec660a44e/notebooks/GaiaDMP_validation.json",
                              "totaltime" : 50,
                              "results" : []
                           }
                      ]
        }

## Dependencies

The following dependencies are required to use the GDMPBenchmarker class:

- Python 3.x
- Requests library (for making HTTP requests)
- SimpleJSON library (for working with JSON data)
- ZDairi library: git+https://github.com/stvoutsin/zdairi.git
