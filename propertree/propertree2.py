# Copyright 2024 Edward Hope-Morley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import operator
import uuid
from collections import UserList, UserDict, ChainMap

from propertree.log import log

REGISTERED_OVERRIDES: dict = {}


class MappedMemberPrimaryConflict(Exception):
    """
    Exception raised when a property is found to be a member of more than one
    primary.
    """
    def __init__(self, member_cls, new_primary, existing_primary):
        super().__init__(f"trying to set {member_cls} override_primary "
                         f"to {new_primary} but it is "
                         f"already set to {existing_primary}")


class RegistryConflictError(Exception):
    """ Exception raised to indicate that a property has already been
    registered for a given key name. """


class InvalidBranchPathError(Exception):
    """ Raised when a branch is referenced with an invalid path. """


class PropertyIsNotAMember(Exception):
    """ Raised when a mapping tries to access a property as a member when that
    property is not a member.
    """


class PropertreeTreeError(Exception):
    """ Generic error for propertree errors. """


class OverrideRegistry():
    """
    The override registry contains registrations of properties to keys and is
    then used later to resolve properties as they are discovered in a tree.
    """
    def __repr__(self):
        info = []
        for key, entry in REGISTERED_OVERRIDES.items():
            info.append(f"{key}:\n  {entry}")

        return '\n'.join(info)

    @staticmethod
    def post_registration_tasks(registry):
        """
        Auto-registration order is random and nothing stops a key
        having properties registered against it more than once. This is a
        cleanup to ensure each registration looks as it should. The last
        property registered against a key takes precedence over the rest.
        """
        for key, entry in registry.items():
            if len(entry) == 1:
                continue

            log.debug("squashing %s registration '%s' -> '%s'", key, entry,
                      entry[-1:])
            registry[key] = entry[-1:]

    @staticmethod
    def _ensure_not_registered(override_cls, key):
        """
        Ensure that the given key has not already been registered and raise
        an RegistryConflictError if it has.
        """
        conflict_msg = (f"registration of override {override_cls.__name__} "
                        "key '{}' will clobber existing entry from override "
                        "{}")
        _registered = REGISTERED_OVERRIDES.get(key)
        if _registered:
            for item in _registered:
                if item.__name__ == override_cls.__name__:
                    continue

                raise RegistryConflictError(conflict_msg.format(
                                                         key,
                                                         item.__name__))

    @classmethod
    def _register(cls, override_cls):
        """
        Register the given property class against all keys it has defined and
        if necessary link to any mappin primaries it maybe associated with.
        """
        try:
            keys = override_cls.get_override_keys_back_compat()
        except AttributeError:
            return

        if not keys:
            return

        for key in keys:
            # NOTE: this is currently disabled but leaving in case it is needed
            # in the future.
            # cls._ensure_not_registered(override_cls, key)
            if key in REGISTERED_OVERRIDES:
                # We only want to allow this for mapping members that share the
                # same key but can't know if an override is associated to a
                # primary until all have been registered so requires a post
                # registration task to complete.
                REGISTERED_OVERRIDES[key].append(override_cls)
            else:
                REGISTERED_OVERRIDES[key] = [override_cls]

        members = []
        if hasattr(override_cls, 'override_members'):
            members = override_cls.override_members

        # Reverse link members to their mapping primary
        for member in members:
            if member.override_primary:
                if member.override_primary != override_cls:
                    raise MappedMemberPrimaryConflict(
                                            member.__name__,
                                            override_cls.__name__,
                                            member.override_primary.__name__)

            member.override_primary = override_cls

    @classmethod
    def register(cls, to_register: list):
        """
        Register override/property classes.

        @param to_register: a list of overrides to register.
        """
        for _cls in to_register:
            cls._register(_cls)

    @staticmethod
    def _unregister(override_cls):
        """
        Unregister a property (and it's keys) from the registry. """
        try:
            keys = override_cls.get_override_keys_back_compat()
        except AttributeError:
            return

        for key in keys:
            if key in REGISTERED_OVERRIDES:
                if len(REGISTERED_OVERRIDES[key]) == 1:
                    del REGISTERED_OVERRIDES[key]
                else:
                    REGISTERED_OVERRIDES[key].remove(override_cls)

        # Reverse link members to their mapping primary
        if hasattr(override_cls, 'override_members'):
            members = override_cls.override_members
        else:
            members = []

        for member in members:
            member.override_primary = None

    @classmethod
    def unregister(cls, to_unregister: list):
        """
        Unregister override/property classes.

        @param to_unregister: a list of overrides to unregister.
        """
        for _cls in to_unregister:
            cls._unregister(_cls)


class OverrideMeta(type):
    """ Used to automatically register property classes on module load. """
    FWD_COMPAT_CLS_METHOD = ['get_override_keys_back_compat']
    FWD_COMPAT_CLS_ATTR = ['_override_keys', '_override_auto_implicit_member',
                           '_override_autoregister',
                           '_override_logical_grouping_type',
                           '_override_members']
    BACK_COMPAT_INST_ATTR = ['override_name', 'override_path']

    @classmethod
    def migrate_protected_attrs(mcs, cls):
        """
        In order to make the changes necessary to switch private attributes to
        public while not breaking any code that is using these attributes we
        allow grace period where we map old format attributes to new.

        This will be removed in a future release.
        """
        to_map = {}
        for attr, value in cls.__dict__.items():
            if attr in cls.FWD_COMPAT_CLS_METHOD:
                to_map['_' + attr] = value
            elif attr in cls.BACK_COMPAT_INST_ATTR + cls.FWD_COMPAT_CLS_ATTR:
                if attr in cls.BACK_COMPAT_INST_ATTR:
                    newattr = '_' + attr
                else:
                    newattr = attr.lstrip('_')

                try:
                    to_map[newattr] = getattr(cls, attr)()
                except TypeError:
                    to_map[newattr] = getattr(cls, attr)

        for k, v in to_map.items():
            setattr(cls, k, v)

    def __init__(cls, _name, _mro, _members):
        cls.migrate_protected_attrs(cls)
        if hasattr(cls, 'override_autoregister'):
            if not cls.override_autoregister:
                return

        OverrideRegistry.register([cls])


class PTreeOverrideBase(metaclass=OverrideMeta):  # noqa, pylint: disable=too-many-instance-attributes
    """ Base class for all property implementations. """
    # For internal use only
    override_primary = None

    # If set to True this allows a property to define a subtree i.e. branches
    # and leaves with their own properties.
    allow_subtree: bool = True

    # This must be set to a list in order for the property to be registered. If
    # list if empty the name of the property class is used as the key.
    override_keys: list | None = None

    # By default all implementations of this class will be registered as
    # override properties. This can be set to False of this behaviour is
    # undesired.
    override_autoregister: bool = True

    # By default when a mapping member is found we check that it's primary has
    # also been discovered and if not one is implicitly registered. If a
    # property is intended to be used both on its own and as a member of a
    # mapping then this can be set to False. This does mean that the mapping
    # will need at least one other member property that has this set to True
    # to be able to trigger an implicit primary registration.
    override_auto_implicit_member: bool = True

    @classmethod
    def get_override_keys_back_compat(cls):
        """
        To support backwards compatibility with propertree.py we support old
        and new ways of defining keys.
        """
        keys = cls.override_keys
        if keys is None:
            return []

        return keys or [cls.__name__.lower()]

    def __init__(self,
                 root: PTreeSection,
                 name: str,
                 content: dict,
                 resolve_path: str,
                 context: dict | None = None,
                 manager: PTreeOverrideManager | None = None,
                 state: State | None = None):
        """
        @param root: PTreeSection object this property belongs to
        @param name: property name
        @param content: property content
        @param resolve_path: full resolve path to property from root
        @param context: optional context dict
        @param manager: PTreeOverrideManager object
        @param state: State object
        """
        self.root = root
        self._override_resolved_name = name
        self.content = content
        self._override_resolve_path = resolve_path
        self.context = context
        self.manager = manager

        if state:
            self._override_parent_path = state['parent']
            self.is_implicit_primary = state['is_implicit_primary']
            self.has_implicit_primary = state['has_implicit_primary']
            self.mapping_ids = state['mapping_ids']
            self.group_ids = state['group_ids']
        else:
            self._override_parent_path = \
                self.is_implicit_primary = \
                self.has_implicit_primary = \
                self.mapping_ids = \
                self.group_ids = None

        if self.mapping_ids:
            self.mapping_id = self.mapping_ids[-1]
        else:
            self.mapping_id = None

        if self.group_ids:
            self.group_id = self.group_ids[-1]
        else:
            self.group_id = None

    @property
    def override_name(self):
        """ This is the key name used to register this override. """
        return self._override_resolved_name

    @property
    def override_parent(self):
        if not self._override_parent_path:
            return None

        return self.manager.property_cache[self._override_parent_path]

    @property
    def override_path(self):
        """ This is the full resolve path for this override object. """
        return f"{self._override_resolve_path}.{self.override_name}"

    def _len_query(self):
        """ The way we query the size/length of a property differs depending
        on the type of property so this supports the different ways to
        query that information.
         """
        if isinstance(self, PTreeMappedOverrideBase):
            return PropQuery(group_id=self.group_id,
                             allow_implicit_primary=self.is_implicit_primary)

        if isinstance(self, PTreeLogicalGrouping):
            return PropQuery(group_id=self.group_id, force_group_head_id=True,
                             allow_implicit_primary=self.is_implicit_primary)

        return PropQuery(group_id=self.group_id,
                         mapping_id=self.mapping_id,
                         allow_implicit_primary=self.is_implicit_primary)

    def __len__(self):
        log.info("%s.__len__()", self.__class__.__name__)
        stack = self.manager.get_property(self.override_path)
        query = self._len_query()
        items = []
        for item in stack:
            if not query.apply(item):
                continue

            items.append(item)

        _len = len(items)
        log.info("%s.__len__() result=%s", self.__class__.__name__, _len)
        return _len

    @property
    def _iter_query(self):
        return PropQuery(mapping_id=self.mapping_id, group_id=self.group_id)

    def __iter__(self):
        log.info("%s.__iter__()", self.__class__.__name__)
        buildinfo = BuildInfo(self._iter_query, fetch_whole_stack=True)
        yield from self.manager.make_property(self.root, self.override_path,
                                              self.context, buildinfo)

    def _get_override_attribute(self, name):
        log.info("%s._get_override_attribute(%s)", self.override_name, name)
        if name in self.content:
            return self.content[name]

        _name = name.replace('_', '-')
        if _name in self.content:
            return self.content[_name]

        raise AttributeError(f"'{self.__class__.__name__}' object has no "
                             f"attribute '{name}'")

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError as exc:
            try:
                return self._get_override_attribute(name)
            except AttributeError:
                raise exc  # pylint: disable=raise-missing-from


class PTreeOverrideLiteralType(PTreeOverrideBase):
    """ Property for literal types. """
    override_keys = ['__override_literal_type__']

    @staticmethod
    def has_valid_type(content):
        """ Ensure the content has a type that we support. """
        return type(content) in [str, int, float, bool]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.has_valid_type(self.content):
            raise TypeError(f"{self.content} is not a valid raw type for "
                            f"{self.__class__.__name__}")

    def __type__(self):
        return type(self.content)

    def __int__(self):
        return int(self.content)

    def __float__(self):
        return float(self.content)

    def __bool__(self):
        assert isinstance(self.content, bool), (f"{self.content} does not "
                                                "have type bool")
        return self.content

    def __str__(self):
        return self.content

    def __eq__(self, string):
        return self.content == string


class PTreeLogicalGrouping(PTreeOverrideBase):
    """
    First class override for logical groupings. This will only take effect when
    used as a property attribute i.e. it cannot be used as a property in its
    own right.
    """
    override_keys = ['and', 'or', 'nand', 'not', 'nor', 'xor']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.override_group_stats = {'items_executed': 0}

    @property
    def _iter_query(self):
        query = super()._iter_query
        query.force_group_head_id = True
        return query

    @classmethod
    def and_stop_on_first_false(cls):
        """
        By default we do not process items in an AND group beyond the first
        False result since they will not change the final result. Some
        implementations may want to override this behaviour.
        """
        return True

    @classmethod
    def or_stop_on_first_true(cls):
        """
        By default we do not process items in an OR group beyond the first
        True result since they will not change the final result. Some
        implementations may want to override this behaviour.
        """
        return True

    @classmethod
    def is_exit_condition_met(cls, group_name, result):
        if not isinstance(result, bool):
            raise TypeError(f"{cls.__name__} item has non-bool type "
                            f"'{type(result)}' - unable to determine exit "
                            f"condition for logical op='{group_name}'")

        if group_name in ['and', 'nand', 'not']:
            if cls.and_stop_on_first_false() and not result:
                log.info("exit condition met for op='%s'", group_name)
                return True
        elif group_name in ['or']:
            if cls.or_stop_on_first_true() and result:
                log.info("exit condition met for op='%s'", group_name)
                return True

        return False

    @property
    def group_name(self):
        return self.override_name.lower()

    @property
    def group_op_map(self):
        return {'and': all,
                'or': any,
                'nand': lambda r: not all(r),
                'not': lambda r: not all(r),
                'nor': lambda r: not any(r),
                'xor': operator.xor}  # xor requires two items exactly

    def get_items(self):
        allow_members = False
        query = PropQuery(mapping_id=self.mapping_id, group_id=self.group_id,
                          allow_grouped=self.group_id is None,
                          allow_members=allow_members,
                          allow_primaries=not allow_members,
                          allow_members_if_group_id_matches=(self.mapping_id is
                                                             not None),
                          allow_implicit_primary=not allow_members)
        yield from self.manager.make_all_properties(
                                                 self.override_path,
                                                 self.root,
                                                 self.context,
                                                 query,
                                                 fetch_whole_stack=True)

    @staticmethod
    def fetch_item_result(item):
        """
        By default we expect each item to be an object with a 'result'
        attribute. Override this method if this is not the case.
        """
        try:
            return item.result
        except Exception:
            log.exception("failed to get result from item %s", item)
            raise

    @property
    def result(self):
        """
        Get the result of each item in the group and apply the chosen logical
        operator to the group. Returns the final result after applying the
        operator.
        """
        log.info("======== %s.result.start ========",
                 self.__class__.__name__)
        log.info("%s.%s.result (path=%s, group_ids=%s)",
                 self.__class__.__name__, self.group_name,
                 self.override_path, self.group_ids)
        results = []
        for item in self.get_items():
            log.info("%s.%s: fetching result from %s (mapping_ids=%s, "
                     "group_ids=%s)",
                     self.__class__.__name__, self.group_name,
                     item.__class__.__name__, item.mapping_ids,
                     item.group_ids)
            result = self.fetch_item_result(item)
            self.override_group_stats['items_executed'] += 1
            results.append(result)
            if self.is_exit_condition_met(self.group_name, result):
                break

        if not results:
            raise PropertreeTreeError("unexpected empty results group")

        ret = self.group_op_map[self.group_name](results)
        log.info("%s.%s(%s) -> %s (group_ids=%s)", self.__class__.__name__,
                 self.group_name.upper(), results, ret, self.group_ids)
        log.info("======== %s.result.end ========",
                 self.__class__.__name__)
        return ret


class PTreeMappedOverrideBase(PTreeOverrideBase):
    """ Base class for implementations of mapped properties. """
    # Add one or more property classes that will be members of this mapping.
    override_members: list = []

    # Set this to optionally override the globally registered implementation of
    # PTreeLogicalGrouping with a custom variant to be used only with this
    # property.
    override_logical_grouping_type = None

    def __iter__(self):
        """ Generator giving all items of this property. """
        log.info("%s.__iter__()", self.__class__.__name__)
        query = PropQuery(allow_implicit_primary=self.is_implicit_primary)
        buildinfo = BuildInfo(query, fetch_whole_stack=True)
        yield from self.manager.make_property(self.root, self.override_path,
                                              self.context, buildinfo)

    @property
    def _member_keys_logical_grouping(self):
        keys = PTreeLogicalGrouping.get_override_keys_back_compat()[:]
        # property names are registered this way so do this to match for
        # name lookups.
        keys = [key.replace('-', '_') for key in keys]
        return keys

    @property
    def _member_keys(self):
        keys = []
        # make sure we don't modify the original
        members = self.override_members[:]
        # Include implicit member keys. We allow members to be grouped and
        # support items of type literal.
        members.extend([PTreeOverrideLiteralType, PTreeLogicalGrouping])

        for member in members:
            keys += member.get_override_keys_back_compat()

        # property names are registered this way so do this to match for
        # name lookups.
        keys = [key.replace('-', '_') for key in keys]
        return keys

    @property
    def members(self):
        """ Generator giving all member properties of this mapping. """
        log.info("%s.members()", self.__class__.__name__)

        # First search for all members excluding implementations of
        # PTreeLogicalGrouping.
        propfilter = [f"{self.override_path}.{name}" for name in
                      self._member_keys
                      if name not in self._member_keys_logical_grouping]
        query = PropQuery(mapping_id=self.mapping_id, group_id=self.group_id,
                          allow_implicit_primary=True)
        buildinfo = BuildInfo(query)
        for path in propfilter:
            yield from self.manager.make_property(self.root, path,
                                                  self.context, buildinfo)

        # Now search for any PTreeLogicalGrouping and return full stack. This
        # is because each item will have its own group id and is therefore
        # independent of others i.e. iterating over an item won't give you
        # the stack.
        propfilter = [f"{self.override_path}.{name}" for name in
                      self._member_keys_logical_grouping]
        query = PropQuery(mapping_id=self.mapping_id, group_id=self.group_id)
        buildinfo = BuildInfo(query, fetch_whole_stack=True)
        for path in propfilter:
            yield from self.manager.make_property(self.root, path,
                                                  self.context, buildinfo)

    def _get_override_attribute(self, name):
        # Allow object attributes to be defined and retrieved.
        if name not in self._member_keys:
            return super()._get_override_attribute(name)

        query = PropQuery(allow_members=True, mapping_id=self.mapping_id,
                          allow_implicit_primary=True, group_id=self.group_id)
        buildinfo = BuildInfo(query)
        path = f"{self.override_path}.{name}"
        flat_path = self.manager.flatten_path(path)

        if flat_path not in self.manager.properties:
            path = f"{self.override_path}.{name.replace('_', '-')}"
            flat_path = self.manager.flatten_path(path)

        if flat_path not in self.manager.properties:
            # For backwards compatibility with propertree v1, allow members to
            # be empty.
            log.info("member '%s' not found in %s (flat_path=%s) - "
                     "returning None", name, self.__class__.__name__,
                     flat_path)
            return None

        stack = self.manager.properties[flat_path]
        return stack.first(self.root, self.context, name, self.manager,
                           buildinfo)


class State(UserDict):
    """ Representation of property state. """
    def __init__(self, content, node_cls, path, parent=None,
                 is_implicit_primary=False, has_implicit_primary=False,
                 mapping_ids=None, group_ids=None, path_context=None):
        """
        @param content: Property content.
        @param node_cls: Class used to create this property.
        @param path: Absolute path to this property.
        @param parent: Property cache path to parent of this property. This
                       will be None if the property has no parent.
        @param is_implicit_primary: If True this property will not be
                                    implicitly resolvable i.e. it will only be
                                    accessible if called directly by name but
                                    will not appear when iterating over all
                                    properties.
        @param has_implicit_primary: if True this means that this is a member
                                     property with an implicitly registered
                                     primary such that when iterating over a
                                     leaf we will allow iterating over members
                                     instead of primaries.
        @param mapping_ids Optional list of mapping ids associated with this
                           property.
        @param group_ids Optional list of group ids associated with this
                         property.
        @param path_context: a unique id representing the context of the path
                             to this property. Since a patch may lead to a
                             list, dict or singleton, this gives us a way to
                             know e.g. if we are within a new list item or not.
        """
        data = {'idx': None, 'content': content, 'cls': node_cls,
                'path': path, 'parent': parent,
                'is_implicit_primary': is_implicit_primary,
                'has_implicit_primary': has_implicit_primary,
                'mapping_ids': mapping_ids or [],
                'group_ids': group_ids or [],
                'is_copy': False,
                'path_context': path_context}
        super().__init__(data)

    def __getitem__(self, key):
        if key == 'cache_path':
            if self.data['idx'] is None:
                raise ValueError("state item index not set")

            return f"{self.data['path']}:{self.data['idx']}"

        return super().__getitem__(key)

    def get_ref(self):
        """
        A dissociated reference to this state object that can be modified
        without impacting the original state data.
        """
        return {'idx': self.data['idx'], 'path': self.data['path']}

    def __repr__(self):
        info = []
        for key, val in self.data.items():
            # Skip this since it will bloat the logs
            if key == 'content':
                continue

            info.append(f"{key}={val}")

        return ", ".join(info)


class PropQuery():  # pylint: disable=too-many-instance-attributes
    """ Property query object. Provides a common way to query for properties.
    """
    def __init__(self, mapping_id=None, group_id=None,
                 allow_members=True, allow_primaries=True,
                 allow_members_if_group_id_matches=False,
                 allow_grouped=False,
                 allow_implicit_primary=False,
                 allow_nested_mappings=True,
                 force_group_head_id=False):
        """
        @param mapping_id: If provided, the item we are looking for must have a
                           matching mapping_id.
        @param group_id: If provided, the item we are looking for must have a
                         matching leading group_id.
        @param allow_members: Allow properties that are members of a mapping.
                              By default only their primary would be returned.
        @param allow_primaries: Allow properties that are mapping primaries.
        @param allow_members_if_group_id_matches: Set True to allow matching
                                                  any members that match
                                                  group_id.
        @param allow_grouped: If a group_id is not provided, allows items with
                              group_ids to be found.
        @param allow_implicit_primary: If set to True implicit primaries will
                                       be included in results.
        @param allow_nested_mappings: nested mappings are stored at the same
                                      (branch) level so if we only want to
                                      return the root mapping we can set this
                                      to False.
        @param: force_group_head_id: Defaults to False. By default, if an
                                     item we are checking is a logical
                                     grouping we will assume that if it has
                                     len(group_ids) > 1 it is nested and
                                     therefore we will check group_id
                                     against the penultimate id. Setting
                                     this to True allows us to force the
                                     check against the HEAD id.
        """
        self.mapping_id = mapping_id
        self.group_id = group_id
        self.allow_members = allow_members
        self.allow_primaries = allow_primaries
        self.allow_members_if_group_id_matches = \
            allow_members_if_group_id_matches
        self.allow_grouped = allow_grouped
        self.allow_implicit_primary = allow_implicit_primary
        self.allow_nested_mappings = allow_nested_mappings
        self.force_group_head_id = force_group_head_id

    def __repr__(self):
        return (f"{self.__class__.__name__}(mapping_id={self.mapping_id}, "
                f"group_id={self.group_id}, "
                f"allow_members={self.allow_members}, "
                f"allow_primaries={self.allow_primaries}, "
                f"allow_grouped={self.allow_grouped}, "
                f"allow_implicit_primary={self.allow_implicit_primary}, "
                f"allow_nested_mappings={self.allow_nested_mappings}, "
                "allow_members_if_group_id_matches="
                f"{self.allow_members_if_group_id_matches})")

    def _gid_to_check(self, item):
        # NOTE: if item is a grouping, its unique id is at the head of
        #       group_ids so if we want to match it as a member of another
        #       grouping i.e. nested then we need to get the penultimate id.
        if not item['group_ids']:
            return None

        if (issubclass(item['cls'], PTreeLogicalGrouping) and
                len(item['group_ids']) > 1 and not self.force_group_head_id):
            return item['group_ids'][-2]

        return item['group_ids'][-1]

    def validate_groupings(self, item):
        """
        NOTE: stacked properties can contain items from different groupings
              (group ids).
        """
        if self.group_id:
            if not item['group_ids']:
                return False

            gid = self._gid_to_check(item)
            if gid != self.group_id:
                log.info("skipped %s with unexpected group_id "
                         "(expected=%s, gid=%s, group_ids=%s))",
                         item['cls'].__name__,
                         self.group_id, gid, item['group_ids'])
                return False
        elif item['group_ids']:
            # Skip grouped properties that are not themselves a group primary
            if not self.allow_grouped:
                if not issubclass(item['cls'], PTreeLogicalGrouping):
                    log.info("skipped grouped %s since "
                             "allow_grouped=False", item['cls'].__name__)
                    return False

                if len(item['group_ids']) > 1:
                    log.info("skipped nested grouping primary %s",
                             item['cls'].__name__)
                    return False

        return True

    @staticmethod
    def _mid_to_check(item):
        # NOTE: if item is a mapping, its unique id is at the head of
        #       mapping_ids so if we want to match it as a member of another
        #       mapping i.e. nested then we need to get the penultimate id.
        if not item['mapping_ids']:
            return None

        if (issubclass(item['cls'], PTreeMappedOverrideBase) and
                len(item['mapping_ids']) > 1):
            return item['mapping_ids'][-2]

        return item['mapping_ids'][-1]

    def validate_mappings(self, item: State):
        if (not self.allow_implicit_primary and
                item['is_implicit_primary']):
            log.info("skipped implicit primary %s", item['cls'].__name__)
            return False

        if self.mapping_id:
            if not item['mapping_ids']:
                log.info("skipped %s with mapping_ids=%s "
                         "(expected=%s)", item['cls'].__name__,
                         item['mapping_ids'], self.mapping_id)
                return False

            mid = self._mid_to_check(item)
            if self.mapping_id != mid:
                log.info("skipped %s with unexpected mapping_id "
                         "(expected=%s, mid=%s, mapping_ids=%s)",
                         item['cls'].__name__, self.mapping_id, mid,
                         item['mapping_ids'])
                return False

        if (not self.allow_members and item['mapping_ids'] and not
                issubclass(item['cls'], PTreeMappedOverrideBase)):

            gid = self._gid_to_check(item)
            if not (item['group_ids'] and
                    self.group_id == gid and
                    self.allow_members_if_group_id_matches):
                log.info("skipped member %s since allowed_members=%s, "
                         "allow_members_if_group_id_matches=%s, "
                         "group_id=%s",
                         item['cls'].__name__, self.allow_members,
                         self.allow_members_if_group_id_matches,
                         self.group_id)
                return False

        if not self.allow_nested_mappings and item['mapping_ids']:
            if len(item['mapping_ids']) > 1:
                return False

        if (not self.allow_primaries and
                issubclass(item['cls'], PTreeMappedOverrideBase)):
            log.info("skipped %s with mapping_ids=%s since it is a "
                     "mapping primary", item['cls'].__name__,
                     item['mapping_ids'])

        return True

    def apply(self, item: State):
        if not self.validate_groupings(item):
            return False

        if not self.validate_mappings(item):
            return False

        gid = self._gid_to_check(item)
        log.info("matched item (%s, expected: group_id=%s, gid=%s, "
                 "mapping_id=%s)", item, self.group_id, gid, self.mapping_id)

        return True


class BuildInfo():  # pylint: disable=too-few-public-methods
    """ Settings for building a property object. """
    def __init__(self,
                 query: PropQuery,
                 path_filter: str | None = None,
                 fetch_whole_stack: bool = False,
                 skip_build: bool = False,
                 allow_copy: bool = False):
        """
        Settings used for fetching and creating property objects.

        @param query: property query used to identify items within
                      a property stack.
        @param path_filter: If we want to find properties that are descendants
                            of a path we can set this to the parent path.
        @param fetch_whole_stack: Set to True to only return the first item
                                  found.
        @param skip_build: Set to True to return stack items rather than
                           creating property objects from them.
        @param allow_copy: By default inherited properties are ignored when
                           searching for properties. Set this to True to
                           include them.
        """
        self.query = query
        self.allow_copy = allow_copy
        self.path_filter = path_filter
        self.fetch_whole_stack = fetch_whole_stack
        self.skip_build = skip_build

    def descendant_check(self, item):
        if self.path_filter is None:
            return True

        if (item['path'] == self.path_filter or
                not item['path'].startswith(self.path_filter)):
            log.info("%s is not descendant of %s - skipping",
                     item['path'], self.path_filter)
            return False

        return True


class PropertyCache(UserDict):
    """ Cache for built property objects. """
    def __getitem__(self, name):
        try:
            return super().__getitem__(name)
        except KeyError:
            log.info("path '%s' not found in %s: %s", name,
                     self.__class__.__name__,
                     ', '.join(list(self.data.keys())))
            raise


class PropertyStateManager(UserList):
    """ Stack for property state objects providing methods to query and
    build property objects. """
    def __init__(self, property_cache, initial_state=None, stacked=False):
        self.property_cache = property_cache
        self.stacked = stacked
        if initial_state:
            initial_state['idx'] = 0
            data = [initial_state]
        else:
            data = []

        super().__init__(data)

    def _assert_field_consistency(self, field):
        if len(self) <= 1:
            return

        first = self.data[0]
        for item in self.data[1:]:
            a = first[field]
            b = item[field]
            msg = f"{a} != {b} (field={field})"
            try:
                assert a == b, msg
            except AssertionError:
                log.error(self)
                raise

    def _has_grouped(self):
        for item in self.data:
            if len(item['group_ids']) > 0:
                return True

        return False

    def append(self, item):
        item['idx'] = len(self.data)
        super().append(item)
        # Paths can vary for grouped items but otherwise should be consistent
        if not self._has_grouped:
            self._assert_field_consistency('path')

    def first(self, root, context, name, manager, buildinfo: BuildInfo):
        log.info("getting first item from stack (depth=%s) of '%s' "
                 "(%s)", len(self), name, buildinfo.query)
        for item in self:
            if not buildinfo.query.apply(item):
                continue

            return self.make(root, context, item, manager)

        log.debug("all items were skipped: %s", repr(self))

    def query_stack(self, query: PropQuery):
        path = self[0]['path']
        flat_path = PTreeOverrideManager.flatten_path(path)
        log.info("querying %s stack with %s (depth=%s)", flat_path, query,
                 len(self))

        num_results = 0
        for item in self:
            if not query.apply(item):
                continue

            num_results += 1
            yield item

        log.info("query reached end of stack with %s results", num_results)

    def build_stack(self, root, context, manager, buildinfo: BuildInfo):
        """
        Build/instantiate each item in a property stack.
        """
        query = buildinfo.query
        path = self[0]['path']
        flat_path = PTreeOverrideManager.flatten_path(path)
        log.debug("building %s stack (%s, depth=%s)", flat_path,
                  query, len(self))

        num_built = 0
        for item in self:
            if not buildinfo.descendant_check(item):
                continue

            if item['is_copy'] and not buildinfo.allow_copy:
                log.info("skipping %s as it is a copy (inherited)",
                         item['cls'].__name__)
                continue

            if not query.apply(item):
                continue

            num_built += 1
            if buildinfo.skip_build:
                yield item
            else:
                yield self.make(root, context, item, manager)

            if not buildinfo.fetch_whole_stack:
                log.info("fetch_whole_stack=False - skipping rest")
                break

        if num_built == 0:
            log.debug("all items were skipped: %s", repr(self))

    def make(self, root, context, item, manager):
        path, _, name = item['path'].rpartition('.')
        cache_key = f"{item['path']}:{item['idx']}"
        if cache_key in self.property_cache:
            log.info("creating %s object (path=%s, idx=%s, from_cache=True)",
                     item['cls'].__name__, item['path'], item['idx'])
            return self.property_cache[cache_key]

        log.info("creating %s object (path=%s, idx=%s, from_cache=False)",
                 item['cls'].__name__, item['path'], item['idx'])

        prop = item['cls'](root, name, item['content'], path,
                           context=context, manager=manager, state=item)
        self.property_cache[cache_key] = prop
        return prop

    def deepcopy(self):
        """
        Make a deepcopy of properties and set all items is_copy=True to mark
        them as global. This can be overridden by descendants who want to
        modify with their own values.
        """
        if self.stacked:
            p = PropertyStateManager(self.property_cache)
            for s in self.data:
                copied = copy.deepcopy(s)
                copied['is_copy'] = True
                p.append(copied)

            return p

        copied = copy.deepcopy(self.data[0])
        copied['is_copy'] = True
        return PropertyStateManager(self.property_cache, initial_state=copied)

    def __repr__(self):
        info = f"\n{self[0]['cls'].__name__}:"  # pylint: disable=no-member
        for item in self:
            info += (f"\n[{item['idx']}] path={item['path']}, "
                     f"is_implicit_primary={item['is_implicit_primary']}, "
                     f"has_implicit_primary={item['has_implicit_primary']}, "
                     f"mapping_ids={item['mapping_ids']}, "
                     f"group_ids={item['group_ids']}")

        return info


class PTreeOverrideManager(UserDict):
    """ Manages a property tree. """
    def __init__(self, root_path, content, override_handlers):
        self.override_handlers = override_handlers
        self._branches = {}
        self._properties_global = {}
        self._branch_properties = {}
        self._property_cache = PropertyCache()
        log.info("starting build")
        super().__init__(self._build(root_path, content, {},
                                     self._branch_properties,
                                     parent_branch=root_path))
        log.info("build complete")
        if not self.data:
            # This allows us to getattr() in a section that has no branches
            log.info("no branches found so setting default root='%s' (%s "
                     "global properties):", root_path,
                     len(self.properties))
            # If the section is truly flat (no branches) then we expect these
            # to contain the same properties albeit branch properties are keyed
            # by name whereas global are keyed by path and therefore can have
            # more than one entry for the same property (think groups etc).
            try:
                msg = ("the number of global properties "
                       f"({len(self.properties)}) is less than the "
                       "the total number of branch properties "
                       f"({len(self._branch_properties)})")
                assert (len(self.properties) ==
                        len(self._branch_properties)), msg
            except AssertionError:
                log.error(self.properties.keys())
                log.error(self._branch_properties.keys())
                for prop in self.properties.values():
                    log.info(prop)
                raise

            self.data[root_path] = self._branch_properties

        # Show all resolved properties
        self.debug_show_all_properties()

    @staticmethod
    def flatten_path(path):
        """
        Since mapping primaries and logical groupings are registered at the
        same branch property level we need to flatten their full path when
        searching for them since that is how they are registered.
        """
        group_keys = PTreeLogicalGrouping.get_override_keys_back_compat()
        map_primary_keys = []
        for cls_list in REGISTERED_OVERRIDES.values():
            for cls in cls_list:
                if issubclass(cls, PTreeMappedOverrideBase):
                    keys = cls.get_override_keys_back_compat()
                    map_primary_keys.extend(keys)

        split_path = list(reversed(path.split('.')))
        if len(split_path) < 3:
            return path

        squashed_path = []
        # always keep start and end but also consider end since it may be a
        # mapping.
        for part in split_path[1:-1]:
            if part in group_keys:
                continue

            if part in map_primary_keys:
                continue

            squashed_path.append(part)

        squashed_path.append(split_path[-1])

        flat_path = ''
        for part in reversed(squashed_path):
            if not flat_path:
                flat_path = part
            else:
                flat_path += "." + part

        flat_path += '.' + split_path[0]
        if path != flat_path:
            log.debug("flattened path %s -> %s", path, flat_path)

        return flat_path

    @property
    def property_cache(self):
        return self._property_cache

    def debug_show_all_properties(self):
        log.debug("=" * 60)
        for path, prop in self.properties.items():
            log.debug("\npath=%s%s\n", path, prop)

    @property
    def branches(self):
        return self._branches

    @property
    def properties(self):
        return self._properties_global

    def get_property(self, path: str, idx: int | None = None):
        log.debug("get_property path=%s, idx=%s", path, idx)
        flat_path = self.flatten_path(path)

        all_props = list(self.properties.keys())
        if flat_path not in all_props:
            log.info("property not found with flat_path=%s available keys "
                     "are:\n%s",
                     flat_path, '\n'.join(list(all_props)))
            return None

        prop = self.properties[flat_path]
        if idx is None:
            return prop

        return prop[idx]

    def make_property(self, root, path, context, buildinfo: BuildInfo,
                      allow_global=False):
        flat_path = self.flatten_path(path)
        if flat_path in self.properties:
            pstate = self.properties[flat_path]
        else:
            pstate = None
            if allow_global:
                _path, _, _name = flat_path.rpartition('.')
                if _path not in self.data:
                    log.info("path %s not found at root level - property %s "
                             "not found", _path, _name)
                else:
                    buildinfo.allow_copy = True
                    log.info("looking for property '%s' in global scope %s",
                             _name, _path)
                    pstate = self.data[_path].get(_name)

            if not pstate:
                log.info("path='%s' has no items", flat_path)
                return

        yield from pstate.build_stack(root, context, self, buildinfo)

    def make_all_branch_properties(self, root, path, context,
                                   query: PropQuery, skip_build):
        """
        Supports properties from branches. Does not support flat structure.
        """
        log.info("making all branch properties (%s)", query)
        buildinfo = BuildInfo(query, fetch_whole_stack=True,
                              skip_build=skip_build)
        for property_state in self.data[self.flatten_path(path)].values():
            yield from property_state.build_stack(root, context, self,
                                                  buildinfo)

    def make_all_properties(self, root_path, root, context, query: PropQuery,
                            fetch_whole_stack=False, skip_build=False):
        log.info("making all properties (%s, root_path=%s)", query, root_path)
        for path in self.properties:
            buildinfo = BuildInfo(query, path_filter=root_path,
                                  fetch_whole_stack=fetch_whole_stack,
                                  skip_build=skip_build)
            yield from self.make_property(root, path, context, buildinfo)

    def _mark_new_branch(self, path, parent_branch):
        """
        Each new branch is marked as a leaf until it gets a branch of its own
        at which point it, and all of its ancestors marked as non-leaf.
        """
        for branch_path, info in self._branches.items():
            if path.startswith(branch_path):
                info['is_leaf'] = False

        self._branches[path] = {'is_leaf': True, 'parent': parent_branch}

    @staticmethod
    def _copy_properties(properties):
        return {name: p.deepcopy() for name, p in properties.items()}

    def _register_property(self, properties, state, stacked):
        name = state['path'].rpartition('.')[2]
        log.info("registering property '%s' (%s, stacked=%s)",
                 name, state, stacked)

        # Do this so that names can be used as Python callable attributes.
        name = name.replace('-', '_')

        if name in properties:
            if properties[name].stacked:
                log.info("adding '%s' to existing stack (depth=%s)",
                         name, len(properties[name]))
                properties[name].append(state)
                return

            log.info("property %s exists but is not stacked", name)

            # NOTE: at the branch level properties are registered by name but
            #       in the global properties they are registered by full
            #       resolve path. This has the potential for conflicts and must
            #       be protected as such.
            if not properties[name][0]['is_copy']:
                msg = (f"A property with name={name} is already registered "
                       f"(path={properties[name][0]['path']}). Overwriting "
                       "this property with one of the "
                       f"same name with path={state['path']} will cause state "
                       "to be lost.")
                raise RegistryConflictError(msg)

        prop = PropertyStateManager(self._property_cache, state,
                                    stacked=stacked)
        properties[name] = \
            self.properties[self.flatten_path(state['path'])] = prop

    def _get_member_override_primary(self, member_path):
        """
        If the property at path is a member of a PTreeMappedOverrideBase
        return primary class otherwise return None.
        """
        log.debug("fetching primary for %s", member_path)
        member_name = member_path.rpartition('.')[2]
        return self._get_override_handler(member_name).override_primary

    def _add_implicit_member_primary(self, primary_cls, member_path, content,
                                     parent_state, properties):
        """
        Create an implicit primary property for the member at member_path.
        """
        primary_key = primary_cls.get_override_keys_back_compat()[0]
        parent_path = member_path.rpartition('.')[0]
        primary_path = f"{parent_path}.{primary_key}"
        log.info("implicitly registering mapping primary '%s' at "
                 "path '%s'", primary_key, primary_path)
        primary_state = State(content, primary_cls, primary_path,
                              is_implicit_primary=True)

        if parent_state:
            primary_state['parent'] = parent_state['cache_path']
            # copy groupings and mappings
            for key in ['mapping_ids', 'group_ids']:
                if parent_state[key]:
                    primary_state[key] = parent_state[key][:]

        primary_state['mapping_ids'].append(str(uuid.uuid4()))
        self._register_property(properties, primary_state, True)
        return primary_state

    def _ensure_member_primary(self, member_path: str, node_cls, content,  # noqa, pylint: disable=too-many-locals,too-many-branches
                               properties: dict,
                               parent_state: State,
                               path_context=None):
        """
        Ensure that if this a mapping member, that it's primary has been
        registered. If it has not this would imply that it is an implicit
        primary.
        """
        primary_cls = self._get_member_override_primary(member_path)
        if not primary_cls:
            return None

        log.info("ensuring member %s primary %s exists (path_context=%s)",
                 member_path, primary_cls, path_context)
        primary_key = primary_cls.get_override_keys_back_compat()[0]
        primary_prop = properties.get(primary_key)

        parent_gid = None
        parent_mid = None
        if primary_prop:
            if parent_state:
                if parent_state['mapping_ids']:
                    parent_mid = parent_state['mapping_ids'][-1]

                if parent_state['group_ids']:
                    parent_gid = parent_state['group_ids'][-1]

            # NOTE: if ungrouped primary exists and is implicit it will/must be
            # a singleton and we associate all descendant members that don't
            # have an explicit primary with this implicit primary.
            pq = PropQuery(allow_implicit_primary=True, allow_grouped=True)
            final_prop = None
            for prop in primary_prop.query_stack(pq):
                if not prop['is_implicit_primary']:
                    final_prop = prop
                    continue

                # Implicit mappings in a dict context that are also part of a
                # logical group should be treated as independent mappings so
                # that their result can be evaluated independently i.e.
                # according to the group and not the internal mapping logic.
                if parent_gid and path_context is None:
                    log.info("skipped implicit primary with path_context=%s",
                             path_context)
                    continue

                if prop['path_context'] != path_context:
                    log.info("skipped implicit primary with path_context=%s "
                             "(expected=%s)", prop['path_context'],
                             path_context)
                    continue

                # if parent_gid is not None and there is a match we expect the
                # first (and only) to be our primary. if parent_gid is None and
                # we get a match we also expect it to be a singleton.

                prim_gid = None
                if prop['group_ids']:
                    prim_gid = prop['group_ids'][-1]

                prim_mid = prop['mapping_ids'][-1]
                log.info("checking implicit primary (mapping_id=%s, "
                         "parent_mid=%s, group_id=%s, parent_gid=%s, "
                         "path_context=%s, parent_path_context=%s)",
                         prim_mid, parent_mid, prim_gid, parent_gid,
                         prop['path_context'], path_context)

                # if the parent and primary have the same group id this
                # means the primary is a member of the group rather than
                # the inverse.
                if parent_gid:
                    if prim_gid != parent_gid:
                        log.info("skipped implicit primary with "
                                 "different grouping id (parent=%s, "
                                 "primary=%s)",
                                 parent_gid, prim_gid)
                        continue

                final_prop = prop
                break

            if final_prop:
                if final_prop['is_implicit_primary']:
                    log.info("primary exists (implicit=True, group_id=%s, "
                             "path_context=%s) - using existing", parent_gid,
                             path_context)
                    return final_prop

                log.info("primary exists (implicit=False) - nothing to "
                         "do")
                return None
        else:
            log.info("primary '%s' does not exist - creating implicit",
                     primary_key)

        if not node_cls.override_auto_implicit_member:
            log.debug("skipping create implicit primary for %s since "
                      "override_auto_implicit_member=False", member_path)
            return None

        return self._add_implicit_member_primary(primary_cls,
                                                 member_path,
                                                 content,
                                                 parent_state,
                                                 properties)

    def check_switch_for_mapping_logical_group_cls(self, node_cls,
                                                   parent_state):
        """
        If we are a PTreeLogicalGrouping that is part of a mapping, find the
        mapping primary to see if it has a customer grouping type and switch
        it out if it does.
        """
        if not (parent_state and parent_state['mapping_ids'] and
                issubclass(node_cls, PTreeLogicalGrouping)):
            return node_cls

        parent_cls = parent_state['cls']
        while issubclass(parent_cls, PTreeLogicalGrouping):
            parent = parent_state['parent']
            if not parent:
                break

            path, _, idx = parent.rpartition(':')
            parent_state = self.get_property(path, int(idx))
            if parent_state:
                parent_cls = parent_state['cls']

        if issubclass(parent_cls, PTreeMappedOverrideBase):
            # its a grouped mapping member, let's make sure we are using the
            # grouping type from this mapping.
            alt_cls = parent_cls.override_logical_grouping_type
            if alt_cls:
                log.info("switching %s for %s", node_cls, alt_cls)
                node_cls = alt_cls

        return node_cls

    def _build_branch_property(self, path, node_cls, content, properties,
                               parent_info: dict, stacked, parent_branch,
                               path_context):
        log.info("new property: path=%s, parent=%s", path, parent_info)
        if parent_info:
            parent_state = self.get_property(parent_info['path'],
                                             parent_info['idx'])
            has_implicit_primary = parent_state['is_implicit_primary']
            mapping_ids = parent_state['mapping_ids'][:]
            # New property inherits its parent's group_ids and we copy parent's
            # group_ids rather than ref since descendants may add further ids
            # to the group.
            group_ids = parent_state.get('group_ids', [])[:]
        else:
            has_implicit_primary = False
            mapping_ids = []
            group_ids = []
            parent_state = None

        if issubclass(node_cls, PTreeMappedOverrideBase):
            # Always stack these to allow for grouped/ungrouped implicits in
            # the same dict.
            stacked = True
            if not mapping_ids:
                mapping_ids = [str(uuid.uuid4())]
            else:
                mapping_ids.append(str(uuid.uuid4()))

        node_cls = self.check_switch_for_mapping_logical_group_cls(
                                                                node_cls,
                                                                parent_state)
        state = State(content, node_cls, path, group_ids=group_ids,
                      mapping_ids=mapping_ids,
                      has_implicit_primary=has_implicit_primary,
                      path_context=path_context)

        if parent_state:
            state['parent'] = parent_state['cache_path']

        if issubclass(node_cls, PTreeLogicalGrouping):
            state['group_ids'].append(str(uuid.uuid4()))

        self._register_property(properties, state, stacked)

        if (issubclass(node_cls, PTreeMappedOverrideBase) or
                issubclass(node_cls, PTreeLogicalGrouping)):
            # NOTE: for groupings we stack grouped properties regardless of if
            # they are in a list or not since they will be identified by their
            # group id and for mapping members we do the same so that we
            # support stacked members that are themselves a mix of grouped and
            # ungrouped.
            # NOTE: we don't copy properties registry since members'
            #       alias principle and if its a grouping thats also like an
            #       alias.
            return self._build(root_path=path, content=content,
                               parent_info=state.get_ref(),
                               properties=properties,
                               stacked=True,
                               parent_branch=parent_branch)

        return {}

    @staticmethod
    def _ensure_not_invalid_member(parent_cls, prop_cls):
        if not issubclass(parent_cls, PTreeMappedOverrideBase):
            return True

        # these are allowed implicitly as members
        if issubclass(prop_cls, PTreeLogicalGrouping):
            return True

        valid_members = [m.__name__ for m in parent_cls.override_members]
        raise PropertyIsNotAMember(f"property {prop_cls.__name__} inside "
                                   f"mapping {parent_cls.__name__} but is "
                                   "not a member of that mapping. Valid "
                                   f"members are: {', '.join(valid_members)}")

    def _get_override_handler(self, key):
        """
        We expect the topmost registered class to be the one that is used.
        """
        return self.override_handlers[key][0]

    def _build(self, root_path, content, parent_info, properties,   # noqa, pylint: disable=too-many-locals,too-many-branches,too-many-statements
               stacked=False, path_context=None, parent_branch=None):
        log.debug("building root_path=%s (parent=%s)", root_path, parent_info)
        tree = {}

        if parent_info:
            # IMPORTANT: do not modify this state
            log.debug("fetching parent %s", parent_info['path'])
            parent_state = self.get_property(parent_info['path'],
                                             parent_info['idx'])
        else:
            parent_state = None

        if isinstance(content, dict):
            # IMPORTANT: process all properties at current level before moving
            #            on to further levels/branches to ensure that all
            #            descendants get the same inherited properties.
            branches = []
            for name, _content in content.items():
                path = f"{root_path}.{name}"
                if parent_state:
                    # Don't tokenise property attributes
                    parent = parent_state['cls']
                    if not parent.allow_subtree or name in dir(parent):
                        log.info("not entering %s.%s: subtree_allowed=%s "
                                 "is_attribute=%s", parent.__name__.lower(),
                                 name,
                                 parent.allow_subtree,
                                 name in dir(parent))
                        continue

                if name not in self.override_handlers:
                    # Stop if content not iterable
                    if not isinstance(_content, (dict, list)):
                        continue

                    log.debug("found branch '%s' - deferring till all "
                              "properties registered", name)
                    branches.append((name, _content))
                    continue

                name = path.rpartition('.')[2]
                node_cls = self._get_override_handler(name)
                if self._get_member_override_primary(path):
                    # if this is a mapping member, ensure its primary
                    # exists.
                    primary_state = self._ensure_member_primary(
                                                 path,
                                                 node_cls,
                                                 content,
                                                 properties,
                                                 parent_state,
                                                 path_context=path_context)
                    if (primary_state and
                            primary_state['is_implicit_primary']):
                        # Ensure parent path is updated for any other
                        # potential members.
                        log.info("updating parent path from %s to %s",
                                 parent_info.get('path'),
                                 primary_state['path'])
                        # NOTE: we are not updating the actual parent
                        # because list items count as independent mappings
                        # i.e. a list of implicit mappings will each end up
                        # with their own parent primary mapping property
                        # IFF they are NOT grouped by a member group of the
                        # same mapping. Conversely, a list of implicit
                        # members that are grouped by a member of their own
                        # parent primary will be treated as part of the
                        # same primary.
                        parent_info = primary_state.get_ref()
                        primary_state['path_context'] = path_context
                elif parent_state:
                    self._ensure_not_invalid_member(
                                          parent_state['cls'],
                                          self._get_override_handler(name))

                if parent_info:
                    path = f"{parent_info['path']}.{name}"

                subtree = self._build_branch_property(path, node_cls,
                                                      _content,
                                                      properties,
                                                      parent_info,
                                                      stacked,
                                                      parent_branch,
                                                      path_context)
                tree = ChainMap(tree, subtree)

            # Now do any branches found at this level
            for (name, _content) in branches:
                log.info("new branch: %s", name)
                path = f"{root_path}.{name}"
                # make copy to allow divergence and inheritance
                tree[path] = nextproperties = self._copy_properties(properties)
                # create new branch
                self._mark_new_branch(path, parent_branch)
                subtree = self._build(root_path=path, content=_content,
                                      parent_info={},
                                      properties=nextproperties,
                                      parent_branch=path)
                tree = ChainMap(tree, subtree)
        elif isinstance(content, list):
            for item in content:
                log.info("found list item")
                subtree = self._build(root_path, item, parent_info,
                                      properties, stacked=True,
                                      path_context=str(uuid.uuid4()),
                                      parent_branch=parent_branch)
                if subtree:
                    self._mark_new_branch(root_path, parent_branch)
                    tree = ChainMap(tree, subtree)
        elif PTreeOverrideLiteralType.has_valid_type(content):
            name = PTreeOverrideLiteralType.get_override_keys_back_compat()[0]
            path = f"{root_path}.{name}"
            node_cls = self._get_override_handler(name)
            subtree = self._build_branch_property(path, node_cls, content,
                                                  properties,
                                                  parent_info,
                                                  stacked, parent_branch,
                                                  path_context)
        else:
            msg = ("unexpected or invalid content '%s' (type=%s, path=%s)",
                   content, type(content), root_path)
            raise ValueError(msg)

        return tree


class BranchInfo():
    """ Holds information about a branch. """
    def __init__(self, path):
        if path is None:
            raise InvalidBranchPathError(f"invalid branch path {path}")

        self._path = path

    @property
    def path(self):
        return self._path.rpartition('.')[2]

    @property
    def name(self):
        return self.path.rpartition('.')[2]


class PTreeSection():  # noqa, pylint: disable=too-many-instance-attributes
    """ The representation of the property tree. """
    def __init__(self,
                 name: str,
                 content: dict | None = None,
                 parent: PTreeSection | None = None,
                 root: PTreeSection | None = None,
                 override_handlers: dict | None = None,
                 override_manager: PTreeOverrideManager | None = None,
                 run_hooks: bool = False,
                 resolve_path: str | None = None,
                 context: dict | None = None):
        """
        Start a new branch section.

        @param name: name of branch.
        @param content: branch content i.e. properties, leaves and other
                        branches.
        @param parent: parent branch.
        @param root: root branch.
        @param override_handlers: registry of override handlers.
        @param override_manager: override manager object.
        @param run_hooks: Set to True to run pre/post hooks.
        @param resolve_path: Resolve path to this branch. Will be None for the
                             root.
        @param context: an optional context object that is passed to all
                        branches and properties.
        """
        log.info("## new section %s: name=%s (resolve_path=%s, "
                 "override_manager=%s)",
                 id(self), name, resolve_path, override_manager is not None)

        if root is None:
            if resolve_path is None:
                resolve_path = name

            self.root = self
        else:
            if resolve_path is None:
                raise PropertreeTreeError("resolve path is None")

            self.root = root

        self.run_hooks = run_hooks
        self._name = name
        self.resolve_path = resolve_path
        self.context = context
        if override_handlers is None:
            self.override_handlers = REGISTERED_OVERRIDES
            OverrideRegistry.post_registration_tasks(self.override_handlers)
            log.debug("final registry state:\n%s\n", OverrideRegistry())
        else:
            self.override_handlers = override_handlers

        self.parent = parent
        self.content = content

        if override_manager is not None:
            self.manager = override_manager
            return

        if self.root == self and self.run_hooks:
            log.info("%s.run: running pre_hook", self.__class__.__name__)
            self.pre_hook()

        self.manager = PTreeOverrideManager(self.resolve_path, self.content,
                                            self.override_handlers)
        log.info("tree: paths=%s, num_branches=%s, branches='%s'",
                 ', '.join(list(self.manager.keys())),
                 len(self.manager.branches),
                 ' '.join(self.manager.branches))

        if self.root == self and self.run_hooks:
            log.info("%s.run: running post_hook", self.__class__.__name__)
            self.post_hook()

    @property
    def name(self):
        return BranchInfo(self._name).name

    def _get_section_attribute(self, name):
        log.info("%s._get_section_attribute(%s)", self.name, name)
        resolve_path = f"{self.resolve_path}.{name}"
        if resolve_path in self.manager.branches:
            return PTreeSection(resolve_path,
                                parent=self,
                                override_manager=self.manager,
                                override_handlers=self.override_handlers,
                                resolve_path=resolve_path,
                                context=self.context)

        log.info("%s not a branch - fetching property", resolve_path)
        buildinfo = BuildInfo(PropQuery(allow_members=True,
                                        allow_grouped=True,
                                        allow_nested_mappings=True,
                                        allow_implicit_primary=True))
        return next(self.manager.make_property(
                                   self.root,
                                   f"{self.resolve_path}.{name}",
                                   self.context, buildinfo,
                                   allow_global=True), None)

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            try:
                return self._get_section_attribute(name)
            except AttributeError:
                log.info("unable to resolve resolve_path=%s, name=%s, "
                         "manager_branches=%s", self.resolve_path, name,
                         list(self.manager.keys()))

        return None

    def _get_root_properties(self, skip_build=False):
        query = PropQuery(allow_members=False, allow_implicit_primary=True,
                          allow_nested_mappings=False)
        if self.resolve_path in self.manager:
            yield from self.manager.make_all_branch_properties(
                                                        self.root,
                                                        self.resolve_path,
                                                        self.context,
                                                        query,
                                                        skip_build=skip_build)
            return

        log.info("section '%s' is flat (has no branches) so returning all "
                 "properties (path=%s)", self.name, self.resolve_path)
        yield from self.manager.make_all_properties(self.resolve_path,
                                                    self.root, self.context,
                                                    query,
                                                    skip_build=skip_build)

    def __iter__(self):
        log.info("%s.__iter__() (resolve_path=%s)", self.name,
                 self.resolve_path)
        yield from self._get_root_properties()

    def __len__(self):
        log.info("%s.__len__()", self.name)
        return len(list(self._get_root_properties(skip_build=True)))

    @property
    def branch_sections(self):
        for resolve_path, branch in self.manager.branches.items():
            if not branch['is_leaf']:
                yield PTreeSection(resolve_path,
                                   parent=BranchInfo(branch['parent']),
                                   root=self.root,
                                   override_manager=self.manager,
                                   override_handlers=self.override_handlers,
                                   resolve_path=resolve_path,
                                   context=self.context)

    @property
    def leaf_sections(self):
        log.info("%s.leaf_sections()", self.__class__.__name__)
        if not self.manager.branches and self.manager.properties:
            yield PTreeSection(self.resolve_path,
                               parent=BranchInfo(self.resolve_path),
                               root=self.root,
                               override_manager=self.manager,
                               override_handlers=self.override_handlers,
                               resolve_path=self.resolve_path,
                               context=self.context)

            return

        for resolve_path, branch in self.manager.branches.items():
            if branch['is_leaf']:
                yield PTreeSection(resolve_path,
                                   parent=BranchInfo(branch['parent']),
                                   root=self.root,
                                   override_manager=self.manager,
                                   override_handlers=self.override_handlers,
                                   resolve_path=resolve_path,
                                   context=self.context)

    def pre_hook(self):
        pass

    def post_hook(self):
        pass
