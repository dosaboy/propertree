# Copyright 2021 Edward Hope-Morley
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
# pylint: disable=missing-class-docstring,pointless-statement

import yaml
from propertree.propertree2 import (
    PTreeLogicalGrouping,
    PTreeOverrideBase,
    PTreeMappedOverrideBase,
    PTreeOverrideLiteralType,
    PTreeSection,
    OverrideRegistry,
)

from . import properties, utils


class PTreeAssertionAttr(PTreeOverrideBase):
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['key', 'value1', 'value2', 'ops', 'message']

    def __str__(self):
        return self.content

    def __eq__(self, string):
        return self.content == string

    @property
    def ops(self):
        return self.content


class PTreeAssertion(PTreeMappedOverrideBase):
    override_autoregister = False
    override_members = [PTreeAssertionAttr]

    @classmethod
    def _override_keys(cls):
        return ['assertion']

    @property
    def result(self):
        return True


class PTreeAssertions(PTreeMappedOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False
    override_members = [PTreeAssertion]

    @classmethod
    def _override_keys(cls):
        return ['assertions']


class GroupedLiteralType(PTreeOverrideLiteralType):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False


class PTreeStrGroups(PTreeMappedOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False
    override_members = [GroupedLiteralType]

    @classmethod
    def _override_keys(cls):
        return ['strgroups']


class TestPTreeMappedProperties(utils.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.requirements = [PTreeAssertion, PTreeAssertionAttr,
                             PTreeAssertions, GroupedLiteralType,
                             PTreeStrGroups]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_mapping_single_member_full(self):
        """
        A single fully defined mapped property i.e. the principle property name
        is used rather than just its member(s).
        """

        _yaml = """
        assertions:
          assertion:
            key: key1
            value1: 1
            value2: 2
            ops: [gt]
            message: it failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            for assertion in leaf.assertions.members:
                self.assertEqual(len(assertion), 1)
                checked.append(assertion.override_name)
                self.assertEqual(type(assertion), PTreeAssertion)
                self.assertEqual(type(assertion.key), PTreeAssertionAttr)
                checked.append(assertion.key)
                self.assertEqual(assertion.key, 'key1')
                self.assertEqual(assertion.value1, 1)
                self.assertEqual(assertion.value2, 2)
                self.assertEqual(assertion.ops, ['gt'])
                self.assertEqual(assertion.message, 'it failed')

        self.assertEqual(checked, ['assertions', 'assertion', 'key1'])

    def test_mapping_single_member_short(self):
        """
        A single lazily defined mapped property i.e. the member property names
        are used rather than the principle.
        """

        _yaml = """
        assertions:
          key: key1
          value1: 1
          value2: 2
          ops: [gt]
          message: it failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            self.assertEqual(type(leaf.assertions), PTreeAssertions)
            for assertion in leaf.assertions.members:
                self.assertEqual(type(assertion), PTreeAssertion)
                self.assertEqual(len(assertion), 1)
                checked.append(assertion.override_name)
                checked.append(assertion.key)
                self.assertEqual(assertion.key, 'key1')
                self.assertEqual(assertion.value1, 1)
                self.assertEqual(assertion.value2, 2)
                self.assertEqual(assertion.ops, ['gt'])
                self.assertEqual(assertion.message, 'it failed')

        self.assertEqual(checked, ['assertions', 'assertion', 'key1'])

    def test_mapping_list_members_partial(self):
        """
        A list of lazily defined properties. One with only a subset of members
        defined.
        """

        _yaml = """
        assertions:
          - assertion:
              key: key1
              value1: 1
              ops: [gt]
              message: it failed
          - assertion:
              key: key2
              value1: 3
              value2: 4
              ops: [lt]
              message: it also failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            for assertion in leaf.assertions.members:
                self.assertEqual(len(assertion), 2)
                checked.append(assertion.override_name)
                for attrs in assertion:
                    checked.append(attrs.key)
                    if attrs.key == 'key1':
                        self.assertEqual(attrs.key, 'key1')
                        self.assertEqual(attrs.value1, 1)
                        self.assertEqual(attrs.value2, None)
                        self.assertEqual(attrs.ops, ['gt'])
                        self.assertEqual(attrs.message, 'it failed')
                    else:
                        self.assertEqual(attrs.key, 'key2')
                        self.assertEqual(attrs.value1, 3)
                        self.assertEqual(attrs.value2, 4)
                        self.assertEqual(attrs.ops, ['lt'])
                        self.assertEqual(attrs.message,
                                         'it also failed')

        self.assertEqual(checked, ['assertions', 'assertion', 'key1', 'key2'])

    def test_mapping_list_members_full(self):
        """
        A list of lazily defined properties. Both with all members defined.
        """
        _yaml = """
        assertions:
          - assertion:
              key: key1
              value1: 1
              value2: 2
              ops: [gt]
              message: it failed
          - assertion:
              key: key2
              value1: 3
              value2: 4
              ops: [lt]
              message: it also failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            self.assertEqual(type(leaf.assertions), PTreeAssertions)
            self.assertEqual(len(leaf.assertions), 1)
            self.assertEqual(len(leaf.assertions.assertion), 2)
            self.assertEqual(type(leaf.assertions.assertion), PTreeAssertion)
            for assertion in leaf.assertions.members:
                for item in assertion:
                    self.assertEqual(len(item), 2)
                    self.assertEqual(item.override_name, 'assertion')
                    checked.append(str(item.key))
                    if item.key == 'key1':
                        self.assertEqual(item.key, 'key1')
                        self.assertEqual(item.value1, 1)
                        self.assertEqual(item.value2, 2)
                        self.assertEqual(item.ops, ['gt'])
                        self.assertEqual(item.message, 'it failed')
                    else:
                        self.assertEqual(item.key, 'key2')
                        self.assertEqual(item.value1, 3)
                        self.assertEqual(item.value2, 4)
                        self.assertEqual(item.ops, ['lt'])
                        self.assertEqual(item.message,
                                         'it also failed')

        self.assertEqual(checked, ['assertions', 'key1', 'key2'])

    def test_mapping_list_members_implicit_full(self):
        _yaml = """
        assertions:
          - key: key1
            value1: 1
            value2: 2
            ops: [gt]
            message: it failed
          - key: key2
            value1: 3
            value2: 4
            ops: [lt]
            message: it also failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            self.assertEqual(type(leaf.assertions), PTreeAssertions)
            self.assertEqual(len(leaf.assertions), 1)
            self.assertEqual(len(leaf.assertions.assertion), 2)
            self.assertEqual(type(leaf.assertions.assertion), PTreeAssertion)
            for assertion in leaf.assertions.members:
                for item in assertion:
                    self.assertEqual(len(item), 2)
                    self.assertEqual(item.override_name, 'assertion')
                    checked.append(str(item.key))
                    if item.key == 'key1':
                        self.assertEqual(item.key, 'key1')
                        self.assertEqual(item.value1, 1)
                        self.assertEqual(item.value2, 2)
                        self.assertEqual(item.ops, ['gt'])
                        self.assertEqual(item.message, 'it failed')
                    else:
                        self.assertEqual(item.key, 'key2')
                        self.assertEqual(item.value1, 3)
                        self.assertEqual(item.value2, 4)
                        self.assertEqual(item.ops, ['lt'])
                        self.assertEqual(item.message,
                                         'it also failed')

        self.assertEqual(checked, ['assertions', 'key1', 'key2'])

    def test_mapping_list_members_full_w_lopt(self):
        """
        A list of properties grouped by a logical operator.
        """
        _yaml = """
        assertions:
          and:
            - assertion:
                key: key1
                value1: 1
                value2: 2
                ops: [gt]
                message: it failed
            - assertion:
                key: key2
                value1: 3
                value2: 4
                ops: [lt]
                message: it also failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            for member in leaf.assertions.members:
                self.assertEqual(len(member), 1)
                checked.append(member.override_name)
                self.assertEqual(member.override_name, 'and')
                self.assertEqual(member.result, True)
                num_items = member.override_group_stats['items_executed']
                self.assertEqual(num_items, 2)

        self.assertEqual(checked, ['assertions', 'and'])

    def test_mapping_list_members_implicit_full_w_lopt(self):
        """
        A list of properties grouped by a logical operator.
        """
        _yaml = """
        assertions:
          and:
            - key: key1
              value1: 1
              value2: 2
              ops: [gt]
              message: it failed
            - key: key2
              value1: 3
              value2: 4
              ops: [lt]
              message: it also failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions.override_name)
            for member in leaf.assertions.members:
                self.assertEqual(len(member), 1)
                checked.append(member.override_name)
                self.assertEqual(member.override_name, 'and')
                self.assertEqual(member.result, True)
                num_items = member.override_group_stats['items_executed']
                self.assertEqual(num_items, 2)

        self.assertEqual(checked, ['assertions', 'and'])

    def test_mapping_list_members_simple_w_lopt(self):
        """
        A list of properties grouped by a logical operator.
        """
        _yaml = """
        strgroups:
          and:
            - True
            - True
            - True
        """
        group_type = properties.PTreeLogicalGroupingWithBoolValues
        OverrideRegistry.register([group_type])
        try:
            root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
            members = []
            for leaf in root.leaf_sections:
                self.assertEqual(type(leaf.strgroups), PTreeStrGroups)
                for strgroup in leaf.strgroups:
                    for member in strgroup.members:
                        self.assertEqual(
                            type(member),
                            properties.PTreeLogicalGroupingWithBoolValues)
                        for item in member:
                            members.append(item.__class__)
                            self.assertTrue(item.result)
                            num_items = \
                                item.override_group_stats['items_executed']
                            self.assertEqual(num_items, 3)
        finally:
            OverrideRegistry.unregister([group_type])
            OverrideRegistry.register([PTreeLogicalGrouping])

        self.assertEqual(members, [group_type])

    def process_optgroup(self, assertiongroup, opname):
        """
        Process a PTreeAssertions mapping that can also have nested
        mappings.

        Returns a list of PTreeAssertionAttr values found.
        """
        vals = []
        for optgroup in assertiongroup:
            self.assertEqual(optgroup.override_name, opname)
            for member in optgroup:
                if member.override_name == 'assertion':
                    if opname == 'and':
                        # i.e. num of assertions n/i nested
                        self.assertEqual(len(member), 2)
                    else:
                        self.assertEqual(len(member), 1)

                    self.assertEqual(type(member), PTreeAssertion)
                    for assertion in member:
                        self.assertEqual(len(assertion), 1)
                        self.assertEqual(assertion.override_name, 'assertion')
                        vals.append(assertion.key)
                else:
                    self.assertEqual(len(member), 1)
                    vals += self.process_optgroup(member, 'not')

        return vals

    def test_mapping_list_members_nested(self):
        """
        This tests nested mappings where those mappings can themselves be
        composites of more than one mapping.
        """
        self.skipTest("this is no longer how logical groupings are handled.")

        _yaml = """
        assertions:
          and:
            - key: true
            - key: foo
            - not:
                key: false
          or:
            - key: False
            - not:
                key: True
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml))
        vals = []
        opnames_to_check = ['and', 'or']
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf), PTreeSection)
            self.assertEqual(type(leaf.assertions), PTreeAssertions)
            self.assertEqual(len(leaf.assertions), 1)
            for assertions in leaf.assertions:
                self.assertEqual(assertions.override_name, 'assertions')
                self.assertEqual(len(assertions), 2)
                for assertiongroup in assertions:
                    self.assertEqual(len(assertiongroup), 1)
                    vals += self.process_optgroup(assertiongroup,
                                                  opnames_to_check.pop(0))

        self.assertEqual(vals, [True, 'foo', False, False, True])
