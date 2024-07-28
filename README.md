# Propertree

Map Python data structures to classes and create tree of resolvable objects.

## Overview

This library provides a set of classes that can be used to take Python data
structures and map them to a set of properties organised in a tree-like
structure. The basic idea is that a Python object with one or more attributes
can be represented by a unique key in a dictionary whereby the the value of
that key represents the internal makeup of the object i.e. attributes etc.

The basic design is as follows:

A ```PTreeSection``` object takes Python data structures dict/list/literal
after having been converted from YAML or JSON. This input is treated like a
tree of properties whereby each level of a structure equates to a branch
containing a set of "property overrides" which are identified by a unique
root key that maps to an implementation of ```PTreeOverrideBase```. Descendant
lists, dictionaries or unknown literals are treated new branches.

Once the whole tree has been mapped, objects can be retreived by either
iterating over the root object or accessing them directly as attributes.

For example lets say we have the following YAML:

```
config:
  fire:
    danger:
      level: high
  banana:
    danger:
      level: low
```

And the following accompanying Python code:

```
from propertree.propertree2 import PTreeOverrideBase, PTreeSection

class Config(PTreeOverrideBase):
  override_keys = ['config']


root = PTreeSection(MYYAML)
```

We can then access the config as follows:

```
print(root.config.fire.danger.level)
print(root.config.banana.danger.level)
```

## Property Inheritance

Property inheritance is supported by passing down all properties identified at
a branch level to all descendent branches. This allows property objects to
access any property within it's call chain although it would be the most
recently overriden version if one exists. For example:

```
input: /etc/foo
checks:
  chk1:
    input: /etc/bar
    condition: C1
  chk2:
    condition: C2
```

In the above, ```checks.chk1.input``` would be "/etc/bar" whereas ```checks.chk2.input``` would be "/etc/foo".


## Mapped Properties

It is possible to compose complex properties made up of one or more "member"
properties. These are called *mapped* properties and are provided by the
```PTreeMappedOverrideBase``` class. A mapped property has two parts; a *primary*
and its *members*. A property can only be a member of one mapped property (i.e.
be associated with a single primary). These properties also have the special
feature that allow them to be defined either *explicitly* using their
full construct i.e. primary and members or *implicitly* using just their
members. If the latter form is used, the primary is implicitly created such
that when the members are accessed it is always done through the primary.

For example, here is some code to define a mapped property:

```
from propertree.propertree2 import PTreeOverrideBase, PTreeMappedOverrideBase, PTreeSection

class MapPrimary(PTreeMappedOverrideBase):
  override_keys = ['mapprimary']
  override_members = ['member1']


class Member1(PTreeOverrideBase):
  override_keys = ['member1']

...
```

the following will both behave the same when accessed:

The explicit declaration:

```
mapprimary:
  member1:
    attr1:
```

And the counterpart implicit declaration:

```
member1:
  attr1:
```

Are both accessed as follows:

```
mapprimary.member1.attr1
```

## Logical Groupings

Sometimes it might be useful to represent properties or content within a
property as a logical function. To achieve this, propertree has builtin
logical operator properties which map to the ```PTreeLogicalGrouping``` class.
This class provides a default implementation of logical operations that can be
used by any property. Grouped items are expected to have a ```result```
attribute that returns a boolean result such that the respective logical
operator of that grouping is then applied to the set of all results.

In the following example we have a top-level operator with two items, each of
which is itself an operator, the first having two property items and second
having one. This equates to AND(OR(P1, P2), NOT(P3)).

```
and:
  or: [P1, P2]
  not: P3
```

Example code for this would look like:

```
from propertree.propertree2 import PTreeSection

root = PTreeSection(MYYAML)
result = root.and.result
```

