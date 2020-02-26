# Local files
from config import config
# Packages
import yaml
import boto3
# For pushover
import http.client
import urllib
# for identifying video file created
import re

# Force a few defaults in case the values aren't specified
for value in ['custom_pushover_token', 'custom_pushover_key']:
    if value not in config.keys():
        config[value] = None

# The functions below should be entirely rewritten based upn the
# particular lambda deployment and use case.
#
#    filter(): evaluate the event data passed in to the lambda to
#    1) determine if the ec2 should launch and to 2) return back a list
#    of values that can be used to format the ec2 user_data.
#    Return: None if the ec2 should not launch or a list of values todo
#    use as substitutions in user_data
#
#    pre_process()
#
#    launched_actions()
#
#    post_process()


def _check_prefix_in_bucket(prefix, bucketname):
    ''' verify that the prefix esists in a bucket '''
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)
    objs = list(bucket.objects.filter(Prefix=prefix))
    if len(objs) > 0:
        print("Prefix {} exists in bucket {}".format(prefix, bucketname))
        return(True)
    else:
        print("Prefix {} not in bucket {}".format(prefix, bucketname))
        return(False)


'''Required filter() function that evaluates the lambda event'''


# Send a message ot pushover
def _send_pushover(message):
    if config['custom_pushover_token'] and config['custom_pushover_key']:
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json",
                     urllib.parse.urlencode({
                         "token": config['custom_pushover_token'],
                         "user": config['custom_pushover_key'],
                         "message": message
                     }), {"Content-type": "application/x-www-form-urlencoded"})
        return(conn.getresponse())


def _create_presigned_url(bucket_name, object_name, expiration=604800):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
        maximum is 604800
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name,
                    'Key': object_name},
            ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


def filter(event):
    ''' evaluate the lambda event data and return:
        - None to abort ec2 execution
        - list containing True and an optional list of values to
          pass to the user_data '''

    print("ec2_lambda received {}".format(event))

    subject = event['Records'][0]['Sns']['Subject']
    message = event['Records'][0]['Sns']['Message']

    # if testfolder exists, use it.
    if 'filter_testfolder' in config.keys():
        message = config['filter_testfolder']

    if not _check_prefix_in_bucket(message, config['custom_s3bucket']):
        return(None)

    if subject == 'TeslaCam Upload':
        return([message])
    else:
        print("'Subject did not match 'TeslaCam Upload'")
        return(None)


def pre_process(eventdata):
    '''Required pre_process() function for custom actions pre-launch'''
    pass


def launched_actions(eventdata, instance):
    '''Required pre_process() function for custom actions before
    waiting for ec2 to finish '''
    _send_pushover("Processing of {} started".format(*eventdata))


def post_process(eventdata, instance):
    ''' Required pre_process() function for custom actions when
    complete'''
    s3 = boto3.client('s3', region_name=config['region'])

    objects = s3.list_objects_v2(Bucket=config['custom_s3bucket'],
                                 Prefix=eventdata[0])['Contents']
    # The format of the created video is:
    # YYYY-MM-DDTHH-MM-SS_YYYY-MM-DDTHH-MM-SS.mp4
    for object in objects:
        match = re.match(
            eventdata[0] + r"/\d\d\d\d-\d\d-\d\dT\d\d-\d\d-\d\d_"
            + r"\d\d\d\d-\d\d-\d\dT\d\d-\d\d-\d\d\.mp4", object['Key'])
        if match:
            break
    if match is None:
        return
    _send_pushover("Processing of {} completed.  View video here: {}".format(
        *eventdata, _create_presigned_url(config['custom_s3bucket'],
                                          match.group())))
