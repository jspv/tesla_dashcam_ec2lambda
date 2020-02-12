import sys
import boto3
import datetime


def get_spot_instance_pricing(region, instance_type, start_time, end_time, zone):
    ec2 = client = boto3.client('ec2', region_name=region)
    result = ec2.describe_spot_price_history(InstanceTypes=[
                                             instance_type], StartTime=start_time, EndTime=end_time, AvailabilityZone=zone)
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
    region = sys.argv[1]
    instance = sys.argv[2]
    start = sys.argv[3]
    stop = sys.argv[4]
    zone = sys.argv[5]

    # Dates shoudl be timezone aware and in UTC
    start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%f%z")
    stop = datetime.datetime.strptime(stop, "%Y-%m-%dT%H:%M:%S.%f%z")

    print(start, stop)
    price = get_spot_instance_pricing(region, instance, start, stop, zone)
    print(price)
