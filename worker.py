#!flask/bin/python
import os
import sys

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


def main(args):
    managers_urls = args.split(",")
    while True:
        for manager_url in managers_urls:
            response = requests.get(manager_url + '/getwork')
            if response.status_code == 400:
                bye()

            if response.status_code == 204: # No content. No work to do.
                continue

            buffer = response.content
            iterations = int(response.headers.get('X-Iterations'))
            result = doWork(buffer, iterations)

            # Publish result to everyone
            for manager_url in managers_urls:
                requests.post(manager_url + '/pushResult', data=result)


if __name__ == '__main__':
    main(sys.argv)