import boto3
import argparse
import prettytable

'''
Returns list of 'Instances' metadata in chosen region/account.
Specify tag_key and/or tag_value to filter by key, value, or key/value pair.
boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances
'''
def get_instance_metadata(ec2_client, tag_key=None, tag_value=None, fix_tags=True):

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
 
    if fix_tags:
        for instance in instance_metadata:
            tags = {}
            for tag_dict in instance['Tags']:
                tags[tag_dict['Key']] = tag_dict['Value']
            instance['Tags'] = tags
 
    return instance_metadata

'''
Returns table, currently expects hard-coded tag ops_group.
TODO: Pass everything in!
'''
def create_table(instance_metadata):
    table = prettytable.PrettyTable(['Tag: ops_group', 'Instance ID', 'Instance Type', 'Launch Time'])
    #table.set_style(prettytable.PLAIN_COLUMNS)
    table.align = 'l'
    for instance in instance_metadata:
        table.add_row(
            [
                instance['Tags'].get('role', 'unknown'),
                instance['InstanceId'],
                instance['InstanceType'],
                str(instance['LaunchTime'])
            ]
        )

    return table

def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', dest='profile', default='default', help='AWS Profile')
    parser.add_argument('-r', dest='region', default='us-east-1', help='AWS Region')
    parser.add_argument('-k', dest='tag_key', default='ops_group', help='Tag Key')
    parser.add_argument('-v', dest='tag_value', default=None, help='Tag Value')
    args = parser.parse_args()
    
    # Configure EC2 client
    boto_session = boto3.session.Session(profile_name = args.profile, region_name = args.region)
    ec2_client = boto_session.client('ec2')

    print '\n' + create_table(get_instance_metadata(ec2_client)).get_string(sortby='Tag: {}'.format(str(args.tag_key)))

if __name__ == "__main__":
    main()