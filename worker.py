#!flask/bin/python
import os
import time

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


def main(manager_url):
    while True:
        response = requests.get(manager_url + '/getwork')
        if response.status_code == 400:
            bye()

        buffer = response.content
        iterations = int(response.headers.get('X-Iterations'))
        requests.post(manager_url + '/pushResult', data=doWork(buffer, iterations))


if __name__ == '__main__':
    main()
