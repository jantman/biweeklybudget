#!/usr/bin/env python
"""
Use like: eval $(dev/ecsenv.py)
"""

import boto3
import logging
from biweeklybudget.cliutils import set_log_info
import json
from pprint import pprint

logger = logging.getLogger(__name__)

format = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=format)
logger = logging.getLogger()
set_log_info(logger)

client = boto3.client('ecs', region_name='us-west-2')
logger.info('Describing "biweeklybudget" service in "personal" ECS cluster...')
svcs = client.describe_services(cluster='personal', services=['biweeklybudget'])
tdef_arn = svcs['services'][0]['deployments'][0]['taskDefinition']
logger.info('Task definition: %s', tdef_arn)
resp = client.describe_task_definition(taskDefinition=tdef_arn)
tdef = resp['taskDefinition']
cdef = tdef['containerDefinitions'][0]
for e in cdef['environment']:
    print(f'export {e["name"]}="{e["value"]}"')
