import os
import requests
import subprocess
import time
from os import listdir
from os.path import isfile, join
import json
import urllib.request, json
import logging
from multiprocessing import Pool, current_process
import random
import string


class Benchmarker(object):

    def getNote(self, urlpath):
        """
        Get the json file given a URL, and return as a json object
        :type urlpath: str
        :rtype: dict
        """

        with urllib.request.urlopen(urlpath) as url:
            jsondata = url.read().decode("utf-8-sig")
            data = json.loads(jsondata)
        return data


    def __init__(self, notebook_config=None, zeppelin_configdir="/"):
        self.configdir = zeppelin_configdir
        self.result_file = "output.json"
        if notebook_config:
            with open(notebook_config) as f:
                self.notebooks = json.load(f)["notebooks"]


    def run_notebook(self, filepath, name, concurrent=False):
        """
        Run a Zeppelin notebook, given a path and name for it. Return the status of the job and how long it took to execute
        :type filepath: str
        :type name: str
        :type concurrent: bool
        :rtype: tuple
        """

        start = time.time()
        status = "SUCCESS"
        tmpfile = "/tmp/" + name + ".json"
        output = []

        try:

            if concurrent:
                p = current_process()
                counter = p._identity[0]
                config = self.configdir + "user" + str(counter) + ".yml"
            else :
                config = self.configdir + "user.yml"


            data = self.getNote(filepath)
            data["name"] = tmpfile
            with open(tmpfile, 'w+') as cred:
                json.dump(data, cred)

            # Make notebook
            batcmd="zdairi --config " + config + " notebook create --filepath " + tmpfile
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            result = pipe.communicate()[0].decode().split("\n")
            text = result[2]
            notebookid = text.split(": ")[1]

            # Run notebook
            batcmd="zdairi --config " + config + " notebook run --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            text = pipe.communicate()[0].decode()

            # Print notebook
            batcmd="zdairi --config " + config + " notebook print --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            result = pipe.communicate()[0].decode().split("\n")
            json_notebook = json.loads("".join(result[2:]))

            for cell in json_notebook["paragraphs"]:
                if "results" in cell:
                    output.append(cell["results"]["msg"][0]["data"].strip())

            # Delete notebook
            batcmd="zdairi --config " + config + " notebook delete --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            os.remove(tmpfile)

        except Exception as e:
            status = "ERROR"
            logging.exception(e)
        end = time.time()
        return (status, end-start, output)


    def run(self, concurrent=False, users=1):
        """
        Wrapper method to run a notebook test, either as a concurrent benchmark or as a single one
        :type concurrent: bool
        :type users: int
        :rtype: dict
        """

        start = time.time()

        results = []
        if concurrent:
            results = self.run_parallel(users)
        else:
            results =  self.run_single()

        with open(self.result_file, 'w+') as outfile:
            json.dump(results, outfile)

        end = time.time()

        print ("Test completed after: {} seconds".format(end-start))

        return results


    def run_parallel(self, concurrent_users):
        """
        Run the benchmarks in the given configuration as a parallel test with multiple concurrent users
        :type concurrent_users: int
        :rtype: dict
        """

        with Pool(processes=concurrent_users) as pool:
            results = pool.map(self.run_single, range(concurrent_users), True)
        pool.close()
        pool.join()
        return results


    def run_single(self, iterable=0, concurrent=False):
        """
        Run a single instance of the benchmark test
        :type iterable: int
        :type concurrent: bool
        :rtype: dict
        """

        results = {}
        for notebook in self.notebooks:
            expectedtime = notebook["totaltime"]
            filepath = notebook["filepath"]
            name = notebook["name"]
            expected_output = notebook["results"]
            valid = "TRUE"

            generated_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            status, totaltime, output = self.run_notebook(filepath, generated_name, concurrent)
            if totaltime > expectedtime and status=="SUCCESS":
                status = "SLOW"

            print(output)
            print(expected_output)
            for i in range(len(output)):
                if output[i]!=expected_output[i]:
                    valid = "FALSE"

            results[name] = {"totaltime" : totaltime, "status" : status, "valid" : valid }
            
        return results


if __name__ == '__main__':

    # Single user benchmark
    # Benchmarker("../config/notebooks/notebooks_quick_pi.json", "../config/zeppelin/").run(concurrent=False, users=1)

    # Multi-user concurrent benchmark
    Benchmarker("../config/notebooks/notebooks_quick_pi.json", "../config/zeppelin/").run(concurrent=True, users=3)
