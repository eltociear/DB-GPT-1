
from bmtools.tools.db_diag.anomaly_detection import prometheus
from bmtools.tools.db_diag.anomaly_detection import detect_anomalies
import numpy as np
import requests
import datetime


# anomalies
prometheus_metrics = ["avg(rate(process_cpu_seconds_total{instance=\"123.56.63.105:9187\"}[5m]) * 1000)", 
                      "node_load1{instance=\"123.56.63.105:9100\"}", 
                      "node_load5{instance=\"123.56.63.105:9100\"}", 
                      "node_load15{instance=\"123.56.63.105:9100\"}", 
                      "node_memory_MemTotal_bytes{instance=~\"123.56.63.105:9100\"} - (node_memory_Cached_bytes{instance=~\"123.56.63.105:9100\"} + node_memory_Buffers_bytes{instance=~\"123.56.63.105:9100\"} + node_memory_MemFree_bytes{instance=~\"123.56.63.105:9100\"})", "pg_stat_activity_count{datname=~\"(imdbload|postgres|sysbench|template0|template1|tpcc|tpch)\", instance=~\"123.56.63.105:9187\", state=\"active\"} !=0"]

def whether_is_abnormal_metric(start_time:int, end_time:int, metric_name : str="cpu_usage"):

    interval_time = 5
    print(metric_name)
    metric_values = prometheus('api/v1/query_range', {'query': metric_name, 'start': start_time-interval_time*60, 'end': end_time+interval_time*60, 'step': '3'})
    # prometheus('api/v1/query_range', {'query': '100 - (avg(irate(node_cpu_seconds_total{instance=~"123.56.63.105:9100",mode="idle"}[1m])) * 100)', 'start': '1684412385', 'end': '1684413285', 'step': '3'})
    print(" === metric_values", metric_values)

    if metric_values["data"]["result"] != []:
        metric_values = metric_values["data"]["result"][0]["values"]
    else:
        raise Exception("No metric values found for the given time range")

    is_abnormal = detect_anomalies(np.array([float(value) for _, value in metric_values]))

    return is_abnormal

def get_abnormal_metric():
    # metric list; time range; anomaly detection

    anomaly_metrics = []
    print(" ===== {} prometheus_metrics: ".format(len(prometheus_metrics)))
    for metric in prometheus_metrics:

        if whether_is_abnormal_metric(1685031891, 1685032125, metric) == True:
            anomaly_metrics.append(metric)
            print(" ===== abnormal: ", metric)

    return anomaly_metrics


if __name__ == "__main__":

    #get_abnormal_metric()

    #res = prometheus('api/v1/query_range', {'query': "{__name__!=""}", 'start': 1684412385, 'end': 1684413285, 'step': '3'})

    # database_monitoring_metrics  
    with open("database_monitoring_metrics", "r") as f:
        data = f.read()

    data = eval(data)

    reserved_metrics = []
    interval_time = 5
    for metric in data:

        start_timestamp_str = "2023-05-31 21:28:00"
        dt = datetime.datetime.strptime(start_timestamp_str, "%Y-%m-%d %H:%M:%S")
        timestamp = dt.timestamp()
        start_time = timestamp

        end_timestamp_str = "2023-05-31 22:24:00"
        dt = datetime.datetime.strptime(end_timestamp_str, "%Y-%m-%d %H:%M:%S")
        timestamp = dt.timestamp()
        end_time = timestamp


        metric_values = prometheus('api/v1/query_range', {'query': metric+"{instance=\"172.27.58.65:9100\"}", 'start': start_time, 'end': end_time, 'step': '3'})
        
        if metric_values["data"]["result"] != []:
            metric_values = metric_values["data"]["result"][0]["values"]

            if detect_anomalies(np.array([float(value) for _, value in metric_values])):
                reserved_metrics.append(metric+"{instance=\"172.27.58.65:9100\"}")
                print(metric+"{instance=\"172.27.58.65:9100\"}")

    print(reserved_metrics)
    print(len(reserved_metrics))

