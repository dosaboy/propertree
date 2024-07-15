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
# pylint: disable=missing-class-docstring,pointless-statement


import yaml
from propertree.propertree2 import (
    PTreeOverrideManager,
    PTreeLogicalGrouping,
    PTreeOverrideLiteralType,
    PTreeSection,
    OverrideRegistry,
    REGISTERED_OVERRIDES,
)
from . import properties, utils  # noqa, pylint: disable=W0611


class TestPTree2Base(utils.BaseTestCase):

    def check_len_and_type(self, prop, prop_len, prop_type):
        self.assertEqual(type(prop), prop_type)
        self.assertEqual(len(prop), prop_len)

    def assert_leaves(self, root, names):
        self.assertEqual(sorted([e.name for e in root.leaf_sections]),
                         sorted(names))


class TestPTreeOverrideRegistry(TestPTree2Base):

    def setUp(self):
        super().setUp()
        OverrideRegistry.register([properties.Input, properties.MapPrimary,
                                   properties.MapMember1])

    def tearDown(self):
        super().tearDown()
        OverrideRegistry.unregister([properties.Input, properties.MapPrimary,
                                     properties.MapMember1])

    def test_post_registration_tasks(self):
        OverrideRegistry.register([properties.Input, properties.MapMember1])
        self.assertEqual(REGISTERED_OVERRIDES,
                         {'__override_literal_type__': [
                              PTreeOverrideLiteralType],
                          'and': [PTreeLogicalGrouping],
                          # Additional non-member override here
                          'input': [properties.Input, properties.Input],
                          'mapprimary': [properties.MapPrimary],
                          # Additional member override here
                          'mapmember1': [properties.MapMember1,
                                         properties.MapMember1],
                          'nand': [PTreeLogicalGrouping],
                          'nor': [PTreeLogicalGrouping],
                          'not': [PTreeLogicalGrouping],
                          'xor': [PTreeLogicalGrouping],
                          'or': [PTreeLogicalGrouping]})
        OverrideRegistry.post_registration_tasks(REGISTERED_OVERRIDES)
        self.assertEqual(REGISTERED_OVERRIDES,
                         {'__override_literal_type__': [
                              PTreeOverrideLiteralType],
                          'and': [PTreeLogicalGrouping],
                          # And now it is gone
                          'input': [properties.Input],
                          'mapprimary': [properties.MapPrimary],
                          # This one remains
                          'mapmember1': [properties.MapMember1],
                          'nand': [PTreeLogicalGrouping],
                          'nor': [PTreeLogicalGrouping],
                          'not': [PTreeLogicalGrouping],
                          'xor': [PTreeLogicalGrouping],
                          'or': [PTreeLogicalGrouping]})
        OverrideRegistry.unregister([properties.MapMember1])
        self.assertEqual(REGISTERED_OVERRIDES,
                         {'__override_literal_type__': [
                              PTreeOverrideLiteralType],
                          'and': [PTreeLogicalGrouping],
                          'input': [properties.Input],
                          'mapprimary': [properties.MapPrimary],
                          'nand': [PTreeLogicalGrouping],
                          'nor': [PTreeLogicalGrouping],
                          'not': [PTreeLogicalGrouping],
                          'xor': [PTreeLogicalGrouping],
                          'or': [PTreeLogicalGrouping]})


class TestPTreeOverrideManager(TestPTree2Base):

    def setUp(self):
        super().setUp()
        OverrideRegistry.register([properties.Requires, properties.MapPrimary])

    def tearDown(self):
        super().tearDown()
        OverrideRegistry.unregister([properties.Requires,
                                     properties.MapPrimary])

    def test_flatten_path(self):
        for (p_in, p_out) in [
                ('root.and', 'root.and'),
                ('root.and.or', 'root.or'),
                ('root.and.or.not.nand', 'root.nand'),
                ('root.and.or.not.bar.nand', 'root.bar.nand'),
                ('root.and.or.not.requires', 'root.requires'),
                ('root.mapprimary.requires.or', 'root.or'),
                ('root.mapprimary.and', 'root.and'),
                ('root.mapprimary.and.requires.or.not', 'root.not'),
                ('root.mapprimary.and.requires.or', 'root.or'),
                ('root.mapprimary.and.requires', 'root.requires'),
                ('root.and.or.not.requires.nand', 'root.nand'),
                ('root.mapprimary.mapmember1', 'root.mapmember1'),
                ('root.foo.mapprimary.mapmember1', 'root.foo.mapmember1'),
                ('root.mapprimary.or.mapmember1', 'root.mapmember1'),
                ('root.mapprimary.and.requires.typecheck',
                 'root.typecheck'),
                ('root.mapprimary.and.requires.or.not.and.typecheck',
                 'root.typecheck'),
                ('root.mapprimary.and.requires.or.typecheck',
                 'root.typecheck')]:
            path = PTreeOverrideManager.flatten_path(p_in)
            self.assertEqual(path, p_out)


class TestSection(TestPTree2Base):

    def setUp(self):
        super().setUp()
        self.requirements = [properties.ValueCheck]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_section(self):
        prop_basic_flat = """
        S1:
          valuecheck:
            key: cheese
            value: cheese
        """
        root = PTreeSection('script', yaml.safe_load(prop_basic_flat))
        self.assertEqual(len(root), 1)

    def test_layered_section(self):
        prop_basic_flat = """
        S1:
          valuecheck:
            key: cheese
            value: cheese
        """
        root = PTreeSection('script', yaml.safe_load(prop_basic_flat))
        self.assertEqual(len(root), 1)


class TestBasicOverrides(TestPTree2Base):

    def setUp(self):
        super().setUp()
        self.requirements = [properties.ValueCheck]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_basic_property(self):
        prop_basic_flat = """
        S1:
          valuecheck:
            key: cheese
            value: cheese
        """
        root = PTreeSection('script', yaml.safe_load(prop_basic_flat))
        self.assert_leaves(root, ['S1'])
        self.check_len_and_type(root.S1.valuecheck, 1, properties.ValueCheck)
        self.assertEqual(root.S1.valuecheck.override_parent, None)
        self.assertEqual(root.S1.valuecheck.result, True)

    def test_basic_property_attr_not_found(self):

        class ValueCheckX(properties.ValueCheck):
            override_keys = ['valuecheckx']

            @property
            def testattr1(self):
                return self.testattr2

            @property
            def testattr2(self):
                return bool(self.nonexistantattr)

            @property
            def testattr3(self):
                return {}.nonexistantattr  # pylint: disable=E1101

            @property
            def testattr4(self):
                return self.testattr3

        prop_basic_flat = """
        S1:
          valuecheckx:
            key: cheese
            value: cheese
        """
        OverrideRegistry.register([ValueCheckX])
        try:
            root = PTreeSection('script', yaml.safe_load(prop_basic_flat))
            with self.assertRaises(AttributeError) as exc:
                root.S1.valuecheckx.notfound

            self.assertEqual(str(exc.exception),
                             "'ValueCheckX' object has no attribute "
                             "'notfound'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.valuecheckx.testattr1

            self.assertEqual(str(exc.exception),
                             "'ValueCheckX' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.valuecheckx.testattr3

            self.assertEqual(str(exc.exception),
                             "'dict' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.valuecheckx.testattr1

            self.assertEqual(str(exc.exception),
                             "'ValueCheckX' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.valuecheckx.testattr4

            self.assertEqual(str(exc.exception),
                             "'dict' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.valuecheckx.testattr1

            self.assertEqual(str(exc.exception),
                             "'ValueCheckX' object has no attribute "
                             "'nonexistantattr'")
        finally:
            OverrideRegistry.unregister([ValueCheckX])

    def test_basic_property_list(self):
        prop_basic_flat_list = """
        S1:
          - valuecheck:
              key: cheese
              value: cheese
          - valuecheck:
              key: cheese2
              value: cheese2
        """
        root = PTreeSection('script', yaml.safe_load(prop_basic_flat_list))
        self.assert_leaves(root, ['S1'])
        self.check_len_and_type(root.S1.valuecheck, 2, properties.ValueCheck)
        for item in root.S1.valuecheck:
            self.assertEqual(item.result, True)

    def test_basic_property_layered_section(self):
        prop_basic_layered = """
        S1:
          S2:
            valuecheck:
              key: cheese
              value: stinky
          S3:
            valuecheck:
              key: cheese
              value: runny
        """
        root = PTreeSection('script', yaml.safe_load(prop_basic_layered))
        self.assert_leaves(root, ['S2', 'S3'])
        self.assertEqual(len(root.S1.S2.valuecheck), 1)
        self.assertEqual(len(root.S1.S3.valuecheck), 1)
        self.assertEqual(len(root.S1.S2), 1)
        for item in root.S1.S2:
            self.assertEqual(item.value, 'stinky')

        self.assertEqual(len(root.S1.S3), 1)
        for item in root.S1.S3:
            self.assertEqual(item.value, 'runny')


class TestOverridesScope(TestPTree2Base):

    def setUp(self):
        super().setUp()
        self.requirements = [properties.Vars, properties.ValueCheck,
                             properties.Checks, properties.VarOps,
                             properties.Input, properties.Check]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_property_reference_global(self):
        prop_ref_global = """
        vars:
          cheese: smelly
        S1:
          valuecheck:
            key: cheese
            value: smelly
        """
        root = PTreeSection('script', yaml.safe_load(prop_ref_global))
        self.assert_leaves(root, ['S1'])
        self.assertEqual(root.vars.cheese, 'smelly')
        self.assertEqual(root.S1.vars.cheese, 'smelly')
        self.assertEqual(root.S1.valuecheck.result, True)

    def test_property_reference_global_not_found(self):
        prop_ref_global = """
        S1:
          valuecheck:
            key: cheese
            value: smelly
        """
        root = PTreeSection('script', yaml.safe_load(prop_ref_global))
        self.assert_leaves(root, ['S1'])
        self.assertEqual(root.vars, None)
        self.assertEqual(root.S1.valuecheck.result, False)

    def test_property_reference_context(self):
        prop_ref_context = """
        vars:
          1k: 1000
        S1:
          checks:
            check1:
              varops: [[$1k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(prop_ref_context))
        self.assert_leaves(root, ['S1'])
        for check in root.S1.checks:
            self.assertEqual(check.result, True)

    def test_inheritance(self):
        inheritance = """
        S1:
          input:
            path: moo
          S2:
            input:
              path: baa
          S3:
            input:
              path: lalala
            S4:
              input:
                path: lalalala
            S5:
              check:
                value: foo
        """
        root = PTreeSection('script', yaml.safe_load(inheritance))
        self.assert_leaves(root, ['S2', 'S4', 'S5'])
        self.assertEqual(root.S1.input.path, 'moo')
        self.assertEqual(root.S1.S2.input.path, 'baa')
        self.assertEqual(root.S1.S3.input.path, 'lalala')
        self.assertEqual(root.S1.S3.S4.input.path, 'lalalala')
        self.assertEqual(root.S1.S3.S5.input.path, 'lalala')
        checked = 0
        for item in root.leaf_sections:
            if item.name == 'S2':
                self.assertEqual(item.input.path, 'baa')
                checked += 1
            elif item.name == 'S4':
                self.assertEqual(item.input.path, 'lalalala')
                checked += 1
                types = set()
                for prop in item:
                    types.add(type(prop))

                self.assertEqual(types, set([properties.Input]))
            elif item.name == 'S5':
                self.assertEqual(item.input.path, 'lalala')
                checked += 1
                types = set()
                for prop in item:
                    types.add(type(prop))

                # Input property should not be returned when iterating over
                # the section since it is not explicitly defined within that
                # section. It is however accessible from the section via
                # inheritance
                self.assertEqual(types, set([properties.Check]))
            else:
                raise Exception(f"unexpected item name={item.name}")  # noqa,pylint: disable=broad-exception-raised

        self.assertEqual(checked, 3)


class TestOverrideLogicalGrouping(TestPTree2Base):

    def setUp(self):
        super().setUp()
        self.requirements = [properties.Vars, properties.ValueCheck,
                             properties.Checks, properties.VarOps,
                             properties.Input]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_simple_property_grouping(self):
        simple_property_grouping = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          - or:
            - varops: [[$2k], [lt, 1000]]
            - varops: [[$1k], [gt, 1000]]
          - or:
            - varops: [[$2k], [lt, 1000]]
            - varops: [[$1k], [eq, 1000]]
          -
            varops: [[$1k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(simple_property_grouping))
        self.assert_leaves(root, ['S1'])
        checked = []
        for item in root.S1:
            checked.append(item.result)
            if isinstance(item, PTreeLogicalGrouping):
                self.assertEqual(item.override_group_stats['items_executed'],
                                 2)

        self.assertEqual(sorted(checked), [False, True, True])

    def test_simple_mapping_grouping(self):
        simple_mapping_grouping = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          - and:
              varops: [[$2k], [lt, 1000]]
          - or:
              varops: [[$2k], [lt, 1000]]
        """
        OverrideRegistry.register([properties.Requires])
        try:
            root = PTreeSection('script',
                                yaml.safe_load(simple_mapping_grouping))
            self.assert_leaves(root, ['S1'])
            checked = []
            for item in root.S1:
                checked.append(item.result)
                if isinstance(item, PTreeLogicalGrouping):
                    num_items = item.override_group_stats['items_executed']
                    self.assertEqual(num_items, 1)

            self.assertEqual(sorted(checked), [False, False])
        finally:
            OverrideRegistry.unregister([properties.Requires])

    def test_nested_property_grouping1(self):
        nested_property_grouping1 = """
        vars:
          1k: 1000
          2k: 2000
        S1_True:
          and:
            not:
              or:
                not:
                  not:
                    varops: [[$2k], [lt, 1000]]
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_property_grouping1))
        self.assert_leaves(root, ['S1_True'])
        checked = []
        for item in root.S1_True:
            checked.append(item.result)

        self.assertEqual(checked, [True])

    def test_nested_property_grouping2(self):
        nested_property_grouping2 = """
        vars:
          1k: 1000
          2k: 2000
        S1_True:
          and:
            - not:
                varops: [[$2k], [lt, 1000]]
            - not:
                varops: [[$1k], [ne, 1000]]
        S1_False:
          and:
            - not:
                varops: [[$2k], [lt, 1000]]
            - not:
                varops: [[$1k], [eq, 1000]]
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_property_grouping2))
        self.assert_leaves(root, ['S1_True', 'S1_False'])
        checked = []
        for item in root.S1_True:
            checked.append(item.result)

        for item in root.S1_False:
            checked.append(item.result)

        self.assertEqual(checked, [True, False])

    def test_check_group_default(self):
        check_group_default = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          checks:
            check_true:
              - varops: [[$1k], [eq, 1000]]
              - varops: [[$2k], [gt, 1000]]
            check_false:
              - varops: [[$1k], [eq, 1000]]
              - varops: [[$2k], [lt, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(check_group_default))
        self.assert_leaves(root, ['S1'])
        checked = []
        for check in root.S1.checks:
            checked.append(check.name)
            if check.name == 'check_true':
                self.assertEqual(check.result, True)
            elif check.name == 'check_false':
                self.assertEqual(check.result, False)
            else:
                break

        self.assertEqual(sorted(checked), ['check_false', 'check_true'])

    def test_check_group_and(self):
        check_group_and = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          checks:
            check_true:
              and:
                - varops: [[$1k], [eq, 1000]]
                - varops: [[$2k], [gt, 1000]]
            check_false:
              and:
                - varops: [[$1k], [eq, 1000]]
                - varops: [[$2k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(check_group_and))
        self.assert_leaves(root, ['S1'])
        checked = []
        for check in root.S1.checks:
            checked.append(check.name)
            if check.name == 'check_true':
                self.assertEqual(check.result, True)
            elif check.name == 'check_false':
                self.assertEqual(check.result, False)
            else:
                break

        self.assertEqual(sorted(checked), ['check_false', 'check_true'])

    def test_check_group_or(self):
        check_group_or = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          checks:
            check_true:
              - or:
                - varops: [[$1k], [eq, 1000]]
                - varops: [[$2k], [eq, 1000]]
              - or:
                - varops: [[$1k], [eq, 1000]]
                - varops: [[$2k], [ne, 1000]]
            check_false:
              - or:
                - varops: [[$1k], [gt, 1000]]
                - varops: [[$2k], [eq, 1000]]
              - or:
                - varops: [[$1k], [gt, 1000]]
                - varops: [[$2k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(check_group_or))
        self.assert_leaves(root, ['S1'])
        checked = []
        for check in root.S1.checks:
            checked.append(check.name)
            if check.name == 'check_true':
                self.assertEqual(check.result, True)
            elif check.name == 'check_false':
                self.assertEqual(check.result, False)
            else:
                break

        self.assertEqual(sorted(checked), ['check_false', 'check_true'])

    def test_check_group_and_exit_early(self):
        check_group_or = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          and:
            - varops: [[$1k], [eq, 1000]]
            - varops: [[$2k], [eq, 1000]]
            - varops: [[$1k], [eq, 1000]]
            - varops: [[$1k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(check_group_or))
        result = None
        for op in root.S1:
            result = op.result
            self.assertEqual(op.override_group_stats['items_executed'], 2)

        self.assertEqual(result, False)

    def test_check_group_nand_exit_early(self):
        check_group_or = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          nand:
            - varops: [[$1k], [eq, 1000]]
            - varops: [[$2k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(check_group_or))
        result = None
        for op in root.S1:
            result = op.result
            self.assertEqual(op.override_group_stats['items_executed'], 2)

        self.assertEqual(result, True)

    def test_check_group_not_exit_early(self):
        check_group_or = """
        vars:
          1k: 1000
          2k: 2000
        S1:
          not:
            - varops: [[$1k], [eq, 1000]]
            - varops: [[$2k], [eq, 1000]]
        """
        root = PTreeSection('script', yaml.safe_load(check_group_or))
        result = None
        for op in root.S1:
            result = op.result
            self.assertEqual(op.override_group_stats['items_executed'], 2)

        self.assertEqual(result, True)


class TestMappedOverrides(TestPTree2Base):

    def setUp(self):
        super().setUp()
        self.requirements = [properties.Requires, properties.MapPrimary,
                             properties.MapMember1, properties.MapMember2,
                             properties.VarOps, properties.Checks,
                             properties.Vars, properties.Input,
                             properties.TypeCheck, properties.Decision]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        super().tearDown()

    def test_mapped_property_attr_access(self):
        mapped_property_basic_members = """
        S1:
          deepmap:
            deepmember1:
              deepmember2:
                key: cheese
                value: smelly
        """
        OverrideRegistry.register([properties.DeepMap, properties.DeepMember1,
                                   properties.DeepMember2])
        OverrideRegistry.unregister([properties.MapPrimary])
        try:
            root = PTreeSection('script',
                                yaml.safe_load(mapped_property_basic_members))
            for primary in root.S1:
                self.assertEqual(primary.deepmember1.override_name,
                                 'deepmember1')
                with self.assertRaises(AttributeError):
                    primary.deepmember2

                with self.assertRaises(AttributeError):
                    primary.value

                with self.assertRaises(AttributeError):
                    primary.deepattr

                with self.assertRaises(AttributeError):
                    primary.deepmember1.deepattr

                self.assertEqual(primary.deepmember1.deepmember2.deepattr,
                                 'deepvalue')
        finally:
            OverrideRegistry.unregister([properties.DeepMap,
                                         properties.DeepMember1,
                                         properties.DeepMember2])

    def test_mapped_property_basic(self):
        mapped_property_basic_members = """
        S1:
          mapprimary:
            mapmember1:
              key: cheese
              value: smelly
            mapmember2:
              key: cheese
              value: ripe
        S2:
          input:
            path: foo
          mapmember1:
            key: cheese
            value: cheddar
          mapmember2:
            key: cheese
            value: wensleydale
        """
        root = PTreeSection('script',
                            yaml.safe_load(mapped_property_basic_members))
        self.assert_leaves(root, ['S1', 'S2'])

        self.assertEqual(len(root.S1), 1)
        self.assertEqual(len(list(root.S1)), 1)
        self.assertEqual(len(root.S2), 2)
        self.assertEqual(len(list(root.S2)), 2)

        for primary in root.S1:
            self.check_len_and_type(primary, 1, properties.MapPrimary)
            for member in primary.members:
                if member.override_name == 'mapmember1':
                    self.assertEqual(type(member), properties.MapMember1)
                else:
                    self.assertEqual(type(member), properties.MapMember2)

        mp = root.S1.mapprimary
        self.assertEqual(mp.override_parent, None)
        self.assertEqual(type(mp), properties.MapPrimary)
        self.assertEqual(mp.mapmember1.override_parent.override_path,
                         'script.S1.mapprimary')
        self.assertEqual(type(mp.mapmember1), properties.MapMember1)
        self.assertEqual(mp.mapmember1.override_name, 'mapmember1')
        self.assertEqual(mp.mapmember1.key, 'cheese')
        self.assertEqual(mp.mapmember1.value, 'smelly')
        self.assertEqual(type(mp.mapmember2), properties.MapMember2)
        self.assertEqual(mp.mapmember2.override_name, 'mapmember2')
        self.assertEqual(mp.mapmember2.override_parent.override_path,
                         'script.S1.mapprimary')
        self.assertEqual(mp.mapmember2.key, 'cheese')
        self.assertEqual(mp.mapmember2.value, 'ripe')

        members = []
        mp = root.S2.mapprimary
        self.assertEqual(len(mp), 1)
        for mpitem in mp:
            self.assertEqual(type(mpitem), properties.MapPrimary)
            member = mpitem.mapmember1
            members.append(member.override_name)
            self.assertEqual(type(member), properties.MapMember1)
            self.assertEqual(member.override_name, 'mapmember1')
            self.assertEqual(member.override_parent.override_path,
                             'script.S2.mapprimary')
            self.assertEqual(member.key, 'cheese')
            self.assertEqual(member.value, 'cheddar')

            member = mpitem.mapmember2
            members.append(member.override_name)
            self.assertEqual(member.override_name, 'mapmember2')
            self.assertEqual(member.override_parent.override_path,
                             'script.S2.mapprimary')
            self.assertEqual(member.key, 'cheese')
            self.assertEqual(member.value, 'wensleydale')

        self.assertEqual(members, ['mapmember1', 'mapmember2'])

    def test_mapped_property_attr_not_found(self):

        class MapPrimaryX(properties.MapPrimary):
            override_keys = ['mapprimaryx']

            @property
            def testattr1(self):
                return self.testattr2

            @property
            def testattr2(self):
                return bool(self.nonexistantattr)

            @property
            def testattr3(self):
                return {}.nonexistantattr  # pylint: disable=E1101

            @property
            def testattr4(self):
                return self.testattr3

        prop_basic_flat = """
        S1:
          mapprimaryx:
            mapmember1:
              key: cheese
              value: cheddar
        """
        OverrideRegistry.unregister([properties.MapPrimary])
        OverrideRegistry.register([MapPrimaryX])
        try:
            root = PTreeSection('script', yaml.safe_load(prop_basic_flat))
            with self.assertRaises(AttributeError) as exc:
                root.S1.mapprimaryx.notfound

            self.assertEqual(str(exc.exception),
                             "'MapPrimaryX' object has no attribute "
                             "'notfound'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.mapprimaryx.testattr1

            self.assertEqual(str(exc.exception),
                             "'MapPrimaryX' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.mapprimaryx.testattr3

            self.assertEqual(str(exc.exception),
                             "'dict' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.mapprimaryx.testattr1

            self.assertEqual(str(exc.exception),
                             "'MapPrimaryX' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.mapprimaryx.testattr4

            self.assertEqual(str(exc.exception),
                             "'dict' object has no attribute "
                             "'nonexistantattr'")

            with self.assertRaises(AttributeError) as exc:
                root.S1.mapprimaryx.testattr1

            self.assertEqual(str(exc.exception),
                             "'MapPrimaryX' object has no attribute "
                             "'nonexistantattr'")

        finally:
            OverrideRegistry.unregister([MapPrimaryX])

    def test_mapped_property_list(self):
        mapped_property_list_members = """
        S1:
          mapprimary:
            - mapmember1:
                key: cheese
                value: cheddar
            - mapmember1:
                key: cheese
                value: brie
        """
        root = PTreeSection('script',
                            yaml.safe_load(mapped_property_list_members))
        cheese_types = []
        self.assert_leaves(root, ['S1'])
        mp = root.S1.mapprimary
        self.assertEqual(type(mp), properties.MapPrimary)
        for member in mp.members:
            self.assertEqual(type(member), properties.MapMember1)
            self.assertEqual(member.override_name, 'mapmember1')
            for item in member:
                self.assertEqual(type(item), properties.MapMember1)
                self.assertEqual(item.override_name, 'mapmember1')
                self.assertEqual(item.override_parent.override_path,
                                 'script.S1.mapprimary')
                self.assertEqual(item.key, 'cheese')
                cheese_types.append(item.value)

        self.assertEqual(cheese_types, ['cheddar', 'brie'])

    def test_mapped_property_grouped_member_first(self):
        mapped_property_grouped_members = """
        vars:
          cheese: cheddar
        S1:
          mapprimary:
            mapmember1:
              key: cheese
              value: wenselydale
            or:
              - mapmember1:
                  key: cheese
                  value: cheddar
              - mapmember1:
                  key: cheese
                  value: brie
        """
        root = PTreeSection('script',
                            yaml.safe_load(mapped_property_grouped_members))
        self.assert_leaves(root, ['S1'])
        mp = root.S1.mapprimary
        self.check_len_and_type(mp, 1, properties.MapPrimary)
        members = []
        results = []
        for member in mp.members:
            if isinstance(member, PTreeLogicalGrouping):
                self.check_len_and_type(member, 1, PTreeLogicalGrouping)
            else:
                self.check_len_and_type(member, 1, properties.MapMember1)

            members.append(member.__class__.__name__)
            for item in member:
                results.append(item.result)

        self.assertEqual(results, [False, True])
        self.assertEqual(members, ['MapMember1', 'PTreeLogicalGrouping'])

    def test_mapped_property_grouped_member_last(self):
        mapped_property_grouped_members = """
        vars:
          cheese: cheddar
        S1:
          mapprimary:
            or:
              - mapmember1:
                  key: cheese
                  value: brie
              - mapmember1:
                  key: cheese
                  value: cheddar
              - mapmember1:
                  key: cheese
                  value: yarg
            mapmember1:
              key: cheese
              value: wenselydale
        """
        root = PTreeSection('script',
                            yaml.safe_load(mapped_property_grouped_members))
        self.assert_leaves(root, ['S1'])
        mp = root.S1.mapprimary
        self.check_len_and_type(mp, 1, properties.MapPrimary)
        members = []
        results = []
        for member in mp.members:
            if isinstance(member, PTreeLogicalGrouping):
                self.check_len_and_type(member, 1, PTreeLogicalGrouping)
            else:
                self.check_len_and_type(member, 1, properties.MapMember1)

            members.append(member.__class__.__name__)
            for item in member:
                results.append(item.result)
                if isinstance(member, PTreeLogicalGrouping):
                    num_items = item.override_group_stats['items_executed']
                    self.assertEqual(num_items, 2)

        self.assertEqual(results, [False, True])
        self.assertEqual(members, ['MapMember1', 'PTreeLogicalGrouping'])

    def test_mapped_property_member_group(self):
        script = """
        vars:
          foo: bar
        S1:
          requires:
            or:
              typecheck:
                value: 123
                type: str
              varops: [[$foo], [eq, bar]]
        """
        OverrideRegistry.unregister([properties.MapPrimary])
        root = PTreeSection('script', yaml.safe_load(script))
        self.assert_leaves(root, ['S1'])
        requires = root.S1.requires
        self.check_len_and_type(requires, 1, properties.Requires)
        members = []
        for member in requires.members:
            self.check_len_and_type(
                member, 1,
                properties.PTreeLogicalGroupingWithCheckRefs)
            for item in member:
                self.assertEqual(item.override_parent.override_path,
                                 'script.S1.requires')
                members.append(item.__class__.__name__)
                self.assertEqual(item.result, True)
                # Each item should be its own mapping with its own primary
                num_items = item.override_group_stats['items_executed']
                self.assertEqual(num_items, 2)

        self.assertEqual(members, ['PTreeLogicalGroupingWithCheckRefs'])

    def test_grouped_implicit_mapped_property(self):
        script = """
        vars:
          foo: bar
        S1:
          or:
            typecheck:
              value: 123
              type: str
            varops: [[$foo], [eq, bar]]
        """
        OverrideRegistry.unregister([properties.MapPrimary])
        root = PTreeSection('script', yaml.safe_load(script))
        self.assert_leaves(root, ['S1'])
        num_items = []
        for item in root.S1:
            self.check_len_and_type(item, 1, properties.PTreeLogicalGrouping)
            self.assertEqual(item.result, True)
            # Each item should be its own mapping with its own primary
            num_items.append(item.override_group_stats['items_executed'])

        self.assertEqual(num_items, [2])

    def test_nested_mapping_explicit(self):
        nested_mapped_property = """
        mapprimary:
          requires:
            - typecheck:
                value: astring
                type: str
            - typecheck:
                value: bstring
                type: str
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_mapped_property))
        self.assertEqual(type(root.mapprimary), properties.MapPrimary)
        primaries = []
        members = []
        submembers = []
        for leaf in root.leaf_sections:  # noqa,pylint: disable=too-many-nested-blocks
            for primary in leaf.mapprimary:
                primaries.append(type(primary))
                self.assertEqual(type(primary), properties.MapPrimary)
                for requires in primary.members:
                    self.assertEqual(requires.override_parent.override_path,
                                     'script.mapprimary')
                    self.check_len_and_type(requires, 1, properties.Requires)
                    for requires_item in requires:
                        members.append(type(requires))
                        for typecheck in requires_item.members:
                            self.assertEqual(typecheck.override_parent.
                                             override_path,
                                             'script.mapprimary.requires')
                            self.check_len_and_type(typecheck, 2,
                                                    properties.TypeCheck)
                            for inst in typecheck:
                                submembers.append(type(inst))

        self.assertEqual(primaries, [properties.MapPrimary])
        self.assertEqual(members, [properties.Requires])
        self.assertEqual(submembers, [properties.TypeCheck,
                                      properties.TypeCheck])

    def test_nested_mapping_explicit_w_member_group(self):
        nested_mapped_property = """
        mapprimary:
          requires:
            - typecheck:
                value: astring
                type: str
            - or:
                - typecheck:
                    value: bstring
                    type: str
                - typecheck:
                    value: 123
                    type: str
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_mapped_property))
        self.assertEqual(type(root.mapprimary), properties.MapPrimary)
        primaries = []
        members = []
        submembers = []
        loggroup_check = {}
        for leaf in root.leaf_sections:  # noqa,pylint: disable=too-many-nested-blocks
            for primary in leaf:
                primaries.append(type(primary))
                self.assertEqual(type(primary), properties.MapPrimary)
                for requires in primary.members:
                    self.check_len_and_type(requires, 1, properties.Requires)
                    for requires_item in requires:
                        members.append(type(requires))
                        for item in requires_item.members:
                            if isinstance(item, properties.TypeCheck):
                                # NOTE: length should be one because the other
                                # two are within a group.
                                self.check_len_and_type(item, 1,
                                                        properties.TypeCheck)
                                for inst in item:
                                    submembers.append(type(inst))
                            else:
                                self.check_len_and_type(
                                  item, 1,
                                  properties.PTreeLogicalGroupingWithCheckRefs)
                                self.assertTrue(item.result)

                            if (isinstance(
                                    item,
                                    properties.
                                    PTreeLogicalGroupingWithCheckRefs)):
                                loggroup_check[item.group_name] = \
                                    item.override_group_stats[
                                        'items_executed']

        # its one because the first item is True
        self.assertEqual(loggroup_check, {'or': 1})
        self.assertEqual(primaries, [properties.MapPrimary])
        self.assertEqual(members, [properties.Requires])
        self.assertEqual(submembers, [properties.TypeCheck])

    def test_nested_mapping_mixed_grouped(self):
        """
        Test top level grouping containing a mix of both implicit and
        explicit mappings where the explicit mapping contains a member
        group.
        """
        nested_mapped_property = """
        mapprimary:
          and:  # this should be a PTreeLogicalGrouping
            - typecheck:
                value: astring
                type: str
            - requires:
                or:  # this should be a PTreeLogicalGroupingWithCheckRefs
                  - not:
                      and:
                        typecheck:
                          value: bstring
                          type: str
                  - typecheck:
                      value: 123
                      type: str
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_mapped_property))
        self.assertEqual(type(root.mapprimary), properties.MapPrimary)
        primaries = []
        members = []
        loggroup_check = {}
        for leaf in root.leaf_sections:
            for primary in leaf:
                primaries.append(type(primary))
                self.assertEqual(type(primary), properties.MapPrimary)
                for member in primary.members:
                    self.check_len_and_type(member, 1, PTreeLogicalGrouping)
                    for item in member:
                        self.check_len_and_type(item, 1, PTreeLogicalGrouping)
                        members.append(type(item))
                        self.assertFalse(item.result)
                        loggroup_check[item.group_name] = \
                            item.override_group_stats['items_executed']

        self.assertEqual(loggroup_check, {'and': 2})
        self.assertEqual(primaries, [properties.MapPrimary])
        self.assertEqual(members, [PTreeLogicalGrouping])

    def test_nested_mapping_implicit(self):
        """
        Note the difference here is that with a list of implicit mappings, each
        item becomes its own mapping.
        """
        nested_mapped_property = """
        mapprimary:
          typecheck:
            value: astring
            type: str
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_mapped_property))
        self.assertEqual(type(root.mapprimary), properties.MapPrimary)
        primaries = []
        members = []
        submembers = []
        for leaf in root.leaf_sections:  # noqa,pylint: disable=too-many-nested-blocks
            for primary in leaf.mapprimary:
                primaries.append(type(primary))
                self.assertEqual(type(primary), properties.MapPrimary)
                for requires in primary.members:
                    self.check_len_and_type(requires, 1, properties.Requires)
                    for requires_item in requires:
                        members.append(type(requires))
                        for typecheck in requires_item.members:
                            self.check_len_and_type(typecheck, 1,
                                                    properties.TypeCheck)
                            for inst in typecheck:
                                submembers.append(type(inst))

        self.assertEqual(primaries, [properties.MapPrimary])
        self.assertEqual(members, [properties.Requires])
        self.assertEqual(submembers, [properties.TypeCheck])

    def test_nested_mapping_implicit_list(self):
        """
        Note the difference here is that with a list of implicit mappings, each
        item becomes its own mapping.
        """
        nested_mapped_property = """
        mapprimary:
          - typecheck:
              value: astring
              type: str
          - typecheck:
              value: bstring
              type: str
        """
        root = PTreeSection('script',
                            yaml.safe_load(nested_mapped_property))
        self.assertEqual(type(root.mapprimary), properties.MapPrimary)
        primaries = []
        members = []
        submembers = []
        for leaf in root.leaf_sections:  # noqa,pylint: disable=too-many-nested-blocks
            for primary in leaf.mapprimary:
                primaries.append(type(primary))
                self.assertEqual(type(primary), properties.MapPrimary)
                for requires in primary.members:
                    self.check_len_and_type(requires, 2, properties.Requires)
                    for requires_item in requires:
                        members.append(type(requires))
                        for typecheck in requires_item.members:
                            self.assertEqual(len(typecheck), 1)
                            for inst in typecheck:
                                submembers.append(type(inst))

        self.assertEqual(primaries, [properties.MapPrimary])
        self.assertEqual(members, [properties.Requires, properties.Requires])
        self.assertEqual(submembers, [properties.TypeCheck,
                                      properties.TypeCheck])

    def test_mapping_mixed_logic(self):
        mapped = """
        S1:
          S2:
            vars:
              foo: bar
            checks:
              mycheck:
                and:
                  - varops: [[$foo], [eq, bar]]
                  - varops: [[$foo], [ne, bar]]
                or:
                  - varops: [[$foo], [eq, bar]]
                  - varops: [[$foo], [ne, bar]]
        """
        root = PTreeSection('script', yaml.safe_load(mapped))
        self.assertEqual([e.name for e in root.leaf_sections], ['S2'])
        self.assertEqual(type(root.S1.S2.checks), properties.Checks)
        for check in root.S1.S2.checks:
            self.assertEqual(check.name, 'mycheck')
            self.assertEqual(check.result, False)

    def test_mapping_stacked_logic(self):
        mapped = """
        requires:
          - not:
              typecheck:
                value: 123
                type: str
          - not:
              typecheck:
                value: iamastr
                type: str
        """
        root = PTreeSection('script', yaml.safe_load(mapped))
        self.assertEqual(type(root.requires), properties.Requires)
        items = []
        for member in root.requires.members:
            self.assertEqual(type(member),
                             properties.PTreeLogicalGroupingWithCheckRefs)
            for item in member:
                items.append(type(item))
                self.assertEqual(type(item),
                                 properties.PTreeLogicalGroupingWithCheckRefs)

        self.assertEqual(items, [properties.PTreeLogicalGroupingWithCheckRefs,
                                 properties.PTreeLogicalGroupingWithCheckRefs])

    def test_mapping_literal_items(self):
        mapped = """
        S1:
          decision: ["foo", "bar"]
        """
        root = PTreeSection('script', yaml.safe_load(mapped))
        self.assertEqual([e.name for e in root.leaf_sections], ['S1'])
        self.assertEqual(type(root.S1.decision), properties.Decision)
        members = []
        for decision in root.S1:
            self.assertEqual(type(decision), properties.Decision)
            for member in decision.members:
                for item in member:
                    members.append(str(item))

        self.assertEqual(members, ['foo', 'bar'])


class TestLiteralOverrides(TestPTree2Base):

    def setUp(self):
        super().setUp()
        OverrideRegistry.register([
                                properties.PTreeLogicalGroupingWithBoolValues])

    def tearDown(self):
        super().tearDown()
        OverrideRegistry.unregister([
                                properties.PTreeLogicalGroupingWithBoolValues])
        OverrideRegistry.register([PTreeLogicalGrouping])

    def test_simple_grouped_literal(self):
        simple_literal = """
        S1_True:
          and:
            - True
            - False
          or:
            - True
            - False
          not:
            - True
        """
        root = PTreeSection('script', yaml.safe_load(simple_literal))
        self.assert_leaves(root, ['S1_True'])
        checked = []
        for group in root:
            self.assertEqual(type(group),
                             properties.PTreeLogicalGroupingWithBoolValues)
            checked.append(group.__class__.__name__)
            if group.group_name == 'and':
                self.assertEqual(group.result, False)
            elif group.group_name == 'or':
                self.assertEqual(group.result, True)
            else:
                self.assertEqual(group.result, False)

        self.assertEqual(checked, ['PTreeLogicalGroupingWithBoolValues',
                                   'PTreeLogicalGroupingWithBoolValues',
                                   'PTreeLogicalGroupingWithBoolValues'])


class TestLargeScript(TestPTree2Base):

    def setUp(self):
        super().setUp()
        self.requirements = [properties.Vars, properties.ValueCheck,
                             properties.Checks, properties.VarOps,
                             properties.Input, properties.Requires,
                             properties.PTreeLogicalGroupingWithCheckRefs,
                             properties.Conclusions, properties.Conclusion,
                             properties.Decision, properties.Raises]
        OverrideRegistry.register(self.requirements)

    def tearDown(self):
        OverrideRegistry.unregister(self.requirements)
        OverrideRegistry.register([PTreeLogicalGrouping])
        super().tearDown()

    def test_large_script(self):
        yaml_script1 = """
        S1:
          input:
            path: F1
          vars:
            foo: bar
          checks:
            mycheck:
              varops: [[$foo], [eq, bar]]
            mycheck2:
              requires:
                varops: [[$foo], [eq, bar]]
            mycheck3:
              and:
                - varops: [[bar], [eq, bar]]
                - varops: [[bar], [ne, foo]]
          conclusions:
            isbar:
              decision:
                and: [mycheck, mycheck2, mycheck3]
              raises:
                type: FooType
                message:
                  blah
        S2:
          input:
            path: F2
        """
        context = {}
        root = PTreeSection('script', yaml.safe_load(yaml_script1),
                            context=context)
        context['checks'] = {c.name: c for c in root.S1.checks}
        self.assertEqual(root.S1.input.path, "F1")
        self.assertEqual(root.S2.input.path, "F2")
        self.assertEqual(root.S1.vars.foo, "bar")
        labels = []
        self.assertEqual([e.name for e in root.leaf_sections],
                         ['S1', 'S2'])

        for check in root.S1.checks:
            if check.override_name == 'mycheck':
                self.assertEqual(len(check), 1)
            elif check.override_name == 'mycheck2':
                self.assertEqual(len(check), 1)
            elif check.override_name == 'mycheck3':
                self.assertEqual(len(check), 1)
            else:
                raise Exception("unknown name")  # noqa,pylint: disable=broad-exception-raised

            labels.append(check.override_name)
            self.assertEqual(check.result, True)

        self.assertEqual(labels, ['mycheck', 'mycheck2', 'mycheck3'])

        labels = []
        for conclusion in root.S1.conclusions:
            labels.append(conclusion.name)
            self.assertEqual(conclusion.override_name, 'conclusion')
            self.assertEqual(conclusion.name, 'isbar')
            self.assertEqual(conclusion.decision.result, True)
            self.assertEqual(conclusion.raises.type, 'FooType')
            self.assertEqual(conclusion.raises.message, 'blah')
            self.assertEqual(labels, ['isbar'])
