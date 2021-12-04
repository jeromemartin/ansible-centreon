def update_macros(obj, macros, data):
    has_changed = False
    m_state, m_list = obj.getmacro()
    if m_list is None:
        m_list = {}
    for k in macros:
        if k.get('name').find("$_HOST") == 0:
            current_macro = m_list.get(k.get('name'))
        else:
            current_macro = m_list.get('$_HOST' + k.get('name').upper() + '$')
        if current_macro is None and (k.get('state') == "present" or k.get('state') is None):
            s, m = obj.setmacro(
                name=k.get('name'),
                value=k.get('value'),
                is_password=k.get('is_password'),
                description=k.get('description'))
            if s:
                has_changed = True
                data.append("Add macros %s" % k.get('name').upper())
            else:
                raise Exception('Unable to set macro %s: %s' % (k.get('name'), m))
        elif current_macro is not None and k.get('state') == "absent":
            s, m = obj.deletemacro(k.get('name'))
            if s:
                has_changed = True
                data.append("Delete macros %s" % k.get('name'))
            else:
                raise Exception('Unable to delete macro %s: %s' % (k.get('name'), m))
        elif current_macro is not None and (k.get('state') == "present" or k.get('state') is None):
            if not current_macro.value == k.get('value') \
                    or not int(current_macro.is_password) == int(k.get('is_password', 0)) \
                    or not current_macro.description == k.get('description', ''):
                s, m = obj.setmacro(
                    name=k.get('name'),
                    value=k.get('value'),
                    is_password=k.get('is_password'),
                    description=k.get('description'))
                if s:
                    has_changed = True
                    data.append("Update macros %s" % k.get('name'))
                else:
                    raise Exception('Unable to set macro %s: %s' % (k.get('name'), m))

    return has_changed


def update_params(obj, params, data):
    _, _ = obj.getparams()
    for k in params:
        pname = k.get('name')
        if not pname:
            raise Exception('Param with empty name!')

        pvalue = k.get('value')
        data.append(f"Setting parameter {pname}")
        if pvalue != obj.params.get(pname):
            s, h = obj.setparam(pname, pvalue)
            if s:
                return True
            else:
                raise Exception(f'Unable to set param {pname}: {h}')


def update_contacts(obj, contacts, data):
    has_changed = False
    m_state, m_list = obj.getcontact()
    if m_list is None:
        m_list = {}

    for k in contacts:
        contact_name = k.get('name')
        contact_state = k.get('state', "present")
        current_contact = m_list.get(contact_name)

        if current_contact is None and contact_state == "present":
            s, m = obj.addcontact(name=contact_name)
            if s:
                has_changed = True
                data.append(f"Add contact {contact_name}")
            else:
                raise Exception(f'Unable to set contact {contact_name}: {m}')
        elif current_contact is not None and contact_state == "absent":
            s, m = obj.deletecontact(contact_name)
            if s:
                has_changed = True
                data.append(f"Delete contact {contact_name}")
            else:
                raise Exception('Unable to delete contact %s: %s' % (contact_name, m))

    return has_changed


def update_contactgroups(obj, contactgroups, data):
    has_changed = False
    m_state, m_list = obj.getcontactgroup()
    if m_list is None:
        m_list = {}

    for k in contactgroups:
        contact_name = k.get('name')
        contact_state = k.get('state', "present")
        current_contact = m_list.get(contact_name)

        if current_contact is None and contact_state == "present":
            s, m = obj.addcontactgroup(name=contact_name)
            if s:
                has_changed = True
                data.append(f"Add contact {contact_name}")
            else:
                raise Exception(f'Unable to set contact group {contact_name}: {m}')
        elif current_contact is not None and contact_state == "absent":
            s, m = obj.deletecontactgroup(contact_name)
            if s:
                has_changed = True
                data.append(f"Delete contact group {contact_name}")
            else:
                raise Exception('Unable to delete contact group %s: %s' % (contact_name, m))

    return has_changed
