import boto3

session = boto3.Session() # add support of keys
ec2_client = session.client('ec2', region_name='us-east-1')


def create_ec2(security_group_id, image_id, instance_type, user_data, die_on_shutdown=False, wait=True):
    instance = ec2_client.create_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        SecurityGroupIds=[security_group_id],
        UserData=user_data,
        InstanceInitiatedShutdownBehavior='terminate' if die_on_shutdown else 'stop'
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
            }
        ]
    )

    return security_group['GroupId']