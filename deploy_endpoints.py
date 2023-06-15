from utils import create_ec2,create_security_group, create_instance_profile

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


def main():
    security_group = create_security_group('shahara', 80)

    # Be aware that create_ec2() always uses 'us-east-1' region, so it might affect image name.
    endpoint_a = create_ec2(security_group, 'ami-02396cdd13e9a1257', 't2.micro',
                            ENDPOINT_USER_DATA % security_group, instance_name="endpoint_a",
                            instance_profile=True)
    print(endpoint_a)

    endpoint_b = create_ec2(security_group, 'ami-02396cdd13e9a1257', 't2.micro',
                            ENDPOINT_USER_DATA % security_group, instance_name="endpoint_b",
                            instance_profile=True)
    print(endpoint_b)


if __name__ == '__main__':
    main()
