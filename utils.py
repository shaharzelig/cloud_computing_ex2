import json
import socket
import time
import uuid

import boto3
import ipaddress

session = boto3.Session() # add support of keys
ec2_client = session.client('ec2', region_name='us-east-1')
iam_client = session.client("iam")

INSTANCE_PROFILE_NAME = "shahar_instance_profile5"
EC2_ADMIN = "ec2-admin"
WAIT_FOR_INSTANCE_PROFILE = 10
TIME_TO_SLEEP_BETWEEN_SYNS = 5

def create_ec2(security_group_id, image_id, instance_type, user_data, instance_name,
               instance_profile=False,
               die_on_shutdown=False, check_for_remote_port=None):

    print("Creating ec2 instance %s" % instance_name)
    if instance_profile:
        instance_profile_name = "instance-profile-" + uuid.uuid4().hex
        create_instance_profile(instance_profile_name)

    time.sleep(WAIT_FOR_INSTANCE_PROFILE)
    instance = ec2_client.run_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        SecurityGroupIds=[security_group_id],
        UserData=user_data,
        InstanceInitiatedShutdownBehavior='terminate' if die_on_shutdown else 'stop',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ],
        KeyName='shahartest',   # TODO: delete
        IamInstanceProfile={"Name": instance_profile_name} if instance_profile else {}
    )

    ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance['Instances'][0]['InstanceId']])
    print("Created ec2 instance %s" % instance_name)
    instance = ec2_client.describe_instances(InstanceIds=[instance['Instances'][0]['InstanceId']])
    instance = instance['Reservations'][0]['Instances'][0]
    if check_for_remote_port:
        print("Waiting for port %d to be open" % check_for_remote_port)

        while not is_remote_tcp_port_open(instance['PublicIpAddress'], check_for_remote_port):
            time.sleep(TIME_TO_SLEEP_BETWEEN_SYNS)

        print("Port %d is open" % check_for_remote_port)
    return instance


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def is_remote_tcp_port_open(remote_addr, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((remote_addr, port))
    sock.close()
    return result == 0


def create_security_group(security_group_name, endpoint_port):
    sec_group_names = [sec_group['GroupName'] for sec_group in ec2_client.describe_security_groups()['SecurityGroups']]
    if security_group_name not in sec_group_names:
        security_group = ec2_client.create_security_group(GroupName=security_group_name,
                                                      Description='Port %d from outside.' % endpoint_port)
    else:
        security_group = ec2_client.describe_security_groups(GroupNames=[security_group_name])['SecurityGroups'][0]
        return security_group['GroupId']

    ec2_client.authorize_security_group_ingress(GroupId=security_group['GroupId'], IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': endpoint_port,
                'ToPort': endpoint_port,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
        {
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }
        ]
    )

    return security_group['GroupId']

def get_available_private_ipv4():
    # Retrieve the default VPC ID
    response = ec2_client.describe_vpcs(
        Filters=[
            {
                'Name': 'isDefault',
                'Values': ['true']
            }
        ]
    )
    vpc_id = response['Vpcs'][0]['VpcId']

    # Retrieve the list of existing private IP addresses in the default VPC
    response = ec2_client.describe_network_interfaces(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [vpc_id]
            },
            {
                'Name': 'private-ip-address',
                'Values': ['!']
            }
        ]
    )
    existing_ips = set()
    for interface in response['NetworkInterfaces']:
        existing_ips.add(interface['PrivateIpAddress'])

    # Find an available private IP address in the default VPC
    ip_range = '172.31.0.0/16'  # Specify the IP range of the default VPC
    all_ips = ipaddress.IPv4Network(ip_range)
    return [str(ip) for ip in all_ips.hosts() if str(ip) not in existing_ips]

def create_ec2_admin_role():
    print("Creating role %s" % EC2_ADMIN)
    roles = iam_client.list_roles()
    if any([role["RoleName"] == EC2_ADMIN for role in roles["Roles"]]):
        print("Role exists")
        return

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    print("Creating role and attaching it AmazonEC2FullAcess policy")
    response = iam_client.create_role(
        RoleName=EC2_ADMIN,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description='Role for EC2 instances to create other instances'
    )

    # Attach necessary permissions to the role
    response = iam_client.attach_role_policy(
        RoleName=EC2_ADMIN,
        PolicyArn='arn:aws:iam::aws:policy/AmazonEC2FullAccess'
    )


def create_instance_profile(instance_profile_name):
    print("Creating instance profile %s" % instance_profile_name)
    instance_profiles = iam_client.list_instance_profiles()
    if not any([ip["InstanceProfileName"] == instance_profile_name for ip in instance_profiles['InstanceProfiles']]):
        iam_client.create_instance_profile(InstanceProfileName=instance_profile_name)
        iam_client.get_waiter('instance_profile_exists').wait(InstanceProfileName=instance_profile_name)

    create_ec2_admin_role()

    print("Adding role %s to instance profile %s" % (EC2_ADMIN, instance_profile_name))
    iam_client.add_role_to_instance_profile(InstanceProfileName=instance_profile_name,
                                            RoleName=EC2_ADMIN)


if __name__ == '__main__':
    print(get_available_private_ipv4()[0])
    print(create_security_group('shahar-teststsertr', 1234))