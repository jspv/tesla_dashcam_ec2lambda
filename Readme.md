# Tesla Dashcam EC2Lambda

Create a AWS stack that will automatically process Tesla Sentry camera files
with the excellent [tesla-dashcam](https://github.com/ehendrix23/tesla_dashcam)
program and send a push notification with a link to view the files.  This project pairs very well with the Raspberry Pi based teslausb most actively maintained [here](https://github.com/marcone/teslausb) with a minor modification.

The lambda is triggered by a message to an SNS topic, the lambda creates an EC2 instance that processes the dashcam files with tesla-dashcam, combining them to a single viewable file.  The lambda then creates a signed url to the combined file and sends it to you via Pushover. Note: URLs are set for one-week duration (current AWS Maximum)

The created AWS resources will all be in a single cloudformaiton stack, the stack outputs provide the necessary SNS Topic and IAM User credentials needed to send the SNS message that fires off the lambda.

## Getting Started

You will need a process for getting Tesla Sentry-mode files to an AWS S3 bucket and a way to send an SNS message to trigger the lambda when the files have been uploaded.  I use a slight modification of the marcone build of [teslausb](https://github.com/marcone/teslausb) that sends the SNS message after each folder is uploaded.  The modification can be found [here](https://github.com/jspv/teslausb/tree/per-event-sns).

To receive push notifications, take a look at [Pushover](https://pushover.net) - this project currelty only supports Pushover messages.

### Prerequisites

You will need an AWS account and a local AWS cli environment set up with appropriate credentials to create the necessary cloudformation, lambda, IAM users, polices and roles.  

In order to receive push notifications with a link to the completed file, you will need [Pushover](https://pushover.net) and an appropriate application key.  


### Installing

After cloning the repository, edit the private.yaml.template and add the your account-specific information and rename the file to **private.yaml**.

#### private.yaml

This file is used to add your customizations into the configuration file and cloudformation templates.  This file is used by the deploy.py convenience script which will make the substitutions listed in the private.yaml file to the  templates *(templates contain .safe in the filename)* and create the actual templates *(with .safe removed)*

The format of private.yaml is as follows:

```
path/filename1:
  STRING_TO_REPLACE: value_to_replace_with
  ANOTHER_STRING_TO_REPLACE: another_value_to_replace_with
path/filename2:
  ...
  ```

## Deployment

#### deploy.pl

This a convenience script that performs that:
1. performs the customizations mentioned above and creates the necessary files
2. Packages up the lambda and needed python dependencies into a ./deploy directory
3. Validates the cloudformaiton template
4. runs ```cloudfomrmation package``` to pack up the lambda and upload it to the s3 bucket specified in private.yaml
5. runs ```cloudformation deploy``` to deploy the cloudformation



## License

This project is licensed under the MIT License.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Acknowledgments

* [ehendrix23](https://github.com/ehendrix23) for  tesla_dashcam
* [cimryan](https://github.com/cimryan) and [marcone](https://github.com/marcone) for the creation and maintenance of teslausb
