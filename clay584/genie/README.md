# Cisco Genie Ansible Collection (Unofficial)

This is an Ansible collection that brings the functionality of Cisco's pyATS and Genie 
libraries to Ansible users.

## What's in this Collection?

### Learn Genie Ansible Module

This is an Ansible module that allows you to `learn` a feature on a device in your Ansible playbook. 
This is the equivalent of running `genie learn <feature>` from the Genie CLI tool.
Using Cisco's Genie libraries, this will connect to the device, run a series of commands, and return 
a data structure that conforms to an OS-agnostic data model, meaning that you could run the `learn_genie` 
module against an IOS, NXOS, IOS-XR, or IOS-XE device for a given feature, and the data returned will be 
in the same format. This allows for much more simple automation logic as the data structures are 
identical regardless of device OS.

The second part of this module allows you to, again, `learn` a feature, but then also compare it 
against a previous run. For example, if you have a playbook, you could learn a feature, make some 
device configuration changes, and then the final task of the playbook, you could learn the feature again 
and compare the two using `genie diff`.

### Parse Genie Ansible Filter Plugin

This is an Ansible filter plugin that can take raw CLI output and return structured data. This is the 
same filter plugin located [here](https://galaxy.ansible.com/clay584/parse_genie). Since Ansible has 
created Ansible Collections, this has been added to this collection. The other project will remain unchanged for 
backward-compatibility, but no further updates will be done to that project. All future work on `parse_genie` 
will be in this collection.

## Installation/Prerequisites



## Usage


### Learn Genie Module



#### Module Parameters
| Parameter     | Choices/Defaults | Comments      |
| ------------- | :-------------:    | ------------- |
| host (string)  |      | The network device hostname/IP address.          |
| port (int) (1-65535)  | Choices: 1-65,535, Default: 22     | The port to connect to.          |
| protocol (str)  | Choices: telnet, ssh, Default: ssh     | The protocol used for connectivity to the device.         |
| username (string) |      | The username for connecting to the device with.          |
| password (string) |      | The password for connecting to the device with.          |
| os (string) |   Choices: Any of the supported Cisco Genie operating systems.   | The operating system of the network device.          |
| feature (string) |   Choices: Any of the supported Cisco Genie Learn features.   | The network feature to learn (i.e. - arp, interface, bgp).          |
| compare_to |  Previous `learn_genie` registered output.    | The output as collected from the `learn_genie` module with Ansible `register`. This is needed in order to `diff` two `learn_genie` runs.          |
| exclude (list) |  List of noisy dict keys to exclude from `diff`.    | The default will use Genie's built-in defaults. This can be used to exclude additional keys from the `diff`. Format is `"{{ ['in_octets', 'uptime'] }}"`          |
| colors (bool) |   Choices: `yes` or `no`, Default: `yes`   | Output colored `diff` output. This requires the Python package `colorama` to be installed on the Ansible control machine.          |

### Parse Genie Filter Plugin

