import json
import os
import requests
import numpy as np
import openai
import paramiko

import sys
sys.path.append(".")

from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet, stopwords
from nltk.tokenize import word_tokenize
import nltk

from ..tool import Tool
from bmtools.tools.database.utils.db_parser import get_conf
from bmtools.tools.database.utils.database import DBArgs, Database
# from bmtools.models.customllm import CustomLLM
from bmtools.knowledge.knowledge_extraction import KnowledgeExtraction
from bmtools.tools.db_diag.anomaly_detection import detect_anomalies
from bmtools.tools.db_diag.anomaly_detection import prometheus

from bmtools.tools.db_diag.example_generate import bm25

from termcolor import colored
import pdb

import configparser
from .optimization_tools.index_selection.selection_utils import selec_com
from .optimization_tools.index_selection.selection_utils.workload import Workload
from .optimization_tools.index_selection.selection_algorithms.extend_algorithm import ExtendAlgorithm
from .optimization_tools.index_selection.selection_utils.postgres_dbms import PostgresDatabaseConnector



import warnings

def obtain_values_of_metrics(start_time, end_time, metrics):

    if end_time - start_time > 11000*3:     # maximum resolution of 11,000 points per timeseries
        #raise Exception("The time range is too large, please reduce the time range")
        warnings.warn("The time range ({}, {}) is too large, please reduce the time range".format(start_time, end_time))

    required_values = {}

    print(" ====> metrics: ", metrics)
    for metric in metrics:
        metric_values = prometheus('api/v1/query_range', {'query': metric, 'start': start_time, 'end': end_time, 'step': '3'})
        if metric_values["data"]["result"] != []:
            metric_values = metric_values["data"]["result"][0]["values"]
        else:
            raise Exception("No metric values found for the given time range")

        # compute the average value of the metric
        max_value = np.max(np.array([float(value) for _, value in metric_values]))

        required_values[metric] = max_value

    return required_values

def find_abnormal_metrics(start_time, end_time, monitoring_metrics, resource):

    resource_keys = ["memory", "cpu", "disk", "network"]

    abnormal_metrics = []
    for metric_name in monitoring_metrics:

        interval_time = 5
        metric_values = prometheus('api/v1/query_range', {'query': metric_name, 'start': start_time-interval_time*60, 'end': end_time+interval_time*60, 'step': '3'})

        if metric_values["data"]["result"] != []:
            metric_values = metric_values["data"]["result"][0]["values"]
        else:
            continue

        if detect_anomalies(np.array([float(value) for _, value in metric_values])):
            
            success = True
            for key in resource_keys:
                if key in metric_name and key != resource:
                    success = False
                    break
            if success:
                abnormal_metrics.append(metric_name)

    return abnormal_metrics


INDEX_SELECTION_ALGORITHMS = {
    # "auto_admin": AutoAdminAlgorithm,
    # "db2advis": DB2AdvisAlgorithm,
    # "drop": DropHeuristicAlgorithm,
    "extend": ExtendAlgorithm,
    # "relaxation": RelaxationAlgorithm,
    # "anytime": AnytimeAlgorithm
}


def get_index_result(algo, work_list, connector, columns,
                        sel_params="parameters", process=False, overhead=False):
    
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)

    pdb.set_trace()

    exp_conf_file = script_dir + f"/optimization_tools/index_selection/selection_data/algo_conf/{algo}_config.json"
    with open(exp_conf_file, "r") as rf:
        exp_config = json.load(rf)

    data = list()
    configs = selec_com.find_parameter_list(exp_config["algorithms"][0],
                                            params=sel_params)
    for config in configs:
        workload = Workload(selec_com.read_row_query(work_list, exp_config,
                                                        columns, type=""))
        connector.drop_hypo_indexes()

        algorithm = INDEX_SELECTION_ALGORITHMS[algo](
            connector, config["parameters"], process)

        if not process and not overhead:
            sel_info = ""
            indexes = algorithm.calculate_best_indexes(
                workload, overhead=overhead)
        else:
            indexes, sel_info = algorithm.calculate_best_indexes(
                workload, overhead=overhead)

        indexes = [str(ind) for ind in indexes]
        cols = [ind.split(",") for ind in indexes]
        cols = [list(map(lambda x: x.split(".")[-1], col)) for col in cols]
        indexes = [
            f"{ind.split('.')[0]}#{','.join(col)}" for ind, col in zip(indexes, cols)]

        no_cost, ind_cost = list(), list()
        total_no_cost, total_ind_cost = 0, 0
        for sql in work_list:
            no_cost_ = connector.get_ind_cost(sql, "")
            total_no_cost += no_cost_
            no_cost.append(no_cost_)

            ind_cost_ = connector.get_ind_cost(sql, indexes)
            total_ind_cost += ind_cost_
            ind_cost.append(ind_cost_)

        data.append({"config": config["parameters"],
                        "workload": work_list,
                        "indexes": indexes,
                        "no_cost": no_cost,
                        "total_no_cost": total_no_cost,
                        "ind_cost": ind_cost,
                        "total_ind_cost": total_ind_cost,
                        "sel_info": sel_info})

    return data


def build_db_diag_tool(config) -> Tool:
    tool = Tool(
        "Database Diagnosis",
        "Diagnose the bottlenecks of a database based on relevant metrics",
        name_for_model="db_diag",
        description_for_model="Plugin for diagnosing the bottlenecks of a database based on relevant metrics",
        logo_url="https://commons.wikimedia.org/wiki/File:Postgresql_elephant.svg",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )

    #URL_CURRENT_WEATHER= "http://api.weatherapi.com/v1/current.json"
    #URL_FORECAST_WEATHER = "http://api.weatherapi.com/v1/forecast.json"

    URL_PROMETHEUS = 'http://8.131.229.55:9090/'
    prometheus_metrics = {#"cpu_usage": "avg(rate(process_cpu_seconds_total{instance=\"172.27.58.65:9187\"}[5m]) * 1000)", 
                          "cpu_usage" : '(avg(irate(node_cpu_seconds_total{instance=~"172.27.58.65:9100",mode="user"}[1m]))) * 100',
                          "cpu_metrics": ["node_scrape_collector_duration_seconds{instance=\"172.27.58.65:9100\"}", "node_procs_running{instance=\"172.27.58.65:9100\"}", "node_procs_blocked{instance=\"172.27.58.65:9100\"}", "node_entropy_available_bits{instance=\"172.27.58.65:9100\"}", "node_load1{instance=\"172.27.58.65:9100\"}", "node_load5{instance=\"172.27.58.65:9100\"}", "node_load15{instance=\"172.27.58.65:9100\"}"], 
                          "memory_usage": "node_memory_MemTotal_bytes{instance=~\"172.27.58.65:9100\"} - (node_memory_Cached_bytes{instance=~\"172.27.58.65:9100\"} + node_memory_Buffers_bytes{instance=~\"172.27.58.65:9100\"} + node_memory_MemFree_bytes{instance=~\"172.27.58.65:9100\"})",
                          "memory_metrics": ["irate(node_disk_write_time_seconds_total{instance=~\"172.27.58.65:9100\"}[1m])", "node_memory_Inactive_anon_bytes{instance=\"172.27.58.65:9100\"}", "node_memory_MemFree_bytes{instance=\"172.27.58.65:9100\"}", "node_memory_Dirty_bytes{instance=\"172.27.58.65:9100\"}", "pg_stat_activity_count{datname=~\"(imdbload|postgres|sysbench|template0|template1|tpcc|tpch)\", instance=~\"172.27.58.65:9187\", state=\"active\"} !=0"],
                          "network_metrics": ["node_sockstat_TCP_tw{instance=\"172.27.58.65:9100\"}", "node_sockstat_TCP_orphan{instance=\"172.27.58.65:9100\"}"]}
    # "node_sockstat_TCP_tw{instance=\"172.27.58.65:9100\"}", 

    # load knowlege extractor
    knowledge_matcher = KnowledgeExtraction("/bmtools/tools/db_diag/root_causes_dbmind.jsonl")

    # load db settings
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    config = get_conf(script_dir + '/my_config.ini', 'postgresql')
    dbargs = DBArgs("postgresql", config=config)  # todo assign database name
    db = Database(dbargs, timeout=-1)

    server_config = get_conf(script_dir + '/my_config.ini', 'benchserver')

    monitoring_metrics = []
    with open(str(os.getcwd()) + "/bmtools/tools/db_diag/database_monitoring_metrics", 'r') as f:
        monitoring_metrics = f.read()
    monitoring_metrics = eval(monitoring_metrics)

    @tool.get("/obtain_start_and_end_time_of_anomaly")
    def obtain_start_and_end_time_of_anomaly():
        # 1691563950.0 1691564190.0
        # 1691570940.0 1691571120.0
        # 1691571630.0 1691571720.0
        # 1691463840.0 1691463990.0
        # 1691897340.0 1691897430.0

        return {"start_time": 1691897340, "end_time": 1691897430}

        '''
        If the anomaly period is recorded on the server side, you can use the following code to obtain the start and end time of the anomaly.q
        '''

        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        start_time = 0
        end_time = 0

        try:
            # Connect to the remote server
            ssh.connect(server_config["server_address"], username=server_config["username"], password=server_config["password"])

            # Create an SFTP client
            sftp = ssh.open_sftp()

            # Change to the remote directory
            sftp.chdir(server_config["remote_directory"])

            # Get a list of files in the directory
            files = sftp.listdir()

            required_file_name = ""
            required_tp = -1
            # Read the contents of each file
            for filename in files:
                remote_filepath = server_config["remote_directory"] + '/' + filename

                if "trigger_time_log" not in filename:
                    continue
                
                tp = filename.split("_")[0]
                
                if tp.isdigit():
                    tp = int(tp)
                    if required_tp < tp:
                        required_tp = tp
                        required_file_name = filename
                        
            file_content = sftp.open(server_config["remote_directory"] + '/' + required_file_name).read()
            file_content = file_content.decode()
            tps = file_content.split("\n")[0]
            start_time = tps.split(";")[0]
            end_time = tps.split(";")[1]

        finally:
            # Close the SFTP session and SSH connection
            sftp.close()
            ssh.close()

        return {"start_time": start_time, "end_time": end_time}

    @tool.get("/whether_is_abnormal_metric")
    def whether_is_abnormal_metric(start_time:int, end_time:int, metric_name : str="cpu_usage"):

        interval_time = 5
        metric_values = prometheus('api/v1/query_range', {'query': prometheus_metrics[metric_name], 'start': start_time, 'end': end_time, 'step': '3'})
        # prometheus('api/v1/query_range', {'query': '100 - (avg(irate(node_cpu_seconds_total{instance=~"172.27.58.65:9100",mode="idle"}[1m])) * 100)', 'start': '1684412385', 'end': '1684413285', 'step': '3'})
        # print(" === metric_values", metric_values)

        # pdb.set_trace()

        if metric_values["data"]["result"] != []:
            metric_values = metric_values["data"]["result"][0]["values"]
        else:
            raise Exception("No metric values found for the given time range")

        is_abnormal = detect_anomalies(np.array([float(value) for _, value in metric_values]))

        if is_abnormal:
            return "The metric is abnormal"
        else:
            return "The metric is normal"


    @tool.get("/cpu_diagnosis_agent")
    def cpu_diagnosis_agent(start_time : int, end_time : int):

        # live_tuples\n- dead_tuples\n- table_size

        cpu_metrics = prometheus_metrics["cpu_metrics"]
        cpu_metrics = cpu_metrics # + find_abnormal_metrics(start_time, end_time, monitoring_metrics, 'cpu')

        print("==== cpu_metrics", cpu_metrics)


        detailed_cpu_metrics = obtain_values_of_metrics(start_time, end_time, cpu_metrics)

        openai.api_key = os.environ["OPENAI_API_KEY"]

        db = Database(dbargs, timeout=-1)
        slow_queries = db.obtain_historical_slow_queries()

        slow_query_state = ""
        for i,query in enumerate(slow_queries):
            slow_query_state += str(i+1) + '. ' + str(query) + "\n"

        print(slow_query_state)

        docs_str = knowledge_matcher.match(detailed_cpu_metrics)

        prompt = """The CPU metric is abnormal. Then obtain the CPU relevant metric values from Prometheus: {}. The slow queries are:
        {}

Next output the analysis of potential causes of the high CPU usage based on the CPU relevant metric values,

Note: include the important slow queries in the output, but not all queries.
{}""".format(detailed_cpu_metrics, slow_query_state, docs_str)

        print(prompt)

        # pdb.set_trace()
        
        # response = openai.Completion.create(
        # model="text-davinci-003",
        # prompt=prompt,
        # temperature=0,
        # max_tokens=1000,
        # top_p=1.0,
        # frequency_penalty=0.0,
        # presence_penalty=0.0,
        # stop=["#", ";"]
        # )
        # output_text = response.choices[0].text.strip()

        # Set up the OpenAI GPT-3 model
        # model_engine = "gpt-3.5-turbo"

        # prompt_response = openai.ChatCompletion.create(
        #     engine="gpt-3.5-turbo",
        #     messages=[
        #         {"role": "assistant", "content": "The table schema is as follows: " + str(schema)},
        #         {"role": "user", "content": str(prompt)}
        #         ]
        # )
        # output_text = prompt_response['choices'][0]['message']['content']

        prompt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": str(prompt)}
            ]
        )

        output_analysis = prompt_response['choices'][0]['message']['content']

        # llm = CustomLLM()
        # output_analysis = llm(prompt)

        return {"diagnose": output_analysis, "knowledge": docs_str}

    @tool.get("/memory_diagnosis_agent")
    def memory_diagnosis_agent(start_time : int, end_time : int):

        memory_metrics = prometheus_metrics["memory_metrics"]

        memory_metrics = prometheus_metrics["memory_metrics"]
        memory_metrics = memory_metrics # + find_abnormal_metrics(start_time, end_time, monitoring_metrics, 'memory')

        detailed_memory_metrics = obtain_values_of_metrics(start_time, end_time, memory_metrics)

        # print with color red
        # print(colored("==== detailed_memory_metrics", "red"), detailed_memory_metrics)

        openai.api_key = os.environ["OPENAI_API_KEY"]

        db = Database(dbargs, timeout=-1)
        slow_queries = db.obtain_historical_slow_queries()

        slow_query_state = ""
        for i,query in enumerate(slow_queries):
            slow_query_state += str(i+1) + '. ' + str(query) + "\n"

        print(slow_query_state)
        
        # TODO: need a similarity match function to match the top-K examples
        # 1. get the categories of incoming metrics. Such as "The abnormal metrics include A, B, C, D"
        # 2. embedding the metrics
        # note: 这个metrics的embedding有可能预计算吗？如果metrics的种类（组合数）有限的话
        # 3. match the top-K examples(embedding)
        # note: 不用embedding如何有效的筛选出来与当前metrics最相关的example呢？可以枚举吗？比如如果我知道某一个example涉及到哪些metrics？
        #       该如何判断某一个metrics跟一段文本是相关的呢？能否用一个模型来判断一段文本涉及到哪些metrics呢？重新训练的话感觉需要很多样本才行
        #       能不能用关键词数量？

        docs_str = knowledge_matcher.match(detailed_memory_metrics)

        prompt = """The memory metric is abnormal. Then obtain the memory metric values from Prometheus: {}. The slow queries are:
        {}
        
Output the analysis of potential causes of the high memory usage based on the memory metric values and slow queries, e.g., 

{}

Note: include the important slow queries in the output.
""".format(detailed_memory_metrics, slow_query_state, docs_str)

        print(prompt)

        # response = openai.Completion.create(
        # model="text-davinci-003",
        # prompt=prompt,
        # temperature=0,
        # max_tokens=1000,
        # top_p=1.0,
        # frequency_penalty=0.0,
        # presence_penalty=0.0,
        # stop=["#", ";"]
        # )
        # output_text = response.choices[0].text.strip()

        # Set up the OpenAI GPT-3 model
        # model_engine = "gpt-3.5-turbo"

        # prompt_response = openai.ChatCompletion.create(
        #     engine="gpt-3.5-turbo",
        #     messages=[
        #         {"role": "assistant", "content": "The table schema is as follows: " + str(schema)},
        #         {"role": "user", "content": str(prompt)}
        #         ]
        # )
        # output_text = prompt_response['choices'][0]['message']['content']

        prompt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": str(prompt)}
            ]
        )

        output_analysis = prompt_response['choices'][0]['message']['content']

        # llm = CustomLLM()
        # output_analysis = llm(prompt)

        return {"diagnose": output_analysis, "knowledge": docs_str}


    @tool.get("/optimize_index_selection")
    def optimize_index_selection(start_time : int, end_time : int):
        """optimize_index_selection(start_time : int, end_time : int) returns the recommended index by running the algorithm 'Extend'. 
           This method uses a recursive algorithm that considers only a limited subset of index candidates.
           The method exploits structures and properties that are typical for real-world workloads and the performance of indexes.
           It identifies beneficial indexes and does not construct similar indexes.
           The recursion only realizes index selections/extensions with significant additional performance per size ratio.

           The following is an example:
           Thoughts: I will use the \\\'optimize_index_selection\\\' command to recommend the index for the given workload.
           Reasoning: I need to recommend the effective index for the given workload. I will use the \\\'optimize_index_selection\\\' command to get the index from 'Extend' and return the result.
           Plan: - Use the \\\'optimize_index_selection\\\' command to get the index. 
           Command: {"name": "optimize_index_selection", 
                     "args": {"workload": "SELECT A.col1 from A join B where A.col2 = B.col2 and B.col3 > 2 group by A.col1"}}
           Result: Command optimize_index_selection returned: "A#col2; B#col2,col3"
        """
        algo = "extend"
        sel_params = "parameters"
        process, overhead = True, True
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
        config = get_conf(script_dir + '/my_config.ini', 'postgresql')
        schema_file = script_dir + f"/optimization_tools/index_selection/selection_data/data_info/schema_job.json"
        workload_file = script_dir + f"/optimization_tools/index_selection/selection_data/data_info/job_templates.sql"

        tables, columns = selec_com.get_columns_from_schema(schema_file)

        # load db settings
        db_config = {}
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)

        config = get_conf(script_dir + '/my_config.ini', 'postgresql')
        db_config["postgresql"] = config
        connector = PostgresDatabaseConnector(db_config, autocommit=True)

        workload = []
        with open(workload_file, "r") as rf:
            for line in rf.readlines():
                workload.append(line.strip())

        indexes, no_cost, total_no_cost, \
        ind_cost, total_ind_cost, sel_info = get_index_result(algo, workload, connector,
                                                              columns, sel_params=sel_params,
                                                              process=process, overhead=overhead)

        pdb.set_trace()

        return f"The recommended indexes by 'Extend' are: {indexes}."

    return tool