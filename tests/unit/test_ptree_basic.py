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
    PTreeOverrideBase,
    PTreeMappedOverrideBase,
    PTreeSection,
    OverrideRegistry,
)

from . import utils


class PTreeStrProp(PTreeOverrideBase):
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['strprop']

    def __str__(self):
        return self.data

    def __eq__(self, string):
        return self.data == string

    @property
    def data(self):
        return self.content


class PTreeDictProp(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['dictprop']


class PTreePropGroup(PTreeMappedOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False
    override_members = [PTreeStrProp, PTreeDictProp]

    @classmethod
    def _override_keys(cls):
        return ['pgroup']


class TestPTreeSimpleProps(utils.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.requirements = [PTreeStrProp]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_struct_simple_prop_single(self):
        _yaml = """
        strprop: myval
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.strprop), PTreeStrProp)
            self.assertEqual(leaf.strprop, "myval")

    def test_struct_simple_prop_multi(self):
        _yaml = """
        s1:
          strprop: myval1
        s2:
          strprop: myval2
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.strprop), PTreeStrProp)
            if leaf.name == 's1':
                self.assertEqual(leaf.strprop, "myval1")
            else:
                self.assertEqual(leaf.strprop, "myval2")

    def test_struct_simple_prop_single_list(self):
        _yaml = """
        - strprop: myval1
        - strprop: myval2
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        vals = []
        for leaf in root.leaf_sections:
            for prop in leaf.strprop:
                self.assertEqual(type(prop), PTreeStrProp)
                vals.append(prop)

            self.assertEqual(vals, ["myval1", "myval2"])


class TestPTreeMappedProps(utils.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.requirements = [PTreeStrProp, PTreeDictProp, PTreePropGroup]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_struct_mapped_prop_single(self):
        _yaml = """
        pgroup:
          strprop: myval
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.pgroup), PTreePropGroup)
            self.assertEqual(len(leaf.pgroup), 1)
            for pgroup in leaf.pgroup:
                self.assertEqual(len(pgroup), 1)
                self.assertEqual(type(pgroup.strprop), PTreeStrProp)
                self.assertEqual(pgroup.strprop, "myval")

    def test_struct_mapped_prop_single_list(self):
        _yaml = """
        pgroup:
          - strprop: '1'
          - strprop: '2'
          - strprop: '3'
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        vals = []
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.pgroup), PTreePropGroup)
            self.assertEqual(len(leaf.pgroup), 1)
            for pgroup in leaf.pgroup:
                members = 0
                for member in pgroup.members:
                    for item in member:
                        members += 1
                        vals.append(str(item))

        self.assertEqual(members, 3)
        self.assertEqual(vals, ['1', '2', '3'])

    def test_struct_mapped_prop_multi_list(self):
        _yaml = """
        - pgroup:
            - strprop: myval1.1
            - strprop: myval1.2
        - pgroup:
            strprop: myval2
        - pgroup:
            dictprop:
              p1: myval3
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        vals = []
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.pgroup), PTreePropGroup)
            self.assertEqual(len(leaf.pgroup), 3)
            for pgroup in leaf.pgroup:
                # Each item still reflects the size of the whole stack
                self.assertEqual(len(pgroup), 3)
                for member in pgroup.members:
                    self.assertTrue(type(member) in [PTreeStrProp,
                                                     PTreeDictProp])
                    for item in member:
                        if item.override_name == 'strprop':
                            self.assertEqual(type(item), PTreeStrProp)
                            vals.append(str(item))
                        else:
                            self.assertEqual(type(item), PTreeDictProp)
                            vals.append(item.p1)

        self.assertEqual(vals, ["myval1.1", "myval1.2", "myval2", "myval3"])

        # The following demonstrates using a shortcut that always returns the
        # first item added to the stack for any member. So basically is only
        # useful if there is only one item in any given member.
        vals = []
        for leaf in root.leaf_sections:
            for pgroup in leaf.pgroup:
                if pgroup.strprop:
                    self.assertEqual(type(pgroup.strprop), PTreeStrProp)
                    vals.append(str(pgroup.strprop))
                else:
                    self.assertEqual(type(pgroup.dictprop), PTreeDictProp)
                    vals.append(pgroup.dictprop.p1)

        self.assertEqual(vals, ["myval1.1", "myval2", "myval3"])

    def test_struct_mapped_prop_single_member_list(self):
        _yaml = """
        pgroup:
          - strprop: myval1
          - strprop: myval2
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        vals = []
        for leaf in root.leaf_sections:
            self.assertEqual(type(leaf.pgroup), PTreePropGroup)
            # one because it is stacked
            self.assertEqual(len(leaf.pgroup), 1)
            for pgroup in leaf:
                self.assertEqual(type(pgroup), PTreePropGroup)
                for member in pgroup.members:
                    self.assertEqual(type(member), PTreeStrProp)
                    for item in member:
                        vals.append(item)

        self.assertEqual(vals, ["myval1", "myval2"])

    def test_struct_mapped_prop_single_member_list_nested(self):
        self.skipTest("this test does not represent a valid use case")
        _yaml = """
        pgroup:
          - strprop: myval1
          - pgroup:
              strprop: myval2
        """
        root = PTreeSection('simpletest', yaml.safe_load(_yaml))
        vals = []
        for leaf in root.leaf_sections:   # noqa,pylint: disable=too-many-nested-blocks
            self.assertEqual(type(leaf.pgroup), PTreePropGroup)
            self.assertEqual(len(leaf.pgroup), 1)
            for pgroup in leaf.pgroup:
                for member in pgroup:
                    if member.override_name == 'pgroup':
                        # nested pgroup
                        self.assertEqual(type(member), PTreePropGroup)
                        self.assertEqual(len(member), 1)
                        for _pgroup in member:
                            for _member in _pgroup:
                                for _item in _member:
                                    vals.append(_item)
                    else:
                        self.assertEqual(type(member), PTreeStrProp)
                        for item in member:
                            vals.append(item)

        self.assertEqual(vals, ["myval1", "myval2"])
