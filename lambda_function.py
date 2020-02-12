""" Lambda to launch ec2-instances """
import boto3
import latest_ami
from botocore.exceptions import ClientError

REGION = 'us-east-1'  # region to launch instance.
AMI = latest_ami.get_newest_image(REGION)['ImageId']
KEYPAIR = 'AlehouseWebAndMailServerKeypair'
SECURITY_GROUP = 'TeslaCam_SecurityGroup'
S3BUCKET = 'org.trashcan.teslacam'
INSTANCE_PROFILE_NAME = 'Teslacam_EC2_Role'
TEST_LOC = '/SentryClips/2020-02-11_18-32-08/'
# matching region/setup amazon linux ami, as per:
# https://aws.amazon.com/amazon-linux-ami/
INSTANCE_TYPE = 'c5d.large'  # instance type to launch.

ec2 = boto3.client('ec2', region_name=REGION)


def lambda_to_ec2(event, context):
    """ Lambda handler taking [message] and creating a httpd instance with an echo. """
    message = event['message']

    # bash script to run:
    #  - update and install httpd (a webserver)
    #  - start the webserver
    #  - create a webpage with the provided message.
    #  - set to shutdown the instance in 5 minutes.
    init_script = f"""#!/bin/bash
yum install -y python3
yum install -y python3-devel
yum install -y gcc
pip3 install tesla_dashcam
yum install -y gnu-free-sans-fonts.noarch

# Load ffmpeg
mkdir /usr/local/bin/ffmpeg.static
cd /usr/local/bin/ffmpeg.static
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz
tar xvf ffmpeg-release-i686-static.tar.xz
rm -rf ffmpeg-release-i686-static.tar.xz
ln -s /usr/local/bin/ffmpeg.static/ffmpeg-*/ffmpeg /usr/local/bin/ffmpeg

# Mount the instance store
mkfs -t xfs /dev/nvme1n1
mkdir /data
mount /dev/nvme1n1 /data

# Copy files to /data
aws s3 sync s3://{S3BUCKET}{TEST_LOC} /data
cd /data
mkdir output
tesla_dashcam . --font /usr/share/fonts/gnu-free/FreeSans.ttf --output /data/output/
aws s3 cp /data/output/* s3://{S3BUCKET}{TEST_LOC}

# shutdown -h +5
shutdown -h"""

    print('Running script:')
    print(init_script)

    print("Checking for the security group")
    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    # Check to see if Security Group exists
    try:
        response = ec2.describe_security_groups(
            GroupNames=[SECURITY_GROUP],
        )
        security_group_id = (response['SecurityGroups'][0]['GroupId'])
    except ClientError as e:
        print('Looks like security group doesn\'t exist, creating it...')

        try:
            response = ec2.create_security_group(GroupName=SECURITY_GROUP,
                                                 Description='TeslaCam Ephemeral EC2',
                                                 VpcId=vpc_id)
            security_group_id = response['GroupId']
            print('Security Group Created %s in vpc %s.' %
                  (security_group_id, vpc_id))

            data = ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 80,
                     'ToPort': 80,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])
            print('Ingress Successfully Set %s' % data)

        except ClientError as e:
            print(e)
            raise

    instance = ec2.run_instances(
        ImageId=AMI,
        InstanceType=INSTANCE_TYPE,
        MinCount=1,  # required by boto, even though it's kinda obvious.
        MaxCount=1,
        # make shutdown in script terminate ec2
        InstanceInitiatedShutdownBehavior='terminate',
        KeyName=KEYPAIR,
        SecurityGroupIds=[security_group_id],
        IamInstanceProfile={
            'Name': INSTANCE_PROFILE_NAME
        },
        UserData=init_script  # file to run on instance init.
    )

    print("New instance created.")
    instance_id = instance['Instances'][0]['InstanceId']
    print(instance_id)

    return instance_id


if __name__ == "__main__":
    event = {'message': "Test Message"}
    lambda_to_ec2(event, "foo")
