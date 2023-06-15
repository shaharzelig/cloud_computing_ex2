#!flask/bin/python
import os
import sys
import itertools
import time

import requests
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    filename='worker.log')
logger = logging.getLogger(__name__)
TIME_TO_SLEEP_BETWEEN_TASK_REQUESTS = 1


def doWork(buffer, iterations):
    import hashlib
    output = hashlib.sha512(buffer).digest()
    for i in range(iterations - 2):
        output = hashlib.sha512(output).digest()
    return hashlib.sha512(output).hexdigest()


def bye():
    while True:
        # os.system("sudo shutdown -h now")
        continue

def send_response_to_manager(manager_ip, response):
    logger.info("Sending response %s to %s" % (response, manager_ip))
    data = {"result": response}
    requests.post("http://" + manager_ip + '/pushResult', json=data)


def get_task(manager_ip):
    time.sleep(TIME_TO_SLEEP_BETWEEN_TASK_REQUESTS)
    logger.info("Getting task from %s" % manager_ip)
    response = requests.get("http://" + manager_ip + '/getwork')

    if response.status_code == 400:
        logger.warning("Got 400 from %s, shutting down" % manager_ip)
        bye()

    if response.status_code == 204: # No content. No work to do.
        logger.info("Got 204 from %s, no work to do" % manager_ip)
        return

    buffer = response.content
    try:
        iterations = int(response.headers.get('X-Iterations'))

    # A bad response, let's not stop everything because of that.
    except Exception as e:
        return

    return buffer, iterations

def get_managers(manager_ip):
    r = requests.get("http://" + manager_ip + '/get_managers')
    return r.json()['managers']

def main(manager_ip):
    while True:
        try:
            managers = get_managers(manager_ip)

            for manager_ip in managers:
                buffer, iterations = get_task(manager_ip)
                result = doWork(buffer, iterations)
                send_response_to_manager(manager_ip, result)

        except Exception as e:
            # Nothing will kill me!
            continue




if __name__ == '__main__':
    main(sys.argv[1])