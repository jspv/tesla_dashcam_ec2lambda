#!/usr/bin/env python

import boto3
import sys

from dateutil import parser

defaultfilter = [{
    'Name': 'name',
    'Values': ['amzn2-ami-hvm-*']
}, {
    'Name': 'description',
    'Values': ['Amazon Linux 2 AMI*']
}, {
    'Name': 'architecture',
    'Values': ['x86_64']
}, {
    'Name': 'owner-alias',
    'Values': ['amazon']
}, {
    'Name': 'owner-id',
    'Values': ['137112412989']
}, {
    'Name': 'state',
    'Values': ['available']
}, {
    'Name': 'root-device-type',
    'Values': ['ebs']
}, {
    'Name': 'virtualization-type',
    'Values': ['hvm']
}, {
    'Name': 'hypervisor',
    'Values': ['xen']
}, {
    'Name': 'image-type',
    'Values': ['machine']
}]


def get_newest_image(region, filters=defaultfilter):
    client = boto3.client('ec2', region_name=region)
    response = client.describe_images(Owners=['amazon'], Filters=filters)
    source_image = _newest_image(response['Images'])
    return source_image


def _newest_image(list_of_images):
    latest = None

    for image in list_of_images:
        if not latest:
            latest = image
            continue

        if parser.parse(image['CreationDate']) > parser.parse(latest['CreationDate']):
            latest = image

    return latest


if __name__ == "__main__":
    region = sys.argv[1]
    source_image = get_newest_image(region)
    print(source_image['ImageId'])
