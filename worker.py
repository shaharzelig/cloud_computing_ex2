#!flask/bin/python
import os
import sys
import itertools
import requests

def doWork(buffer, iterations):
    import hashlib
    output = hashlib.sha512(buffer).digest()
    for i in range(iterations - 1):
        output = hashlib.sha512(output).digest()
    return output


def bye():
    while True:
        os.system("sudo shutdown -h now")

def send_response_to_all_managers(managers, response):
    for manager_url in managers:
        requests.post(manager_url + '/pushResult', data=response)


def get_task(manager_urls):
    for manager_url in itertools.cycle(manager_urls):
        response = requests.get(manager_url + '/getwork')

        if response.status_code == 400:
            bye()

        if response.status_code == 204: # No content. No work to do.
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