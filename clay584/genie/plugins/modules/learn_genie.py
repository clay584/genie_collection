#!/usr/bin/python

# Copyright: (c) 2020, Clay Curtis <jccurtis@presidio.com>
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
    feature:
        description:
            - The device feature to be learned from the device
        required: true
    compare_to:
        description:
            - Compare to prior genie learn data (diff)
        required: false
    exclude:
        description:
            - Exclude noisy keys such as packet counters, timestamps, uptime, etc.
        required: false
    no_default_exclusion:
        description:
            - Do not exclude any noisy keys in the Genie diff operation such as packet counters, timestamps, uptime, etc.
        required: false
    colors:
        description:
            - Turn on or off colored diff output. Defaults to on (colored output). Requires Python package "colorama".
        required: false

# extends_documentation_fragment:
#     - azure

author:
    - Clay Curtis (@ccurtis584)
"""

EXAMPLES = """
# Learn the state of BGP
- name: Learn BGP Feature
  learn_genie:
    host: 10.1.1.1
    username: admin
    password: password1234
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
    # from pyats.topology import loader
    from genie.utils.diff import Diff
    HAS_GENIE = True
except ImportError:
    HAS_GENIE = False

if not HAS_GENIE:
    raise AnsibleError(
        "You must have PyATS/Genie packages installed on the Ansible control node!"
    )

try:
    from colorama import Fore, Back, Style, init
    init()
except ImportError:  # fallback so that the imported classes always exist
    class ColorFallback():
        __getattr__ = lambda self, name: ''
    Fore = Back = Style = ColorFallback()


def color_diff(diff):
    diff_list = diff.splitlines()
    for line in diff_list:
        if line.startswith('+++'):
            yield Fore.WHITE + line + Fore.RESET
        elif line.startswith('---'):
            yield Fore.WHITE + line + Fore.RESET
        elif line.startswith('+'):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith('-'):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith('@@'):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        host=dict(type="str", required=True),
        port=dict(type="int", required=False),
        protocol=dict(type="str", required=False),
        username=dict(type="str", required=True),
        password=dict(type="str", required=True, no_log=True),
        os=dict(type="str", required=True),
        feature=dict(type="str", required=True),
        compare_to=dict(type="raw", required=False),
        exclude=dict(type="list", required=False),
        no_default_exclusion=dict(type="bool", required=False),
        colors=dict(type="bool", required=False)
    )
    # TODO: Add protocol so Unicon can use anything
    # print(type(module_args['compare_to']))
    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(changed=False)

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
    feature = module.params["feature"]
    if module.params.get("compare_to"):
        # compare_to = json.loads(module.params.get("compare_to"))
        compare_to = module.params.get("compare_to")
    if module.params.get("exclude"):
        excluded_keys = module.params.get("exclude")
    if module.params.get("no_default_exclusion") is False:
        no_default_exclusion = False
    elif module.params.get("no_default_exclusion") is None:
        no_default_exclusion = False
    else:
        no_default_exclusion = True
    if module.params.get("colors") is False:
        colors = False
    elif module.params.get("colors") is not None:
        colors = True
    else:
        colors = True
    if module.params.get("protocol") == "telnet":
        protocol = "telnet"
    else:
        protocol = "ssh"

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    # Check user input
    for k, v in module.params.items():
        if k == "port" and v is not None:
            if not isinstance(v, int) and v not in range(1-65535):
                raise AnsibleError(
                    "The {} parameter must be an integer between 0-65535".format(k)
                )
        elif k == "compare_to":
            pass
        elif k == "port":
            pass
        elif k == "exclude":
            pass
        elif k == "colors":
            pass
        elif k == "no_default_exclusion":
            pass
        elif k == "protocol":
            pass
        else:
            if not isinstance(v, string_types):
                raise AnsibleError(
                    "The {} parameter must be a string such as a hostname or IP address.".format(
                        k
                    )
                )

    # Did the user pass in a feature that is supported on a given platform
    genie_ops = importlib.util.find_spec("genie.libs.ops")
    ops_file_obj = Path(genie_ops.origin).parent.joinpath("ops.json")
    with open(ops_file_obj, "r") as f:
        ops_json = json.load(f)
    supported_features = [k for k, _ in ops_json.items()]

    # Load in default exclusions for diffs for all features for genie learn
    # genie_yamls = importlib.util.find_spec("genie.libs.sdk.genie_yamls")
    # genie_excludes = Path(genie_yamls.origin).parent.joinpath("pts_datafile.yaml")
    # with open(genie_excludes, "r") as f:
    #     diff_excludes = json.load(f)
    # supported_features = [k for k, _ in ops_json.items()]

    default_excludes = {}
    from importlib import import_module
    for i in supported_features:
        modulename = "genie.libs.ops.{}.{}".format(i, i)
        package_name = i.capitalize()
        try:
            this_module = import_module(modulename, package_name)
            this_class = getattr(this_module, package_name)
            this_excludes = this_class.exclude
            default_excludes.update({i: this_excludes})
        except AttributeError:
            default_excludes.update({i: []})

        # this_module = __import__(modulename)
        # default_excludes.append({i: this_module.i)
        # from genie.libs.ops.i.i import Interface

    # Is the feature even supported?
    if feature not in supported_features:
        raise AnsibleError(
            "The feature entered is not supported on the current version of Genie.\nCurrently supported features: {0}\n{1}".format(
                to_native(supported_features),
                "https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/models",
            )
        )

    # Is the feature supported on the OS that was provided from the user?
    for f in ops_json.items():
        if feature == f[0]:
            if os not in [k for k, _ in f[1].items()]:
                raise AnsibleError(
                    "The {0} feature entered is not supported on {1}.\nCurrently supported features & platforms:\n{2}".format(
                        feature, os,
                        "https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/models",
                    )
                )

    testbed = {
        "devices": {
            host: {
                "ip": host,
                "port": port,
                "protocol": protocol,
                "username": username,
                "password": password,
                "os": os,
            }
        }
    }

    tb = load(testbed)
    dev = tb.devices[host]
    dev.connect(log_stdout=False, learn_hostname=True)
    output = dev.learn(feature)

    # Do diff if compare_to was provided
    if module.params.get("compare_to"):
        # do genie diff
        # print(type(compare_to['genie'][feature]))
        # print(type(output.info))
        # dd = Diff({"a": "yes"}, {"a": "no"})
        # with open('/tmp/compare_to.txt', 'w') as f:
        #     f.write(json.dumps(compare_to['genie'][feature]))
        # with open('/tmp/output.txt', 'w') as f:
        #     f.write(json.dumps(output.info))

        before = compare_to['genie'][feature]
        current = json.dumps(output.info)
        current = json.loads(current)
        # current = eval(str(output.info))
        try:
            excluded_keys
            if no_default_exclusion:
                merged_exclusions = excluded_keys
            else:
                merged_exclusions = list(set().union(excluded_keys, default_excludes[feature]))
            dd = Diff(before, current, exclude=merged_exclusions)
        except NameError:
            if len(default_excludes[feature]) > 0:
                if no_default_exclusion:
                    dd = Diff(before, current)
                else:
                    dd = Diff(before, current, exclude=default_excludes[feature])
            else:
                dd = Diff(before, current)
        dd.findDiff()
        if colors:
            result.update({"diff": {"prepared": '\n'.join(color_diff(str(dd)))}})
        else:
            result.update({"diff": {"prepared": str(dd)}})
        module._diff = True
        if len(str(dd)) > 0:
            result['changed'] = True

    feature_data = {
        feature: output.info
    }

    result.update({"genie": feature_data})

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
