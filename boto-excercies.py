import boto3
import argparse
from pprint import pprint

'''
Returns list of 'Instances' metadata in chosen region/account.
Specify tag_key and/or tag_value to filter by key, value, or key/value pair.
http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
'''
def get_instance_metadata(ec2_client, tag_key=None, tag_value=None):

    kwargs = {}

    if tag_key:
        # Both specified, filter by key=tag_key and value=tag_value
        if tag_value:
            kwargs['Filters'] = [
                {
                    'Name': 'tag:{}'.format(tag_key),
                    'Values': [tag_value]
                }
            ]
        # Only key is specified, filter by key=tag_key (any value)
        else:
            kwargs['Filters'] = [
                {
                    'Name': 'tag-key',
                    'Values': [tag_key]
                }
            ]
    # Only value is specified, filter by value=tag_value (any key)
    elif tag_value:
        kwargs['Filters'] = [
            {
                'Name': 'tag-value',
                'Values': [tag_value]
            }
        ]

    instance_metadata = []

    # AWS responses are 1MB maximum, >1MB is paginated
    # If there are more pages, instances_page['NextToken'] = token_string
    # If there are no more pages, 'NextToken' not in instances_page
    while True:
        instances_page = ec2_client.describe_instances(**kwargs)
        for reservation in instances_page['Reservations']:
            instance_metadata += reservation['Instances']
        if 'NextToken' not in instances_page:
            break
        else:
            kwargs['NextToken'] = instances_page['NextToken']

    return instance_metadata

def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', dest = 'profile', default = 'default', help = 'AWS Profile')
    parser.add_argument('-r', dest = 'region', default ='us-east-1', help = 'AWS Region')
    args = parser.parse_args()
    
    # Configure EC2 client
    boto_session = boto3.session.Session(profile_name = args.profile, region_name = args.region)
    ec2_client = boto_session.client('ec2')

    pprint(get_instance_metadata(ec2_client))

if __name__ == "__main__":
    main()