import yaml

# Load the configuraiton settings
config = yaml.safe_load(open('parameters.yaml'))

# Force a few defaults in case the values aren't specified
for value in ['spot', 'keypair']:
    if value not in config.keys():
        config[value] = None
