""" Lambda to launch ec2-instances """

from botocore.exceptions import WaiterError
from botocore.exceptions import ClientError
# Local files
from config import config
import custom
import latest_ami
# Python packages
import argparse
import datetime
import logging
import base64
import boto3

# Optional logging
# logging.basicConfig(level=logging.DEBUG)

if config['ami'] == 'latest_ami':
    config['ami'] = latest_ami.get_newest_image(config['region'])['ImageId']

ec2 = boto3.client('ec2', region_name=config['region'])
ec2_resource = boto3.resource('ec2', region_name=config['region'])


# Wrap a waiter to try twice.
def wait_twice(waiter_func):
    for _ in range(2):
        try:
            result = waiter_func()
        except WaiterError as e:
            pass
        else:
            return(result)
    raise e


def lambda_to_ec2(event, context):
    """ Lambda handler to launch ec2 instance"""

    # ensure we're using global config
    global config

    # pass the event to event_filter.filter function to determine if the event
    # meets the criteria to continue.
    eventdata = custom.filter(event)
    if eventdata is None:
        return

    # pass in any values from eventdata as well as those in parameters.yaml
    # to .format() to use for substituions
    init_script = config['user_data'].format(*eventdata, **config)

    print(init_script)

    # If stackname is set, get ecurity_group and instance_profile from stack
    # outputs
    if config['stackname'] is not None:
        stack = boto3.client('cloudformation')
        response = stack.describe_stacks(StackName=config['stackname'])
        for output in response['Stacks'][0]['Outputs']:
            if output['OutputKey'] == config['security_group']:
                config['security_group'] = output['OutputValue']
            if output['OutputKey'] == config['instance_profile_name']:
                config['instance_profile_name'] = output['OutputValue']

    LaunchSpecification = {
        'ImageId': config['ami'],
        'InstanceType': config['instance_type'],
        'SecurityGroups': [config['security_group']],
        'IamInstanceProfile': {
            'Name': config['instance_profile_name']
        }
    }

    # Add keypair if there is one specified
    if config['keypair']:
        LaunchSpecification['KeyName'] = config['keypair']

    # Handle and custom pre-processing
    custom.pre_process(eventdata)

    if config['spot'] is True:
        # userdata in request_spot_instances needs to be encoded
        LaunchSpecification['UserData'] = str(
            base64.b64encode(init_script.encode('utf-8')), "utf-8")

        spotrequest = ec2.request_spot_instances(
            InstanceCount=1,
            LaunchSpecification=LaunchSpecification)

        spotinst_id = (spotrequest['SpotInstanceRequests'][0]
                       ['SpotInstanceRequestId'])
        print("ec2_lambda spotinst {} requested at {}".format(
            spotinst_id, datetime.datetime.now()))
        waiter = ec2.get_waiter('spot_instance_request_fulfilled')
        waiter.wait(SpotInstanceRequestIds=[spotinst_id])

        print("ec2_lambda spotinst {} fulfilled at {}".format(
            spotinst_id, datetime.datetime.now()))

        instance_id = (ec2.describe_spot_instance_requests(
            SpotInstanceRequestIds=[spotinst_id])['SpotInstanceRequests'][0]
            ['InstanceId'])

    else:
        # Standard (non-spot) instance
        # These parameters don't exist in request_spot_instances
        LaunchSpecification['UserData'] = init_script
        LaunchSpecification['MinCount'] = 1
        LaunchSpecification['MaxCount'] = 1
        LaunchSpecification['InstanceInitiatedShutdownBehavior'] = 'terminate'
        instance = ec2.run_instances(**LaunchSpecification)
        instance_id = instance['Instances'][0]['InstanceId']

    print("ec2_lambda instance {} created at {}".format(
        instance_id, datetime.datetime.now()))
    instance_resource = ec2_resource.Instance(id=instance_id)
    instance_resource.wait_until_running()
    start = datetime.datetime.now()
    print("ec2_lambda instance {} noted as running at {}".format(
        instance_id, start))

    # handle any custom actions at lauchtime
    custom.launched_actions(eventdata, instance_resource)

    try:
        wait_twice(instance_resource.wait_until_terminated)
    except WaiterError:
        print("Terminating instance, running too long")
        instance_resource.terminate()
        return

    # Complete any post processing
    custom.post_process(eventdata, instance_resource)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--subject', help='simulated sns subject', required=True)
    parser.add_argument(
        '--message', help='simulated sns subject', required=True)
    args = parser.parse_args()
    event = {'Records': [
        {'Sns': {'Subject': args.subject, 'Message': args.message}}]}
    lambda_to_ec2(event, "foo")
