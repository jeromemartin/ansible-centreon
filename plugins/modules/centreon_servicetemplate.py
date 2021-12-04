#!/usr/bin/python
# -*- coding: utf-8 -*-

import packaging.version

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'metadata_version': '0.2',
                    'version': '0.2'}

DOCUMENTATION = '''
---
module: centreon_servicetemplate
version_added: "2.8"
description: Manage Centreon service templates.
short_description: Manage Centreon service templates

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
  instance:
    description:
      - Poller instance
    default: Central
  applycfg:
    description:
      - Apply configuration on poller
    default: True
    choices: ['True','False']
  validate_certs:
    type: bool
    default: yes
    description:
      - If C(no), SSL certificates will not be validated.
  name:
    description:
      - Service name
    type: str
    required: True
  template:
    description:
      - Service template name
    type: str
    required: True
  params:
    description:
      - Config specific parameter (dict)
  macros:
    description:
      - Set Host Macros (dict)
  state:
    description:
      - Create / Delete service on Centreon
    default: present
    choices: ['present', 'absent']
  status:
    description:
      - Enable/disable service
    default: enabled
    choices: ['enabled', 'disabled']
requirements:
  - Python Centreon API
author:
    - Guillaume Watteeux
    - Jérôme Martin
'''

EXAMPLES = '''
- community.centreon.centreon_servicetemplate:
    url: "{{ centreon_url }}"
    username: "{{ centreon_api_user }}"
    password: "{{ centreon_api_pass }}"
    name: "MyTemplate"
    alias: tpl
    template: "OS-Linux-Disks-NRPE3"
    macros:
      - name: VAR
        value: 2
    instance: Central
    status: enabled
    state: present
    applycfg: True
'''

# =============================================
# Centreon module API Rest
#
from ansible.module_utils.basic import AnsibleModule

# import module snippets
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
            alias=dict(required=False),
            template=dict(required=False),
            params=dict(type='list', default=None),
            macros=dict(type='list', default=None),
            contacts=dict(type='list', default=None),
            contactgroups=dict(type=list, default=None),
            instance=dict(default='Central'),
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
    template = module.params["template"]
    params = module.params["params"]
    macros = module.params["macros"]
    contacts = module.params["contacts"]
    contactgroups = module.params["contactgroups"]
    instance = module.params["instance"]
    state = module.params["state"]
    status = module.params["status"]
    applycfg = module.params["applycfg"]
    validate_certs = module.params["validate_certs"]

    has_changed = False

    try:
        centreon = Centreon(url, username, password, check_ssl=validate_certs)
    except Exception as e:
        module.fail_json(msg="Unable to connect to Centreon API: %s" % str(e))
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

    data = []
    service_state, service = centreon.servicetemplates.get(name)

    if not service_state and state == "present":
        try:
            data.append(f"Add '{name}', alias='{alias}', '{instance}', '{template}'")
            service_state, res = centreon.servicetemplates.add(name, alias, template)
            if not service_state:
                module.fail_json(msg=f"Unable to create service template {name}: {res}", changed=has_changed)
                return

            # Apply the host templates for create associate services
            service_state, service = centreon.servicetemplates.get(name)
            has_changed = True
            data.append(f"Added service: {name}")
        except Exception as e:
            module.fail_json(msg='Create: %s - %s' % (e, data), changed=has_changed)
            return

    if not service_state:
        module.fail_json(msg=f"Unable to find service {name}: {data}", changed=has_changed)
        return

    if state == "absent":
        del_state, del_res = centreon.servicetemplates.delete(name)
        if del_state:
            has_changed = True
            if applycfg:
                poller.applycfg()
            module.exit_json(changed=has_changed, result=f"Service {name} deleted")
        else:
            module.fail_json(msg='State: %s' % del_res, changed=has_changed)

    if status == "disabled" and int(service.activate) == 1:
        d_state, d_res = service.disable()
        if d_state:
            has_changed = True
            data.append("Service template disabled")
        else:
            module.fail_json(msg=f'Unable to disable service {name}: {d_state}', changed=has_changed)

    if status == "enabled" and int(service.activate) == 0:
        e_state, e_res = service.enable()
        if e_state:
            has_changed = True
            data.append("Service template enabled")
        else:
            module.fail_json(msg=f'Unable to enable service {name}: {e_state}', changed=has_changed)

    #### Contacts
    if contacts:
        try:
            has_changed = centreon_utils.update_contacts(service, contacts, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update contacts: {str(e)}", changed=has_changed)
            return

    #### Contacts Groups
    if contactgroups:
        try:
            has_changed = centreon_utils.update_contactgroups(service, contactgroups, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update contact groupss: {str(e)}", changed=has_changed)
            return

    #### Macros
    if macros:
        try:
            has_changed = centreon_utils.update_macros(service, macros, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update macros: {str(e)}", changed=has_changed)
            return

    #### Params
    if params:
        try:
            has_changed = centreon_utils.update_params(service, params, data)
        except Exception as e:
            module.fail_json(msg=f"Failed to update params: {str(e)}", changed=has_changed)
            return

    if applycfg and has_changed:
        poller.applycfg()
    module.exit_json(changed=has_changed, msg=data)


if __name__ == '__main__':
    main()
