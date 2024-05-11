import random
import graph
from py_btrees.btree import BTree

M = 5
L = 3
btree = BTree(M, L)
keys = [i for i in range(20)]
random.shuffle(keys)
print(keys)
for k in keys:
    btree.insert(k, str(k))

g = graph.create(btree)
# print(g.source)
g.view()
