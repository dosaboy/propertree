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

from unittest import mock

import yaml
from propertree.propertree2 import (
    PTreeOverrideBase,
    PTreeLogicalGrouping,
    PTreeMappedOverrideBase,
    PTreeSection,
    OverrideRegistry,
)

from . import utils


class PTreeInput(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['input']


class PTreeMessage(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['message', 'message-alt']

    def __str__(self):
        return self.content


class PTreeMeta(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['meta']


class PTreeSettings(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['settings']

    @property
    def a_property(self):
        return "i am a property"


class PTreeAction(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['action', 'altaction']


class PTreeLiterals(PTreeOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False

    @classmethod
    def _override_keys(cls):
        return ['literals']


class PTreeMappedGroup(PTreeMappedOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False
    override_members = [PTreeSettings, PTreeAction]

    @classmethod
    def _override_keys(cls):
        return ['group']

    @property
    def all(self):
        _all = {}
        if self.settings:
            _all['settings'] = self.settings.content

        if self.action:
            _all['action'] = self.action.content

        return _all


class PTreeLogicalGroupingWithStrRefs(PTreeLogicalGrouping):
    override_autoregister = False

    @property
    def result(self):
        items = []
        if isinstance(self.content, list):
            for item in self.content:
                if isinstance(item, str):
                    items.append(item)
        else:
            items.append(self.content)

        return items


class PTreeMappedRefs(PTreeMappedOverrideBase):  # noqa,pylint: disable=too-few-public-methods
    override_autoregister = False
    override_logical_grouping_type = PTreeLogicalGroupingWithStrRefs

    @classmethod
    def _override_keys(cls):
        return ['refs']


class TestPTree(utils.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.requirements = [PTreeLogicalGrouping, PTreeInput,
                             PTreeMessage, PTreeMeta, PTreeSettings,
                             PTreeAction, PTreeLiterals, PTreeMappedGroup,
                             PTreeMappedRefs]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_struct(self):
        with open('examples/checks.yaml', encoding='utf-8') as fd:
            root = PTreeSection('fruit tastiness', yaml.safe_load(fd.read()))
            for leaf in root.leaf_sections:
                if leaf.name == 'meta':
                    self.assertEqual(leaf.meta.category, 'tastiness')

                self.assertEqual(leaf.root.name, 'fruit tastiness')
                self.assertEqual(leaf.input.type, 'dict')
                if leaf.parent.name == 'apples':
                    if leaf.name == 'tasty':
                        self.assertEqual(str(leaf.message),
                                         'they make good cider.')
                        self.assertIsNone(leaf.message_alt, None)
                        self.assertEqual(leaf.input.value,
                                         {'color': 'red', 'crunchiness': 15})
                        self.assertEqual(leaf.settings.crunchiness,
                                         {'operator': 'ge', 'value': 10})
                        self.assertEqual(leaf.settings.color,
                                         {'operator': 'eq', 'value': 'red'})
                    else:
                        self.assertEqual(str(leaf.message),
                                         'default message')
                        self.assertIsNone(leaf.message_alt, None)
                        self.assertEqual(leaf.input.value,
                                         {'color': 'brown', 'crunchiness': 0})
                        self.assertEqual(leaf.settings.crunchiness,
                                         {'operator': 'le', 'value': 5})
                        self.assertEqual(leaf.settings.color,
                                         {'operator': 'eq', 'value': 'brown'})
                else:
                    self.assertEqual(leaf.parent.name, 'oranges')
                    self.assertEqual(str(leaf.message),
                                     'they make good juice.')
                    self.assertEqual(str(leaf.message_alt),
                                     'and good marmalade.')
                    self.assertEqual(leaf.input.value,
                                     {'acidity': 2, 'color': 'orange'})
                    self.assertEqual(leaf.settings.acidity,
                                     {'operator': 'lt', 'value': 5})
                    self.assertEqual(leaf.settings.color,
                                     {'operator': 'eq', 'value': 'red'})

    def test_empty_struct(self):
        root = PTreeSection('root', content={})
        for leaf in root.leaf_sections:
            self.assertEqual(leaf.input.type, 'dict')

    def test_struct_w_mapping(self):
        with open('examples/checks2.yaml', encoding='utf-8') as fd:
            root = PTreeSection('atest', yaml.safe_load(fd.read()))
            for leaf in root.leaf_sections:
                self.assertTrue(leaf.name in ['item1', 'item2', 'item3',
                                              'item4', 'item5'])
                if leaf.name == 'item1':
                    self.assertEqual(type(leaf.group), PTreeMappedGroup)
                    self.assertEqual(len(leaf.group), 1)
                    self.assertEqual(leaf.group.settings.plum, 'pie')
                    self.assertEqual(leaf.group.action.eat, 'now')
                    self.assertEqual(leaf.group.all,
                                     {'settings': {'plum': 'pie'},
                                      'action': {'eat': 'now'}})
                elif leaf.name == 'item2':
                    self.assertEqual(leaf.group.settings.apple, 'tart')
                    self.assertEqual(leaf.group.action.eat, 'later')
                    self.assertEqual(leaf.group.all,
                                     {'settings': {'apple': 'tart'},
                                      'action': {'eat': 'later'}})
                elif leaf.name == 'item3':
                    self.assertEqual(str(leaf.message), 'message not mapped')
                    self.assertEqual(leaf.group.settings.ice, 'cream')
                    self.assertEqual(leaf.group.action, None)
                    self.assertEqual(leaf.group.all,
                                     {'settings': {'ice': 'cream'}})
                elif leaf.name == 'item4':
                    self.assertEqual(leaf.group.settings.treacle, 'tart')
                    self.assertEqual(leaf.group.action.want, 'more')
                    self.assertEqual(leaf.group.all,
                                     {'settings': {'treacle': 'tart'},
                                      'action': {'want': 'more'}})
                elif leaf.name == 'item5':
                    self.assertEqual(len(leaf.group), 3)
                    checked = 0
                    for i, _group in enumerate(leaf.group):
                        if i == 0:
                            checked += 1
                            self.assertEqual(_group.settings.strawberry,
                                             'jam')
                            self.assertEqual(_group.action.lots, 'please')
                        elif i == 1:
                            checked += 1
                            self.assertEqual(_group.settings.cherry, 'jam')
                            self.assertEqual(_group.action.lots, 'more')
                        elif i == 2:
                            checked += 1
                            self.assertEqual(_group.settings.cherry, 'jam')
                            self.assertEqual(_group.action.lots, 'more')
                            self.assertEqual(_group.altaction.still, 'more')

                    self.assertEqual(checked, 3)

    def test_struct_w_metagroup_list(self):
        _yaml = """
        item1:
          group:
            - settings:
                result: true
            - settings:
                result: false
        """
        root = PTreeSection('mgtest', yaml.safe_load(_yaml))
        for leaf in root.leaf_sections:
            self.assertEqual(len(leaf.group), 1)
            self.assertEqual(len(leaf.group.settings), 2)
            results = [s.result for s in leaf.group.settings]

        self.assertEqual(results, [True, False])

    def test_struct_w_metagroup_w_logical_opt(self):
        _yaml = """
        item1:
          group:
            and:
              - settings:
                  result: true
              - settings:
                  result: false
        """
        root = PTreeSection('mgtest', yaml.safe_load(_yaml))
        results = []
        for leaf in root.leaf_sections:
            self.assertEqual(len(leaf.group), 1)
            for prop in leaf.group.members:
                for item in prop:
                    results.append(item.result)

        self.assertEqual(results, [False])

    def test_struct_w_metagroup_w_multiple_logical_opts(self):
        _yaml = """
        item1:
          group:
            or:
              - settings:
                  result: true
              - settings:
                  result: false
            and:
              settings:
                result: false
        """
        root = PTreeSection('mgtest', yaml.safe_load(_yaml))
        results = []
        for leaf in root.leaf_sections:
            self.assertEqual(len(leaf.group), 1)
            for prop in leaf.group.members:
                for item in prop:
                    results.append(item.result)

        self.assertEqual(results, [False, True])

    def test_struct_w_metagroup_w_mixed_list(self):
        _yaml = """
        item1:
          group:
            - or:
                settings:
                  result: true
            - settings:
                result: false
        """
        root = PTreeSection('mgtest', yaml.safe_load(_yaml))
        results = []
        for leaf in root.leaf_sections:
            self.assertEqual(len(leaf.group), 1)
            for group in leaf.group:
                for prop in group.members:
                    for item in prop:
                        results.append(item.result)

        self.assertEqual(sorted(results), sorted([True, False]))

    def test_struct_w_metagroup_w_mixed_list_w_str_overrides(self):
        _yaml = """
        item1:
          refs:
            - or: ref1
              and: [ref2, ref3]
        """
        root = PTreeSection('mgtest', yaml.safe_load(_yaml))
        results = []
        for leaf in root.leaf_sections:
            self.assertEqual(leaf.name, 'item1')
            for member in leaf.refs.members:
                for item in member:
                    self.assertTrue(item.override_name in ['and', 'or',
                                                           'ref4'])
                    if item.override_name == 'or':
                        results.extend(item.result)
                    elif item.override_name == 'and':
                        results.extend(item.result)

        self.assertEqual(sorted(results),
                         sorted(['ref1', 'ref2', 'ref3']))

    @mock.patch.object(PTreeSection, 'post_hook')
    @mock.patch.object(PTreeSection, 'pre_hook')
    def test_hooks_called(self, mock_pre_hook, mock_post_hook):
        _yaml = """
        myroot:
          leaf1:
            settings:
              brake: off
          leaf2:
            settings:
              clutch: on
        """
        PTreeSection('hooktest', yaml.safe_load(_yaml),
                     run_hooks=False)
        self.assertFalse(mock_pre_hook.called)
        self.assertFalse(mock_post_hook.called)

        PTreeSection('hooktest', yaml.safe_load(_yaml),
                     run_hooks=True)
        self.assertTrue(mock_pre_hook.called)
        self.assertTrue(mock_post_hook.called)

    def test_resolve_paths(self):
        _yaml = """
        myroot:
          sub1:
            sub2:
              leaf1:
                settings:
                  brake: off
                action: go
              leaf2:
                settings:
                  clutch: on
          sub3:
            leaf3:
              settings:
                clutch: on
        """
        root = PTreeSection('resolvtest', yaml.safe_load(_yaml))
        resolved = []
        for leaf in root.leaf_sections:
            resolved.append(leaf.resolve_path)
            resolved.append(leaf.group.override_path)
            for setting in leaf.group.members:
                resolved.append(setting.override_path)

        expected = ['resolvtest.myroot.sub1.sub2.leaf1',
                    'resolvtest.myroot.sub1.sub2.leaf1.group',
                    'resolvtest.myroot.sub1.sub2.leaf1.group.settings',
                    'resolvtest.myroot.sub1.sub2.leaf1.group.action',
                    'resolvtest.myroot.sub1.sub2.leaf2',
                    'resolvtest.myroot.sub1.sub2.leaf2.group',
                    'resolvtest.myroot.sub1.sub2.leaf2.group.settings',
                    'resolvtest.myroot.sub3.leaf3',
                    'resolvtest.myroot.sub3.leaf3.group',
                    'resolvtest.myroot.sub3.leaf3.group.settings']

        self.assertEqual(resolved, expected)

    def test_context(self):
        _yaml = """
        myroot:
          leaf1:
            settings:
              brake: off
        """

        class ContextHandler():
            def __init__(self):
                self.context = {}

            def set(self, key, value):
                self.context[key] = value

            def get(self, key):
                return self.context.get(key)

        root = PTreeSection('contexttest', yaml.safe_load(_yaml),
                            context=ContextHandler())
        for leaf in root.leaf_sections:
            for setting in leaf.group.members:
                self.assertIsNone(setting.context.get('k1'))
                setting.context.set('k1', 'notk2')
                self.assertEqual(setting.context.get('k1'), 'notk2')

    def test_literal_types(self):
        _yaml = """
        literals:
          red: meat
          bits: 8
          bytes: 1
          stringbits: '8'
        """
        root = PTreeSection('literaltest', yaml.safe_load(_yaml))
        for leaf in root.leaf_sections:
            self.assertEqual(leaf.literals.red, 'meat')
            self.assertEqual(leaf.literals.bytes, 1)
            self.assertEqual(leaf.literals.bits, 8)
            self.assertEqual(leaf.literals.stringbits, '8')
