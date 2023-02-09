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
import yaml

from . import utils

from propertree import (
    PTreeOverrideBase,
    PTreeMappedOverrideBase,
    PTreeOverrideRawType,
    PTreeSection
)
from propertree.propertree import MappedOverrideState


class PTreeAssertionAttr(PTreeOverrideBase):

    @classmethod
    def _override_keys(cls):
        return ['key', 'value1', 'value2', 'ops', 'message']

    @property
    def ops(self):
        return self.content


class PTreeAssertion(PTreeMappedOverrideBase):

    @classmethod
    def _override_keys(cls):
        return ['assertion']

    @classmethod
    def _override_mapped_member_types(cls):
        return [PTreeAssertionAttr]


class PTreeAssertionsBase(PTreeMappedOverrideBase):

    @classmethod
    def _override_mapped_member_types(cls):
        return [PTreeAssertion]


class PTreeAssertionsLogicalOpt(PTreeAssertionsBase):

    @classmethod
    def _override_keys(cls):
        return ['and', 'or', 'not']


class PTreeAssertions(PTreeAssertionsBase):

    @classmethod
    def _override_keys(cls):
        return ['assertions']

    @classmethod
    def _override_mapped_member_types(cls):
        return super()._override_mapped_member_types() + \
                    [PTreeAssertionsLogicalOpt]


class PTreeStrGroupBase(PTreeMappedOverrideBase):

    @classmethod
    def _override_mapped_member_types(cls):
        return [PTreeOverrideRawType]


class PTreeStrGroupLogicalOpt(PTreeStrGroupBase):

    @classmethod
    def _override_keys(cls):
        return ['and', 'or', 'not']


class PTreeStrGroups(PTreeStrGroupBase):

    @classmethod
    def _override_keys(cls):
        return ['strgroups']

    @classmethod
    def _override_mapped_member_types(cls):
        return super()._override_mapped_member_types() + \
                    [PTreeStrGroupLogicalOpt]


class TestPTreeMappedProperties(utils.BaseTestCase):

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
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeAssertions])
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions._override_name)
            for assertion in leaf.assertions.members:
                self.assertEqual(len(assertion), 1)
                checked.append(assertion._override_name)
                for attrs in assertion:
                    checked.append(attrs.key)
                    self.assertEqual(attrs.key, 'key1')
                    self.assertEqual(attrs.value1, 1)
                    self.assertEqual(attrs.value2, 2)
                    self.assertEqual(attrs.ops, ['gt'])
                    self.assertEqual(attrs.message, 'it failed')

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
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeAssertions])
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions._override_name)
            for assertion in leaf.assertions.members:
                self.assertEqual(len(assertion), 1)
                checked.append(assertion._override_name)
                for attrs in assertion:
                    checked.append(attrs.key)
                    self.assertEqual(attrs.key, 'key1')
                    self.assertEqual(attrs.value1, 1)
                    self.assertEqual(attrs.value2, 2)
                    self.assertEqual(attrs.ops, ['gt'])
                    self.assertEqual(attrs.message, 'it failed')

        self.assertEqual(checked, ['assertions', 'assertion', 'key1'])

    def test_mapping_list_members_partial(self):
        """
        A list of lazily defined properties. One with only a subset of members
        defined.
        """

        _yaml = """
        assertions:
          - key: key1
            value1: 1
            ops: [gt]
            message: it failed
          - key: key2
            value1: 3
            value2: 4
            ops: [lt]
            message: it also failed
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeAssertions])
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions._override_name)
            for assertion in leaf.assertions.members:
                self.assertEqual(len(assertion), 2)
                checked.append(assertion._override_name)
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
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeAssertions])
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions._override_name)
            self.assertEqual(type(leaf.assertions), PTreeAssertions)
            self.assertEqual(len(leaf.assertions), 1)
            self.assertEqual(len(leaf.assertions.assertion), 2)
            self.assertEqual(type(leaf.assertions.assertion), PTreeAssertion)
            for assertion in leaf.assertions.assertion:
                self.assertEqual(len(assertion), 5)
                self.assertEqual(assertion._override_name, 'assertion')
                checked.append(assertion.key)
                if assertion.key == 'key1':
                    self.assertEqual(assertion.key, 'key1')
                    self.assertEqual(assertion.value1, 1)
                    self.assertEqual(assertion.value2, 2)
                    self.assertEqual(assertion.ops, ['gt'])
                    self.assertEqual(assertion.message, 'it failed')
                else:
                    self.assertEqual(assertion.key, 'key2')
                    self.assertEqual(assertion.value1, 3)
                    self.assertEqual(assertion.value2, 4)
                    self.assertEqual(assertion.ops, ['lt'])
                    self.assertEqual(assertion.message,
                                     'it also failed')

        self.assertEqual(checked, ['assertions', 'key1', 'key2'])

    def test_mapping_list_members_full_w_lopt(self):
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
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeAssertions])
        checked = []
        for leaf in root.leaf_sections:
            checked.append(leaf.assertions._override_name)
            for groups in leaf.assertions.members:
                self.assertEqual(len(groups), 1)
                checked.append(groups._override_name)
                self.assertEqual(groups._override_name, 'and')
                for assertion in groups.members:
                    self.assertEqual(len(assertion), 2)
                    checked.append(assertion._override_name)
                    for attrs in assertion:
                        checked.append(attrs.key)
                        if attrs.key == 'key1':
                            self.assertEqual(attrs.key, 'key1')
                            self.assertEqual(attrs.value1, 1)
                            self.assertEqual(attrs.value2, 2)
                            self.assertEqual(attrs.ops, ['gt'])
                            self.assertEqual(attrs.message, 'it failed')
                        else:
                            self.assertEqual(attrs.key, 'key2')
                            self.assertEqual(attrs.value1, 3)
                            self.assertEqual(attrs.value2, 4)
                            self.assertEqual(attrs.ops, ['lt'])
                            self.assertEqual(attrs.message,
                                             'it also failed')

        self.assertEqual(checked, ['assertions', 'and', 'assertion', 'key1',
                                   'key2'])

    def test_mapping_list_members_simple_w_lopt(self):
        """
        A list of properties grouped by a logical operator.
        """

        _yaml = """
        strgroups:
          and:
            - a
            - b
            - c
        """
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeStrGroups])
        vals = []
        ops_items = 0
        ops_members = 0
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.strgroups), PTreeStrGroups)
            for groups in leaf.strgroups:
                self.assertEqual(type(groups), MappedOverrideState)
                for member in groups:
                    self.assertEqual(type(member), PTreeStrGroupLogicalOpt)
                    self.assertEqual(len(member), 1)
                    for item in member:
                        ops_members += 1
                        self.assertEqual(type(item), MappedOverrideState)
                        self.assertEqual(len(item), 3)
                        for x in item:
                            ops_items += 1
                            self.assertEqual(type(x), PTreeOverrideRawType)
                            vals.append(str(x))

        self.assertEqual(ops_members, 1)
        self.assertEqual(ops_items, 3)
        self.assertEqual(vals, ['a', 'b', 'c'])

    def process_optgroup(self, assertiongroup, opname):
        """
        Process a PTreeAssertionsLogicalOpt mapping that can also have nested
        mappings.

        Returns a list of PTreeAssertionAttr values found.
        """
        vals = []
        self.assertEqual(type(assertiongroup), PTreeAssertionsLogicalOpt)
        for optgroup in assertiongroup:
            self.assertEqual(optgroup._override_name, opname)
            for member in optgroup:
                if member._override_name == 'assertion':
                    if opname == 'and':
                        # i.e. num of assertions n/i nested
                        self.assertEqual(len(member), 2)
                    else:
                        self.assertEqual(len(member), 1)

                    self.assertEqual(type(member), PTreeAssertion)
                    for assertion in member:
                        self.assertEqual(len(assertion), 1)
                        self.assertEqual(assertion._override_name, 'assertion')
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
        root = PTreeSection('mappingtest', yaml.safe_load(_yaml),
                            override_handlers=[PTreeAssertions])
        vals = []
        opnames_to_check = ['and', 'or']
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf), PTreeSection)
            self.assertEqual(type(leaf.assertions), PTreeAssertions)
            self.assertEqual(len(leaf.assertions), 1)
            for assertions in leaf.assertions:
                self.assertEqual(assertions._override_name, 'assertions')
                self.assertEqual(len(assertions), 2)
                for assertiongroup in assertions:
                    self.assertEqual(len(assertiongroup), 1)
                    vals += self.process_optgroup(assertiongroup,
                                                  opnames_to_check.pop(0))

        self.assertEqual(vals, [True, 'foo', False, False, True])
