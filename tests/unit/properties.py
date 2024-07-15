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

# Disable these globally since they don't apply here
# pylint: disable=too-few-public-methods

import operator

from propertree.log import log
from propertree.propertree2 import (
    PTreeSection,
    PTreeOverrideBase,
    PTreeMappedOverrideBase,
    PTreeLogicalGrouping,
)


class TestPTreeOverrideBase(PTreeOverrideBase):
    """ Base class for test override properties. """
    # Disable auto-registration to avoid conflicts across tests. All tests must
    # register the overrides they need.
    override_autoregister = False


class TestPTreeMappedOverrideBase(PTreeMappedOverrideBase):
    """ Base class for test override mapping properties. """
    # Disable auto-registration to avoid conflicts across tests. All tests must
    # register the overrides they need.
    override_autoregister = False


class PTreeLogicalGroupingWithBoolValues(PTreeLogicalGrouping):
    """ Test logical grouping with bool values. """
    override_autoregister = False

    @staticmethod
    def fetch_item_result(item):
        return item.content


class PTreeLogicalGroupingWithCheckRefs(PTreeLogicalGrouping):
    """ Test logical grouping with string check refs. """
    override_autoregister = False

    def get_check_item(self, name):
        checks = self.context['checks']
        try:
            return checks[name]
        except AttributeError:
            log.error("check '%s' not found in %s", name, checks)

        return None

    def get_items(self):
        items = []
        for item in self.content:
            if self.context and 'checks' in self.context:
                items.append(self.get_check_item(item))

        if items:
            return items

        # Allow to be used for any other purpose i.e. not just check refs
        return super().get_items()


class Vars(TestPTreeOverrideBase):
    """ Test vars property. """
    override_keys = []
    _allow_subtree = False


class Input(TestPTreeOverrideBase):
    """ Test input property. """
    override_keys = []

    @property
    def path(self):
        return self.content['path']


class VarOps(TestPTreeOverrideBase):
    """ Test varops property. """
    override_keys = []

    @property
    def result(self):
        _input = None
        for item in self.content:
            if _input is None:
                _input = item[0]
                continue

            if isinstance(_input, str) and _input.startswith('$'):
                key = _input.partition('$')[2]
                if self.context:
                    vars_prop = self.context['vars']
                else:
                    vars_prop = self.root.vars

                _input = getattr(vars_prop, key)

            log.debug("%s: %s(%s, %s)", self.__class__.__name__, item[0],
                      _input, item[1])
            return getattr(operator, item[0])(_input, item[1])


class Check(TestPTreeOverrideBase):
    """ Test check property. """
    override_keys = []

    @property
    def name(self):
        return self.override_name

    @property
    def items(self):
        section = PTreeSection(self.override_name, self.content,
                               resolve_path=self.override_path,
                               context=self.context)
        for item in section:
            log.debug("check item: label=%s, type=%s", self.override_name,
                      type(item))
            yield item

    def __len__(self):
        return len(list(self.items))

    @property
    def result(self):
        log.debug("getting result for check=%s", self.name)
        results = []
        for item in self.items:
            results.append(item.result)

        log.debug("CHECK AND(%s)", results)
        return all(results)


class ValueCheck(TestPTreeOverrideBase):
    """ Test varcheck property. """
    override_keys = ['valuecheck']

    @property
    def key(self):
        return self.content['key']

    @property
    def value(self):
        return self.content['value']

    @property
    def result(self):
        if self.root.vars:
            return getattr(self.root.vars, self.key) == self.value

        return self.key == self.value


class Checks(TestPTreeOverrideBase):
    """ Test checks property. """
    override_keys = []
    _allow_subtree = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _context = {'vars': self.root.vars}
        if not self.context:
            self.context = _context
        else:
            self.context.update(_context)

    def __getattr__(self, name):
        log.debug("%s.__getattr__(%s)", self.__class__.__name__, name)
        return Check(self.root, name, self.content[name],
                     self.override_path,
                     context=self.context)

    def __iter__(self):
        log.debug("%s.__iter__()", self.__class__.__name__)
        for name in self.content:
            yield Check(self.root, name, self.content[name],
                        self.override_path,
                        context=self.context)


class TypeCheck(TestPTreeOverrideBase):
    """ Test check property. """
    override_keys = []

    @property
    def value(self):
        return self.content.get('value')

    @property
    def value_type(self):
        return self.content.get('type')

    @property
    def result(self):
        log.debug("%s.result", self.__class__.__name__)
        return str(type(self.value).__name__) == self.value_type


class Requires(TestPTreeMappedOverrideBase):
    """ Test requires property. """
    override_keys = []
    override_members = [TypeCheck, VarOps]
    override_logical_grouping_type = PTreeLogicalGroupingWithCheckRefs

    @property
    def result(self):
        log.debug("getting requires result")
        results = []
        for member in self.members:
            for item in member:
                results.append(item.result)

        if not results:
            raise Exception("results list is empty")  # noqa,pylint: disable=broad-exception-raised

        log.debug("%s: %s", self.__class__.__name__, results)
        return all(results)


class Decision(TestPTreeMappedOverrideBase):
    """ Test decision property. """
    override_keys = []
    # NOTE: no members since we are using mapping to get the implicit
    #       PTreeLogicalGrouping.

    @property
    def result(self):
        results = []
        for item in self.members:
            results.append(item.result)

        log.debug("%s: %s", self.__class__.__name__, results)
        return all(results)


class Raises(TestPTreeOverrideBase):
    """ Test raises property. """
    override_keys = []

    @property
    def type(self):
        return self.content['type']

    @property
    def message(self):
        return self.content['message']


class Conclusion(TestPTreeMappedOverrideBase):
    """ Test conclusion property. """
    override_keys = []
    override_members = [Decision, Raises]


class Conclusions(TestPTreeOverrideBase):
    """ Test conclusions property. """
    override_keys = []
    _allow_subtree = False

    def __iter__(self):
        for name, content in self.content.items():
            s = PTreeSection(self.override_name,
                             {name: {'conclusion': content}},
                             context=self.context)
            for c in s.leaf_sections:
                c.conclusion.name = c.name
                yield c.conclusion


class MapMember1(ValueCheck):
    """ Test map member property. """
    override_keys = []


class MapMember2(ValueCheck):
    """ Test map member property. """
    override_keys = []


class MapPrimary(TestPTreeMappedOverrideBase):
    """ Test map primary property. """
    override_keys = []
    override_members = [MapMember1, MapMember2, Requires]


class DeepMember2(ValueCheck):
    """ Test map member property. """
    override_keys = []

    @property
    def deepattr(self):
        return "deepvalue"


class DeepMember1(TestPTreeMappedOverrideBase):
    """ Test map member property. """
    override_keys = []
    override_members = [DeepMember2]


class DeepMap(TestPTreeMappedOverrideBase):
    """ Test map primary property. """
    override_keys = []
    override_members = [DeepMember1]
