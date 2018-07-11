# boto-excercise
Simple python tool using boto3 to list instances by tags

## Requirements
- You can install boto3 and prettytable with `pip install -r requirements.txt`.
- AWS credentials must be set up. The easiest way to do that is to [install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration) and [follow the instructions here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration).
- The policy for your IAM user(s) must allow DescribeInstances


## Usage
### -p (profiles)
Specify as comma-delimited list of locally configured AWS CLI/Boto profiles

Example: `-p default,stage,prod`
### -r (regions)
Specify as comma-delimited list of AWS regions from which to gather data. Can specify 'all' for all AWS regions.

Example: `-r us-east-1,us-west-2`
### -t (tag key)
Specifies the key of the tag to list in the dedicated tag column.

Default is `ops_group`

### -v (tag value)
Currently does nothing unless `-s` (strict mode enabled). With `-s` allows you to filter by value so that you only see instances that match your key/value pair.

### -x (arbitrary properties)
This argument allows you to specify arbitrary properties to display in additional columns. All it requires is knowing the structure of the boto response object returned by descibe_instances(). You can specify the property by its position in the instance metadata, each dictionary key or list index seperated by a period. You can supply multiple, separated by commas. 

For example, `-x NetworkInterfaces.0.Association.PublicIp` adds a column for the public IP of the 0th network interface in the NetworkInterfaces list. EC2 instances often only need one interface so this tends to get you the one and only public IP. See 'Usage Examples' section for usage paired with examples of metadata structure.

Additional items:
* The 'Tags' object is converted to a normal dict, so you can do `-x Tags.tag_key_name`
* 'Region' is added to the instance metadata even though it is absent from the original describe_instances call
* The profile that was used to describe each instance is added with the key 'LocalAwsCredsProfile' (this is used to display the default 'Profile' column)

## Usage Examples
### Multi-Region and Multi-Profile
```
python boto_excercise.py -r us-east-1,eu-west-1 -p default,stage,prod
```
### Add Column With Arbitrary Property (-x)
To add a column for availability zone, you can do the following:
```
python boto_excercise.py -r us-west-2 -p stage -x Placement.AvailabilityZone
```
This works because the 'Placement' key in the dictionary at `describe_instances['Reservations']['Instances']` has the following structure:
```python
'Placement': {
    'AvailabilityZone': 'us-east-1a',
    'GroupName': '',
    'Tenancy': 'default'},
}
```
So `-x Placement.AvailabilityZone` fetches `describe_instances['Reservations']['Instances'][n]['Placement']['AvailabilityZone']` for all `n` instances

### Add Multiple Columns With Arbitrary Properties (-x)
Here we add an AZ column like in the above singular example, but we additionally add the public IP of the 0th network interface in the NetworkInterfaces list. EC2 instances often only need one interface so this tends to get you the one and only public IP. Notice that `NetworkInterfaces.0...` works, positive ints are supported for indexing in lists.
```
python boto_excercise.py -r us-west-2 -p stage -x Placement.AvailabilityZone,NetworkInterfaces.0.Association.PublicIp
```
Here is a trimmed down example of the NetworkInterfaces list, with just one interface:
```python
'NetworkInterfaces': [
    {
        'Association': {
            'IpOwnerId': '12345678910',
            'PublicDnsName': 'ec2-52-206-160-108.compute-1.amazonaws.com',
        'PublicIp': 'a.b.c.d'},
        'Attachment': {
            'AttachTime': datetime.datetime(2016, 8, 3, 20, 2, 25, tzinfo=tzutc()),
            'NetworkInterfaceId': 'eni-xxxxxxxx',
            'OwnerId': '12345678910',
        }
        'PrivateDnsName': 'ip-e-f-g-h.ec2.internal',
        '.Association.PublicIp': 'e.f.g.h',
        'SubnetId': 'subnet-yyyyyyyy',
        'VpcId': 'vpc-zzzzzzzz'
    },
]
```
### Strict Mode (Just Key)
This only lists instances with the tag 'environment'
```
python boto_excercise.py -r us-west-2 -p stage -t environment -s
```

### Strict Mode (Key & Value)
This only lists instances where the tag 'environment' has value 'staging_01'
```
python boto_excercise.py -r us-west-2 -p stage -t environment -v staging_01 -s
```