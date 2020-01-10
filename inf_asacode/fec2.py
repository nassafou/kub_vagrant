#!/usr/bin/env python
 
 '''
 external inventory script
 =================================
 
 Generates inventory that Ansible can understand by making API request to
 using the Boto library.
 
 NOTE: This script assumes Ansible is being executed where the environment
 variables needed for Boto have already been set:
'
'
 
 Optional region environment variable if region is 'auto'
 
.ini file alongside it.  To specify a
_INI_PATH environment variable:
 
.ini
 
 If you're using eucalyptus you need to set the above variables and
 you need to define:
 
_URL=http://hostname_of_your_cc:port/services/Eucalyptus
 
) you can choose a profile
.py --boto-profile prod) or using
 the AWS_PROFILE variable:
 
.py myplaybook.yml
 
 For more details, see: http://docs.pythonboto.org/en/latest/boto_config_tut.html
 
 instances by creating an environment variable
_INSTANCE_FILTERS, which has the same format as the instance_filters
.ini.  For example, to find all hosts whose name begins
 with 'webserver', one might use:
 
_INSTANCE_FILTERS='tag:Name=webserver*'
 
 When run against a specific host, this script returns the following variables:
_ami_launch_index
_architecture
_association
_attachTime
_attachment
_attachmentId
_block_devices
_client_token
_deleteOnTermination
_description
_deviceIndex
_dns_name
_eventsSet
_group_name
_hypervisor
_id
_image_id
_instanceState
_instance_type
_ipOwnerId
_ip_address
_item
_kernel
_key_name
_launch_time
_monitored
_monitoring
_networkInterfaceId
_ownerId
_persistent
_placement
_platform
_previous_state
_private_dns_name
_private_ip_address
_publicIp
_public_dns_name
_ramdisk
_reason
_region
_requester_id
_root_device_name
_root_device_type
_security_group_ids
_security_group_names
_shutdown_state
_sourceDestCheck
_spot_instance_request_id
_state
_state_code
_state_reason
_status
_subnet_id
_tenancy
_virtualization_type
_vpc_id
 
.instance object. There is a lack of
 consistency with variable spellings (camelCase and underscores) since this
 just loops through all variables the object exposes. It is preferred to use the
 ones with underscores when multiple exist.
 
 In addition, if an instance has AWS tags associated with it, each tag is a new
 variable named:
_tag_[Key] = [Value]
 
_security_group_ids' and
_security_group_names'.
 
 When destination_format and destination_format_tags are specified
 the destination_format can be built from the instance tags and attributes.
 The behavior will first check the user defined tags, then proceed to
 check instance attributes, and finally if neither are found 'nil' will
 be used instead.
 
 'my_instance': {
',             # attribute
a', # attribute
',  # attribute
_tag_deployment': 'blue',      # tag
_tag_clusterid': 'ansible',    # tag
_tag_Name': 'webserver',       # tag
     ...
 }
 
.ini file the following settings are specified:
 ...
}
 destination_format_tags: Name,clusterid,deployment,private_dns_name
 ...
 
 These settings would produce a destination_format as the following:
'
 '''
 
, Peter Sankauskas
 #
 # This file is part of Ansible,
 #
 # Ansible is free software: you can redistribute it and/or modify
 # it under the terms of the GNU General Public License as published by
 of the License, or
 # (at your option) any later version.
 #
 # Ansible is distributed in the hope that it will be useful,
 # but WITHOUT ANY WARRANTY; without even the implied warranty of
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 # GNU General Public License for more details.
 #
 # You should have received a copy of the GNU General Public License
 # along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
 
 ######################################################################
 
 import sys
 import os
 import argparse
 import re
 from time import time
 from copy import deepcopy
 from datetime import date, datetime
 import boto

 from boto import rds
 from boto import elasticache

 from boto import sts
 
 from ansible.module_utils import six
_utils
 from ansible.module_utils.six.moves import configparser
 
 = False
 try:
  # noqa
 = True
 except ImportError:
     pass
 
 from collections import defaultdict
 
 import json
 
 DEFAULTS = {
     'all_elasticache_clusters': 'False',
     'all_elasticache_nodes': 'False',
     'all_elasticache_replication_groups': 'False',
     'all_instances': 'False',
     'all_rds_instances': 'False',
     'aws_access_key_id': '',
     'aws_secret_access_key': '',
     'aws_security_token': '',
     'boto_profile': '',
',
     'cache_path': '~/.ansible/tmp',
     'destination_variable': 'public_dns_name',
     'elasticache': 'True',
     'eucalyptus': 'False',
     'eucalyptus_host': '',
     'expand_csv_tags': 'False',
     'group_by_ami_id': 'True',
     'group_by_availability_zone': 'True',
     'group_by_aws_account': 'False',
     'group_by_elasticache_cluster': 'True',
     'group_by_elasticache_engine': 'True',
     'group_by_elasticache_parameter_group': 'True',
     'group_by_elasticache_replication_group': 'True',
     'group_by_instance_id': 'True',
     'group_by_instance_state': 'False',
     'group_by_instance_type': 'True',
     'group_by_key_pair': 'True',
     'group_by_platform': 'True',
     'group_by_rds_engine': 'True',
     'group_by_rds_parameter_group': 'True',
     'group_by_region': 'True',
_names': 'True',
     'group_by_security_group': 'True',
     'group_by_tag_keys': 'True',
     'group_by_tag_none': 'True',
     'group_by_vpc_id': 'True',
     'hostname_variable': '',
     'iam_role': '',
     'include_rds_clusters': 'False',
     'nested_groups': 'False',
     'pattern_exclude': '',
     'pattern_include': '',
     'rds': 'False',
     'regions': 'all',
',
     'replace_dash_in_groups': 'True',
': 'False',
_excluded_zones': '',
_hostnames': '',
     'stack_filters': 'False',
     'vpc_destination_variable': 'ip_address'
 }
 
 
Inventory(object):
 
     def _empty_inventory(self):
         return {"_meta": {"hostvars": {}}}
 
     def _json_serial(self, obj):
         """JSON serializer for objects not serializable by default json code"""
 
         if isinstance(obj, (datetime, date)):
             return obj.isoformat()
         raise TypeError("Type %s not serializable" % type(obj))
 
     def __init__(self):
         ''' Main execution path '''
 
         # Inventory grouped by instance IDs, tags, security groups, regions,
         # and availability zones
         self.inventory = self._empty_inventory()
 
         self.aws_account_id = None
 
         # Index of hostname (address) to instance ID
         self.index = {}
 
         # Boto profile to use (if any)
         self.boto_profile = None
 
         # AWS credentials.
         self.credentials = {}
 
         # Read settings and parse CLI arguments
         self.parse_cli_args()
         self.read_settings()
 
         # Make sure that profile_name is not passed at all if not set
 boto will fall over otherwise
         if self.boto_profile:
Connection, 'profile_name'):
 to use profile")
 
         # Cache
         if self.args.refresh_cache:
             self.do_api_calls_update_cache()
         elif not self.is_cache_valid():
             self.do_api_calls_update_cache()
 
         # Data to print
         if self.args.host:
             data_to_print = self.get_host_info()
 
         elif self.args.list:
             # Display list of instances for inventory
             if self.inventory == self._empty_inventory():
                 data_to_print = self.get_inventory_from_cache()
             else:
                 data_to_print = self.json_format_dict(self.inventory, True)
 
         print(data_to_print)
 
     def is_cache_valid(self):
         ''' Determines if the cache files have expired, or if it is still valid '''
 
         if os.path.isfile(self.cache_path_cache):
             mod_time = os.path.getmtime(self.cache_path_cache)
             current_time = time()
             if (mod_time + self.cache_max_age) > current_time:
                 if os.path.isfile(self.cache_path_index):
                     return True
 
         return False
 
     def read_settings(self):
.ini file '''
 
         scriptbasename = __file__
         scriptbasename = os.path.basename(scriptbasename)
         scriptbasename = scriptbasename.replace('.py', '')
 
         defaults = {
': {
.ini'),
                 'ini_path': os.path.join(os.path.dirname(__file__), '%s.ini' % scriptbasename)
             }
         }
 
:
             config = configparser.ConfigParser(DEFAULTS)
         else:
             config = configparser.SafeConfigParser(DEFAULTS)
']['ini_path'])
_ini_path))
 
_ini_path):
']['ini_fallback'])
 
_ini_path):
_ini_path)
 
         # Add empty sections if they don't exist
         try:
')
         except configparser.DuplicateSectionError:
             pass
 
         try:
             config.add_section('credentials')
         except configparser.DuplicateSectionError:
             pass
 
         # is eucalyptus?
', 'eucalyptus')
', 'eucalyptus_host')
 
         # Regions
         self.regions = []
', 'regions')
         if (config_regions == 'all'):
             if self.eucalyptus_host:
                 self.regions.append(boto.connect_euca(host=self.eucalyptus_host).region.name, **self.credentials)
             else:
', 'regions_exclude')
 
.regions():
                     if region_info.name not in config_regions_exclude:
                         self.regions.append(region_info.name)
         else:
             self.regions = config_regions.split(",")
         if 'auto' in self.regions:
             env_region = os.environ.get('AWS_REGION')
             if env_region is None:
                 env_region = os.environ.get('AWS_DEFAULT_REGION')
             self.regions = [env_region]
 
         # Destination addresses
', 'destination_variable')
', 'vpc_destination_variable')
', 'hostname_variable')
 
', 'destination_format') and \
', 'destination_format_tags'):
', 'destination_format')
', 'destination_format_tags').split(',')
         else:
             self.destination_format = None
             self.destination_format_tags = None
 

')
_hostnames')
 
_excluded_zones = []
_excluded_zones').split(',') if a]
 
         # Include RDS instances?
', 'rds')
 
         # Include RDS cluster instances?
', 'include_rds_clusters')
 
         # Include ElastiCache instances?
', 'elasticache')
 
 instances?
', 'all_instances')
 
         # Instance states to be gathered in inventory. Default is 'running'.
         # Setting 'all_instances' to 'yes' overrides this option.
_valid_instance_states = [
             'pending',
             'running',
             'shutting-down',
             'terminated',
             'stopping',
             'stopped'
         ]
_instance_states = []
         if self.all_instances:
_valid_instance_states
', 'instance_states'):
', 'instance_states').split(','):
                 instance_state = instance_state.strip()
_valid_instance_states:
                     continue
_instance_states.append(instance_state)
         else:
_instance_states = ['running']
 
         # Return all RDS instances? (if RDS is enabled)
', 'all_rds_instances')
 
         # Return all ElastiCache replication groups? (if ElastiCache is enabled)
', 'all_elasticache_replication_groups')
 
         # Return all ElastiCache clusters? (if ElastiCache is enabled)
', 'all_elasticache_clusters')
 
         # Return all ElastiCache nodes? (if ElastiCache is enabled)
', 'all_elasticache_nodes')
 
         # boto configuration profile (prefer CLI argument then environment variables then config file)
         self.boto_profile = self.args.boto_profile or \
             os.environ.get('AWS_PROFILE') or \
', 'boto_profile')
 
         # AWS credentials (prefer environment variables)
         if not (self.boto_profile or os.environ.get('AWS_ACCESS_KEY_ID') or
                 os.environ.get('AWS_PROFILE')):
 
             aws_access_key_id = config.get('credentials', 'aws_access_key_id')
             aws_secret_access_key = config.get('credentials', 'aws_secret_access_key')
             aws_security_token = config.get('credentials', 'aws_security_token')
 
             if aws_access_key_id:
                 self.credentials = {
                     'aws_access_key_id': aws_access_key_id,
                     'aws_secret_access_key': aws_secret_access_key
                 }
                 if aws_security_token:
                     self.credentials['security_token'] = aws_security_token
 
         # Cache related
', 'cache_path'))
         if self.boto_profile:
             cache_dir = os.path.join(cache_dir, 'profile_' + self.boto_profile)
         if not os.path.exists(cache_dir):
             os.makedirs(cache_dir)
 
'
         cache_id = self.boto_profile or os.environ.get('AWS_ACCESS_KEY_ID', self.credentials.get('aws_access_key_id'))
         if cache_id:
             cache_name = '%s-%s' % (cache_name, cache_id)
]
         self.cache_path_cache = os.path.join(cache_dir, "%s.cache" % cache_name)
         self.cache_path_index = os.path.join(cache_dir, "%s.index" % cache_name)
', 'cache_max_age')
 
', 'expand_csv_tags')
 
         # Configure nested groups instead of flat namespace.
', 'nested_groups')
 
         # Replace dash or not in group names
', 'replace_dash_in_groups')
 
         # IAM role to assume for connection
', 'iam_role')
 
         # Configure which groups should be created.
 
         group_by_options = [a for a in DEFAULTS if a.startswith('group_by')]
         for option in group_by_options:
', option))
 
         # Do we need to just include hosts that match a pattern?
', 'pattern_include')
         if self.pattern_include:
             self.pattern_include = re.compile(self.pattern_include)
 
         # Do we need to exclude hosts that match a pattern?
', 'pattern_exclude')
         if self.pattern_exclude:
             self.pattern_exclude = re.compile(self.pattern_exclude)
 
         # Do we want to stack multiple filters?
', 'stack_filters')
 
 API docs). Ignore invalid filters.
_instance_filters = []
 
_INSTANCE_FILTERS' in os.environ:
', 'instance_filters') else '')
 
             if self.stack_filters and '&' in filters:
                 self.fail_with_error("AND filters along with stack_filter enabled is not supported.\n")
 
             filter_sets = [f for f in filters.split(',') if f]
 
             for filter_set in filter_sets:
                 filters = {}
                 filter_set = filter_set.strip()
                 for instance_filter in filter_set.split("&"):
                     instance_filter = instance_filter.strip()
                     if not instance_filter or '=' not in instance_filter:
                         continue
)]
                     if not filter_key:
                         continue
                     filters[filter_key] = filter_value
_instance_filters.append(filters.copy())
 
     def parse_cli_args(self):
         ''' Command line argument processing '''
 
')
         parser.add_argument('--list', action='store_true', default=True,
                             help='List instances (default: True)')
         parser.add_argument('--host', action='store',
                             help='Get all the variables about a specific instance')
         parser.add_argument('--refresh-cache', action='store_true', default=False,
 (default: False - use cache files)')
         parser.add_argument('--profile', '--boto-profile', action='store', dest='boto_profile',
')
         self.args = parser.parse_args()
 
     def do_api_calls_update_cache(self):
         ''' Do API calls to each region, and save data in cache files '''
 
_enabled:
_records()
 
         for region in self.regions:
             self.get_instances_by_region(region)
             if self.rds_enabled:
                 self.get_rds_instances_by_region(region)
             if self.elasticache_enabled:
                 self.get_elasticache_clusters_by_region(region)
                 self.get_elasticache_replication_groups_by_region(region)
             if self.include_rds_clusters:
                 self.include_rds_clusters_by_region(region)
 
         self.write_to_cache(self.inventory, self.cache_path_cache)
         self.write_to_cache(self.index, self.cache_path_index)
 
     def connect(self, region):
         ''' create connection to api server'''
         if self.eucalyptus:
             conn = boto.connect_euca(host=self.eucalyptus_host, **self.credentials)
'
         else:
, region)
         return conn
 
     def boto_fix_security_token_in_profile(self, connect_args):
 '''
         profile = 'profile ' + self.boto_profile
         if boto.config.has_option(profile, 'aws_security_token'):
             connect_args['security_token'] = boto.config.get(profile, 'aws_security_token')
         return connect_args
 
     def connect_to_aws(self, module, region):
         connect_args = deepcopy(self.credentials)
 
         # only pass the profile name if it's set (as it is not supported by older boto versions)
         if self.boto_profile:
             connect_args['profile_name'] = self.boto_profile
             self.boto_fix_security_token_in_profile(connect_args)
         elif os.environ.get('AWS_SESSION_TOKEN'):
             connect_args['security_token'] = os.environ.get('AWS_SESSION_TOKEN')
 
         if self.iam_role:
             sts_conn = sts.connect_to_region(region, **connect_args)
             role = sts_conn.assume_role(self.iam_role, 'ansible_dynamic_inventory')
             connect_args['aws_access_key_id'] = role.credentials.access_key
             connect_args['aws_secret_access_key'] = role.credentials.secret_key
             connect_args['security_token'] = role.credentials.session_token
 
         conn = module.connect_to_region(region, **connect_args)
         # connect_to_region will fail "silently" by returning None if the region name is wrong or not supported
         if conn is None:
             self.fail_with_error("region name: %s likely not supported, or AWS is down.  connection to region failed." % region)
         return conn
 
     def get_instances_by_region(self, region):
 API call to the list of instances in a particular
         region '''
 
         try:
             conn = self.connect(region)
             reservations = []
_instance_filters:
                 if self.stack_filters:
                     filters_dict = {}
_instance_filters:
                         filters_dict.update(filters)
                     reservations.extend(conn.get_all_instances(filters=filters_dict))
                 else:
_instance_filters:
                         reservations.extend(conn.get_all_instances(filters=filters))
             else:
                 reservations = conn.get_all_instances()
 
             # Pull the tags back in a second step
             # AWS are on record as saying that the tags fetched in the first `get_all_instances` request are not
             # reliable and may be missing, and the only way to guarantee they are there is by calling `get_all_tags`
             instance_ids = []
             for reservation in reservations:
                 instance_ids.extend([instance.id for instance in reservation.instances])
 

             tags = []
, len(instance_ids), max_filter_value):
                 tags.extend(conn.get_all_tags(filters={'resource-type': 'instance', 'resource-id': instance_ids[i:i + max_filter_value]}))
 
             tags_by_instance_id = defaultdict(dict)
             for tag in tags:
                 tags_by_instance_id[tag.res_id][tag.name] = tag.value
 
             if (not self.aws_account_id) and reservations:
].owner_id
 
             for reservation in reservations:
                 for instance in reservation.instances:
                     instance.tags = tags_by_instance_id[instance.id]
                     self.add_instance(instance, region)
 
         except boto.exception.BotoServerError as e:
             if e.error_code == 'AuthFailure':
                 error = self.get_auth_error_message()
             else:
                 backend = 'Eucalyptus' if self.eucalyptus else 'AWS'
                 error = "Error connecting to %s backend.\n%s" % (backend, e.message)
 instances')
 
     def tags_match_filters(self, tags):
         ''' return True if given tags match configured filters '''
_instance_filters:
             return True
 
_instance_filters:
             for filter_name, filter_value in filters.items():
] != 'tag:':
                     continue
:]
                 if filter_name not in tags:
                     if self.stack_filters:
                         return False
                     continue
                 if isinstance(filter_value, list):
                     if self.stack_filters and tags[filter_name] not in filter_value:
                         return False
                     if not self.stack_filters and tags[filter_name] in filter_value:
                         return True
                 if isinstance(filter_value, six.string_types):
                     if self.stack_filters and tags[filter_name] != filter_value:
                         return False
                     if not self.stack_filters and tags[filter_name] == filter_value:
                         return True
 
         return self.stack_filters
 
     def get_rds_instances_by_region(self, region):
         ''' Makes an AWS API call to the list of RDS instances in a particular
         region '''
 
:
 and try again",
                                  "getting RDS instances")
 
_inventory_conn('client', 'rds', region, **self.credentials)
         db_instances = client.describe_db_instances()
 
         try:
             conn = self.connect_to_aws(rds, region)
             if conn:
                 marker = None
                 while True:
                     instances = conn.get_all_dbinstances(marker=marker)
                     marker = instances.marker
                     for index, instance in enumerate(instances):
                         # Add tags to instances.
                         instance.arn = db_instances['DBInstances'][index]['DBInstanceArn']
                         tags = client.list_tags_for_resource(ResourceName=instance.arn)['TagList']
                         instance.tags = {}
                         for tag in tags:
                             instance.tags[tag['Key']] = tag['Value']
                         if self.tags_match_filters(instance.tags):
                             self.add_rds_instance(instance, region)
                     if not marker:
                         break
         except boto.exception.BotoServerError as e:
             error = e.reason
 
             if e.error_code == 'AuthFailure':
                 error = self.get_auth_error_message()
             elif e.error_code == "OptInRequired":
                 error = "RDS hasn't been enabled for this account yet. " \
                     "You must either log in to the RDS service through the AWS console to enable it, " \
.ini"
             elif not e.reason == "Forbidden":
                 error = "Looks like AWS RDS is down:\n%s" % e.message
             self.fail_with_error(error, 'getting RDS instances')
 
     def include_rds_clusters_by_region(self, region):
:
 and try again",
                                  "getting RDS clusters")
 
_inventory_conn('client', 'rds', region, **self.credentials)
 
         marker, clusters = '', []
         while marker is not None:
             resp = client.describe_db_clusters(Marker=marker)
             clusters.extend(resp["DBClusters"])
             marker = resp.get('Marker', None)
 
]
         c_dict = {}
         for c in clusters:
_instance_filters:
                 matches_filter = True
             else:
                 matches_filter = False
 
             try:
                 # arn:aws:rds:<region>:<account number>:<resourcetype>:<name>
                 tags = client.list_tags_for_resource(
                     ResourceName='arn:aws:rds:' + region + ':' + account_id + ':cluster:' + c['DBClusterIdentifier'])
                 c['Tags'] = tags['TagList']
 
_instance_filters:
_instance_filters:
                         for filter_key, filter_values in filters.items():
                             # get AWS tag key e.g. tag:env will be 'env'
]
                             # Filter values is a list (if you put multiple values for the same tag name)
                             matches_filter = any(d['Key'] == tag_name and d['Value'] in filter_values for d in c['Tags'])
 
                             if matches_filter:
                                 # it matches a filter, so stop looking for further matches
                                 break
 
                         if matches_filter:
                             break
 
             except Exception as e:
:
) means deletion does not fully complete and leave an 'empty' cluster.
                     # Ignore errors when trying to find tags for these
                     pass
 
             # ignore empty clusters caused by AWS bug
:
                 continue
             elif matches_filter:
                 c_dict[c['DBClusterIdentifier']] = c
 
         self.inventory['db_clusters'] = c_dict
 
     def get_elasticache_clusters_by_region(self, region):
         ''' Makes an AWS API call to the list of ElastiCache clusters (with
         nodes' info) in a particular region.'''
 
         # ElastiCache boto module doesn't provide a get_all_instances method,
         # that's why we need to call describe directly (it would be called by
         # the shorthand method anyway...)
         clusters = []
         try:
             conn = self.connect_to_aws(elasticache, region)
             if conn:
                 # show_cache_node_info = True
                 # because we also want nodes' information

                 while _marker:
:
                         _marker = None
                     response = conn.describe_cache_clusters(None, None, _marker, True)
                     _marker = response['DescribeCacheClustersResponse']['DescribeCacheClustersResult']['Marker']
                     try:
                         # Boto also doesn't provide wrapper classes to CacheClusters or
                         # CacheNodes. Because of that we can't make use of the get_list
                         # method in the AWSQueryConnection. Let's do the work manually
                         clusters = clusters + response['DescribeCacheClustersResponse']['DescribeCacheClustersResult']['CacheClusters']
                     except KeyError as e:
                         error = "ElastiCache query to AWS failed (unexpected format)."
                         self.fail_with_error(error, 'getting ElastiCache clusters')
         except boto.exception.BotoServerError as e:
             error = e.reason
 
             if e.error_code == 'AuthFailure':
                 error = self.get_auth_error_message()
             elif e.error_code == "OptInRequired":
                 error = "ElastiCache hasn't been enabled for this account yet. " \
                     "You must either log in to the ElastiCache service through the AWS console to enable it, " \
.ini"
             elif not e.reason == "Forbidden":
                 error = "Looks like AWS ElastiCache is down:\n%s" % e.message
             self.fail_with_error(error, 'getting ElastiCache clusters')
 
         for cluster in clusters:
             self.add_elasticache_cluster(cluster, region)
 
     def get_elasticache_replication_groups_by_region(self, region):
         ''' Makes an AWS API call to the list of ElastiCache replication groups
         in a particular region.'''
 
         # ElastiCache boto module doesn't provide a get_all_instances method,
         # that's why we need to call describe directly (it would be called by
         # the shorthand method anyway...)
         try:
             conn = self.connect_to_aws(elasticache, region)
             if conn:
                 response = conn.describe_replication_groups()
 
         except boto.exception.BotoServerError as e:
             error = e.reason
 
             if e.error_code == 'AuthFailure':
                 error = self.get_auth_error_message()
             if not e.reason == "Forbidden":
                 error = "Looks like AWS ElastiCache [Replication Groups] is down:\n%s" % e.message
             self.fail_with_error(error, 'getting ElastiCache clusters')
 
         try:
             # Boto also doesn't provide wrapper classes to ReplicationGroups
             # Because of that we can't make use of the get_list method in the
             # AWSQueryConnection. Let's do the work manually
             replication_groups = response['DescribeReplicationGroupsResponse']['DescribeReplicationGroupsResult']['ReplicationGroups']
 
         except KeyError as e:
             error = "ElastiCache [Replication Groups] query to AWS failed (unexpected format)."
             self.fail_with_error(error, 'getting ElastiCache clusters')
 
         for replication_group in replication_groups:
             self.add_elasticache_replication_group(replication_group, region)
 
     def get_auth_error_message(self):
         ''' create an informative error message if there is an issue authenticating'''
 inventory."]
         if None in [os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY')]:
             errors.append(' - No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY environment vars found')
         else:
             errors.append(' - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment vars found but may not be correct')
 
         boto_paths = ['/etc/boto.cfg', '~/.boto', '~/.aws/credentials']
         boto_config_found = [p for p in boto_paths if os.path.isfile(os.path.expanduser(p))]
:
             errors.append(" - Boto configs found at '%s', but the credentials contained may not be correct" % ', '.join(boto_config_found))
         else:
             errors.append(" - No Boto config found at any expected location '%s'" % ', '.join(boto_paths))
 
         return '\n'.join(errors)
 
     def fail_with_error(self, err_msg, err_operation=None):
         '''log an error to std err for ansible-playbook to consume and exit'''
         if err_operation:
             err_msg = 'ERROR: "{err_msg}", while: {err_operation}'.format(
                 err_msg=err_msg, err_operation=err_operation)
         sys.stderr.write(err_msg)
)
 
     def get_instance(self, region, instance_id):
         conn = self.connect(region)
 
         reservations = conn.get_all_instances([instance_id])
         for reservation in reservations:
             for instance in reservation.instances:
                 return instance
 
     def add_instance(self, instance, region):
         ''' Adds an instance to the inventory and index, as long as it is
         addressable '''
 
         # Only return instances with desired instance states
_instance_states:
             return
 
         # Select the best destination address
         # When destination_format and destination_format_tags are specified
         # the following code will attempt to find the instance tags first,
         # then the instance attributes next, and finally if neither are found
         # assign nil for the desired destination format attribute.
         if self.destination_format and self.destination_format_tags:
             dest_vars = []
             inst_tags = getattr(instance, 'tags')
             for tag in self.destination_format_tags:
                 if tag in inst_tags:
                     dest_vars.append(inst_tags[tag])
                 elif hasattr(instance, tag):
                     dest_vars.append(getattr(instance, tag))
                 else:
                     dest_vars.append('nil')
 
             dest = self.destination_format.format(*dest_vars)
         elif instance.subnet_id:
             dest = getattr(instance, self.vpc_destination_variable, None)
             if dest is None:
                 dest = getattr(instance, 'tags').get(self.vpc_destination_variable, None)
         else:
             dest = getattr(instance, self.destination_variable, None)
             if dest is None:
                 dest = getattr(instance, 'tags').get(self.destination_variable, None)
 
         if not dest:
             # Skip instances we cannot address (e.g. private VPC subnet)
             return
 
         # Set the inventory name
         hostname = None
         if self.hostname_variable:
             if self.hostname_variable.startswith('tag_'):
:], None)
             else:
                 hostname = getattr(instance, self.hostname_variable)
 

_hostnames:
_names(instance)
_names:
_hostnames):
                     hostname = name
 
         # If we can't get a nice hostname, use the destination address
         if not hostname:
             hostname = dest
 hostnames
_hostnames):
             hostname = hostname.lower()
         else:
             hostname = self.to_safe(hostname).lower()
 
         # if we only want to include hosts that match a pattern, skip those that don't
         if self.pattern_include and not self.pattern_include.match(hostname):
             return
 
         # if we need to exclude hosts that match a pattern, skip those
         if self.pattern_exclude and self.pattern_exclude.match(hostname):
             return
 
         # Add to index
         self.index[hostname] = [region, instance.id]
 
)
         if self.group_by_instance_id:
             self.inventory[instance.id] = [hostname]
             if self.nested_groups:
                 self.push_group(self.inventory, 'instances', instance.id)
 
         # Inventory: Group by region
         if self.group_by_region:
             self.push(self.inventory, region, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'regions', region)
 
         # Inventory: Group by availability zone
         if self.group_by_availability_zone:
             self.push(self.inventory, instance.placement, hostname)
             if self.nested_groups:
                 if self.group_by_region:
                     self.push_group(self.inventory, region, instance.placement)
                 self.push_group(self.inventory, 'zones', instance.placement)
 
         # Inventory: Group by Amazon Machine Image (AMI) ID
         if self.group_by_ami_id:
             ami_id = self.to_safe(instance.image_id)
             self.push(self.inventory, ami_id, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'images', ami_id)
 
         # Inventory: Group by instance type
         if self.group_by_instance_type:
             type_name = self.to_safe('type_' + instance.instance_type)
             self.push(self.inventory, type_name, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'types', type_name)
 
         # Inventory: Group by instance state
         if self.group_by_instance_state:
             state_name = self.to_safe('instance_state_' + instance.state)
             self.push(self.inventory, state_name, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'instance_states', state_name)
 
         # Inventory: Group by platform
         if self.group_by_platform:
             if instance.platform:
                 platform = self.to_safe('platform_' + instance.platform)
             else:
                 platform = self.to_safe('platform_undefined')
             self.push(self.inventory, platform, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'platforms', platform)
 
         # Inventory: Group by key pair
         if self.group_by_key_pair and instance.key_name:
             key_name = self.to_safe('key_' + instance.key_name)
             self.push(self.inventory, key_name, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'keys', key_name)
 
         # Inventory: Group by VPC
         if self.group_by_vpc_id and instance.vpc_id:
             vpc_id_name = self.to_safe('vpc_id_' + instance.vpc_id)
             self.push(self.inventory, vpc_id_name, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'vpcs', vpc_id_name)
 
         # Inventory: Group by security group
         if self.group_by_security_group:
             try:
                 for group in instance.groups:
                     key = self.to_safe("security_group_" + group.name)
                     self.push(self.inventory, key, hostname)
                     if self.nested_groups:
                         self.push_group(self.inventory, 'security_groups', key)
             except AttributeError:
                 self.fail_with_error('\n'.join(['Package boto seems a bit older.',
.']))
 
         # Inventory: Group by AWS account ID
         if self.group_by_aws_account:
             self.push(self.inventory, self.aws_account_id, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'accounts', self.aws_account_id)
 
         # Inventory: Group by tag keys
         if self.group_by_tag_keys:
             for k, v in instance.tags.items():
                 if self.expand_csv_tags and v and ',' in v:
                     values = map(lambda x: x.strip(), v.split(','))
                 else:
                     values = [v]
 
                 for v in values:
                     if v:
                         key = self.to_safe("tag_" + k + "=" + v)
                     else:
                         key = self.to_safe("tag_" + k)
                     self.push(self.inventory, key, hostname)
                     if self.nested_groups:
                         self.push_group(self.inventory, 'tags', self.to_safe("tag_" + k))
                         if v:
                             self.push_group(self.inventory, self.to_safe("tag_" + k), key)
 
 domain names if enabled
_names:
_names(instance)
_names:
                 self.push(self.inventory, name, hostname)
                 if self.nested_groups:
', name)
 
         # Global Tag: instances without tags
:
             self.push(self.inventory, 'tag_none', hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'tags', 'tag_none')
 
 instances
', hostname)
 
         self.inventory["_meta"]["hostvars"][hostname] = self.get_host_info_dict_from_instance(instance)
         self.inventory["_meta"]["hostvars"][hostname]['ansible_host'] = dest
 
     def add_rds_instance(self, instance, region):
         ''' Adds an RDS instance to the inventory and index, as long as it is
         addressable '''
 
         # Only want available instances unless all_rds_instances is True
         if not self.all_rds_instances and instance.status != 'available':
             return
 
         # Select the best destination address
]
 
         if not dest:
             # Skip instances we cannot address (e.g. private VPC subnet)
             return
 
         # Set the inventory name
         hostname = None
         if self.hostname_variable:
             if self.hostname_variable.startswith('tag_'):
:], None)
             else:
                 hostname = getattr(instance, self.hostname_variable)
 
         # If we can't get a nice hostname, use the destination address
         if not hostname:
             hostname = dest
 
         hostname = self.to_safe(hostname).lower()
 
         # Add to index
         self.index[hostname] = [region, instance.id]
 
)
         if self.group_by_instance_id:
             self.inventory[instance.id] = [hostname]
             if self.nested_groups:
                 self.push_group(self.inventory, 'instances', instance.id)
 
         # Inventory: Group by region
         if self.group_by_region:
             self.push(self.inventory, region, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'regions', region)
 
         # Inventory: Group by availability zone
         if self.group_by_availability_zone:
             self.push(self.inventory, instance.availability_zone, hostname)
             if self.nested_groups:
                 if self.group_by_region:
                     self.push_group(self.inventory, region, instance.availability_zone)
                 self.push_group(self.inventory, 'zones', instance.availability_zone)
 
         # Inventory: Group by instance type
         if self.group_by_instance_type:
             type_name = self.to_safe('type_' + instance.instance_class)
             self.push(self.inventory, type_name, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'types', type_name)
 
         # Inventory: Group by VPC
         if self.group_by_vpc_id and instance.subnet_group and instance.subnet_group.vpc_id:
             vpc_id_name = self.to_safe('vpc_id_' + instance.subnet_group.vpc_id)
             self.push(self.inventory, vpc_id_name, hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'vpcs', vpc_id_name)
 
         # Inventory: Group by security group
         if self.group_by_security_group:
             try:
                 if instance.security_group:
                     key = self.to_safe("security_group_" + instance.security_group.name)
                     self.push(self.inventory, key, hostname)
                     if self.nested_groups:
                         self.push_group(self.inventory, 'security_groups', key)
 
             except AttributeError:
                 self.fail_with_error('\n'.join(['Package boto seems a bit older.',
.']))
         # Inventory: Group by tag keys
         if self.group_by_tag_keys:
             for k, v in instance.tags.items():
                 if self.expand_csv_tags and v and ',' in v:
                     values = map(lambda x: x.strip(), v.split(','))
                 else:
                     values = [v]
 
                 for v in values:
                     if v:
                         key = self.to_safe("tag_" + k + "=" + v)
                     else:
                         key = self.to_safe("tag_" + k)
                     self.push(self.inventory, key, hostname)
                     if self.nested_groups:
                         self.push_group(self.inventory, 'tags', self.to_safe("tag_" + k))
                         if v:
                             self.push_group(self.inventory, self.to_safe("tag_" + k), key)
 
         # Inventory: Group by engine
         if self.group_by_rds_engine:
             self.push(self.inventory, self.to_safe("rds_" + instance.engine), hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'rds_engines', self.to_safe("rds_" + instance.engine))
 
         # Inventory: Group by parameter group
         if self.group_by_rds_parameter_group:
             self.push(self.inventory, self.to_safe("rds_parameter_group_" + instance.parameter_group.name), hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'rds_parameter_groups', self.to_safe("rds_parameter_group_" + instance.parameter_group.name))
 
         # Global Tag: instances without tags
:
             self.push(self.inventory, 'tag_none', hostname)
             if self.nested_groups:
                 self.push_group(self.inventory, 'tags', 'tag_none')
 
         # Global Tag: all RDS instances
         self.push(self.inventory, 'rds', hostname)
 
         self.inventory["_meta"]["hostvars"][hostname] = self.get_host_info_dict_from_instance(instance)
         self.inventory["_meta"]["hostvars"][hostname]['ansible_host'] = dest
 
     def add_elasticache_cluster(self, cluster, region):
         ''' Adds an ElastiCache cluster to the inventory and index, as long as
         it's nodes are addressable '''
 
         # Only want available clusters unless all_elasticache_clusters is True
         if not self.all_elasticache_clusters and cluster['CacheClusterStatus'] != 'available':
             return
 
         # Select the best destination address
         if 'ConfigurationEndpoint' in cluster and cluster['ConfigurationEndpoint']:
             # Memcached cluster
             dest = cluster['ConfigurationEndpoint']['Address']
             is_redis = False
         else:
             # Redis sigle node cluster
             # Because all Redis clusters are single nodes, we'll merge the
             # info from the cluster with info about the node
]['Endpoint']['Address']
             is_redis = True
 
         if not dest:
             # Skip clusters we cannot address (e.g. private VPC subnet)
             return
 
         # Add to index
         self.index[dest] = [region, cluster['CacheClusterId']]
 
)
         if self.group_by_instance_id:
             self.inventory[cluster['CacheClusterId']] = [dest]
             if self.nested_groups:
                 self.push_group(self.inventory, 'instances', cluster['CacheClusterId'])
 
         # Inventory: Group by region
         if self.group_by_region and not is_redis:
             self.push(self.inventory, region, dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'regions', region)
 
         # Inventory: Group by availability zone
         if self.group_by_availability_zone and not is_redis:
             self.push(self.inventory, cluster['PreferredAvailabilityZone'], dest)
             if self.nested_groups:
                 if self.group_by_region:
                     self.push_group(self.inventory, region, cluster['PreferredAvailabilityZone'])
                 self.push_group(self.inventory, 'zones', cluster['PreferredAvailabilityZone'])
 
         # Inventory: Group by node type
         if self.group_by_instance_type and not is_redis:
             type_name = self.to_safe('type_' + cluster['CacheNodeType'])
             self.push(self.inventory, type_name, dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'types', type_name)
 
         # Inventory: Group by VPC (information not available in the current
         # AWS API version for ElastiCache)
 
         # Inventory: Group by security group
         if self.group_by_security_group and not is_redis:
 
             # Check for the existence of the 'SecurityGroups' key and also if
             # this key has some value. When the cluster is not placed in a SG
             # the query can return None here and cause an error.
             if 'SecurityGroups' in cluster and cluster['SecurityGroups'] is not None:
                 for security_group in cluster['SecurityGroups']:
                     key = self.to_safe("security_group_" + security_group['SecurityGroupId'])
                     self.push(self.inventory, key, dest)
                     if self.nested_groups:
                         self.push_group(self.inventory, 'security_groups', key)
 
         # Inventory: Group by engine
         if self.group_by_elasticache_engine and not is_redis:
             self.push(self.inventory, self.to_safe("elasticache_" + cluster['Engine']), dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'elasticache_engines', self.to_safe(cluster['Engine']))
 
         # Inventory: Group by parameter group
         if self.group_by_elasticache_parameter_group:
             self.push(self.inventory, self.to_safe("elasticache_parameter_group_" + cluster['CacheParameterGroup']['CacheParameterGroupName']), dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'elasticache_parameter_groups', self.to_safe(cluster['CacheParameterGroup']['CacheParameterGroupName']))
 
         # Inventory: Group by replication group
         if self.group_by_elasticache_replication_group and 'ReplicationGroupId' in cluster and cluster['ReplicationGroupId']:
             self.push(self.inventory, self.to_safe("elasticache_replication_group_" + cluster['ReplicationGroupId']), dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'elasticache_replication_groups', self.to_safe(cluster['ReplicationGroupId']))
 
         # Global Tag: all ElastiCache clusters
         self.push(self.inventory, 'elasticache_clusters', cluster['CacheClusterId'])
 
         host_info = self.get_host_info_dict_from_describe_dict(cluster)
 
         self.inventory["_meta"]["hostvars"][dest] = host_info
 
         # Add the nodes
         for node in cluster['CacheNodes']:
             self.add_elasticache_node(node, cluster, region)
 
     def add_elasticache_node(self, node, cluster, region):
         ''' Adds an ElastiCache node to the inventory and index, as long as
         it is addressable '''
 
         # Only want available nodes unless all_elasticache_nodes is True
         if not self.all_elasticache_nodes and node['CacheNodeStatus'] != 'available':
             return
 
         # Select the best destination address
         dest = node['Endpoint']['Address']
 
         if not dest:
             # Skip nodes we cannot address (e.g. private VPC subnet)
             return
 
         node_id = self.to_safe(cluster['CacheClusterId'] + '_' + node['CacheNodeId'])
 
         # Add to index
         self.index[dest] = [region, node_id]
 
)
         if self.group_by_instance_id:
             self.inventory[node_id] = [dest]
             if self.nested_groups:
                 self.push_group(self.inventory, 'instances', node_id)
 
         # Inventory: Group by region
         if self.group_by_region:
             self.push(self.inventory, region, dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'regions', region)
 
         # Inventory: Group by availability zone
         if self.group_by_availability_zone:
             self.push(self.inventory, cluster['PreferredAvailabilityZone'], dest)
             if self.nested_groups:
                 if self.group_by_region:
                     self.push_group(self.inventory, region, cluster['PreferredAvailabilityZone'])
                 self.push_group(self.inventory, 'zones', cluster['PreferredAvailabilityZone'])
 
         # Inventory: Group by node type
         if self.group_by_instance_type:
             type_name = self.to_safe('type_' + cluster['CacheNodeType'])
             self.push(self.inventory, type_name, dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'types', type_name)
 
         # Inventory: Group by VPC (information not available in the current
         # AWS API version for ElastiCache)
 
         # Inventory: Group by security group
         if self.group_by_security_group:
 
             # Check for the existence of the 'SecurityGroups' key and also if
             # this key has some value. When the cluster is not placed in a SG
             # the query can return None here and cause an error.
             if 'SecurityGroups' in cluster and cluster['SecurityGroups'] is not None:
                 for security_group in cluster['SecurityGroups']:
                     key = self.to_safe("security_group_" + security_group['SecurityGroupId'])
                     self.push(self.inventory, key, dest)
                     if self.nested_groups:
                         self.push_group(self.inventory, 'security_groups', key)
 
         # Inventory: Group by engine
         if self.group_by_elasticache_engine:
             self.push(self.inventory, self.to_safe("elasticache_" + cluster['Engine']), dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'elasticache_engines', self.to_safe("elasticache_" + cluster['Engine']))
 
         # Inventory: Group by parameter group (done at cluster level)
 
         # Inventory: Group by replication group (done at cluster level)
 
         # Inventory: Group by ElastiCache Cluster
         if self.group_by_elasticache_cluster:
             self.push(self.inventory, self.to_safe("elasticache_cluster_" + cluster['CacheClusterId']), dest)
 
         # Global Tag: all ElastiCache nodes
         self.push(self.inventory, 'elasticache_nodes', dest)
 
         host_info = self.get_host_info_dict_from_describe_dict(node)
 
         if dest in self.inventory["_meta"]["hostvars"]:
             self.inventory["_meta"]["hostvars"][dest].update(host_info)
         else:
             self.inventory["_meta"]["hostvars"][dest] = host_info
 
     def add_elasticache_replication_group(self, replication_group, region):
         ''' Adds an ElastiCache replication group to the inventory and index '''
 
         # Only want available clusters unless all_elasticache_replication_groups is True
         if not self.all_elasticache_replication_groups and replication_group['Status'] != 'available':
             return
 
         # Skip clusters we cannot address (e.g. private VPC subnet or clustered redis)
]['PrimaryEndpoint'] is None or \
]['PrimaryEndpoint']['Address'] is None:
             return
 
         # Select the best destination address (PrimaryEndpoint)
]['PrimaryEndpoint']['Address']
 
         # Add to index
         self.index[dest] = [region, replication_group['ReplicationGroupId']]
 
)
         if self.group_by_instance_id:
             self.inventory[replication_group['ReplicationGroupId']] = [dest]
             if self.nested_groups:
                 self.push_group(self.inventory, 'instances', replication_group['ReplicationGroupId'])
 
         # Inventory: Group by region
         if self.group_by_region:
             self.push(self.inventory, region, dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'regions', region)
 
         # Inventory: Group by availability zone (doesn't apply to replication groups)
 
         # Inventory: Group by node type (doesn't apply to replication groups)
 
         # Inventory: Group by VPC (information not available in the current
         # AWS API version for replication groups
 
         # Inventory: Group by security group (doesn't apply to replication groups)
         # Check this value in cluster level
 
         # Inventory: Group by engine (replication groups are always Redis)
         if self.group_by_elasticache_engine:
             self.push(self.inventory, 'elasticache_redis', dest)
             if self.nested_groups:
                 self.push_group(self.inventory, 'elasticache_engines', 'redis')
 
         # Global Tag: all ElastiCache clusters
         self.push(self.inventory, 'elasticache_replication_groups', replication_group['ReplicationGroupId'])
 
         host_info = self.get_host_info_dict_from_describe_dict(replication_group)
 
         self.inventory["_meta"]["hostvars"][dest] = host_info
 
_records(self):
         ''' Get and store the map of resource records to domain names that
         point to them. '''
 
         if self.boto_profile:
Connection(profile_name=self.boto_profile)
         else:
Connection()
_conn.get_zones()
 
_excluded_zones]
 
_records = {}
 
_zones:
_conn.get_all_rrsets(zone.id)
 
             for record_set in rrsets:
                 record_name = record_set.name
 
                 if record_name.endswith('.'):
]
 
                 for resource in record_set.resource_records:
_records.setdefault(resource, set())
_records[resource].add(record_name)
 
_names(self, instance):
         ''' Check if an instance is referenced in the records we have from
. If it is, return the list of domain names pointing to said
         instance. If nothing points to it, return an empty list. '''
 
         instance_attributes = ['public_dns_name', 'private_dns_name',
                                'ip_address', 'private_ip_address']
 
         name_list = set()
 
         for attrib in instance_attributes:
             try:
                 value = getattr(instance, attrib)
             except AttributeError:
                 continue
 
_records:
_records[value])
 
         return list(name_list)
 
     def get_host_info_dict_from_instance(self, instance):
         instance_vars = {}
         for key in vars(instance):
             value = getattr(instance, key)
_' + key)
 
             # Handle complex types

__state':
_state'] = instance.state or ''
_state_code'] = instance.state_code
__previous_state':
_previous_state'] = instance.previous_state or ''
_previous_state_code'] = instance.previous_state_code
             elif isinstance(value, (int, bool)):
                 instance_vars[key] = value
             elif isinstance(value, six.string_types):
                 instance_vars[key] = value.strip()
             elif value is None:
                 instance_vars[key] = ''
_region':
                 instance_vars[key] = value.name
__placement':
_placement'] = value.zone
_tags':
                 for k, v in value.items():
                     if self.expand_csv_tags and ',' in v:
                         v = list(map(lambda x: x.strip(), v.split(',')))
_tag_' + k)
                     instance_vars[key] = v
_groups':
                 group_ids = []
                 group_names = []
                 for group in value:
                     group_ids.append(group.id)
                     group_names.append(group.name)
_security_group_ids"] = ','.join([str(i) for i in group_ids])
_security_group_names"] = ','.join([str(i) for i in group_names])
_block_device_mapping':
_block_devices"] = {}
                 for k, v in value.items():
_block_devices"][os.path.basename(k)] = v.volume_id
             else:
                 pass
                 # TODO Product codes if someone finds them useful
                 # print key
                 # print type(value)
                 # print value
 
_account_id')] = self.aws_account_id
 
         return instance_vars
 
     def get_host_info_dict_from_describe_dict(self, describe_dict):
         ''' Parses the dictionary returned by the API call into a flat list
             of parameters. This method should be used only when 'describe' is
             used directly because Boto doesn't provide specific classes. '''
 
'
, RDS and ElastiCache are different services.
         # I'm just following the pattern used until now to not break any
         # compatibility.
 
         host_info = {}
         for key in describe_dict:
             value = describe_dict[key]
_' + self.uncammelize(key))
 
             # Handle complex types
 
             # Target: Memcached Cache Clusters
_configuration_endpoint' and value:
_configuration_endpoint_address'] = value['Address']
_configuration_endpoint_port'] = value['Port']
 
             # Target: Cache Nodes and Redis Cache Clusters (single node)
_endpoint' and value:
_endpoint_address'] = value['Address']
_endpoint_port'] = value['Port']
 
             # Target: Redis Replication Groups
_node_groups' and value:
]['PrimaryEndpoint']['Address']
]['PrimaryEndpoint']['Port']

]['NodeGroupMembers']:
                     if node['CurrentRole'] == 'primary':
_primary_cluster_address'] = node['ReadEndpoint']['Address']
_primary_cluster_port'] = node['ReadEndpoint']['Port']
_primary_cluster_id'] = node['CacheClusterId']
                     elif node['CurrentRole'] == 'replica':
_replica_cluster_address_' + str(replica_count)] = node['ReadEndpoint']['Address']
_replica_cluster_port_' + str(replica_count)] = node['ReadEndpoint']['Port']
_replica_cluster_id_' + str(replica_count)] = node['CacheClusterId']

 
             # Target: Redis Replication Groups
_member_clusters' and value:
_member_clusters'] = ','.join([str(i) for i in value])
 
             # Target: All Cache Clusters
_cache_parameter_group':
_cache_node_ids_to_reboot"] = ','.join([str(i) for i in value['CacheNodeIdsToReboot']])
_cache_parameter_group_name'] = value['CacheParameterGroupName']
_cache_parameter_apply_status'] = value['ParameterApplyStatus']
 
             # Target: Almost everything
_security_groups':
 
                 # Skip if SecurityGroups is None
                 # (it is possible to have the key defined but no value in it).
                 if value is not None:
                     sg_ids = []
                     for sg in value:
                         sg_ids.append(sg['SecurityGroupId'])
_security_group_ids"] = ','.join([str(i) for i in sg_ids])
 
             # Target: Everything
             # Preserve booleans and integers
             elif isinstance(value, (int, bool)):
                 host_info[key] = value
 
             # Target: Everything
             # Sanitize string values
             elif isinstance(value, six.string_types):
                 host_info[key] = value.strip()
 
             # Target: Everything
             # Replace None by an empty string
             elif value is None:
                 host_info[key] = ''
 
             else:
                 # Remove non-processed complex types
                 pass
 
         return host_info
 
     def get_host_info(self):
         ''' Get variables about a specific host '''
 
:
             # Need to load index from cache
             self.load_index_from_cache()
 
         if self.args.host not in self.index:
             # try updating the cache
             self.do_api_calls_update_cache()
             if self.args.host not in self.index:
                 # host might not exist anymore
                 return self.json_format_dict({}, True)
 
         (region, instance_id) = self.index[self.args.host]
 
         instance = self.get_instance(region, instance_id)
         return self.json_format_dict(self.get_host_info_dict_from_instance(instance), True)
 
     def push(self, my_dict, key, element):
         ''' Push an element onto an array that may not have been defined in
         the dict '''
         group_info = my_dict.setdefault(key, [])
         if isinstance(group_info, dict):
             host_list = group_info.setdefault('hosts', [])
             host_list.append(element)
         else:
             group_info.append(element)
 
     def push_group(self, my_dict, key, element):
         ''' Push a group as a child of another group. '''
         parent_group = my_dict.setdefault(key, {})
         if not isinstance(parent_group, dict):
             parent_group = my_dict[key] = {'hosts': parent_group}
         child_groups = parent_group.setdefault('children', [])
         if element not in child_groups:
             child_groups.append(element)
 
     def get_inventory_from_cache(self):
         ''' Reads the inventory from the cache file and returns it as a JSON
         object '''
 
         with open(self.cache_path_cache, 'r') as f:
             json_inventory = f.read()
             return json_inventory
 
     def load_index_from_cache(self):
         ''' Reads the index from the cache file sets self.index '''
 
         with open(self.cache_path_index, 'rb') as f:
             self.index = json.load(f)
 
     def write_to_cache(self, data, filename):
         ''' Writes data in JSON format to a file '''
 
         json_data = self.json_format_dict(data, True)
         with open(filename, 'w') as f:
             f.write(json_data)
 
     def uncammelize(self, key):
', key)
', temp).lower()
 
     def to_safe(self, word):
         ''' Converts 'bad' characters in a string to underscores so they can be used as Ansible groups '''
\_"
         if not self.replace_dash_in_groups:
             regex += r"\-"
         return re.sub(regex + "]", "_", word)
 
     def json_format_dict(self, data, pretty=False):
         ''' Converts a dict to a JSON object and dumps it as a formatted
         string '''
 
         if pretty:
, default=self._json_serial)
         else:
             return json.dumps(data, default=self._json_serial)
 
 
 if __name__ == '__main__':
     # Run the script
Inventory()
