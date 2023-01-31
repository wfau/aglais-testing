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


    def __init__(self, notebook_config=None, users="/tmp/user_list.yml", config_dir="/tmp/",  zeppelin_url="", verbose=False):
        self.verbose = verbose
        user_file = open(users)
        self.zeppelin_url = zeppelin_url.strip("/")
        self.users_file = users
        self.config_dir = config_dir
        self.notebooks = []

        try:
            self.generate_zdairi_user_configs()
        except Exception as e:
            logging.exception(e)

        try:
            if notebook_config:
                if notebook_config.startswith("http"):
                    self.notebooks = self.getNote(notebook_config)["notebooks"]
                else:
                    with open(notebook_config) as f:
                        self.notebooks = json.load(f)["notebooks"]
        except Exception as e:
            logging.exception(e)


    def generate_zdairi_user_configs(self):
        counter = 0
        postfix = ""
        user_file = open(self.users_file)
        user_dictionary = json.load(user_file)
        user_file.close()
        user_list = user_dictionary.get("users",[])

        for user in user_list:
            shiro_user = user.get("shirouser", {})
            if shiro_user:
                f = open(self.config_dir + "user" +  postfix + ".yml", "w")
                f.write("zeppelin_url: " + self.zeppelin_url +  "\n")
                f.write("zeppelin_auth: true\n")
                f.write("zeppelin_user: "  + shiro_user.get("name") + "\n")
                f.write("zeppelin_password: " + shiro_user.get("password") + "\n")
                f.close()
                counter += 1
                postfix = str(counter)


    def delete_notebook(self, notebookid, config):
        # Delete notebook
        batcmd="zdairi --config " + config + " notebook delete --notebook " + notebookid
        pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)


    def run_notebook(self, filepath, name, concurrent=False, delete=True):
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
        notebookid = None
        result = ""
        messages = []

        try:

            if concurrent:
                p = current_process()
                counter = p._identity[0]
                config = self.config_dir + "user" + str(counter) + ".yml"
            else :
                config = self.config_dir + "user.yml"


            data = self.getNote(filepath)
            data["name"] = tmpfile
            with open(tmpfile, 'w+') as cred:
                json.dump(data, cred)
        except Exception as e:
            logging.exception(e)

        try:
            # Make notebook
            batcmd="zdairi --config " + config + " notebook create --filepath " + tmpfile
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            zdairi_result = pipe.communicate()[0]
            result = zdairi_result.decode().split("\n")
            text = result[0]
            notebookid = text.split(": ")[1]
        except Exception as e:
            messages.append("Exception encountered while trying to create a notebook: " + tmpfile  + " for user in config: " + config)
            messages.append(zdairi_result.decode())

        # Temporary fix.. If notebook failed to create, try once more
        if not notebookid:
            try:
                # Make notebook
                batcmd="zdairi --config " + config + " notebook create --filepath " + tmpfile
                pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                zdairi_result = pipe.communicate()[0]
                result = zdairi_result.decode().split("\n")
                text = result[0]
                notebookid = text.split(": ")[1]
            except Exception as e:
                messages.append("Exception encountered while trying to create a notebook: " + tmpfile  + " for user in config: " + config) 
                messages.append(zdairi_result.decode())



        try:
            # Run notebook
            batcmd="zdairi --config " + config + " notebook run --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            text = pipe.communicate()[0].decode()

            # Print notebook
            batcmd="zdairi --config " + config + " notebook print --notebook " + notebookid
            pipe = subprocess.Popen(batcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            zdairi_output = pipe.communicate()[0]
            result = zdairi_output.decode().split("\n")
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
        except Exception as e:
            status = "FAIL"
            messages.append("Exception encountered while trying to create a notebook: " + tmpfile  + " for user in config: " + config) 
            messages.append(zdairi_output.decode())

        if status == "FAILED":
            status = "FAIL"
        if status == "SUCCESS":
            status = "PASS"

        end = time.time()
        endtime_iso = datetime.now()
        return (status, msg, end-start, output, starttime_iso.strftime('%Y-%m-%dT%H:%M:%S.%f%z'), endtime_iso.strftime('%Y-%m-%dT%H:%M:%S.%f%z'), notebookid, config, messages)


    def run(self, concurrent=False, users=1, delay_start=0, delay_notebook=0, delete=True):
        """
        Wrapper method to run a notebook test, either as a concurrent benchmark or as a single one
        :type concurrent: bool
        :type users: int
        :rtype: dict
        """

        start = time.time()

        results = []
        if concurrent:
            results = self._run_parallel(users, delay_start, delay_notebook, delete)
        else:
            results =  self._run_single(0, False, delay_start, delay_notebook, delete)

        end = time.time()

        print (json.dumps(results))

        return results


    def _run_parallel(self, concurrent_users=True, delay_start=0, delay_notebook=0, delete=True):
        """
        Run the benchmarks in the given configuration as a parallel test with multiple concurrent users
        :type concurrent_users: int
        :rtype: dict
        """
        with Pool(processes=concurrent_users) as pool:
            results = pool.starmap(self._run_single, list(zip(range(concurrent_users), [True]*concurrent_users, [delay_start]*concurrent_users, [delay_notebook]*concurrent_users, [delete]*concurrent_users)))
        pool.close()
        pool.join()
        return results


    def _run_single(self, iterable=0, concurrent=False, delay_start=0, delay_notebook=0, delete=True):
        """
        Run a single instance of the benchmark test
        :type iterable: int
        :type concurrent: bool
        :rtype: dict
        """

        results = []
        time.sleep(delay_start * iterable )
        created_notebooks = []
        totaltime = 0

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
            messages = []

            try:

                generated_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
                result, msg, totaltime, output, start, finish, notebookid, user_config, messages = self.run_notebook(filepath, generated_name, concurrent, delete)
                created_notebooks.append([notebookid, user_config])

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
                results.append({"name" : name, "result" : result, "outputs" : {"valid" : output_valid}, "messages" : messages, "time" : {"result" : timing_status, "elapsed" : "{:.2f}".format(totaltime), "expected" : "{:.2f}".format(expectedtime), "percent" : percent_change, "start" : start, "finish": finish  }, "logs" : msg})

            except Exception as e:
                logging.exception(e)
                result = "FAIL"
                output_valid = False
                results.append({"name" : name, "result" : result, "outputs" : {"valid" : output_valid}, "messages" : messages, "time" : {"result" : timing_status, "elapsed" : "{:.2f}".format(totaltime), "expected" : "{:.2f}".format(expectedtime), "percent" : percent_change, "start" : start, "finish": finish  }, "logs" : msg })

            time.sleep(delay_notebook)

        if delete:
            for notebook in created_notebooks:
                self.delete_notebook(notebook[0], notebook[1])
        return results


if __name__ == '__main__':

    # Multi-user concurrent benchmark
    AglaisBenchmarker("../config/notebooks/notebooks_quick_pi.json", "../config/zeppelin/").run(concurrent=True, users=3)
