#!/usr/bin/env python
    2 
    3 '''
    4 EC2 external inventory script
    5 =================================
    6 
    7 Generates inventory that Ansible can understand by making API request to
    8 AWS EC2 using the Boto library.
    9 
   10 NOTE: This script assumes Ansible is being executed where the environment
   11 variables needed for Boto have already been set:
   12     export AWS_ACCESS_KEY_ID='AK123'
   13     export AWS_SECRET_ACCESS_KEY='abc123'
   14 
   15 Optional region environment variable if region is 'auto'
   16 
   17 This script also assumes that there is an ec2.ini file alongside it.  To specify a
   18 different path to ec2.ini, define the EC2_INI_PATH environment variable:
   19 
   20     export EC2_INI_PATH=/path/to/my_ec2.ini
   21 
   22 If you're using eucalyptus you need to set the above variables and
   23 you need to define:
   24 
   25     export EC2_URL=http://hostname_of_your_cc:port/services/Eucalyptus
   26 
   27 If you're using boto profiles (requires boto>=2.24.0) you can choose a profile
   28 using the --boto-profile command line argument (e.g. ec2.py --boto-profile prod) or using
   29 the AWS_PROFILE variable:
   30 
   31     AWS_PROFILE=prod ansible-playbook -i ec2.py myplaybook.yml
   32 
   33 For more details, see: http://docs.pythonboto.org/en/latest/boto_config_tut.html
   34 
   35 You can filter for specific EC2 instances by creating an environment variable
   36 named EC2_INSTANCE_FILTERS, which has the same format as the instance_filters
   37 entry documented in ec2.ini.  For example, to find all hosts whose name begins
   38 with 'webserver', one might use:
   39 
   40     export EC2_INSTANCE_FILTERS='tag:Name=webserver*'
   41 
   42 When run against a specific host, this script returns the following variables:
   43  - ec2_ami_launch_index
   44  - ec2_architecture
   45  - ec2_association
   46  - ec2_attachTime
   47  - ec2_attachment
   48  - ec2_attachmentId
   49  - ec2_block_devices
   50  - ec2_client_token
   51  - ec2_deleteOnTermination
   52  - ec2_description
   53  - ec2_deviceIndex
   54  - ec2_dns_name
   55  - ec2_eventsSet
   56  - ec2_group_name
   57  - ec2_hypervisor
   58  - ec2_id
   59  - ec2_image_id
   60  - ec2_instanceState
   61  - ec2_instance_type
   62  - ec2_ipOwnerId
   63  - ec2_ip_address
   64  - ec2_item
   65  - ec2_kernel
   66  - ec2_key_name
   67  - ec2_launch_time
   68  - ec2_monitored
   69  - ec2_monitoring
   70  - ec2_networkInterfaceId
   71  - ec2_ownerId
   72  - ec2_persistent
   73  - ec2_placement
   74  - ec2_platform
   75  - ec2_previous_state
   76  - ec2_private_dns_name
   77  - ec2_private_ip_address
   78  - ec2_publicIp
   79  - ec2_public_dns_name
   80  - ec2_ramdisk
   81  - ec2_reason
   82  - ec2_region
   83  - ec2_requester_id
   84  - ec2_root_device_name
   85  - ec2_root_device_type
   86  - ec2_security_group_ids
   87  - ec2_security_group_names
   88  - ec2_shutdown_state
   89  - ec2_sourceDestCheck
   90  - ec2_spot_instance_request_id
   91  - ec2_state
   92  - ec2_state_code
   93  - ec2_state_reason
   94  - ec2_status
   95  - ec2_subnet_id
   96  - ec2_tenancy
   97  - ec2_virtualization_type
   98  - ec2_vpc_id
   99 
  100 These variables are pulled out of a boto.ec2.instance object. There is a lack of
  101 consistency with variable spellings (camelCase and underscores) since this
  102 just loops through all variables the object exposes. It is preferred to use the
  103 ones with underscores when multiple exist.
  104 
  105 In addition, if an instance has AWS tags associated with it, each tag is a new
  106 variable named:
  107  - ec2_tag_[Key] = [Value]
  108 
  109 Security groups are comma-separated in 'ec2_security_group_ids' and
  110 'ec2_security_group_names'.
  111 
  112 When destination_format and destination_format_tags are specified
  113 the destination_format can be built from the instance tags and attributes.
  114 The behavior will first check the user defined tags, then proceed to
  115 check instance attributes, and finally if neither are found 'nil' will
  116 be used instead.
  117 
  118 'my_instance': {
  119     'region': 'us-east-1',             # attribute
  120     'availability_zone': 'us-east-1a', # attribute
  121     'private_dns_name': '172.31.0.1',  # attribute
  122     'ec2_tag_deployment': 'blue',      # tag
  123     'ec2_tag_clusterid': 'ansible',    # tag
  124     'ec2_tag_Name': 'webserver',       # tag
  125     ...
  126 }
  127 
  128 Inside of the ec2.ini file the following settings are specified:
  129 ...
  130 destination_format: {0}-{1}-{2}-{3}
  131 destination_format_tags: Name,clusterid,deployment,private_dns_name
  132 ...
  133 
  134 These settings would produce a destination_format as the following:
  135 'webserver-ansible-blue-172.31.0.1'
  136 '''
  137 
  138 # (c) 2012, Peter Sankauskas
  139 #
  140 # This file is part of Ansible,
  141 #
  142 # Ansible is free software: you can redistribute it and/or modify
  143 # it under the terms of the GNU General Public License as published by
  144 # the Free Software Foundation, either version 3 of the License, or
  145 # (at your option) any later version.
  146 #
  147 # Ansible is distributed in the hope that it will be useful,
  148 # but WITHOUT ANY WARRANTY; without even the implied warranty of
  149 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  150 # GNU General Public License for more details.
  151 #
  152 # You should have received a copy of the GNU General Public License
  153 # along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
  154 
  155 ######################################################################
  156 
  157 import sys
  158 import os
  159 import argparse
  160 import re
  161 from time import time
  162 from copy import deepcopy
  163 from datetime import date, datetime
  164 import boto
  165 from boto import ec2
  166 from boto import rds
  167 from boto import elasticache
  168 from boto import route53
  169 from boto import sts
  170 
  171 from ansible.module_utils import six
  172 from ansible.module_utils import ec2 as ec2_utils
  173 from ansible.module_utils.six.moves import configparser
  174 
  175 HAS_BOTO3 = False
  176 try:
  177     import boto3  # noqa
  178     HAS_BOTO3 = True
  179 except ImportError:
  180     pass
  181 
  182 from collections import defaultdict
  183 
  184 import json
  185 
  186 DEFAULTS = {
  187     'all_elasticache_clusters': 'False',
  188     'all_elasticache_nodes': 'False',
  189     'all_elasticache_replication_groups': 'False',
  190     'all_instances': 'False',
  191     'all_rds_instances': 'False',
  192     'aws_access_key_id': '',
  193     'aws_secret_access_key': '',
  194     'aws_security_token': '',
  195     'boto_profile': '',
  196     'cache_max_age': '300',
  197     'cache_path': '~/.ansible/tmp',
  198     'destination_variable': 'public_dns_name',
  199     'elasticache': 'True',
  200     'eucalyptus': 'False',
  201     'eucalyptus_host': '',
  202     'expand_csv_tags': 'False',
  203     'group_by_ami_id': 'True',
  204     'group_by_availability_zone': 'True',
  205     'group_by_aws_account': 'False',
  206     'group_by_elasticache_cluster': 'True',
  207     'group_by_elasticache_engine': 'True',
  208     'group_by_elasticache_parameter_group': 'True',
  209     'group_by_elasticache_replication_group': 'True',
  210     'group_by_instance_id': 'True',
  211     'group_by_instance_state': 'False',
  212     'group_by_instance_type': 'True',
  213     'group_by_key_pair': 'True',
  214     'group_by_platform': 'True',
  215     'group_by_rds_engine': 'True',
  216     'group_by_rds_parameter_group': 'True',
  217     'group_by_region': 'True',
  218     'group_by_route53_names': 'True',
  219     'group_by_security_group': 'True',
  220     'group_by_tag_keys': 'True',
  221     'group_by_tag_none': 'True',
  222     'group_by_vpc_id': 'True',
  223     'hostname_variable': '',
  224     'iam_role': '',
  225     'include_rds_clusters': 'False',
  226     'nested_groups': 'False',
  227     'pattern_exclude': '',
  228     'pattern_include': '',
  229     'rds': 'False',
  230     'regions': 'all',
  231     'regions_exclude': 'us-gov-west-1, cn-north-1',
  232     'replace_dash_in_groups': 'True',
  233     'route53': 'False',
  234     'route53_excluded_zones': '',
  235     'route53_hostnames': '',
  236     'stack_filters': 'False',
  237     'vpc_destination_variable': 'ip_address'
  238 }
  239 
  240 
  241 class Ec2Inventory(object):
  242 
  243     def _empty_inventory(self):
  244         return {"_meta": {"hostvars": {}}}
  245 
  246     def _json_serial(self, obj):
  247         """JSON serializer for objects not serializable by default json code"""
  248 
  249         if isinstance(obj, (datetime, date)):
  250             return obj.isoformat()
  251         raise TypeError("Type %s not serializable" % type(obj))
  252 
  253     def __init__(self):
  254         ''' Main execution path '''
  255 
  256         # Inventory grouped by instance IDs, tags, security groups, regions,
  257         # and availability zones
  258         self.inventory = self._empty_inventory()
  259 
  260         self.aws_account_id = None
  261 
  262         # Index of hostname (address) to instance ID
  263         self.index = {}
  264 
  265         # Boto profile to use (if any)
  266         self.boto_profile = None
  267 
  268         # AWS credentials.
  269         self.credentials = {}
  270 
  271         # Read settings and parse CLI arguments
  272         self.parse_cli_args()
  273         self.read_settings()
  274 
  275         # Make sure that profile_name is not passed at all if not set
  276         # as pre 2.24 boto will fall over otherwise
  277         if self.boto_profile:
  278             if not hasattr(boto.ec2.EC2Connection, 'profile_name'):
  279                 self.fail_with_error("boto version must be >= 2.24 to use profile")
  280 
  281         # Cache
  282         if self.args.refresh_cache:
  283             self.do_api_calls_update_cache()
  284         elif not self.is_cache_valid():
  285             self.do_api_calls_update_cache()
  286 
  287         # Data to print
  288         if self.args.host:
  289             data_to_print = self.get_host_info()
  290 
  291         elif self.args.list:
  292             # Display list of instances for inventory
  293             if self.inventory == self._empty_inventory():
  294                 data_to_print = self.get_inventory_from_cache()
  295             else:
  296                 data_to_print = self.json_format_dict(self.inventory, True)
  297 
  298         print(data_to_print)
  299 
  300     def is_cache_valid(self):
  301         ''' Determines if the cache files have expired, or if it is still valid '''
  302 
  303         if os.path.isfile(self.cache_path_cache):
  304             mod_time = os.path.getmtime(self.cache_path_cache)
  305             current_time = time()
  306             if (mod_time + self.cache_max_age) > current_time:
  307                 if os.path.isfile(self.cache_path_index):
  308                     return True
  309 
  310         return False
  311 
  312     def read_settings(self):
  313         ''' Reads the settings from the ec2.ini file '''
  314 
  315         scriptbasename = __file__
  316         scriptbasename = os.path.basename(scriptbasename)
  317         scriptbasename = scriptbasename.replace('.py', '')
  318 
  319         defaults = {
  320             'ec2': {
  321                 'ini_fallback': os.path.join(os.path.dirname(__file__), 'ec2.ini'),
  322                 'ini_path': os.path.join(os.path.dirname(__file__), '%s.ini' % scriptbasename)
  323             }
  324         }
  325 
  326         if six.PY3:
  327             config = configparser.ConfigParser(DEFAULTS)
  328         else:
  329             config = configparser.SafeConfigParser(DEFAULTS)
  330         ec2_ini_path = os.environ.get('EC2_INI_PATH', defaults['ec2']['ini_path'])
  331         ec2_ini_path = os.path.expanduser(os.path.expandvars(ec2_ini_path))
  332 
  333         if not os.path.isfile(ec2_ini_path):
  334             ec2_ini_path = os.path.expanduser(defaults['ec2']['ini_fallback'])
  335 
  336         if os.path.isfile(ec2_ini_path):
  337             config.read(ec2_ini_path)
  338 
  339         # Add empty sections if they don't exist
  340         try:
  341             config.add_section('ec2')
  342         except configparser.DuplicateSectionError:
  343             pass
  344 
  345         try:
  346             config.add_section('credentials')
  347         except configparser.DuplicateSectionError:
  348             pass
  349 
  350         # is eucalyptus?
  351         self.eucalyptus = config.getboolean('ec2', 'eucalyptus')
  352         self.eucalyptus_host = config.get('ec2', 'eucalyptus_host')
  353 
  354         # Regions
  355         self.regions = []
  356         config_regions = config.get('ec2', 'regions')
  357         if (config_regions == 'all'):
  358             if self.eucalyptus_host:
  359                 self.regions.append(boto.connect_euca(host=self.eucalyptus_host).region.name, **self.credentials)
  360             else:
  361                 config_regions_exclude = config.get('ec2', 'regions_exclude')
  362 
  363                 for region_info in ec2.regions():
  364                     if region_info.name not in config_regions_exclude:
  365                         self.regions.append(region_info.name)
  366         else:
  367             self.regions = config_regions.split(",")
  368         if 'auto' in self.regions:
  369             env_region = os.environ.get('AWS_REGION')
  370             if env_region is None:
  371                 env_region = os.environ.get('AWS_DEFAULT_REGION')
  372             self.regions = [env_region]
  373 
  374         # Destination addresses
  375         self.destination_variable = config.get('ec2', 'destination_variable')
  376         self.vpc_destination_variable = config.get('ec2', 'vpc_destination_variable')
  377         self.hostname_variable = config.get('ec2', 'hostname_variable')
  378 
  379         if config.has_option('ec2', 'destination_format') and \
  380            config.has_option('ec2', 'destination_format_tags'):
  381             self.destination_format = config.get('ec2', 'destination_format')
  382             self.destination_format_tags = config.get('ec2', 'destination_format_tags').split(',')
  383         else:
  384             self.destination_format = None
  385             self.destination_format_tags = None
  386 
  387         # Route53
  388         self.route53_enabled = config.getboolean('ec2', 'route53')
  389         self.route53_hostnames = config.get('ec2', 'route53_hostnames')
  390 
  391         self.route53_excluded_zones = []
  392         self.route53_excluded_zones = [a for a in config.get('ec2', 'route53_excluded_zones').split(',') if a]
  393 
  394         # Include RDS instances?
  395         self.rds_enabled = config.getboolean('ec2', 'rds')
  396 
  397         # Include RDS cluster instances?
  398         self.include_rds_clusters = config.getboolean('ec2', 'include_rds_clusters')
  399 
  400         # Include ElastiCache instances?
  401         self.elasticache_enabled = config.getboolean('ec2', 'elasticache')
  402 
  403         # Return all EC2 instances?
  404         self.all_instances = config.getboolean('ec2', 'all_instances')
  405 
  406         # Instance states to be gathered in inventory. Default is 'running'.
  407         # Setting 'all_instances' to 'yes' overrides this option.
  408         ec2_valid_instance_states = [
  409             'pending',
  410             'running',
  411             'shutting-down',
  412             'terminated',
  413             'stopping',
  414             'stopped'
  415         ]
  416         self.ec2_instance_states = []
  417         if self.all_instances:
  418             self.ec2_instance_states = ec2_valid_instance_states
  419         elif config.has_option('ec2', 'instance_states'):
  420             for instance_state in config.get('ec2', 'instance_states').split(','):
  421                 instance_state = instance_state.strip()
  422                 if instance_state not in ec2_valid_instance_states:
  423                     continue
  424                 self.ec2_instance_states.append(instance_state)
  425         else:
  426             self.ec2_instance_states = ['running']
  427 
  428         # Return all RDS instances? (if RDS is enabled)
  429         self.all_rds_instances = config.getboolean('ec2', 'all_rds_instances')
  430 
  431         # Return all ElastiCache replication groups? (if ElastiCache is enabled)
  432         self.all_elasticache_replication_groups = config.getboolean('ec2', 'all_elasticache_replication_groups')
  433 
  434         # Return all ElastiCache clusters? (if ElastiCache is enabled)
  435         self.all_elasticache_clusters = config.getboolean('ec2', 'all_elasticache_clusters')
  436 
  437         # Return all ElastiCache nodes? (if ElastiCache is enabled)
  438         self.all_elasticache_nodes = config.getboolean('ec2', 'all_elasticache_nodes')
  439 
  440         # boto configuration profile (prefer CLI argument then environment variables then config file)
  441         self.boto_profile = self.args.boto_profile or \
  442             os.environ.get('AWS_PROFILE') or \
  443             config.get('ec2', 'boto_profile')
  444 
  445         # AWS credentials (prefer environment variables)
  446         if not (self.boto_profile or os.environ.get('AWS_ACCESS_KEY_ID') or
  447                 os.environ.get('AWS_PROFILE')):
  448 
  449             aws_access_key_id = config.get('credentials', 'aws_access_key_id')
  450             aws_secret_access_key = config.get('credentials', 'aws_secret_access_key')
  451             aws_security_token = config.get('credentials', 'aws_security_token')
  452 
  453             if aws_access_key_id:
  454                 self.credentials = {
  455                     'aws_access_key_id': aws_access_key_id,
  456                     'aws_secret_access_key': aws_secret_access_key
  457                 }
  458                 if aws_security_token:
  459                     self.credentials['security_token'] = aws_security_token
  460 
  461         # Cache related
  462         cache_dir = os.path.expanduser(config.get('ec2', 'cache_path'))
  463         if self.boto_profile:
  464             cache_dir = os.path.join(cache_dir, 'profile_' + self.boto_profile)
  465         if not os.path.exists(cache_dir):
  466             os.makedirs(cache_dir)
  467 
  468         cache_name = 'ansible-ec2'
  469         cache_id = self.boto_profile or os.environ.get('AWS_ACCESS_KEY_ID', self.credentials.get('aws_access_key_id'))
  470         if cache_id:
  471             cache_name = '%s-%s' % (cache_name, cache_id)
  472         cache_name += '-' + str(abs(hash(__file__)))[1:7]
  473         self.cache_path_cache = os.path.join(cache_dir, "%s.cache" % cache_name)
  474         self.cache_path_index = os.path.join(cache_dir, "%s.index" % cache_name)
  475         self.cache_max_age = config.getint('ec2', 'cache_max_age')
  476 
  477         self.expand_csv_tags = config.getboolean('ec2', 'expand_csv_tags')
  478 
  479         # Configure nested groups instead of flat namespace.
  480         self.nested_groups = config.getboolean('ec2', 'nested_groups')
  481 
  482         # Replace dash or not in group names
  483         self.replace_dash_in_groups = config.getboolean('ec2', 'replace_dash_in_groups')
  484 
  485         # IAM role to assume for connection
  486         self.iam_role = config.get('ec2', 'iam_role')
  487 
  488         # Configure which groups should be created.
  489 
  490         group_by_options = [a for a in DEFAULTS if a.startswith('group_by')]
  491         for option in group_by_options:
  492             setattr(self, option, config.getboolean('ec2', option))
  493 
  494         # Do we need to just include hosts that match a pattern?
  495         self.pattern_include = config.get('ec2', 'pattern_include')
  496         if self.pattern_include:
  497             self.pattern_include = re.compile(self.pattern_include)
  498 
  499         # Do we need to exclude hosts that match a pattern?
  500         self.pattern_exclude = config.get('ec2', 'pattern_exclude')
  501         if self.pattern_exclude:
  502             self.pattern_exclude = re.compile(self.pattern_exclude)
  503 
  504         # Do we want to stack multiple filters?
  505         self.stack_filters = config.getboolean('ec2', 'stack_filters')
  506 
  507         # Instance filters (see boto and EC2 API docs). Ignore invalid filters.
  508         self.ec2_instance_filters = []
  509 
  510         if config.has_option('ec2', 'instance_filters') or 'EC2_INSTANCE_FILTERS' in os.environ:
  511             filters = os.getenv('EC2_INSTANCE_FILTERS', config.get('ec2', 'instance_filters') if config.has_option('ec2', 'instance_filters') else '')
  512 
  513             if self.stack_filters and '&' in filters:
  514                 self.fail_with_error("AND filters along with stack_filter enabled is not supported.\n")
  515 
  516             filter_sets = [f for f in filters.split(',') if f]
  517 
  518             for filter_set in filter_sets:
  519                 filters = {}
  520                 filter_set = filter_set.strip()
  521                 for instance_filter in filter_set.split("&"):
  522                     instance_filter = instance_filter.strip()
  523                     if not instance_filter or '=' not in instance_filter:
  524                         continue
  525                     filter_key, filter_value = [x.strip() for x in instance_filter.split('=', 1)]
  526                     if not filter_key:
  527                         continue
  528                     filters[filter_key] = filter_value
  529                 self.ec2_instance_filters.append(filters.copy())
  530 
  531     def parse_cli_args(self):
  532         ''' Command line argument processing '''
  533 
  534         parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on EC2')
  535         parser.add_argument('--list', action='store_true', default=True,
  536                             help='List instances (default: True)')
  537         parser.add_argument('--host', action='store',
  538                             help='Get all the variables about a specific instance')
  539         parser.add_argument('--refresh-cache', action='store_true', default=False,
  540                             help='Force refresh of cache by making API requests to EC2 (default: False - use cache files)')
  541         parser.add_argument('--profile', '--boto-profile', action='store', dest='boto_profile',
  542                             help='Use boto profile for connections to EC2')
  543         self.args = parser.parse_args()
  544 
  545     def do_api_calls_update_cache(self):
  546         ''' Do API calls to each region, and save data in cache files '''
  547 
  548         if self.route53_enabled:
  549             self.get_route53_records()
  550 
  551         for region in self.regions:
  552             self.get_instances_by_region(region)
  553             if self.rds_enabled:
  554                 self.get_rds_instances_by_region(region)
  555             if self.elasticache_enabled:
  556                 self.get_elasticache_clusters_by_region(region)
  557                 self.get_elasticache_replication_groups_by_region(region)
  558             if self.include_rds_clusters:
  559                 self.include_rds_clusters_by_region(region)
  560 
  561         self.write_to_cache(self.inventory, self.cache_path_cache)
  562         self.write_to_cache(self.index, self.cache_path_index)
  563 
  564     def connect(self, region):
  565         ''' create connection to api server'''
  566         if self.eucalyptus:
  567             conn = boto.connect_euca(host=self.eucalyptus_host, **self.credentials)
  568             conn.APIVersion = '2010-08-31'
  569         else:
  570             conn = self.connect_to_aws(ec2, region)
  571         return conn
  572 
  573     def boto_fix_security_token_in_profile(self, connect_args):
  574         ''' monkey patch for boto issue boto/boto#2100 '''
  575         profile = 'profile ' + self.boto_profile
  576         if boto.config.has_option(profile, 'aws_security_token'):
  577             connect_args['security_token'] = boto.config.get(profile, 'aws_security_token')
  578         return connect_args
  579 
  580     def connect_to_aws(self, module, region):
  581         connect_args = deepcopy(self.credentials)
  582 
  583         # only pass the profile name if it's set (as it is not supported by older boto versions)
  584         if self.boto_profile:
  585             connect_args['profile_name'] = self.boto_profile
  586             self.boto_fix_security_token_in_profile(connect_args)
  587         elif os.environ.get('AWS_SESSION_TOKEN'):
  588             connect_args['security_token'] = os.environ.get('AWS_SESSION_TOKEN')
  589 
  590         if self.iam_role:
  591             sts_conn = sts.connect_to_region(region, **connect_args)
  592             role = sts_conn.assume_role(self.iam_role, 'ansible_dynamic_inventory')
  593             connect_args['aws_access_key_id'] = role.credentials.access_key
  594             connect_args['aws_secret_access_key'] = role.credentials.secret_key
  595             connect_args['security_token'] = role.credentials.session_token
  596 
  597         conn = module.connect_to_region(region, **connect_args)
  598         # connect_to_region will fail "silently" by returning None if the region name is wrong or not supported
  599         if conn is None:
  600             self.fail_with_error("region name: %s likely not supported, or AWS is down.  connection to region failed." % region)
  601         return conn
  602 
  603     def get_instances_by_region(self, region):
  604         ''' Makes an AWS EC2 API call to the list of instances in a particular
  605         region '''
  606 
  607         try:
  608             conn = self.connect(region)
  609             reservations = []
  610             if self.ec2_instance_filters:
  611                 if self.stack_filters:
  612                     filters_dict = {}
  613                     for filters in self.ec2_instance_filters:
  614                         filters_dict.update(filters)
  615                     reservations.extend(conn.get_all_instances(filters=filters_dict))
  616                 else:
  617                     for filters in self.ec2_instance_filters:
  618                         reservations.extend(conn.get_all_instances(filters=filters))
  619             else:
  620                 reservations = conn.get_all_instances()
  621 
  622             # Pull the tags back in a second step
  623             # AWS are on record as saying that the tags fetched in the first `get_all_instances` request are not
  624             # reliable and may be missing, and the only way to guarantee they are there is by calling `get_all_tags`
  625             instance_ids = []
  626             for reservation in reservations:
  627                 instance_ids.extend([instance.id for instance in reservation.instances])
  628 
  629             max_filter_value = 199
  630             tags = []
  631             for i in range(0, len(instance_ids), max_filter_value):
  632                 tags.extend(conn.get_all_tags(filters={'resource-type': 'instance', 'resource-id': instance_ids[i:i + max_filter_value]}))
  633 
  634             tags_by_instance_id = defaultdict(dict)
  635             for tag in tags:
  636                 tags_by_instance_id[tag.res_id][tag.name] = tag.value
  637 
  638             if (not self.aws_account_id) and reservations:
  639                 self.aws_account_id = reservations[0].owner_id
  640 
  641             for reservation in reservations:
  642                 for instance in reservation.instances:
  643                     instance.tags = tags_by_instance_id[instance.id]
  644                     self.add_instance(instance, region)
  645 
  646         except boto.exception.BotoServerError as e:
  647             if e.error_code == 'AuthFailure':
  648                 error = self.get_auth_error_message()
  649             else:
  650                 backend = 'Eucalyptus' if self.eucalyptus else 'AWS'
  651                 error = "Error connecting to %s backend.\n%s" % (backend, e.message)
  652             self.fail_with_error(error, 'getting EC2 instances')
  653 
  654     def tags_match_filters(self, tags):
  655         ''' return True if given tags match configured filters '''
  656         if not self.ec2_instance_filters:
  657             return True
  658 
  659         for filters in self.ec2_instance_filters:
  660             for filter_name, filter_value in filters.items():
  661                 if filter_name[:4] != 'tag:':
  662                     continue
  663                 filter_name = filter_name[4:]
  664                 if filter_name not in tags:
  665                     if self.stack_filters:
  666                         return False
  667                     continue
  668                 if isinstance(filter_value, list):
  669                     if self.stack_filters and tags[filter_name] not in filter_value:
  670                         return False
  671                     if not self.stack_filters and tags[filter_name] in filter_value:
  672                         return True
  673                 if isinstance(filter_value, six.string_types):
  674                     if self.stack_filters and tags[filter_name] != filter_value:
  675                         return False
  676                     if not self.stack_filters and tags[filter_name] == filter_value:
  677                         return True
  678 
  679         return self.stack_filters
  680 
  681     def get_rds_instances_by_region(self, region):
  682         ''' Makes an AWS API call to the list of RDS instances in a particular
  683         region '''
  684 
  685         if not HAS_BOTO3:
  686             self.fail_with_error("Working with RDS instances requires boto3 - please install boto3 and try again",
  687                                  "getting RDS instances")
  688 
  689         client = ec2_utils.boto3_inventory_conn('client', 'rds', region, **self.credentials)
  690         db_instances = client.describe_db_instances()
  691 
  692         try:
  693             conn = self.connect_to_aws(rds, region)
  694             if conn:
  695                 marker = None
  696                 while True:
  697                     instances = conn.get_all_dbinstances(marker=marker)
  698                     marker = instances.marker
  699                     for index, instance in enumerate(instances):
  700                         # Add tags to instances.
  701                         instance.arn = db_instances['DBInstances'][index]['DBInstanceArn']
  702                         tags = client.list_tags_for_resource(ResourceName=instance.arn)['TagList']
  703                         instance.tags = {}
  704                         for tag in tags:
  705                             instance.tags[tag['Key']] = tag['Value']
  706                         if self.tags_match_filters(instance.tags):
  707                             self.add_rds_instance(instance, region)
  708                     if not marker:
  709                         break
  710         except boto.exception.BotoServerError as e:
  711             error = e.reason
  712 
  713             if e.error_code == 'AuthFailure':
  714                 error = self.get_auth_error_message()
  715             elif e.error_code == "OptInRequired":
  716                 error = "RDS hasn't been enabled for this account yet. " \
  717                     "You must either log in to the RDS service through the AWS console to enable it, " \
  718                     "or set 'rds = False' in ec2.ini"
  719             elif not e.reason == "Forbidden":
  720                 error = "Looks like AWS RDS is down:\n%s" % e.message
  721             self.fail_with_error(error, 'getting RDS instances')
  722 
  723     def include_rds_clusters_by_region(self, region):
  724         if not HAS_BOTO3:
  725             self.fail_with_error("Working with RDS clusters requires boto3 - please install boto3 and try again",
  726                                  "getting RDS clusters")
  727 
  728         client = ec2_utils.boto3_inventory_conn('client', 'rds', region, **self.credentials)
  729 
  730         marker, clusters = '', []
  731         while marker is not None:
  732             resp = client.describe_db_clusters(Marker=marker)
  733             clusters.extend(resp["DBClusters"])
  734             marker = resp.get('Marker', None)
  735 
  736         account_id = boto.connect_iam().get_user().arn.split(':')[4]
  737         c_dict = {}
  738         for c in clusters:
  739             if not self.ec2_instance_filters:
  740                 matches_filter = True
  741             else:
  742                 matches_filter = False
  743 
  744             try:
  745                 # arn:aws:rds:<region>:<account number>:<resourcetype>:<name>
  746                 tags = client.list_tags_for_resource(
  747                     ResourceName='arn:aws:rds:' + region + ':' + account_id + ':cluster:' + c['DBClusterIdentifier'])
  748                 c['Tags'] = tags['TagList']
  749 
  750                 if self.ec2_instance_filters:
  751                     for filters in self.ec2_instance_filters:
  752                         for filter_key, filter_values in filters.items():
  753                             # get AWS tag key e.g. tag:env will be 'env'
  754                             tag_name = filter_key.split(":", 1)[1]
  755                             # Filter values is a list (if you put multiple values for the same tag name)
  756                             matches_filter = any(d['Key'] == tag_name and d['Value'] in filter_values for d in c['Tags'])
  757 
  758                             if matches_filter:
  759                                 # it matches a filter, so stop looking for further matches
  760                                 break
  761 
  762                         if matches_filter:
  763                             break
  764 
  765             except Exception as e:
  766                 if e.message.find('DBInstanceNotFound') >= 0:
  767                     # AWS RDS bug (2016-01-06) means deletion does not fully complete and leave an 'empty' cluster.
  768                     # Ignore errors when trying to find tags for these
  769                     pass
  770 
  771             # ignore empty clusters caused by AWS bug
  772             if len(c['DBClusterMembers']) == 0:
  773                 continue
  774             elif matches_filter:
  775                 c_dict[c['DBClusterIdentifier']] = c
  776 
  777         self.inventory['db_clusters'] = c_dict
  778 
  779     def get_elasticache_clusters_by_region(self, region):
  780         ''' Makes an AWS API call to the list of ElastiCache clusters (with
  781         nodes' info) in a particular region.'''
  782 
  783         # ElastiCache boto module doesn't provide a get_all_instances method,
  784         # that's why we need to call describe directly (it would be called by
  785         # the shorthand method anyway...)
  786         clusters = []
  787         try:
  788             conn = self.connect_to_aws(elasticache, region)
  789             if conn:
  790                 # show_cache_node_info = True
  791                 # because we also want nodes' information
  792                 _marker = 1
  793                 while _marker:
  794                     if _marker == 1:
  795                         _marker = None
  796                     response = conn.describe_cache_clusters(None, None, _marker, True)
  797                     _marker = response['DescribeCacheClustersResponse']['DescribeCacheClustersResult']['Marker']
  798                     try:
  799                         # Boto also doesn't provide wrapper classes to CacheClusters or
  800                         # CacheNodes. Because of that we can't make use of the get_list
  801                         # method in the AWSQueryConnection. Let's do the work manually
  802                         clusters = clusters + response['DescribeCacheClustersResponse']['DescribeCacheClustersResult']['CacheClusters']
  803                     except KeyError as e:
  804                         error = "ElastiCache query to AWS failed (unexpected format)."
  805                         self.fail_with_error(error, 'getting ElastiCache clusters')
  806         except boto.exception.BotoServerError as e:
  807             error = e.reason
  808 
  809             if e.error_code == 'AuthFailure':
  810                 error = self.get_auth_error_message()
  811             elif e.error_code == "OptInRequired":
  812                 error = "ElastiCache hasn't been enabled for this account yet. " \
  813                     "You must either log in to the ElastiCache service through the AWS console to enable it, " \
  814                     "or set 'elasticache = False' in ec2.ini"
  815             elif not e.reason == "Forbidden":
  816                 error = "Looks like AWS ElastiCache is down:\n%s" % e.message
  817             self.fail_with_error(error, 'getting ElastiCache clusters')
  818 
  819         for cluster in clusters:
  820             self.add_elasticache_cluster(cluster, region)
  821 
  822     def get_elasticache_replication_groups_by_region(self, region):
  823         ''' Makes an AWS API call to the list of ElastiCache replication groups
  824         in a particular region.'''
  825 
  826         # ElastiCache boto module doesn't provide a get_all_instances method,
  827         # that's why we need to call describe directly (it would be called by
  828         # the shorthand method anyway...)
  829         try:
  830             conn = self.connect_to_aws(elasticache, region)
  831             if conn:
  832                 response = conn.describe_replication_groups()
  833 
  834         except boto.exception.BotoServerError as e:
  835             error = e.reason
  836 
  837             if e.error_code == 'AuthFailure':
  838                 error = self.get_auth_error_message()
  839             if not e.reason == "Forbidden":
  840                 error = "Looks like AWS ElastiCache [Replication Groups] is down:\n%s" % e.message
  841             self.fail_with_error(error, 'getting ElastiCache clusters')
  842 
  843         try:
  844             # Boto also doesn't provide wrapper classes to ReplicationGroups
  845             # Because of that we can't make use of the get_list method in the
  846             # AWSQueryConnection. Let's do the work manually
  847             replication_groups = response['DescribeReplicationGroupsResponse']['DescribeReplicationGroupsResult']['ReplicationGroups']
  848 
  849         except KeyError as e:
  850             error = "ElastiCache [Replication Groups] query to AWS failed (unexpected format)."
  851             self.fail_with_error(error, 'getting ElastiCache clusters')
  852 
  853         for replication_group in replication_groups:
  854             self.add_elasticache_replication_group(replication_group, region)
  855 
  856     def get_auth_error_message(self):
  857         ''' create an informative error message if there is an issue authenticating'''
  858         errors = ["Authentication error retrieving ec2 inventory."]
  859         if None in [os.environ.get('AWS_ACCESS_KEY_ID'), os.environ.get('AWS_SECRET_ACCESS_KEY')]:
  860             errors.append(' - No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY environment vars found')
  861         else:
  862             errors.append(' - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment vars found but may not be correct')
  863 
  864         boto_paths = ['/etc/boto.cfg', '~/.boto', '~/.aws/credentials']
  865         boto_config_found = [p for p in boto_paths if os.path.isfile(os.path.expanduser(p))]
  866         if len(boto_config_found) > 0:
  867             errors.append(" - Boto configs found at '%s', but the credentials contained may not be correct" % ', '.join(boto_config_found))
  868         else:
  869             errors.append(" - No Boto config found at any expected location '%s'" % ', '.join(boto_paths))
  870 
  871         return '\n'.join(errors)
  872 
  873     def fail_with_error(self, err_msg, err_operation=None):
  874         '''log an error to std err for ansible-playbook to consume and exit'''
  875         if err_operation:
  876             err_msg = 'ERROR: "{err_msg}", while: {err_operation}'.format(
  877                 err_msg=err_msg, err_operation=err_operation)
  878         sys.stderr.write(err_msg)
  879         sys.exit(1)
  880 
  881     def get_instance(self, region, instance_id):
  882         conn = self.connect(region)
  883 
  884         reservations = conn.get_all_instances([instance_id])
  885         for reservation in reservations:
  886             for instance in reservation.instances:
  887                 return instance
  888 
  889     def add_instance(self, instance, region):
  890         ''' Adds an instance to the inventory and index, as long as it is
  891         addressable '''
  892 
  893         # Only return instances with desired instance states
  894         if instance.state not in self.ec2_instance_states:
  895             return
  896 
  897         # Select the best destination address
  898         # When destination_format and destination_format_tags are specified
  899         # the following code will attempt to find the instance tags first,
  900         # then the instance attributes next, and finally if neither are found
  901         # assign nil for the desired destination format attribute.
  902         if self.destination_format and self.destination_format_tags:
  903             dest_vars = []
  904             inst_tags = getattr(instance, 'tags')
  905             for tag in self.destination_format_tags:
  906                 if tag in inst_tags:
  907                     dest_vars.append(inst_tags[tag])
  908                 elif hasattr(instance, tag):
  909                     dest_vars.append(getattr(instance, tag))
  910                 else:
  911                     dest_vars.append('nil')
  912 
  913             dest = self.destination_format.format(*dest_vars)
  914         elif instance.subnet_id:
  915             dest = getattr(instance, self.vpc_destination_variable, None)
  916             if dest is None:
  917                 dest = getattr(instance, 'tags').get(self.vpc_destination_variable, None)
  918         else:
  919             dest = getattr(instance, self.destination_variable, None)
  920             if dest is None:
  921                 dest = getattr(instance, 'tags').get(self.destination_variable, None)
  922 
  923         if not dest:
  924             # Skip instances we cannot address (e.g. private VPC subnet)
  925             return
  926 
  927         # Set the inventory name
  928         hostname = None
  929         if self.hostname_variable:
  930             if self.hostname_variable.startswith('tag_'):
  931                 hostname = instance.tags.get(self.hostname_variable[4:], None)
  932             else:
  933                 hostname = getattr(instance, self.hostname_variable)
  934 
  935         # set the hostname from route53
  936         if self.route53_enabled and self.route53_hostnames:
  937             route53_names = self.get_instance_route53_names(instance)
  938             for name in route53_names:
  939                 if name.endswith(self.route53_hostnames):
  940                     hostname = name
  941 
  942         # If we can't get a nice hostname, use the destination address
  943         if not hostname:
  944             hostname = dest
  945         # to_safe strips hostname characters like dots, so don't strip route53 hostnames
  946         elif self.route53_enabled and self.route53_hostnames and hostname.endswith(self.route53_hostnames):
  947             hostname = hostname.lower()
  948         else:
  949             hostname = self.to_safe(hostname).lower()
  950 
  951         # if we only want to include hosts that match a pattern, skip those that don't
  952         if self.pattern_include and not self.pattern_include.match(hostname):
  953             return
  954 
  955         # if we need to exclude hosts that match a pattern, skip those
  956         if self.pattern_exclude and self.pattern_exclude.match(hostname):
  957             return
  958 
  959         # Add to index
  960         self.index[hostname] = [region, instance.id]
  961 
  962         # Inventory: Group by instance ID (always a group of 1)
  963         if self.group_by_instance_id:
  964             self.inventory[instance.id] = [hostname]
  965             if self.nested_groups:
  966                 self.push_group(self.inventory, 'instances', instance.id)
  967 
  968         # Inventory: Group by region
  969         if self.group_by_region:
  970             self.push(self.inventory, region, hostname)
  971             if self.nested_groups:
  972                 self.push_group(self.inventory, 'regions', region)
  973 
  974         # Inventory: Group by availability zone
  975         if self.group_by_availability_zone:
  976             self.push(self.inventory, instance.placement, hostname)
  977             if self.nested_groups:
  978                 if self.group_by_region:
  979                     self.push_group(self.inventory, region, instance.placement)
  980                 self.push_group(self.inventory, 'zones', instance.placement)
  981 
  982         # Inventory: Group by Amazon Machine Image (AMI) ID
  983         if self.group_by_ami_id:
  984             ami_id = self.to_safe(instance.image_id)
  985             self.push(self.inventory, ami_id, hostname)
  986             if self.nested_groups:
  987                 self.push_group(self.inventory, 'images', ami_id)
  988 
  989         # Inventory: Group by instance type
  990         if self.group_by_instance_type:
  991             type_name = self.to_safe('type_' + instance.instance_type)
  992             self.push(self.inventory, type_name, hostname)
  993             if self.nested_groups:
  994                 self.push_group(self.inventory, 'types', type_name)
  995 
  996         # Inventory: Group by instance state
  997         if self.group_by_instance_state:
  998             state_name = self.to_safe('instance_state_' + instance.state)
  999             self.push(self.inventory, state_name, hostname)
 1000             if self.nested_groups:
 1001                 self.push_group(self.inventory, 'instance_states', state_name)
 1002 
 1003         # Inventory: Group by platform
 1004         if self.group_by_platform:
 1005             if instance.platform:
 1006                 platform = self.to_safe('platform_' + instance.platform)
 1007             else:
 1008                 platform = self.to_safe('platform_undefined')
 1009             self.push(self.inventory, platform, hostname)
 1010             if self.nested_groups:
 1011                 self.push_group(self.inventory, 'platforms', platform)
 1012 
 1013         # Inventory: Group by key pair
 1014         if self.group_by_key_pair and instance.key_name:
 1015             key_name = self.to_safe('key_' + instance.key_name)
 1016             self.push(self.inventory, key_name, hostname)
 1017             if self.nested_groups:
 1018                 self.push_group(self.inventory, 'keys', key_name)
 1019 
 1020         # Inventory: Group by VPC
 1021         if self.group_by_vpc_id and instance.vpc_id:
 1022             vpc_id_name = self.to_safe('vpc_id_' + instance.vpc_id)
 1023             self.push(self.inventory, vpc_id_name, hostname)
 1024             if self.nested_groups:
 1025                 self.push_group(self.inventory, 'vpcs', vpc_id_name)
 1026 
 1027         # Inventory: Group by security group
 1028         if self.group_by_security_group:
 1029             try:
 1030                 for group in instance.groups:
 1031                     key = self.to_safe("security_group_" + group.name)
 1032                     self.push(self.inventory, key, hostname)
 1033                     if self.nested_groups:
 1034                         self.push_group(self.inventory, 'security_groups', key)
 1035             except AttributeError:
 1036                 self.fail_with_error('\n'.join(['Package boto seems a bit older.',
 1037                                                 'Please upgrade boto >= 2.3.0.']))
 1038 
 1039         # Inventory: Group by AWS account ID
 1040         if self.group_by_aws_account:
 1041             self.push(self.inventory, self.aws_account_id, hostname)
 1042             if self.nested_groups:
 1043                 self.push_group(self.inventory, 'accounts', self.aws_account_id)
 1044 
 1045         # Inventory: Group by tag keys
 1046         if self.group_by_tag_keys:
 1047             for k, v in instance.tags.items():
 1048                 if self.expand_csv_tags and v and ',' in v:
 1049                     values = map(lambda x: x.strip(), v.split(','))
 1050                 else:
 1051                     values = [v]
 1052 
 1053                 for v in values:
 1054                     if v:
 1055                         key = self.to_safe("tag_" + k + "=" + v)
 1056                     else:
 1057                         key = self.to_safe("tag_" + k)
 1058                     self.push(self.inventory, key, hostname)
 1059                     if self.nested_groups:
 1060                         self.push_group(self.inventory, 'tags', self.to_safe("tag_" + k))
 1061                         if v:
 1062                             self.push_group(self.inventory, self.to_safe("tag_" + k), key)
 1063 
 1064         # Inventory: Group by Route53 domain names if enabled
 1065         if self.route53_enabled and self.group_by_route53_names:
 1066             route53_names = self.get_instance_route53_names(instance)
 1067             for name in route53_names:
 1068                 self.push(self.inventory, name, hostname)
 1069                 if self.nested_groups:
 1070                     self.push_group(self.inventory, 'route53', name)
 1071 
 1072         # Global Tag: instances without tags
 1073         if self.group_by_tag_none and len(instance.tags) == 0:
 1074             self.push(self.inventory, 'tag_none', hostname)
 1075             if self.nested_groups:
 1076                 self.push_group(self.inventory, 'tags', 'tag_none')
 1077 
 1078         # Global Tag: tag all EC2 instances
 1079         self.push(self.inventory, 'ec2', hostname)
 1080 
 1081         self.inventory["_meta"]["hostvars"][hostname] = self.get_host_info_dict_from_instance(instance)
 1082         self.inventory["_meta"]["hostvars"][hostname]['ansible_host'] = dest
 1083 
 1084     def add_rds_instance(self, instance, region):
 1085         ''' Adds an RDS instance to the inventory and index, as long as it is
 1086         addressable '''
 1087 
 1088         # Only want available instances unless all_rds_instances is True
 1089         if not self.all_rds_instances and instance.status != 'available':
 1090             return
 1091 
 1092         # Select the best destination address
 1093         dest = instance.endpoint[0]
 1094 
 1095         if not dest:
 1096             # Skip instances we cannot address (e.g. private VPC subnet)
 1097             return
 1098 
 1099         # Set the inventory name
 1100         hostname = None
 1101         if self.hostname_variable:
 1102             if self.hostname_variable.startswith('tag_'):
 1103                 hostname = instance.tags.get(self.hostname_variable[4:], None)
 1104             else:
 1105                 hostname = getattr(instance, self.hostname_variable)
 1106 
 1107         # If we can't get a nice hostname, use the destination address
 1108         if not hostname:
 1109             hostname = dest
 1110 
 1111         hostname = self.to_safe(hostname).lower()
 1112 
 1113         # Add to index
 1114         self.index[hostname] = [region, instance.id]
 1115 
 1116         # Inventory: Group by instance ID (always a group of 1)
 1117         if self.group_by_instance_id:
 1118             self.inventory[instance.id] = [hostname]
 1119             if self.nested_groups:
 1120                 self.push_group(self.inventory, 'instances', instance.id)
 1121 
 1122         # Inventory: Group by region
 1123         if self.group_by_region:
 1124             self.push(self.inventory, region, hostname)
 1125             if self.nested_groups:
 1126                 self.push_group(self.inventory, 'regions', region)
 1127 
 1128         # Inventory: Group by availability zone
 1129         if self.group_by_availability_zone:
 1130             self.push(self.inventory, instance.availability_zone, hostname)
 1131             if self.nested_groups:
 1132                 if self.group_by_region:
 1133                     self.push_group(self.inventory, region, instance.availability_zone)
 1134                 self.push_group(self.inventory, 'zones', instance.availability_zone)
 1135 
 1136         # Inventory: Group by instance type
 1137         if self.group_by_instance_type:
 1138             type_name = self.to_safe('type_' + instance.instance_class)
 1139             self.push(self.inventory, type_name, hostname)
 1140             if self.nested_groups:
 1141                 self.push_group(self.inventory, 'types', type_name)
 1142 
 1143         # Inventory: Group by VPC
 1144         if self.group_by_vpc_id and instance.subnet_group and instance.subnet_group.vpc_id:
 1145             vpc_id_name = self.to_safe('vpc_id_' + instance.subnet_group.vpc_id)
 1146             self.push(self.inventory, vpc_id_name, hostname)
 1147             if self.nested_groups:
 1148                 self.push_group(self.inventory, 'vpcs', vpc_id_name)
 1149 
 1150         # Inventory: Group by security group
 1151         if self.group_by_security_group:
 1152             try:
 1153                 if instance.security_group:
 1154                     key = self.to_safe("security_group_" + instance.security_group.name)
 1155                     self.push(self.inventory, key, hostname)
 1156                     if self.nested_groups:
 1157                         self.push_group(self.inventory, 'security_groups', key)
 1158 
 1159             except AttributeError:
 1160                 self.fail_with_error('\n'.join(['Package boto seems a bit older.',
 1161                                                 'Please upgrade boto >= 2.3.0.']))
 1162         # Inventory: Group by tag keys
 1163         if self.group_by_tag_keys:
 1164             for k, v in instance.tags.items():
 1165                 if self.expand_csv_tags and v and ',' in v:
 1166                     values = map(lambda x: x.strip(), v.split(','))
 1167                 else:
 1168                     values = [v]
 1169 
 1170                 for v in values:
 1171                     if v:
 1172                         key = self.to_safe("tag_" + k + "=" + v)
 1173                     else:
 1174                         key = self.to_safe("tag_" + k)
 1175                     self.push(self.inventory, key, hostname)
 1176                     if self.nested_groups:
 1177                         self.push_group(self.inventory, 'tags', self.to_safe("tag_" + k))
 1178                         if v:
 1179                             self.push_group(self.inventory, self.to_safe("tag_" + k), key)
 1180 
 1181         # Inventory: Group by engine
 1182         if self.group_by_rds_engine:
 1183             self.push(self.inventory, self.to_safe("rds_" + instance.engine), hostname)
 1184             if self.nested_groups:
 1185                 self.push_group(self.inventory, 'rds_engines', self.to_safe("rds_" + instance.engine))
 1186 
 1187         # Inventory: Group by parameter group
 1188         if self.group_by_rds_parameter_group:
 1189             self.push(self.inventory, self.to_safe("rds_parameter_group_" + instance.parameter_group.name), hostname)
 1190             if self.nested_groups:
 1191                 self.push_group(self.inventory, 'rds_parameter_groups', self.to_safe("rds_parameter_group_" + instance.parameter_group.name))
 1192 
 1193         # Global Tag: instances without tags
 1194         if self.group_by_tag_none and len(instance.tags) == 0:
 1195             self.push(self.inventory, 'tag_none', hostname)
 1196             if self.nested_groups:
 1197                 self.push_group(self.inventory, 'tags', 'tag_none')
 1198 
 1199         # Global Tag: all RDS instances
 1200         self.push(self.inventory, 'rds', hostname)
 1201 
 1202         self.inventory["_meta"]["hostvars"][hostname] = self.get_host_info_dict_from_instance(instance)
 1203         self.inventory["_meta"]["hostvars"][hostname]['ansible_host'] = dest
 1204 
 1205     def add_elasticache_cluster(self, cluster, region):
 1206         ''' Adds an ElastiCache cluster to the inventory and index, as long as
 1207         it's nodes are addressable '''
 1208 
 1209         # Only want available clusters unless all_elasticache_clusters is True
 1210         if not self.all_elasticache_clusters and cluster['CacheClusterStatus'] != 'available':
 1211             return
 1212 
 1213         # Select the best destination address
 1214         if 'ConfigurationEndpoint' in cluster and cluster['ConfigurationEndpoint']:
 1215             # Memcached cluster
 1216             dest = cluster['ConfigurationEndpoint']['Address']
 1217             is_redis = False
 1218         else:
 1219             # Redis sigle node cluster
 1220             # Because all Redis clusters are single nodes, we'll merge the
 1221             # info from the cluster with info about the node
 1222             dest = cluster['CacheNodes'][0]['Endpoint']['Address']
 1223             is_redis = True
 1224 
 1225         if not dest:
 1226             # Skip clusters we cannot address (e.g. private VPC subnet)
 1227             return
 1228 
 1229         # Add to index
 1230         self.index[dest] = [region, cluster['CacheClusterId']]
 1231 
 1232         # Inventory: Group by instance ID (always a group of 1)
 1233         if self.group_by_instance_id:
 1234             self.inventory[cluster['CacheClusterId']] = [dest]
 1235             if self.nested_groups:
 1236                 self.push_group(self.inventory, 'instances', cluster['CacheClusterId'])
 1237 
 1238         # Inventory: Group by region
 1239         if self.group_by_region and not is_redis:
 1240             self.push(self.inventory, region, dest)
 1241             if self.nested_groups:
 1242                 self.push_group(self.inventory, 'regions', region)
 1243 
 1244         # Inventory: Group by availability zone
 1245         if self.group_by_availability_zone and not is_redis:
 1246             self.push(self.inventory, cluster['PreferredAvailabilityZone'], dest)
 1247             if self.nested_groups:
 1248                 if self.group_by_region:
 1249                     self.push_group(self.inventory, region, cluster['PreferredAvailabilityZone'])
 1250                 self.push_group(self.inventory, 'zones', cluster['PreferredAvailabilityZone'])
 1251 
 1252         # Inventory: Group by node type
 1253         if self.group_by_instance_type and not is_redis:
 1254             type_name = self.to_safe('type_' + cluster['CacheNodeType'])
 1255             self.push(self.inventory, type_name, dest)
 1256             if self.nested_groups:
 1257                 self.push_group(self.inventory, 'types', type_name)
 1258 
 1259         # Inventory: Group by VPC (information not available in the current
 1260         # AWS API version for ElastiCache)
 1261 
 1262         # Inventory: Group by security group
 1263         if self.group_by_security_group and not is_redis:
 1264 
 1265             # Check for the existence of the 'SecurityGroups' key and also if
 1266             # this key has some value. When the cluster is not placed in a SG
 1267             # the query can return None here and cause an error.
 1268             if 'SecurityGroups' in cluster and cluster['SecurityGroups'] is not None:
 1269                 for security_group in cluster['SecurityGroups']:
 1270                     key = self.to_safe("security_group_" + security_group['SecurityGroupId'])
 1271                     self.push(self.inventory, key, dest)
 1272                     if self.nested_groups:
 1273                         self.push_group(self.inventory, 'security_groups', key)
 1274 
 1275         # Inventory: Group by engine
 1276         if self.group_by_elasticache_engine and not is_redis:
 1277             self.push(self.inventory, self.to_safe("elasticache_" + cluster['Engine']), dest)
 1278             if self.nested_groups:
 1279                 self.push_group(self.inventory, 'elasticache_engines', self.to_safe(cluster['Engine']))
 1280 
 1281         # Inventory: Group by parameter group
 1282         if self.group_by_elasticache_parameter_group:
 1283             self.push(self.inventory, self.to_safe("elasticache_parameter_group_" + cluster['CacheParameterGroup']['CacheParameterGroupName']), dest)
 1284             if self.nested_groups:
 1285                 self.push_group(self.inventory, 'elasticache_parameter_groups', self.to_safe(cluster['CacheParameterGroup']['CacheParameterGroupName']))
 1286 
 1287         # Inventory: Group by replication group
 1288         if self.group_by_elasticache_replication_group and 'ReplicationGroupId' in cluster and cluster['ReplicationGroupId']:
 1289             self.push(self.inventory, self.to_safe("elasticache_replication_group_" + cluster['ReplicationGroupId']), dest)
 1290             if self.nested_groups:
 1291                 self.push_group(self.inventory, 'elasticache_replication_groups', self.to_safe(cluster['ReplicationGroupId']))
 1292 
 1293         # Global Tag: all ElastiCache clusters
 1294         self.push(self.inventory, 'elasticache_clusters', cluster['CacheClusterId'])
 1295 
 1296         host_info = self.get_host_info_dict_from_describe_dict(cluster)
 1297 
 1298         self.inventory["_meta"]["hostvars"][dest] = host_info
 1299 
 1300         # Add the nodes
 1301         for node in cluster['CacheNodes']:
 1302             self.add_elasticache_node(node, cluster, region)
 1303 
 1304     def add_elasticache_node(self, node, cluster, region):
 1305         ''' Adds an ElastiCache node to the inventory and index, as long as
 1306         it is addressable '''
 1307 
 1308         # Only want available nodes unless all_elasticache_nodes is True
 1309         if not self.all_elasticache_nodes and node['CacheNodeStatus'] != 'available':
 1310             return
 1311 
 1312         # Select the best destination address
 1313         dest = node['Endpoint']['Address']
 1314 
 1315         if not dest:
 1316             # Skip nodes we cannot address (e.g. private VPC subnet)
 1317             return
 1318 
 1319         node_id = self.to_safe(cluster['CacheClusterId'] + '_' + node['CacheNodeId'])
 1320 
 1321         # Add to index
 1322         self.index[dest] = [region, node_id]
 1323 
 1324         # Inventory: Group by node ID (always a group of 1)
 1325         if self.group_by_instance_id:
 1326             self.inventory[node_id] = [dest]
 1327             if self.nested_groups:
 1328                 self.push_group(self.inventory, 'instances', node_id)
 1329 
 1330         # Inventory: Group by region
 1331         if self.group_by_region:
 1332             self.push(self.inventory, region, dest)
 1333             if self.nested_groups:
 1334                 self.push_group(self.inventory, 'regions', region)
 1335 
 1336         # Inventory: Group by availability zone
 1337         if self.group_by_availability_zone:
 1338             self.push(self.inventory, cluster['PreferredAvailabilityZone'], dest)
 1339             if self.nested_groups:
 1340                 if self.group_by_region:
 1341                     self.push_group(self.inventory, region, cluster['PreferredAvailabilityZone'])
 1342                 self.push_group(self.inventory, 'zones', cluster['PreferredAvailabilityZone'])
 1343 
 1344         # Inventory: Group by node type
 1345         if self.group_by_instance_type:
 1346             type_name = self.to_safe('type_' + cluster['CacheNodeType'])
 1347             self.push(self.inventory, type_name, dest)
 1348             if self.nested_groups:
 1349                 self.push_group(self.inventory, 'types', type_name)
 1350 
 1351         # Inventory: Group by VPC (information not available in the current
 1352         # AWS API version for ElastiCache)
 1353 
 1354         # Inventory: Group by security group
 1355         if self.group_by_security_group:
 1356 
 1357             # Check for the existence of the 'SecurityGroups' key and also if
 1358             # this key has some value. When the cluster is not placed in a SG
 1359             # the query can return None here and cause an error.
 1360             if 'SecurityGroups' in cluster and cluster['SecurityGroups'] is not None:
 1361                 for security_group in cluster['SecurityGroups']:
 1362                     key = self.to_safe("security_group_" + security_group['SecurityGroupId'])
 1363                     self.push(self.inventory, key, dest)
 1364                     if self.nested_groups:
 1365                         self.push_group(self.inventory, 'security_groups', key)
 1366 
 1367         # Inventory: Group by engine
 1368         if self.group_by_elasticache_engine:
 1369             self.push(self.inventory, self.to_safe("elasticache_" + cluster['Engine']), dest)
 1370             if self.nested_groups:
 1371                 self.push_group(self.inventory, 'elasticache_engines', self.to_safe("elasticache_" + cluster['Engine']))
 1372 
 1373         # Inventory: Group by parameter group (done at cluster level)
 1374 
 1375         # Inventory: Group by replication group (done at cluster level)
 1376 
 1377         # Inventory: Group by ElastiCache Cluster
 1378         if self.group_by_elasticache_cluster:
 1379             self.push(self.inventory, self.to_safe("elasticache_cluster_" + cluster['CacheClusterId']), dest)
 1380 
 1381         # Global Tag: all ElastiCache nodes
 1382         self.push(self.inventory, 'elasticache_nodes', dest)
 1383 
 1384         host_info = self.get_host_info_dict_from_describe_dict(node)
 1385 
 1386         if dest in self.inventory["_meta"]["hostvars"]:
 1387             self.inventory["_meta"]["hostvars"][dest].update(host_info)
 1388         else:
 1389             self.inventory["_meta"]["hostvars"][dest] = host_info
 1390 
 1391     def add_elasticache_replication_group(self, replication_group, region):
 1392         ''' Adds an ElastiCache replication group to the inventory and index '''
 1393 
 1394         # Only want available clusters unless all_elasticache_replication_groups is True
 1395         if not self.all_elasticache_replication_groups and replication_group['Status'] != 'available':
 1396             return
 1397 
 1398         # Skip clusters we cannot address (e.g. private VPC subnet or clustered redis)
 1399         if replication_group['NodeGroups'][0]['PrimaryEndpoint'] is None or \
 1400            replication_group['NodeGroups'][0]['PrimaryEndpoint']['Address'] is None:
 1401             return
 1402 
 1403         # Select the best destination address (PrimaryEndpoint)
 1404         dest = replication_group['NodeGroups'][0]['PrimaryEndpoint']['Address']
 1405 
 1406         # Add to index
 1407         self.index[dest] = [region, replication_group['ReplicationGroupId']]
 1408 
 1409         # Inventory: Group by ID (always a group of 1)
 1410         if self.group_by_instance_id:
 1411             self.inventory[replication_group['ReplicationGroupId']] = [dest]
 1412             if self.nested_groups:
 1413                 self.push_group(self.inventory, 'instances', replication_group['ReplicationGroupId'])
 1414 
 1415         # Inventory: Group by region
 1416         if self.group_by_region:
 1417             self.push(self.inventory, region, dest)
 1418             if self.nested_groups:
 1419                 self.push_group(self.inventory, 'regions', region)
 1420 
 1421         # Inventory: Group by availability zone (doesn't apply to replication groups)
 1422 
 1423         # Inventory: Group by node type (doesn't apply to replication groups)
 1424 
 1425         # Inventory: Group by VPC (information not available in the current
 1426         # AWS API version for replication groups
 1427 
 1428         # Inventory: Group by security group (doesn't apply to replication groups)
 1429         # Check this value in cluster level
 1430 
 1431         # Inventory: Group by engine (replication groups are always Redis)
 1432         if self.group_by_elasticache_engine:
 1433             self.push(self.inventory, 'elasticache_redis', dest)
 1434             if self.nested_groups:
 1435                 self.push_group(self.inventory, 'elasticache_engines', 'redis')
 1436 
 1437         # Global Tag: all ElastiCache clusters
 1438         self.push(self.inventory, 'elasticache_replication_groups', replication_group['ReplicationGroupId'])
 1439 
 1440         host_info = self.get_host_info_dict_from_describe_dict(replication_group)
 1441 
 1442         self.inventory["_meta"]["hostvars"][dest] = host_info
 1443 
 1444     def get_route53_records(self):
 1445         ''' Get and store the map of resource records to domain names that
 1446         point to them. '''
 1447 
 1448         if self.boto_profile:
 1449             r53_conn = route53.Route53Connection(profile_name=self.boto_profile)
 1450         else:
 1451             r53_conn = route53.Route53Connection()
 1452         all_zones = r53_conn.get_zones()
 1453 
 1454         route53_zones = [zone for zone in all_zones if zone.name[:-1] not in self.route53_excluded_zones]
 1455 
 1456         self.route53_records = {}
 1457 
 1458         for zone in route53_zones:
 1459             rrsets = r53_conn.get_all_rrsets(zone.id)
 1460 
 1461             for record_set in rrsets:
 1462                 record_name = record_set.name
 1463 
 1464                 if record_name.endswith('.'):
 1465                     record_name = record_name[:-1]
 1466 
 1467                 for resource in record_set.resource_records:
 1468                     self.route53_records.setdefault(resource, set())
 1469                     self.route53_records[resource].add(record_name)
 1470 
 1471     def get_instance_route53_names(self, instance):
 1472         ''' Check if an instance is referenced in the records we have from
 1473         Route53. If it is, return the list of domain names pointing to said
 1474         instance. If nothing points to it, return an empty list. '''
 1475 
 1476         instance_attributes = ['public_dns_name', 'private_dns_name',
 1477                                'ip_address', 'private_ip_address']
 1478 
 1479         name_list = set()
 1480 
 1481         for attrib in instance_attributes:
 1482             try:
 1483                 value = getattr(instance, attrib)
 1484             except AttributeError:
 1485                 continue
 1486 
 1487             if value in self.route53_records:
 1488                 name_list.update(self.route53_records[value])
 1489 
 1490         return list(name_list)
 1491 
 1492     def get_host_info_dict_from_instance(self, instance):
 1493         instance_vars = {}
 1494         for key in vars(instance):
 1495             value = getattr(instance, key)
 1496             key = self.to_safe('ec2_' + key)
 1497 
 1498             # Handle complex types
 1499             # state/previous_state changed to properties in boto in https://github.com/boto/boto/commit/a23c379837f698212252720d2af8dec0325c9518
 1500             if key == 'ec2__state':
 1501                 instance_vars['ec2_state'] = instance.state or ''
 1502                 instance_vars['ec2_state_code'] = instance.state_code
 1503             elif key == 'ec2__previous_state':
 1504                 instance_vars['ec2_previous_state'] = instance.previous_state or ''
 1505                 instance_vars['ec2_previous_state_code'] = instance.previous_state_code
 1506             elif isinstance(value, (int, bool)):
 1507                 instance_vars[key] = value
 1508             elif isinstance(value, six.string_types):
 1509                 instance_vars[key] = value.strip()
 1510             elif value is None:
 1511                 instance_vars[key] = ''
 1512             elif key == 'ec2_region':
 1513                 instance_vars[key] = value.name
 1514             elif key == 'ec2__placement':
 1515                 instance_vars['ec2_placement'] = value.zone
 1516             elif key == 'ec2_tags':
 1517                 for k, v in value.items():
 1518                     if self.expand_csv_tags and ',' in v:
 1519                         v = list(map(lambda x: x.strip(), v.split(',')))
 1520                     key = self.to_safe('ec2_tag_' + k)
 1521                     instance_vars[key] = v
 1522             elif key == 'ec2_groups':
 1523                 group_ids = []
 1524                 group_names = []
 1525                 for group in value:
 1526                     group_ids.append(group.id)
 1527                     group_names.append(group.name)
 1528                 instance_vars["ec2_security_group_ids"] = ','.join([str(i) for i in group_ids])
 1529                 instance_vars["ec2_security_group_names"] = ','.join([str(i) for i in group_names])
 1530             elif key == 'ec2_block_device_mapping':
 1531                 instance_vars["ec2_block_devices"] = {}
 1532                 for k, v in value.items():
 1533                     instance_vars["ec2_block_devices"][os.path.basename(k)] = v.volume_id
 1534             else:
 1535                 pass
 1536                 # TODO Product codes if someone finds them useful
 1537                 # print key
 1538                 # print type(value)
 1539                 # print value
 1540 
 1541         instance_vars[self.to_safe('ec2_account_id')] = self.aws_account_id
 1542 
 1543         return instance_vars
 1544 
 1545     def get_host_info_dict_from_describe_dict(self, describe_dict):
 1546         ''' Parses the dictionary returned by the API call into a flat list
 1547             of parameters. This method should be used only when 'describe' is
 1548             used directly because Boto doesn't provide specific classes. '''
 1549 
 1550         # I really don't agree with prefixing everything with 'ec2'
 1551         # because EC2, RDS and ElastiCache are different services.
 1552         # I'm just following the pattern used until now to not break any
 1553         # compatibility.
 1554 
 1555         host_info = {}
 1556         for key in describe_dict:
 1557             value = describe_dict[key]
 1558             key = self.to_safe('ec2_' + self.uncammelize(key))
 1559 
 1560             # Handle complex types
 1561 
 1562             # Target: Memcached Cache Clusters
 1563             if key == 'ec2_configuration_endpoint' and value:
 1564                 host_info['ec2_configuration_endpoint_address'] = value['Address']
 1565                 host_info['ec2_configuration_endpoint_port'] = value['Port']
 1566 
 1567             # Target: Cache Nodes and Redis Cache Clusters (single node)
 1568             if key == 'ec2_endpoint' and value:
 1569                 host_info['ec2_endpoint_address'] = value['Address']
 1570                 host_info['ec2_endpoint_port'] = value['Port']
 1571 
 1572             # Target: Redis Replication Groups
 1573             if key == 'ec2_node_groups' and value:
 1574                 host_info['ec2_endpoint_address'] = value[0]['PrimaryEndpoint']['Address']
 1575                 host_info['ec2_endpoint_port'] = value[0]['PrimaryEndpoint']['Port']
 1576                 replica_count = 0
 1577                 for node in value[0]['NodeGroupMembers']:
 1578                     if node['CurrentRole'] == 'primary':
 1579                         host_info['ec2_primary_cluster_address'] = node['ReadEndpoint']['Address']
 1580                         host_info['ec2_primary_cluster_port'] = node['ReadEndpoint']['Port']
 1581                         host_info['ec2_primary_cluster_id'] = node['CacheClusterId']
 1582                     elif node['CurrentRole'] == 'replica':
 1583                         host_info['ec2_replica_cluster_address_' + str(replica_count)] = node['ReadEndpoint']['Address']
 1584                         host_info['ec2_replica_cluster_port_' + str(replica_count)] = node['ReadEndpoint']['Port']
 1585                         host_info['ec2_replica_cluster_id_' + str(replica_count)] = node['CacheClusterId']
 1586                         replica_count += 1
 1587 
 1588             # Target: Redis Replication Groups
 1589             if key == 'ec2_member_clusters' and value:
 1590                 host_info['ec2_member_clusters'] = ','.join([str(i) for i in value])
 1591 
 1592             # Target: All Cache Clusters
 1593             elif key == 'ec2_cache_parameter_group':
 1594                 host_info["ec2_cache_node_ids_to_reboot"] = ','.join([str(i) for i in value['CacheNodeIdsToReboot']])
 1595                 host_info['ec2_cache_parameter_group_name'] = value['CacheParameterGroupName']
 1596                 host_info['ec2_cache_parameter_apply_status'] = value['ParameterApplyStatus']
 1597 
 1598             # Target: Almost everything
 1599             elif key == 'ec2_security_groups':
 1600 
 1601                 # Skip if SecurityGroups is None
 1602                 # (it is possible to have the key defined but no value in it).
 1603                 if value is not None:
 1604                     sg_ids = []
 1605                     for sg in value:
 1606                         sg_ids.append(sg['SecurityGroupId'])
 1607                     host_info["ec2_security_group_ids"] = ','.join([str(i) for i in sg_ids])
 1608 
 1609             # Target: Everything
 1610             # Preserve booleans and integers
 1611             elif isinstance(value, (int, bool)):
 1612                 host_info[key] = value
 1613 
 1614             # Target: Everything
 1615             # Sanitize string values
 1616             elif isinstance(value, six.string_types):
 1617                 host_info[key] = value.strip()
 1618 
 1619             # Target: Everything
 1620             # Replace None by an empty string
 1621             elif value is None:
 1622                 host_info[key] = ''
 1623 
 1624             else:
 1625                 # Remove non-processed complex types
 1626                 pass
 1627 
 1628         return host_info
 1629 
 1630     def get_host_info(self):
 1631         ''' Get variables about a specific host '''
 1632 
 1633         if len(self.index) == 0:
 1634             # Need to load index from cache
 1635             self.load_index_from_cache()
 1636 
 1637         if self.args.host not in self.index:
 1638             # try updating the cache
 1639             self.do_api_calls_update_cache()
 1640             if self.args.host not in self.index:
 1641                 # host might not exist anymore
 1642                 return self.json_format_dict({}, True)
 1643 
 1644         (region, instance_id) = self.index[self.args.host]
 1645 
 1646         instance = self.get_instance(region, instance_id)
 1647         return self.json_format_dict(self.get_host_info_dict_from_instance(instance), True)
 1648 
 1649     def push(self, my_dict, key, element):
 1650         ''' Push an element onto an array that may not have been defined in
 1651         the dict '''
 1652         group_info = my_dict.setdefault(key, [])
 1653         if isinstance(group_info, dict):
 1654             host_list = group_info.setdefault('hosts', [])
 1655             host_list.append(element)
 1656         else:
 1657             group_info.append(element)
 1658 
 1659     def push_group(self, my_dict, key, element):
 1660         ''' Push a group as a child of another group. '''
 1661         parent_group = my_dict.setdefault(key, {})
 1662         if not isinstance(parent_group, dict):
 1663             parent_group = my_dict[key] = {'hosts': parent_group}
 1664         child_groups = parent_group.setdefault('children', [])
 1665         if element not in child_groups:
 1666             child_groups.append(element)
 1667 
 1668     def get_inventory_from_cache(self):
 1669         ''' Reads the inventory from the cache file and returns it as a JSON
 1670         object '''
 1671 
 1672         with open(self.cache_path_cache, 'r') as f:
 1673             json_inventory = f.read()
 1674             return json_inventory
 1675 
 1676     def load_index_from_cache(self):
 1677         ''' Reads the index from the cache file sets self.index '''
 1678 
 1679         with open(self.cache_path_index, 'rb') as f:
 1680             self.index = json.load(f)
 1681 
 1682     def write_to_cache(self, data, filename):
 1683         ''' Writes data in JSON format to a file '''
 1684 
 1685         json_data = self.json_format_dict(data, True)
 1686         with open(filename, 'w') as f:
 1687             f.write(json_data)
 1688 
 1689     def uncammelize(self, key):
 1690         temp = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
 1691         return re.sub('([a-z0-9])([A-Z])', r'\1_\2', temp).lower()
 1692 
 1693     def to_safe(self, word):
 1694         ''' Converts 'bad' characters in a string to underscores so they can be used as Ansible groups '''
 1695         regex = r"[^A-Za-z0-9\_"
 1696         if not self.replace_dash_in_groups:
 1697             regex += r"\-"
 1698         return re.sub(regex + "]", "_", word)
 1699 
 1700     def json_format_dict(self, data, pretty=False):
 1701         ''' Converts a dict to a JSON object and dumps it as a formatted
 1702         string '''
 1703 
 1704         if pretty:
 1705             return json.dumps(data, sort_keys=True, indent=2, default=self._json_serial)
 1706         else:
 1707             return json.dumps(data, default=self._json_serial)
 1708 
 1709 
 1710 if __name__ == '__main__':
 1711     # Run the script
 1712     Ec2Inventory()
