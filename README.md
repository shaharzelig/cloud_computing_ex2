# cloud_computing_ex2

Usage

Teh script deploy_endpoints.py deploys 2 managers. It will print to stdout their IP addresses.
This script assume AWS access keys details are configured in the system to the default profile (with aws configure).
AWS resources created by this script: EC2 instance, role, instance profile, security group.
This script waits for port 80 to be open in each of the instances.
Note: execution might take few minutes.
```
USAGE:
python.exe deploy_endpoints.py 
Creating ec2 instance endpoint_a
Creating instance profile ....
Creating role ec2-admin
Role exists
Adding role ec2-admin to instance profile instance-profile-...
executing run_instances
Waiting for instance to be running
Created ec2 instance endpoint_a
Creating ec2 instance endpoint_b
Creating instance profile instance-profile-...
Creating role ec2-admin
Role exists
Adding role ec2-admin to instance profile instance-profile-...
executing run_instances
Waiting for instance to be running
Created ec2 instance endpoint_b
Waiting for ports
public address a: ...
private address a: ...
public address b: ...
private address b: ...
Make them siblings
Registring sibling: http://.../register_sibling?sibling=...
Registring sibling: http://.../register_sibling?sibling=...
Registring sibling: http://.../register_sibling?sibling=...
Registring sibling: http://.../register_sibling?sibling=...
```

For endpoint operations:
```
curl -X POST http://<manager's public ip>/pullCompleted?top=100
curl -X PUT http://<manager's public ip>/enqueue?iterations=50
curl -X POST http://<manager's public ip>/register_sibling?sibling=<private ip of the sibling>
```
 Note:
 Registering a sibling has 2 impacts:
* The manager will ask for the sibling's results if needed.
* The workers that are being spawned by this manager will know its sibling, and will ask it for tasks.



Failure Modes
There several options for failures.
1. AWS region
The deployment (e.g. the image we use for the EC2) is hardcoded for us-east-1, so if there are problems in this region (might happen...) the system will not work.
2. AWS Instance Profile Creation
 The system waits for an instance profile in AWS to be ready for registration WAIT_FOR_INSTANCE_PROFILE=10 seconds.
If it will take longer, and wait funciton will return early, there will be a problem with creating this ec2 - **undefined behaviour**.
3. No retries mechanism
In most cases, the system does not retry upon failure. This means that if something will not work as expected (e.g. AWS networking/compute issues), **the behaviour is undefined.**
4. Existing of a built-in policy.
The system assumes the existance of the built-in policy AmazonEC2FullAcess. If there will be a special case, where this policy does not live in the account, the creation of the managers will fail.
5. The worker crashes
If a worker crashes, and it is not asking for task, it's manager will not tell it to die and therefore it **will not be reduced from the workers quota**. Means that if a worker dies independantly, without the order of the manager, it will keep occupie workers quota.
In addition, if a worker crashes, and did not respond to a task, the data is lost and cannot be retrieved.
6. Crashes of the managers
If one of the managers crashes, the task in its queue are lost and could not be retrieved. In addition, workers that are doing a task given by this manager, will send it back to it, and therefore the result is lost and could not be retrieved.
Moreover, when a manager dies, the workers that it spawned could get killed by other manager. Therefor they will exist until manually, terminated.
7. Data persistence
None of the tasks data is stored on disk, and therefore upon shutdown this data will be lost and could not be retrieved.
8. Randomness collisions
A part of the name of several AWS resources is a random string (guid4). If there will be a collision (very unlikely), 
9. the system will not work as expected.