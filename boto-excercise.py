import boto3
import argparse
import prettytable
from tqdm import tqdm


ALL_REGIONS = [
    'ap-south-1',
    'eu-west-3',
    'eu-west-2',
    'eu-west-1',
    'ap-northeast-2',
    'ap-northeast-1',
    'sa-east-1',
    'ca-central-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'eu-central-1',
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2'
]


'''
https://stackoverflow.com/questions/30648317
Returns value of arbitrarily nested keys, None if KeyError
e.g. return data[key_list[0]][key_list[1]]...[key_list[n]]
'''
def deep_access(data, key_list):
    value = data
    for key in key_list:
        try:
            value = value[key]
        except Exception as e:
            value = None
            break
    return value


'''
Returns list of 'Instances' metadata in chosen region/account, see
boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.describe_instances.

Specify tag_key and/or tag_value to filter by key, value, or key/value pair.

add_region and add_profile will add the string passed to each instance['Region'] and
instance['LocalAwsCredsProfile'] repectively.

If True, fix_tags will take the frustrating [{'Key': key_name,'Value': value}] tag structure,
converting it into a real dict where Tags[key_name] = value

TODO: different way of getting profile into table rather than adding to metadata?
'''
def get_instance_metadata(
    ec2_client,
    tag_key=None,
    tag_value=None,
    fix_tags=True,
    add_region=None,
    add_profile=None
):

    kwargs = {}

    if tag_key:
        if tag_value:
            # Both specified, filter by key=tag_key and value=tag_value
            kwargs['Filters'] = [
                {
                    'Name': 'tag:{}'.format(tag_key),
                    'Values': [tag_value]
                }
            ]
        else:
            # Only key is specified, filter by key=tag_key (any value)
            kwargs['Filters'] = [
                {
                    'Name': 'tag-key',
                    'Values': [tag_key]
                }
            ]
    elif tag_value:
        # Only value is specified, filter by value=tag_value (any key)
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

    # 'Fix' tags -- make instance['Tags'] a dict
    if fix_tags:
        for instance in instance_metadata:
            tags = {}
            for tag_dict in instance.get('Tags', {}):
                tags[tag_dict['Key']] = tag_dict['Value']
            instance['Tags'] = tags

    if add_region:
        for instance in instance_metadata:
            instance['Region'] = add_region

    if add_profile:
        for instance in instance_metadata:
            instance['LocalAwsCredsProfile'] = add_profile

    return instance_metadata


'''
Returns constructed PrettyTable

column_map keys become column headings, column_map values are a list of nested keys to access in
each list of instance metadata. For example:
    column_map['Availability Zone'] = ['Placement', 'AvailabilityZone']
This would create a column labeled 'Availability Zone' where the value for each instance (row)
is instance['Placement']['AvailabilityZone']
'''
def create_table(instance_metadata, column_map):

    columns = [key for key in sorted(column_map.keys())]
    table = prettytable.PrettyTable(columns)
    table.align = 'l'
    # TODO: option for borderless? # table.set_style(prettytable.PLAIN_COLUMNS)

    # Construct table
    for instance in instance_metadata:
        row = []
        for column in columns:
            value = deep_access(instance, column_map[column])
            if value is None:
                value = 'unknown'
            row.append(value)
        table.add_row(row)

    return table


'''
Strips whitespace, splits on ',' and returns list of strings
'''
def comma_delimited_list(comma_delimited_string):
    return comma_delimited_string.replace(' ','').split(',')


'''
Splits on '.', casts digits (positive integers) to ints, returns list
'''
def period_delimited_list(period_delimited_string):
    keys = period_delimited_string.split('.')
    for i in range(len(keys)):
        if keys[i].isdigit():
            keys[i] = int(keys[i])
    return keys


'''
TODO: full strict mode (not just tags, anything else)
TODO: choose sort column?
'''
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p',
        dest='profiles',
        default='default',
        help='AWS Profiles: Can provide multiple as comma-delimited string.'
    )
    parser.add_argument(
        '-r',
        dest='regions',
        default='us-east-1',
        help='AWS Regions: Can provide multiple as comma-delimited string, or string \'all\''
    )
    parser.add_argument(
        '-k',
        dest='tag_key',
        default='ops_group',
        help='Tag Key'
    )
    parser.add_argument(
        '-v',
        dest='tag_value',
        default=None,
        help='Tag Value'
    )
    parser.add_argument(
        '-s',
        action='store_true',
        dest='strict_mode',
        default=None,
        help='Strict Mode: Displays only instances that match specified tag key and (optionally) tag value'
    )
    parser.add_argument(
        '-x',
        dest='arbitrary_properties',
        default=None,
        help='Arbitrary Properties: One or more period-delimited strings, seperated by commas, \
            where x.y.z is instance[x][y][z] and instance is an object in AWS describe_instances \
            response object Reservations[\'Instances\'] e.g. \
            \'-x NetworkInterfaces.0.Association.PublicIp,Placement.AvailabilityZone\''
    )
    args = parser.parse_args()

    if args.regions == 'all':
        regions = ALL_REGIONS
    else:
        regions = comma_delimited_list(args.regions)
    profiles = comma_delimited_list(args.profiles)

    instance_metadata = []
    # progress bar description is 'region/profile', updates as it iterates
    max_description_length = len(max(profiles, key=len)) + len(max(regions, key=len)) + 1
    print
    with tqdm(total=len(regions)*len(profiles), ncols=100) as progress:
        for region in regions:
            for profile in profiles:
                description = '{}/{}'.format(region, profile)
                description += ' ' * (max_description_length - len(description))
                progress.set_description(description)

                boto_session = boto3.session.Session(profile_name=profile, region_name=region)
                ec2_client = boto_session.client('ec2')

                if args.strict_mode:
                    instance_metadata += get_instance_metadata(
                        ec2_client,
                        add_region=region,
                        add_profile=profile,
                        tag_key=args.tag_key,
                        tag_value=args.tag_value
                    )
                else:
                    instance_metadata += get_instance_metadata(
                        ec2_client,
                        add_region=region,
                        add_profile=profile
                    )

                progress.update()

        # after completion, set to generic description
        progress.set_description('Instance Metadata')

    # See create_table() for explanation of column_map
    column_map = {
        'Instance ID': ['InstanceId'],
        'Instance Type': ['InstanceType'],
        'Launch Time': ['LaunchTime'],
        'Profile': ['LocalAwsCredsProfile'],
        'Region': ['Region'],
        'Tag: {}'.format(args.tag_key): ['Tags', args.tag_key]
    }

    if args.arbitrary_properties:
        properties = comma_delimited_list(args.arbitrary_properties)
        for prop in properties:
            pdl = period_delimited_list(prop)
            column_map[ prop] = pdl

    table = create_table(instance_metadata, column_map)
    table_string = table.get_string(sortby='Tag: {}'.format(args.tag_key))
    print '\n' + table_string + '\n'


if __name__ == "__main__":
    main()