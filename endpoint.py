#!flask/bin/python
import time
import queue
import boto3 as boto3
import flask
import requests
from flask import Flask, jsonify, abort, request
import argparse
from collections import deque
from utils import create_ec2

app = Flask(__name__)
RESULTS = queue.Queue()
JOBS = queue.Queue()
BAD_THREASHOLD_BEFORE_SPAWN = 1
GOOD_THREASHOLD_BEFORE_KILL = 0.1
NUMBER_OF_INTERVALS_TO_KEEP = 10
MANAGER_INTERVAL = 10
SECURITY_GROUP = ""

get_work_history = deque(maxlen=NUMBER_OF_INTERVALS_TO_KEEP)

WORKERS = []
killing_list = []
SIBLINGS = []

def get_results(n):
    return RESULTS.get(n)

WORKER_USER_DATA = '''#!/bin/bash
            sudo yum update -y
            sudo yum install -y python3
            sudo yum install -y python3-pip
            sudo yum install -y git
            git clone https://github.com/shaharzelig/cloud_computing_ex2.git
            cd cloud_computing_ex2
            sudo chmod 777 worker.py
            sudo pip3 install -r requirements.txt
            sudo python3 worker.py %s'''


def spawn_worker():
    workers_security_group = ""
    WORKERS.append(create_ec2(workers_security_group, 'ami-02396cdd13e9a1257', 't2.micro',
                              WORKER_USER_DATA % ",".join(SIBLINGS)))


def kill_worker():
    worker_to_kill = WORKERS.pop()
    ipv4 = worker_to_kill['Instances'][0]['PrivateIpAddress']
    killing_list.append(ipv4)


def compute_avg():
    history = list(get_work_history)
    if not history:
        return 0

    history.sort()
    intervals = [history[i] - history[i - 1] for i in range(1, len(history))]
    return sum(intervals) / len(intervals)


def workers_manager():
    while True:
        time.sleep(MANAGER_INTERVAL)
        avg = compute_avg()
        if avg > BAD_THREASHOLD_BEFORE_SPAWN:
            spawn_worker()  # This method should block until new worker is spawned and working.

        elif avg < GOOD_THREASHOLD_BEFORE_KILL:
            kill_worker()  # This method should block until worker is killed.

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = int(request.args.get('iterations'))
    if not iterations:
        return abort(400, 'iterations must be provided')
    JOBS.put_nowait((request.data, iterations))
    return 200


@app.route('/getwork', methods=['GET'])
def get_work():
    ipv4 = request.remote_addr
    if ipv4 in killing_list:        # Consider use a lock to use the list.
        killing_list.remove(ipv4)
        return abort(400, 'Dear worker, please do harakiri')

    now = time.time()
    get_work_history.append(now)

    job = JOBS.get()
    resp = flask.Response(job[0])
    resp.headers['X-Iterations'] = job[1]
    return resp

@app.route('/pushResult', methods=['POST'])
def push_result(result):
    RESULTS.put_nowait(result)

@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    try:
        top = int(request.args.get('top'))

    # not just ValueError.
    except Exception:
        return abort(400, 'top must be a valid integer')

    results = get_results(top)
    if len(results) < top:
        for sibling in SIBLINGS:
            try:
                r = requests.post('http://{}/pullCompleted?top={}'.format(sibling, top - len(results)))
                results.extend(r.json())

            except Exception:
                pass

    return "\n".join(results)


@app.route('/register_sibling', methods=['POST'])
def register_sibling():
    sibling = request.args.get('sibling')
    if not sibling:
        return abort(400, 'sibling must be provided')
    SIBLINGS.append(sibling)
    return 'ok'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--security-group', required=True)
    args = parser.parse_args()
    if not args.security_group:
        print('security-group must be provided')
        exit(1)
    SECURITY_GROUP = args.security_group
    app.run(host='0.0.0.0', port=80)