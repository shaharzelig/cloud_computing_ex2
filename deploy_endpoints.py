import time
import requests
from utils import create_ec2, create_security_group, is_remote_tcp_port_open

ENDPOINT_USER_DATA = '''#!/bin/bash
        sudo yum update -y
        sudo yum install -y python3
        sudo yum install -y python3-pip
        sudo yum install -y git
        git clone https://github.com/shaharzelig/cloud_computing_ex2.git
        cd cloud_computing_ex2
        sudo chmod 777 endpoint.py
        sudo pip3 install --ignore-installed -r requirements.txt
        sudo python3 endpoint.py --security-group %s'''


def block_until_ports_are_open(sockets):
    closed_sockets = [socket for socket in sockets if not is_remote_tcp_port_open(socket[0], socket[1])]
    while len(closed_sockets) > 0:
        closed_sockets = [socket for socket in sockets if not is_remote_tcp_port_open(socket[0], socket[1])]
        time.sleep(5)


def create_endpoint(name, security_group):
    endpoint_a = create_ec2(security_group, 'ami-02396cdd13e9a1257', 't2.micro',
                            ENDPOINT_USER_DATA % security_group, instance_name=name,
                            instance_profile=True)
    ip_a = endpoint_a["PublicIpAddress"]
    ip_a_private = endpoint_a["PrivateIpAddress"]

    return ip_a, ip_a_private


def make_them_siblings(public_ip, private_ip):
    url = "http://{}/register_sibling?sibling={}".format(public_ip, private_ip)
    print("Registering sibling: " + url + private_ip)
    r = requests.post(url)


def main():
    security_group = create_security_group('shahara', 80)

    endpoint_a_public_ip, endpoint_a_private_ip = create_endpoint("endpoint_a", security_group)
    endpoint_b_public_ip, endpoint_b_private_ip = create_endpoint("endpoint_b", security_group)


    print("Waiting for ports")
    block_until_ports_are_open([(endpoint_a_public_ip, 80), (endpoint_b_public_ip, 80)])

    print("public address a: " + endpoint_a_public_ip)
    print("private address a: " + endpoint_a_private_ip)
    print("public address b: " + endpoint_b_public_ip)
    print("private address b: " + endpoint_b_private_ip)

    print("Make them siblings")
    make_them_siblings(endpoint_a_public_ip, endpoint_b_private_ip)
    make_them_siblings(endpoint_b_public_ip, endpoint_a_private_ip)


if __name__ == '__main__':
    main()
