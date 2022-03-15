import os
import requests
import subprocess
import time
from os import listdir
from os.path import isfile, join
import simplejson as json
import logging
from multiprocessing import Pool, current_process
import random
import string
import hashlib
from datetime import datetime

class AglaisBenchmarker(object):

    def getNote(self, urlpath):
        """
        Get the json file given a URL, and return as a json object
        :type urlpath: str
        :rtype: dict
        """
        response = requests.get(urlpath).text
        d = json.loads(response, strict=False)
        return d


    def __init__(self, notebook_config=None, zeppelin_configdir="/", verbose=True):
        self.verbose = verbose
        self.configdir = zeppelin_configdir
        #self.result_file = "output.json"
        self.notebooks = []
        try:
            if notebook_config:
                if notebook_config.startswith("http"):
                    self.notebooks = self.getNote(notebook_config)["notebooks"]
                else:
                    with open(notebook_config) as f:
                        self.notebooks = json.load(f)["notebooks"]
        except Exception as e:
            logging.exception(e)


    def run_notebook(self, filepath, name, concurrent=False):
        """
        Run a Zeppelin notebook, given a path and name for it. Return the status of the job and how long it took to execute
        :type filepath: str
        :type name: str
        :type concurrent: bool
        :rtype: tuple
        """

        start = time.time()
        starttime_iso = datetime.now()

        status = "FAIL"
        msg = ""
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
            result = pipe.communicate()[0]

            result = result.decode().split("\n")
            text = result[0]
            notebookid = text.split(": ")[1]

            # Run notebook
            batcmd="zdairi --config " + config + " notebook run --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            text = pipe.communicate()[0].decode()

            # Print notebook
            batcmd="zdairi --config " + config + " notebook print --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            result = pipe.communicate()[0]
            result = result.decode().split("\n")
            json_notebook = json.loads("".join(result), strict=False)

            for cell in json_notebook["paragraphs"]:
                if len(cell.get("results", []))>0:
                    status = cell["results"]["code"].upper()
                    if len(cell["results"].get("msg")) > 0:
                        result_msg = cell["results"]["msg"][0]["data"].strip()
                        output.append(result_msg)
                        if status=="ERROR":
                            msg = result_msg
                            break

            # Delete notebook
            #batcmd="zdairi --config " + config + " notebook delete --notebook " + notebookid
            #pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            #os.remove(tmpfile)

        except Exception as e:
            status = "FAIL"
            logging.exception(e)

        if status == "FAILED":
            status = "FAIL"
        if status == "SUCCESS":
            status = "PASS"

        end = time.time()
        endtime_iso = datetime.now()
        return (status, msg, end-start, output, starttime_iso.strftime('%Y-%m-%dT%H:%M:%S.%f%z'), endtime_iso.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))


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
            if self.verbose:
                print ("Test started [Multi User]")
            results = self._run_parallel(users)
        else:
            if self.verbose:
                print ("Test started [Single User]")

            results =  [self._run_single()]

        end = time.time()
        result = "PASS"
        for res in results:
            if not res:
                result = "FAIL"
                break

            for k,v in res.items():
                if v["result"] != "PASS":
                    result = v["result"]
                    break

        if self.verbose:
            print ("Test completed! ({:.2f} seconds)".format(end-start))

        print ("------------ Test Result: [" + result + "] ------------")

        if self.verbose:
            print (results)

        return results


    def _run_parallel(self, concurrent_users):
        """
        Run the benchmarks in the given configuration as a parallel test with multiple concurrent users
        :type concurrent_users: int
        :rtype: dict
        """
        with Pool(processes=concurrent_users) as pool:
            results = pool.starmap(self._run_single, list(zip(range(concurrent_users), [True]*concurrent_users)))
        pool.close()
        pool.join()
        return results


    def _run_single(self, iterable=0, concurrent=False):
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
            result = "PASS"
            output_valid = True
            timing_status = "FAST"
            msg = ""
            percent_change = 0
            start, finish = (0,0)

            try:

                generated_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
                result, msg, totaltime, output, start, finish = self.run_notebook(filepath, generated_name, concurrent)

                if totaltime > expectedtime:
                    timing_status = "SLOW"

                if len(expected_output)>0:
                    for i, cell in enumerate(output):
                        md5hash = hashlib.md5(str(cell).encode('utf-8')).hexdigest()
                        if md5hash != expected_output.get(str(i),""):
                            if expected_output.get(str(i),"")!="":
                                output_valid = False
                                result = "FAIL"
                                msg += "Expected/Actual output missmatch of cell #" + str(i) + "! "

                percent_change = "{:.2f}".format(((totaltime - expectedtime)/expectedtime)*100)
                results[name] = {"result" : result, "outputs" : {"valid" : output_valid}, "time" : {"result" : timing_status, "elapsed" : "{:.2f}".format(totaltime), "expected" : "{:.2f}".format(expectedtime), "percent" : percent_change, "start" : start, "finish": finish  }, "logs" : msg}

            except Exception as e:
                logging.exception(e)
                result = "FAIL"
                output_valid = False
                results[name] = {"result" : result, "outputs" : {"valid" : output_valid}, "time" : {"result" : timing_status, "elapsed" : "{:.2f}".format(totaltime), "expected" : "{:.2f}".format(expectedtime), "percent" : percent_change, "start" : start, "finish": finish  }, "logs" : msg }

        return results


if __name__ == '__main__':

    # Multi-user concurrent benchmark
    AglaisBenchmarker("../config/notebooks/notebooks_quick_pi.json", "../config/zeppelin/").run(concurrent=True, users=3)

