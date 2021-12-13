#!/usr/bin/env python
import datetime
import time
import json
import requests
import os
import sys

# ElasticSearch Cluster to Monitor
elasticServer = os.environ.get('ES_METRICS_CLUSTER_URL', 'http://server1:9200')
interval = int(os.environ.get('ES_METRICS_INTERVAL', '60'))

# ElasticSearch Cluster to Send Metrics
elasticIndex = os.environ.get('ES_METRICS_INDEX_NAME', 'elasticsearch_metrics')
elasticMonitoringCluster = os.environ.get(
    'ES_METRICS_MONITORING_CLUSTER_URL', 'http://server2:9200')


def fetch_clusterhealth():
    try:
        utc_datetime = datetime.datetime.utcnow()
        endpoint = "/_cluster/health"
        response = requests.get(elasticServer + endpoint)
        data = response.json()
        cluster_name = data['cluster_name']
        data['@timestamp'] = str(
            utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
        if data['status'] == 'green':
            data['status_code'] = 0
        elif data['status'] == 'yellow':
            data['status_code'] = 1
        elif data['status'] == 'red':
            data['status_code'] = 2
        post_data(data)
        return cluster_name
    except IOError as err:
        print("IOError: Maybe can't connect to elasticsearch.")
        cluster_name = "unknown"
        return cluster_name


def fetch_clusterstats():
    utc_datetime = datetime.datetime.utcnow()
    endpoint = "/_cluster/stats"
    response = requests.get(elasticServer + endpoint)
    data = response.json()
    data['@timestamp'] = str(
        utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
    post_data(data)


def fetch_nodestats(cluster_name):
    utc_datetime = datetime.datetime.utcnow()
    endpoint = "/_cat/nodes?v&h=n"
    response = requests.get(elasticServer + endpoint)
    response = response.content.decode("utf-8")
    nodes = response[1:-1].strip().split('\n')
    for node in nodes:
        endpoint = "/_nodes/%s/stats" % node.rstrip()
        response = requests.get(elasticServer + endpoint)
        data = response.json()
        nodeID = list(data['nodes'].keys())
        try:
            data['nodes'][nodeID[0]]['@timestamp'] = str(
                utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
            data['nodes'][nodeID[0]]['cluster_name'] = cluster_name
            newdata = data['nodes'][nodeID[0]]
            post_data(newdata)
        except Exception as ex:
            print("error on identify node: ", ex)
            continue


def fetch_indexstats(cluster_name):
    utc_datetime = datetime.datetime.utcnow()
    endpoint = "/_stats"
    response = requests.get(elasticServer + endpoint)
    data = response.json()
    data['_all']['@timestamp'] = str(
        utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
    data['_all']['cluster_name'] = cluster_name
    post_data(data['_all'])


def post_data(data):
    utc_datetime = datetime.datetime.utcnow()
    url_parameters = {'cluster': elasticMonitoringCluster, 'index': elasticIndex,
                      'index_period': utc_datetime.strftime("%Y.%m.%d"), }
    url = "%(cluster)s/%(index)s-%(index_period)s/message" % url_parameters
    headers = {'content-type': 'application/json'}
    try:
        requests.post(url, headers=headers, data=json.dumps(data))
    except Exception as e:
        print("Error:  {0}".format(str(e)))


def main():
    cluster_name = fetch_clusterhealth()
    if cluster_name != "unknown":
        fetch_clusterstats()
        fetch_nodestats(cluster_name)
        fetch_indexstats(cluster_name)


if __name__ == '__main__':
    try:
        print("start")
        next = 0
        while True:
            if time.time() >= next:
                next = time.time() + interval
                now = time.time()
                main()
                elapsed = time.time() - now
                print("Total Elapsed Time: %s" % elapsed)
                timeDiff = next - time.time()

                # Check timediff , if timediff >=0 sleep, if < 0 send metrics to es
                if timeDiff >= 0:
                    time.sleep(timeDiff)

    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
