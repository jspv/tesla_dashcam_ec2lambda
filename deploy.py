""" Build and deploy the tesla_dashcam lambda """

import boto3
import botocore
import yaml
import sys
import os
import subprocess
import shutil
import argparse
from distutils.util import strtobool


# Load and process customizations
customizations = yaml.safe_load((open('customizations.yaml')))
for safefilename in customizations:
    safefile = open(safefilename, 'r')
    new = safefile.read()
    for replacement in customizations[safefilename].items():
        new = new.replace(*replacement)
    newfilename = safefilename.replace('.safe', '')
    newfile = open(newfilename, 'w')
    newfile.write(new)
    safefile.close()
    newfile.close()

# Load the configuration settings
config = yaml.safe_load(open('deploy_parameters.yaml'))


def yes_no_query(question):
    sys.stdout.write('{} [y/n]\n'.format(question))
    while True:
        try:
            return strtobool(input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')


def bucket_exists_in_region(bucketname):
    s3 = boto3.client('s3')
    if config['region'] == 'us-east-1':
        location = None
    else:
        location = config['region']

    for bucket in s3.list_buckets()["Buckets"]:
        if (bucket['Name'] == bucketname and
            (s3.get_bucket_location(Bucket=bucket['Name'])
             ['LocationConstraint']) == location):
            return(True)
    return(False)


def create_bucket(bucketname):
    s3 = boto3.resource('s3', region_name=config['region'])
    '''
    Dumb issue with specifying us-east-1 region
    https://docs.aws.amazon.com/cli/latest/reference/s3api/create-bucket.html
    '''
    if config['region'] == 'us-east-1':
        bucket = s3.create_bucket(Bucket=bucketname)
    else:
        bucket = s3.create_bucket(Bucket=bucketname,
                                  CreateBucketConfiguration={
                                      'LocationConstraint': config['region']})
    print("Created bucket {}".format(bucketname))


def main():
    # ensure using global config
    global config

    parser = argparse.ArgumentParser()
    parser.add_argument('--nodeploy', action='store_true',
                        help='Skip deployment of lambda code', required=False)
    args = parser.parse_args()

    # Validate the cloudformation template
    cmd = ("aws cloudformation validate-template "
           f"--template-body file://{config['cloudformation_template']} "
           )
    print(cmd)
    try:
        validate_cmd = subprocess.check_call(cmd.split(" "))
    except subprocess.CalledProcessError:
        print('Cloudformaiton template validation failed')
        exit()

    # if lambda_bucket is set, ensure it exists
    if 'lambda_bucket' in config.keys():
        if not bucket_exists_in_region(config['lambda_bucket']):
            print("Error: Required s3 bucket {} does not exist in region "
                  "{}".format(config['lambda_bucket'], config['region']))
            if yes_no_query("Create {}?".format(config['lambda_bucket'])):
                create_bucket(config['lambda_bucket'])
            else:
                sys.exit("exiting")

    if not args.nodeploy:
        # Prepare the deployment area
        # Copy over the lambda files
        if os.path.isdir(config['deploy_dir']):
            shutil.rmtree(config['deploy_dir'])
        shutil.copytree(config['code_dir'], config['deploy_dir'])

        # Pull in the requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "-r", os.path.join(config['deploy_dir'],
                                                  config['deploy_recs']), "-t",
                               config['deploy_dir']])

        # Set permissions
        for root, dirs, files in os.walk(config['deploy_dir']):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o0755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o0644)

    # Run 'cloudformation package' on the cloudformaiton template.  This
    # Will package up the lambda files and upload them and create an
    # Updated template we can use to create the stack
    cmd = ("aws cloudformation package "
           f"--template-file {config['cloudformation_template']} "
           f"--s3-bucket {config['lambda_bucket']} "
           f"--s3-prefix {config['lambda_prefix']} "
           f"--output-template-file {config['cloudformation_output']}"
           # " --force-upload"
           )
    print(cmd)
    package_cmd = subprocess.run(cmd.split(" "))

    # Now Deploy the Stack
    cmd = ("aws cloudformation deploy "
           "--capabilities CAPABILITY_NAMED_IAM "
           f"--template-file {config['cloudformation_output']} "
           f"--stack-name {config['stackname']}")
    print(cmd)
    deploy_cmd = subprocess.run(cmd.split(" "))

    # Create keypair if needed
    # if 'keypair' in config.keys():


if __name__ == "__main__":
    main()
