#!flask/bin/python
import threading
import time
import queue
import boto3 as boto3
import flask
import requests
from flask import Flask, jsonify, abort, request
import argparse
from collections import deque
from utils import create_ec2
import logging
app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    filename='manager.log')

RESULTS = queue.Queue()
JOBS = queue.Queue()
BAD_THREASHOLD_BEFORE_SPAWN = 1
GOOD_THREASHOLD_BEFORE_KILL = 0.1
NUMBER_OF_INTERVALS_TO_KEEP = 10
MANAGER_INTERVAL = 10
SECURITY_GROUP = None

MIN_NUMBER_OF_WORKERS = 2
MAX_NUMBER_OF_WORKERS = 10

get_work_history = deque(maxlen=NUMBER_OF_INTERVALS_TO_KEEP)

WORKERS = []
killing_list = []
SIBLINGS = []


def get_results(n):
    results_to_return = []
    while not RESULTS.empty() and len(results_to_return) < n:
        results_to_return.append(RESULTS.get_nowait())
    app.logger.info("Got %d results" % len(results_to_return))
    return results_to_return


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
    app.logger.info("Spawning new worker")
    if len(WORKERS) >= MAX_NUMBER_OF_WORKERS:
        app.logger.info("Can't spawn more workers, reached max number of workers %d" %
                        MAX_NUMBER_OF_WORKERS)
        return

    WORKERS.append(create_ec2(SECURITY_GROUP, 'ami-02396cdd13e9a1257', 't2.micro',
                              WORKER_USER_DATA % ",".join(SIBLINGS), instance_name="worker"))


def kill_worker():
    if len(WORKERS) <= MIN_NUMBER_OF_WORKERS:
        app.logger.info("Can't kill more workers, reached min number of workers %d" %
                        MIN_NUMBER_OF_WORKERS)
        return
    app.logger.info("Killing worker")
    worker_to_kill = WORKERS.pop()
    ipv4 = worker_to_kill['Instances'][0]['PrivateIpAddress']
    killing_list.append(ipv4)


def compute_avg():
    history = list(get_work_history)
    if len(history) < 2:
        return 0

    history.sort()
    intervals = [history[i] - history[i - 1] for i in range(1, len(history))]
    return sum(intervals) / len(intervals)


def workers_manager():
    app.logger.info("Starting workers manager")
    while True:
        time.sleep(MANAGER_INTERVAL)
        app.logger.info("Currently having %d workers" % len(WORKERS))
        app.logger.info("Checking if need to spawn or kill workers")
        avg = compute_avg()
        if len(WORKERS) < MIN_NUMBER_OF_WORKERS:
            app.logger.info("Not enough workers (existing %d, min %d), spawning new worker"
                            % (len(WORKERS), MIN_NUMBER_OF_WORKERS))
            spawn_worker()

        elif avg > BAD_THREASHOLD_BEFORE_SPAWN:
            spawn_worker()  # This method should block until new worker is spawned and working.

        elif avg < GOOD_THREASHOLD_BEFORE_KILL:
            kill_worker()  # This method should block until worker is killed.

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    try:
        iterations = int(request.args.get('iterations'))
    except:
        return abort(400, 'iterations must be provided')
    JOBS.put_nowait((request.data, iterations))
    return jsonify({"status": "success"}), 200


@app.route('/getwork', methods=['GET'])
def get_work():
    ipv4 = request.remote_addr
    if ipv4 in killing_list:        # Consider use a lock to use the list.
        killing_list.remove(ipv4)
        return abort(400, 'Dear worker, please do harakiri')

    now = time.time()
    get_work_history.append(now)

    if JOBS.empty():
        return jsonify({"status": "no jobs"}), 204

    job = JOBS.get()
    resp = flask.Response(job[0])
    resp.headers['X-Iterations'] = job[1]
    return resp, 200

@app.route('/pushResult', methods=['POST'])
def push_result():
    result_json = request.get_json()
    if "result" not in result_json.keys():
        return abort(400, 'result must be provided')

    app.logger.info("Got result %s" % result_json)
    result = result_json["result"]
    RESULTS.put_nowait(result)
    return jsonify({"status": "success"}), 200

@app.route('/pullCompleted', methods=['POST'])
def pull_completed():
    try:
        top = int(request.args.get('top'))

    # not just ValueError.
    except Exception:
        app.logger.warning("Got invalid top for pullCompleted")
        return abort(400, 'top must be a valid integer')

    results = get_results(top)

    if len(results) < top:
        app.logger.info("Not enough results (got %d, top=%d), asking siblings" % (len(results), top))
        for sibling in SIBLINGS:
            app.logger.info("Asking sibling %s" % sibling)
            try:
                r = requests.post('http://{}/pullCompleted?top={}'.format(sibling, top - len(results)))

                app.logger.info("Adding %s 's results")
                results += r.json()["results"]

            except Exception:
                app.logger.warning("Failed to get results from sibling %s" % sibling)
                continue

    return jsonify({"results": results}), 200


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
    t = threading.Thread(target=workers_manager)
    t.start()
    app.run(host='0.0.0.0', port=80)
