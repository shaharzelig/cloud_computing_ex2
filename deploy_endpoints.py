from utils import create_ec2,create_security_group

ENDPOINT_USER_DATA = '''#!/bin/bash
        sudo yum update -y
        sudo yum install -y python3
        sudo yum install -y python3-pip
        sudo yum install -y git
        git clone https://github.com/shaharzelig/cloud_computing_ex2.git
        cd cloud_computing_ex2
        sudo chmod 777 app.py
        sudo pip3 install -r requirements.txt
        sudo python3 app.py'''

def main():
    security_group = create_security_group('workers', 80)

    # Be aware that create_ec2() always uses 'us-east-1' region, so it might affect image name.
    endpoint_a = create_ec2(security_group, 'ami-02396cdd13e9a1257', 't2.micro', ENDPOINT_USER_DATA)
    endpoint_a = create_ec2(security_group, 'ami-02396cdd13e9a1257', 't2.micro', ENDPOINT_USER_DATA)



if __name__ == '__main__':
    main()