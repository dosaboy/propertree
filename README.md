# Propertree

A Python library for creating custom objects from yaml or json structures.

YAML and JSON provide a nice way to define a structure and this library provides
a way to give meaning to that structure so that it can be used in code. Once
yaml or json is loaded into Python we can then "walk the tree" until we find
items that we recognise. This library supports different types of "overrides"
that are essentially a dictionary with a unique root key and content that can
be extracted as properties on a class.
