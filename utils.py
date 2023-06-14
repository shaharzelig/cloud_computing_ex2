import boto3
import ipaddress

session = boto3.Session() # add support of keys
ec2_client = session.client('ec2', region_name='us-east-1')


def create_ec2(security_group_id, image_id, instance_type, user_data, instance_name, die_on_shutdown=False, wait=True):
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
        KeyName='shahartest'   # TODO: delete
    )

    if wait:
        ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance['Instances'][0]['InstanceId']])
    return instance


def create_security_group(security_group_name, endpoint_port):
    security_group = ec2_client.create_security_group(GroupName=security_group_name,
                                                      Description='Port %d from outside.' % endpoint_port)
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

if __name__ == '__main__':
    print(get_available_private_ipv4()[0])
    print(create_security_group('shahar-teststsertr', 1234))