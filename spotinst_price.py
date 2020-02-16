import sys
import boto3
import datetime
import argparse


def get_spot_instance_pricing(region, instance_type, start_time,
                              end_time, zone):
    ec2 = client = boto3.client('ec2', region_name=region)
    result = ec2.describe_spot_price_history(
        InstanceTypes=[instance_type], StartTime=start_time,
        EndTime=end_time, AvailabilityZone=zone)

    assert 'NextToken' not in result or result['NextToken'] == ''

    total_cost = 0.0

    total_seconds = (end_time - start_time).total_seconds()
    total_hours = total_seconds / (60 * 60)
    computed_seconds = 0

    last_time = end_time
    for price in result["SpotPriceHistory"]:
        price["SpotPrice"] = float(price["SpotPrice"])

        available_seconds = (last_time - price["Timestamp"]).total_seconds()
        remaining_seconds = total_seconds - computed_seconds
        used_seconds = min(available_seconds, remaining_seconds)

        total_cost += (price["SpotPrice"] / (60 * 60)) * used_seconds
        computed_seconds += used_seconds

        last_time = price["Timestamp"]

    # Difference b/w first and last returned times
    avg_hourly_cost = total_cost / total_hours
    return avg_hourly_cost, total_cost, total_hours


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument('--spotid', help='spot instance request ID')
    parser.add_argument('--region')
    parser.add_argument('--instance')
    parser.add_argument('--start')
    parser.add_argument('--stop')
    parser.add_argument('--zone')
    args = parser.parse_args()
    if ((not args.spotid and
         not (args.region and args.instance and args.start
              and args.stop and args.zone))
        or (args.spotid and (args.instance or args.start or
                             args.stop or args.zone))):
        parser.error(
            'either spotid and region is specified or all of the following '
            'need to be provided: region, instance, start, stop, zone'
        )
    if not args.spotid:
        # Dates should be timezone aware and in UTC
        start = datetime.datetime.strptime(
            args.start, "%Y-%m-%dT%H:%M:%S.%f%z")
        stop = datetime.datetime.strptime(
            args.stop, "%Y-%m-%dT%H:%M:%S.%f%z")
        price = get_spot_instance_pricing(
            args.region, args.instance, start, stop, args.zone)
    else:
        # Pull the data from the spot instance request identifier
        ec2 = boto3.client('ec2', region_name=args.region)
        response = ec2.describe_spot_instance_requests(
            SpotInstanceRequestIds=[args.spotid])

        spot = response['SpotInstanceRequests'][0]
        start = spot['CreateTime']
        stop = datetime.datetime.strptime(
            spot['Status']['Message'].split(' ')[0], "%Y-%m-%dT%H:%M:%S%z")
        instance = spot['LaunchSpecification']['InstanceType']
        zone = spot['LaunchSpecification']['Placement']['AvailabilityZone']
        price = get_spot_instance_pricing(
            args.region, instance, start, stop, zone)

    print(price)
