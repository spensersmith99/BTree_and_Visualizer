from collections import deque
from typing import Any, Dict, Iterable, List
from py_btrees.btree import BTree
from py_btrees.btree_node import BTreeNode, get_node
from py_btrees.disk import Address

import graphviz  # type: ignore
from graphviz import nohtml


def create(tree: BTree) -> None:
    g = graphviz.Digraph('btree',
                         node_attr={'shape': 'record', 'height': '.1'})

    d = index_nodes(tree)

    for node in d.values():
        name = str(node.my_addr)
        label = None

        keys = [stringify(k) for k in node.keys]

        if node.is_leaf:
            keySection = '|'.join(keys)
            dataSection = '|'.join([stringify(x) for x in node.data])
            label = f'{{{keySection}}}|{{{dataSection}}}'

        else:
            links = [f'<f{i}>' for i in range(len(node.children_addrs))]

            boxes = [''] * (len(links) + len(keys))
            boxes[::2] = links
            boxes[1::2] = keys

            label = "|".join(boxes)

        g.node(name, nohtml(label))

        for i, childAddr in enumerate(node.children_addrs):
            child = d[childAddr]
            g.edge(f'{name}:f{i}', str(child.my_addr), label=str(child.index_in_parent))

    return g


def iterate(tree: BTree) -> Iterable[BTreeNode]:
    q = deque([get_node(tree.root_addr)])

    while len(q):
        node = q.popleft()
        yield node

        for childAddr in node.children_addrs:
            q.append(get_node(childAddr))


def index_nodes(tree: BTree) -> Dict[Address, BTreeNode]:
    return {node.my_addr: node for node in iterate(tree)}


def stringify(item: Any) -> str:
    if isinstance(item, str):
        return f"'{item}'"
    else:
        return str(item)