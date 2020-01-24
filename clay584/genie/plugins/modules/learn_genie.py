#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    "metadata_version": "0.1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: learn_genie

short_description: This module utilizes the Cisco PyATS/Genie framework to "learn" features from network devices.

version_added: "2.9"

description:
    - "This module allows for the user of the Ansible module to reach out to a network device and pull back CLI data, parse it, and 'learn' the entirety of a given feature on a network device."

options:
    host:
        description:
            - The network device that PyATS/Genie should connect to
        required: true
    port:
        description:
            - The port number for SSH on the device
        required: false
    username:
        description:
            - The username used to connect to the device
        required: true
    password:
        description:
            - The password used to connect to the device
        required: true
    os:
        description:
            - Network operating system of the device
        required: true
    connection:
        description:
            - What connection mechanism used. Currently, only unicon is supported.
        required: false
    feature:
        description:
            - The device feature to be learned from the device

# extends_documentation_fragment:
#     - azure

author:
    - Clay Curtis (@ccurtis584)
"""

EXAMPLES = """
# Learn a feature
- name: Learn BGP Feature
  learn_genie:
    host: 10.1.1.1
    os: iosxe
    feature: bgp
"""

RETURN = """
feature_data:
    description: An OS-agnostic data structure for the feature which will be the same regardless of device operating system. 
    type: dict
    returned: always
"""

import json
import importlib
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError
from ansible.module_utils.six import string_types
from ansible.module_utils._text import to_native


try:
    from genie.testbed import load

    HAS_GENIE = True
except ImportError:
    HAS_GENIE = False

if not HAS_GENIE:
    raise AnsibleError(
        "You must have PyATS/Genie packages installed on the Ansible control node!"
    )


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        host=dict(type="str", required=True),
        port=dict(type="int", required=False),
        username=dict(type="str", required=True),
        password=dict(type="str", required=True),
        os=dict(type="str", required=True),
        connection=dict(type="str", required=False),
        feature=dict(type="str", required=True),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(changed=False, feature_data="")

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    host = module.params["host"]
    if module.params.get("port") is not None:
        port = module.params["port"]
    else:
        port = 22
    username = module.params["username"]
    password = module.params["password"]
    os = module.params["os"]
    connection = module.params["connection"]
    feature = module.params["feature"]

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    # Check user input
    for k, v in module.params.items():
        if k == "port" and v is not None:
            if not isinstance(v, int):
                raise AnsibleError(
                    "The {} parameter must be an integer between 0-65535".format(k)
                )
        else:
            if k != "port":
                if not isinstance(v, string_types):
                    raise AnsibleError(
                        "The {} parameter must be a string such as a hostname or IP address.".format(
                            k
                        )
                    )

    # Is the os param one of the Genie support OSes?
    if module.params["os"] not in ["ios", "iosxe", "iosxr", "nxos"]:
        raise AnsibleError(
            "The os parameter must be one of ios, iosxe, nxos, or iosxr."
        )
    # Is the connection param one of the supported methods?
    if module.params["connection"] not in ["unicon"]:
        raise AnsibleError(
            "The connection parameter must be unicon. Other connection types not supported at this time."
        )

    # Did the user pass in a feature that is supported?
    genie_ops = importlib.util.find_spec("genie.libs.ops")
    ops_file_obj = Path(genie_ops.origin).parent.joinpath("ops.json")
    with open(ops_file_obj, "r") as f:
        ops_json = json.load(f)
    supported_features = [k for k, _ in ops_json.items()]

    if feature not in supported_features:
        raise AnsibleError(
            "The feature entered is not supported on the current version of Genie.\nCurrently supported features: {0}\n{1}".format(
                to_native(supported_features),
                "https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/models",
            )
        )

    from genie.testbed import load

    o = {
        "devices": {
            host: {
                "ip": host,
                "port": port,
                "protocol": "ssh",
                "username": username,
                "password": password,
                "os": os,
            }
        }
    }
    testbed = load(o)
    dev = testbed.devices[host]
    dev.connect(learn_hostname=True)
    output = dev.learn(feature)

    result["feature_data"] = output.info

    # use whatever logic you need to determine whether or not this module
    # made any modifications to your target
    # if module.params['new']:
    #     result['changed'] = True

    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    # if module.params['name'] == 'fail me':
    #     module.fail_json(msg='You requested this to fail', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
