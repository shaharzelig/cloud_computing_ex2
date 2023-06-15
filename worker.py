#!flask/bin/python
import os
import sys
import itertools
import time

import requests
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    filename='/var/log/worker.log')
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

def send_response_to_all_managers(managers, response):
    for manager_url in managers:
        logger.info("Sending response %s to %s" % (response, manager_url))
        data = {"result": response}
        requests.post("http://" + manager_url + '/pushResult',json=data)


def get_task(manager_urls):
    for manager_url in itertools.cycle(manager_urls):
        time.sleep(TIME_TO_SLEEP_BETWEEN_TASK_REQUESTS)
        logger.info("Getting task from %s" % manager_url)
        response = requests.get("http://" + manager_url + '/getwork')

        if response.status_code == 400:
            logger.warning("Got 400 from %s, shutting down" % manager_url)
            bye()

        if response.status_code == 204: # No content. No work to do.
            logger.info("Got 204 from %s, no work to do" % manager_url)
            continue

        buffer = response.content
        try:
            iterations = int(response.headers.get('X-Iterations'))

        # A bad response, let's not stop everything because of that.
        except Exception as e:
            continue

        yield buffer, iterations


def main(args):
    for buffer, iterations in get_task(args):
        result = doWork(buffer, iterations)

        # Publish result to everyone
        send_response_to_all_managers(args, result)


if __name__ == '__main__':
    main(sys.argv[1:])