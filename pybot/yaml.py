from collections import OrderedDict

from ruamel.yaml import YAML


def _constr_dict(constructor, node):
    od = OrderedDict()
    for key_node, value_node in node.value:
        key = constructor.construct_object(key_node)
        value = constructor.construct_object(value_node)
        od[key] = value
    return od


def _repr_dict(representer, data):
    return representer.represent_mapping(
        yaml.resolver.DEFAULT_MAPPING_TAG, data)


yaml = YAML()
yaml.constructor.add_constructor(yaml.resolver.DEFAULT_MAPPING_TAG,
        _constr_dict)
yaml.representer.add_representer(OrderedDict, _repr_dict)
