#!/usr/bin/python
# -*- coding: utf-8 -*-

import packaging.version
# import module snippets
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    'status': ['preview'],
    'supported_by': 'community',
    'metadata_version': '0.3',
    'version': '0.3'
}

DOCUMENTATION = '''
---
module: centreon_host
version_added: "2.2"
description: Manage Centreon hosts.
short_description: Manage Centreon hosts

options:
  url:
    description:
      - Centreon URL
    required: True

  username:
    description:
      - Centreon API username
    required: True
  password:
    description:
      - Centreon API username's password
    required: True
  name:
    description:
      - Hostname
    required: True
  hosttemplates:
    description:
      - Host Template list for this host
    type: list
  alias:
    description:
      - Host alias
  ipaddr:
    description:
      - IP address
  instance:
    description:
      - Poller instance to check host
    default: Central
  hostgroups:
    description:
      - Hostgroups list
    type: list
  params:
    description:
      - Config specific parameter (dict)
  macros:
    description:
      - Set Host Macros (dict)
  state:
    description:
      - Create / Delete host on Centreon
    default: present
    choices: ['present', 'absent']
  status:
    description:
      - Enable / Disable host on Centreon
    default: enabled
    choices: c
  validate_certs:
    type: bool
    default: yes
    description:
      - If C(no), SSL certificates will not be validated.
requirements:
  - Python Centreon API
author:
    - Guillaume Watteeux
    - Jérôme Martin
'''

EXAMPLES = '''
# Add host
 - community.centreon.centreon_host:
     url: 'https://centreon.company.net/centreon'
     username: 'ansible_api'
     password: 'strong_pass_from_vault'
     name: "{{ ansible_fqdn }}"
     alias: "{{ ansible_hostname }}"
     ipaddr: "{{ ansible_default_ipv4.address }}"
     hosttemplates:
       - name: OS-Linux-SNMP-custom
       - name: OS-Linux-SNMP-disk
         state: absent
     hostgroups:
       - name: Linux-Servers
       - name: Production-Servers
       - name: App1
         state: absent
     instance: Central
     status: enabled
     state: present:
     params:
       notes_url: "https://wiki.company.org/servers/{{ ansible_fqdn }}"
       notes: "My Best server"
     macros:
       - name: MACRO1
         value: value1
         ispassword: 1
       - name: MACRO2
         value: value2
         desc: my macro
         state: absent
'''

# =============================================
# Centreon module API Rest
#
from ansible_collections.community.centreon.plugins.module_utils import centreon_utils

try:
    from centreonapi.centreon import Centreon
    from centreonapi import __version__ as centreonapi_version
except ImportError:
    centreonapi_found = False
else:
    centreonapi_found = True


def main():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(required=True),
            username=dict(default='admin', no_log=True),
            password=dict(default='centreon', no_log=True),
            name=dict(required=True),
            hosttemplates=dict(type=list, default=None),
            alias=dict(default=None),
            ipaddr=dict(default=None),
            instance=dict(default='Central'),
            hostgroups=dict(type=list, default=None),
            params=dict(type=list, default=None),
            macros=dict(type=list, default=None),
            contacts=dict(type=list, default=None),
            contactgroups=dict(type=list, default=None),
            state=dict(default='present', choices=['present', 'absent']),
            status=dict(default='enabled', choices=['enabled', 'disabled']),
            applycfg=dict(default=True, type='bool'),
            validate_certs=dict(default=True, type='bool'),
        )
    )

    if not centreonapi_found or packaging.version.parse(centreonapi_version) < packaging.version.parse("0.2.0"):
        module.fail_json(msg="Python centreonapi >= 0.2.0 module is required")

    url = module.params["url"]
    username = module.params["username"]
    password = module.params["password"]
    name = module.params["name"]
    alias = module.params["alias"]
    ipaddr = module.params["ipaddr"]
    hosttemplates = module.params["hosttemplates"]
    instance = module.params["instance"]
    hostgroups = module.params["hostgroups"]
    params = module.params["params"]
    macros = module.params["macros"]
    contacts = module.params["contacts"]
    contactgroups = module.params["contactgroups"]
    state = module.params["state"]
    status = module.params["status"]
    applycfg = module.params["applycfg"]
    validate_certs = module.params["validate_certs"]

    has_changed = False

    try:
        centreon = Centreon(url, username, password, check_ssl=validate_certs)
    except Exception as e:
        module.fail_json(
            msg="Unable to connect to Centreon API: %s" % str(e)
        )
        return

    try:
        st, poller = centreon.pollers.get(instance)
    except Exception as e:
        module.fail_json(msg="Unable to get pollers: {}".format(e))
        return

    if not st and poller is None:
        module.fail_json(msg="Poller '%s' does not exists" % instance)
    elif not st:
        module.fail_json(msg="Unable to get poller list %s " % poller)

    data = list()

    host_state, host = centreon.hosts.get(name)

    if not host_state and state == "present":
        try:
            data.append("Add %s %s %s %s %s %s" %
                        (name, alias, ipaddr, instance, hosttemplates, hostgroups))
            centreon.hosts.add(
                name,
                alias,
                ipaddr,
                instance,
                hosttemplates,
                hostgroups
            )
            # Apply the host templates for create associate services
            host_state, host = centreon.hosts.get(name)
            host.applytemplate()
            has_changed = True
            data.append("Add host: %s" % name)
        except Exception as e:
            module.fail_json(msg='Create: %s - %s' % (e, data), changed=has_changed)
            return

    if not host_state:
        module.fail_json(msg="Unable to find host %s " % name, changed=has_changed)
        return

    if state == "absent":
        del_state, del_res = centreon.hosts.delete(host)
        if del_state:
            has_changed = True
            if applycfg:
                poller.applycfg()
            module.exit_json(
                changed=has_changed, result="Host %s deleted" % name
            )
        else:
            module.fail_json(msg='State: %s' % del_res, changed=has_changed)

    if status == "disabled" and int(host.activate) == 1:
        d_state, d_res = host.disable()
        if d_state:
            has_changed = True
            data.append("Host disabled")
        else:
            module.fail_json(msg='Unable to disable host %s: %s' % (host.name, d_state), changed=has_changed)

    if status == "enabled" and int(host.activate) == 0:
        e_state, e_res = host.enable()
        if e_state:
            has_changed = True
            data.append("Host enabled")
        else:
            module.fail_json(msg='Unable to enable host %s: %s' % (host.name, e_state), changed=has_changed)

    if not host.address == ipaddr and ipaddr:
        s_state, s_res = host.setparam('address', ipaddr)
        if s_state:
            has_changed = True
            data.append(
                "Change ip addr: %s -> %s" % (host.address, ipaddr)
            )
        else:
            module.fail_json(msg='Unable to change ip add: %s' % s_res, changed=has_changed)

    if not host.alias == alias and alias:
        s_state, s_res = host.setparam('alias', alias)
        if s_state:
            has_changed = True
            data.append("Change alias: %s -> %s" % (host.alias, alias))
        else:
            module.fail_json(msg='Unable to change alias %s: %s' % (alias, s_res), changed=has_changed)

    #### HostGroup
    if hostgroups:
        hg_state, hg_list = host.gethostgroup()
        if hg_state:
            hostgroup_list = list()
            if hg_list is not None:
                for hg in hg_list.keys():
                    hostgroup_list.append(hg)
            del_hostgroup = list()
            add_hostgroup = list()
            for hgp in hostgroups:
                if hgp.get('name') in hostgroup_list and hgp.get('state') == 'absent':
                    del_hostgroup.append(hgp.get('name'))
                elif hgp.get('name') not in hostgroup_list and (
                        hgp.get('state') == "present" or hgp.get('state') is None):
                    add_hostgroup.append(hgp.get('name'))

            if add_hostgroup:
                s, h = host.addhostgroup(add_hostgroup)
                if s:
                    has_changed = True
                    data.append("Add HostGroup: %s" % add_hostgroup)
                else:
                    module.fail_json(msg='Unable to add hostgroup: %s, %s' % (add_hostgroup, h), changed=has_changed)

            if del_hostgroup:
                s, h = host.deletehostgroup(del_hostgroup)
                if s:
                    has_changed = True
                    data.append("Del HostGroup: %s" % del_hostgroup)
                else:
                    module.fail_json(msg='Unable to delete hostgroup: %s, %s' % (del_hostgroup, h), changed=has_changed)

    #### HostTemplates
    if hosttemplates:
        ht_state, ht_list = host.gettemplate()
        if ht_state:
            template_list = list()
            if ht_list is not None:
                for tpl in ht_list.keys():
                    template_list.append(tpl)
            del_host_template = list()
            add_host_template = list()
            for tmpl in hosttemplates:
                if tmpl.get('name') in template_list and tmpl.get('state') == "absent":
                    del_host_template.append(tmpl.get('name'))
                elif tmpl.get('name') not in template_list \
                        and (tmpl.get('state') == "present"
                             or tmpl.get('state') is None):
                    add_host_template.append(tmpl.get('name'))

            if add_host_template:
                s, h = host.addtemplate(add_host_template)
                if s:
                    host.applytemplate()
                    has_changed = True
                    data.append("Add HostTemplate: %s" % add_host_template)
                else:
                    module.fail_json(msg='Unable to add hostTemplate: %s' % add_host_template, changed=has_changed)

            if del_host_template:
                s, h = host.deletetemplate(del_host_template)
                if s:
                    host.applytemplate()
                    has_changed = True
                    data.append("Del HostTemplate: %s" % del_host_template)
                else:
                    module.fail_json(msg='Unable to del hostTemplate: %s' % del_host_template, changed=has_changed)

    #### Contacts
    if contacts:
        try:
            has_changed = centreon_utils.update_contacts(host, contacts, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update contacts: {str(e)}", changed=has_changed)
            return

    #### Contacts Groups
    if contactgroups:
        try:
            has_changed = centreon_utils.update_contactgroups(host, contactgroups, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update contact groups: {str(e)}", changed=has_changed)
            return

    #### Macros
    if macros:
        try:
            has_changed = centreon_utils.update_macros(host, macros, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update macros: {str(e)}", changed=has_changed)
            return

    #### Params
    if params:
        try:
            has_changed = centreon_utils.update_params(host, params, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update params: {str(e)}", changed=has_changed)
            return

    if applycfg and has_changed:
        poller.applycfg()
    module.exit_json(changed=has_changed, msg=data)


if __name__ == '__main__':
    main()
