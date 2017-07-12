#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import requests
# import logging

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['stableinterface'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: kafka_connect
short_description: Deploy Kafka connectors configurations onto your Kafka connect instances
description:
    - This module deploys kafka connectors configuration on your connect instances
    - Ensures that the existing configurations haven't changed
    - Can delete the missing connectors if wanted
    - This module has been tested with Kafka Connect 0.10.2.1
version_added: 2.4
author: Stephane Maarek (@simplesteph)
options:
    connect_base_url:
        description:
            - Kafka Connect base URL, prefixed with http:// or https://
            - Should include the port ex: http://127.0.0.1:8083/
        required: true
        version_added: 2.4
    connectors:
        description:
            - Array of connector configurations with the form key=value
            - Each connector must have the "name", "connector.class" and "tasks.max" parameters
        required: true
        version_added: 2.4
    delete_missing:
        description:
            - Set to "yes" if you want to delete any other connectors that does not exist in the connectors array
        choices: ["yes", "no"]
        default: "yes"
        required: false
        version_added: 2.4
requirements:
    - Make sure the requests python module is installed
notes: Check mode isn't supported
'''

EXAMPLES = '''
# Only add or update this connector
- name:                   Test that my module works
  kafka_connect:
   connect_base:          "http://localhost:8083"
   connectors:
    - name:               "hdfs-sink-connector"
      connector.class:    "io.confluent.connect.hdfs.HdfsSinkConnector"
      tasks.max:          "10"
      topics:             "test-topic"
      hdfs.url:           "hdfs://fakehost:9000"
      hadoop.conf.dir:    "/opt/hadoop/conf"
      hadoop.home:        "/opt/hadoop"
      flush.size:         "100"
      rotate.interval.ms: 1000
   delete_missing:        no
  register:               result

- debug:                  var=result

# Delete all the other connectors but this one
- name:                   Test that my module works
  kafka_connect:
   connect_base:          "http://localhost:8083"
   connectors:
    - name:               "hdfs-sink-connector"
      connector.class:    "io.confluent.connect.hdfs.HdfsSinkConnector"
      tasks.max:          "10"
      topics:             "test-topic"
      hdfs.url:           "hdfs://fakehost:9000"
      hadoop.conf.dir:    "/opt/hadoop/conf"
      hadoop.home:        "/opt/hadoop"
      flush.size:         "100"
      rotate.interval.ms: 1000
   delete_missing:        yes
  register:               result
'''

RETURN = '''
deleted:
    description: list of connector names that were deleted
    type: list
new:
    description: list of connector configs that were added
    type: list
updated:
    description: list of connector configs that were updated
'''


def convert_dict_values_to_str(connector):
    return dict([key, str(value)] for key, value in connector.iteritems())


def main():
    module = AnsibleModule(
        argument_spec=dict(
            connect_base_url=dict(required=True, type='str'),
            connectors=dict(required=True, type='list'),
            delete_missing=dict(default=True, type='bool')
        )
    )

    changed = False

    final_new = []
    final_updated = []
    final_deleted = []

    # cast values of configs as strings
    connectors = [convert_dict_values_to_str(
        connector) for connector in module.params['connectors']]
    # remove the trailing backslash if provided
    if not (module.params['connect_base_url'].startswith("http://") or
            module.params['connect_base_url'].startswith("https://")):
        module.fail_json(
            msg="please prefix your connect_base_url by http:// or https://")

    connect_base_url = module.params['connect_base_url'].rstrip('/')

    if not (can_connect_to_rest_api(connect_base_url)):
        module.fail_json(msg="Can't connect to Kafka Connect REST Interface, check the base URL",
                         connect_base_url=connect_base_url)

    missing_params_connectors = validate_connectors_mandatory_parameters(
        connectors)
    if len(missing_params_connectors) > 0:
        module.fail_json(msg="These connectors are missing 'name', 'tasks.max' or 'connector.class' attributes",
                         missing_names=missing_params_connectors)

    invalid_connectors = validate_connectors_api(connect_base_url, connectors)
    if len(invalid_connectors) > 0:
        module.fail_json(msg="These connector configurations could not be validated",
                         invalid_connectors=invalid_connectors)

    # get the list of connectors and compare
    existing_connectors = load_existing_connectors(connect_base_url)
    connector_names = [c['name'] for c in connectors]

    new_connectors_configs = [c for c in connectors if c[
        'name'] not in existing_connectors]
    updated_connectors_configs = [
        c for c in connectors if c['name'] in existing_connectors]
    deleted_connectors_names = [
        c_name for c_name in existing_connectors if c_name not in connector_names]

    for new_connector_config in new_connectors_configs:
        # these should all be 201
        config = create_or_update_connector(
            connect_base_url, new_connector_config)["config"]
        final_new.append(config)
        changed = True

    for uc in updated_connectors_configs:
        previous_config = get_connector_config(connect_base_url, uc['name'])
        # these should all be 200.
        config = create_or_update_connector(connect_base_url, uc)["config"]
        new_config = get_connector_config(connect_base_url, uc['name'])
        if new_config != previous_config:
            changed = True
            final_updated.append(config)

    # apply configurations one by one
    if module.params['delete_missing']:
        for deleted_connector_name in deleted_connectors_names:
            delete_connector(connect_base_url, deleted_connector_name)
            final_deleted.append(deleted_connector_name)
            changed = True
    elif deleted_connectors_names:
        print("NOT DELETING any connectors since deletion is disabled")

    meta = {
        'new': final_new,
        'updated': final_updated,
        'deleted': final_deleted
    }

    module.exit_json(changed=changed, meta=meta)


def can_connect_to_rest_api(connect_base_url):
    return requests.get(connect_base_url).status_code == 200


def missing_parameters(connector):
    return "name" not in connector or "connector.class" not in connector or "tasks.max" not in connector


def validate_connectors_mandatory_parameters(connectors):
    invalid_connectors = [c for c in connectors if missing_parameters(c)]
    return invalid_connectors


def validate_connectors_api(connect_base_url, connectors):
    invalid_connectors = [{connector['name']:
                           {'config': connector,
                            'errors': validate_connector_api(connect_base_url, connector)}
                           }
                          for connector in connectors if len(validate_connector_api(connect_base_url, connector)) > 0]
    return invalid_connectors


def validate_connector_api(connect_base_url, connector):
    response = requests.put(connect_base_url + '/connector-plugins/' + connector['connector.class'] + '/config/validate',
                            json=connector).json()
    invalid_configs = [config for config in response['configs'] if
                       'errors' in config['value'] and len(config['value']['errors']) > 0]
    return invalid_configs


def load_existing_connectors(connect_base_url):
    return requests.get(connect_base_url + '/connectors/').json()


# http://docs.confluent.io/current/connect/restapi.html#put--connectors-(string-name)-config
def create_or_update_connector(connect_base_url, new_connector_config):
    response = requests.put(connect_base_url + '/connectors/' + new_connector_config['name'] + '/config',
                            json=new_connector_config)
    status = response.status_code
    # logging.debug(status)
    # logging.debug(response.content)
    if (status == 200):
        "updated"
    if (status == 201):
        "created"
    if (status == 409):
        "conflict - rebalancing - retry?"
    return response.json()


def get_connector_config(connect_base_url, connector_name):
    response = requests.get(
        connect_base_url + '/connectors/' + connector_name + '/config').json()
    return response


def delete_connector(connect_base_url, name):
    req = requests.delete(connect_base_url + '/connectors/' + name + '/')
    req.raise_for_status()


if __name__ == '__main__':
    # logging.basicConfig(filename='/tmp/ansible_debug.log', level=logging.DEBUG)
    main()
