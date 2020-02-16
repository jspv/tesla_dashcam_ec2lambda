'''Required filter() function that evaluates the lambda event'''
import yaml

config = yaml.safe_load(open('parameters.yaml'))

# The function below should be entirely rewritten based upn the
# particular lambda deployment and use case


def filter(event):
    ''' evaluate the lambda event data and return:
        - None to abort ec2 execution
        - list containing True and an optional list of values to
          pass to the user_data '''
    # if testfolder exists, use it.
    if 'filter_testfolder' in config.keys():
        folder = config['filter_testfolder']
    else:
        # Assign folder from event here.
        pass

    return [folder]
