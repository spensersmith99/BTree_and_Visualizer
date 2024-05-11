import bisect, math, random
from typing import Any, List, Optional, Tuple, Union, Dict, Generic, TypeVar, cast, NewType
from py_btrees.disk import DISK, Address
from py_btrees.btree_node import BTreeNode, KT, VT, get_node

"""
----------------------- Starter code for your B-Tree -----------------------

Helpful Tips (You will need these):
1. Your tree should be composed of BTreeNode objects, where each node has:
    - the disk block address of its parent node
    - the disk block addresses of its children nodes (if non-leaf)
    - the data items inside (if leaf)
    - a flag indicating whether it is a leaf

------------- THE ONLY DATA STORED IN THE `BTree` OBJECT SHOULD BE THE `M` & `L` VALUES AND THE ADDRESS OF THE ROOT NODE -------------
-------------              THIS IS BECAUSE THE POINT IS TO STORE THE ENTIRE TREE ON DISK AT ALL TIMES                    -------------

2. Create helper methods:
    - get a node's parent with DISK.read(parent_address)
    - get a node's children with DISK.read(child_address)
    - write a node back to disk with DISK.write(self)
    - check the health of your tree (makes debugging a piece of cake)
        - go through the entire tree recursively and check that children point to their parents, etc.
        - now call this method after every insertion in your testing and you will find out where things are going wrong
3. Don't fall for these common bugs:
    - Forgetting to update a node's parent address when its parent splits
        - Remember that when a node splits, some of its children no longer have the same parent
    - Forgetting that the leaf and the root are edge cases
    - FORGETTING TO WRITE BACK TO THE DISK AFTER MODIFYING / CREATING A NODE
    - Forgetting to test odd / even M values
    - Forgetting to update the KEYS of a node who just gained a child
    - Forgetting to redistribute keys or children of a node who just split
    - Nesting nodes inside of each other instead of using disk addresses to reference them
        - This may seem to work but will fail our grader's stress tests
4. USE THE DEBUGGER
5. USE ASSERT STATEMENTS AS MUCH AS POSSIBLE
    - e.g. `assert node.parent != None or node == self.root` <- if this fails, something is very wrong

--------------------------- BEST OF LUCK ---------------------------
"""


# Complete both the find and insert methods to earn full credit
class BTree:
    def __init__(self, M: int, L: int):
        """
        Initialize a new BTree.
        You do not need to edit this method, nor should you.
        """
        self.root_addr: Address = DISK.new() # Remember, this is the ADDRESS of the root node
        # DO NOT RENAME THE ROOT MEMBER -- LEAVE IT AS self.root_addr
        DISK.write(self.root_addr, BTreeNode(self.root_addr, None, None, True))
        self.M = M  # M will fall in the range 2 to 99999
        self.L = L  # L will fall in the range 1 to 99999

    def find(self, key: KT, node=None) -> Optional[VT]:
        """
        Find a key and return the value associated with it.
        If it is not in the BTree, return None.

        This should be implemented with a logarithmic search
        in the node.keys array, not a linear search.
        """
        if node is not None:
            # returns where the new key would go in the sorted list of keys using logarithmic time
            chd_ind = bisect.bisect_left(node.keys, key)
            # if the index in the keys list matches the key we are trying to insert
            if chd_ind < len(node.keys) and key == node.keys[chd_ind]:
                if node.is_leaf:
                    # return the data associated with that key
                    return node.find_data(key)
                else:
                    # recurse down to the i-th child of the node where i = the index of the child we want to investigate
                    return self.find(key, node.get_child(chd_ind))
            # if node is a leaf then we can not recurse further and we return None
            elif node.is_leaf:
                return None
            else:
                # otherwise, recurse down the tree to the i-th child of the node
                return self.find(key, node.get_child(chd_ind))
        else:
            # starts at root and begins the recursion down
            root = get_node(self.root_addr)
            return self.find(key, root)

    def find_node(self, key: KT, node=None) -> Optional[BTreeNode]:
        '''
        Returns a BTreeNode for a given key in a BTree.
        Returns leaf node that key should be inserted into or None if it is a leaf with no parent.
        Works analogously to the find method above.
        '''
        if node is not None:
            chd_ind = bisect.bisect_left(node.keys, key)
            if chd_ind < len(node.keys) and key == node.keys[chd_ind]:
                if node.is_leaf:
                    return node
                else:
                    return self.find_node(key, node.get_child(chd_ind))
            # if node is a leaf, we can not recurse further and we return None
            elif node.is_leaf:
                u = node.parent_addr
                if u is not None:
                    return node
                else:
                    return None
            else:
                return self.find_node(key, node.get_child(chd_ind))
        else:
            root = get_node(self.root_addr)
            return self.find_node(key, root)

    def insert(self, key: KT, value: VT) -> None:
        '''
        Inserts a key-value pair into the BTree.
        Makes use of a find_node method that works like a regular find method with a twist.
        Makes use of a split_child method that splits the i-th child of a given node.
        Overwrites old values if the key exists in the BTree.
        '''
        # base case; starting at the root
        root = get_node(self.root_addr)
        # run a find on the key
        insertion_node = self.find_node(key)
        if insertion_node is None:
            if root.is_leaf and len(root.keys) <= self.L+1:
                root.insert_data(key, value)
                root.write_back()
        elif insertion_node is not None:
            if insertion_node.is_leaf:
                insertion_node.insert_data(key, value)
                insertion_node.write_back()
                # once a leaf's keys are over the allotted amount, we need to split it
                if len(insertion_node.keys) == self.L + 1:
                    self.split_child(get_node(insertion_node.parent_addr), insertion_node.index_in_parent)
                    parent_node = get_node(insertion_node.parent_addr)
                    # splitting a node, may cause us to have to split further up the tree; this checks for that
                    while len(parent_node.keys) == self.M:
                        check = parent_node.parent_addr
                        if check is not None:
                            self.split_child(get_node(parent_node.parent_addr), parent_node.index_in_parent)
                            parent_node = get_node(parent_node.parent_addr)
                        else:
                            # we are at root
                            break
        root = get_node(self.root_addr)
        # handles case when root is full and splits it
        if (root.is_leaf and len(root.keys) == self.L+1) or (not root.is_leaf and len(root.keys) == self.M):
            new_root = BTreeNode(DISK.new(), parent_addr=None, index_in_parent=None, is_leaf=False)
            new_root.write_back()
            self.root_addr = new_root.my_addr
            # add old root as a child of the new root
            new_root.children_addrs.insert(0, root.my_addr)
            new_root.write_back()
            self.split_child(new_root, 0)

    def split_child(self, node, index_of_child):
        '''
        Splits the i-th child of a specific node assuming that the i-th child is indeed full.
        '''
        left_node = get_node(node.children_addrs[index_of_child])
        left_node.index_in_parent = index_of_child
        left_node.parent_addr = node.my_addr
        left_node.write_back()
        # create a new empty right node for half of our keys
        right_node = BTreeNode(DISK.new(), parent_addr=node.my_addr, index_in_parent=index_of_child+1, is_leaf=left_node.is_leaf)
        node.children_addrs.insert(index_of_child+1, right_node.my_addr)
        if not left_node.is_leaf:
            # take median key and push it to the parent node
            node.keys.append(left_node.keys[math.ceil(self.M / 2) - 1])
            node.keys.sort()
            node.write_back()
            # take right half of keys/children and put it back in right node
            right_node.keys = left_node.keys[math.ceil(self.M / 2): self.M]
            right_node.children_addrs = left_node.children_addrs[math.ceil(self.M / 2): self.M+1]
            k = 0
            for address in right_node.children_addrs:
                child = get_node(address)
                child.index_in_parent = k
                child.parent_addr = right_node.my_addr
                child.write_back()
                k += 1
            right_node.write_back()
            #take left half of keys/children and put it back in left node
            left_node.keys = left_node.keys[0: math.ceil(self.M / 2)-1]
            left_node.children_addrs = left_node.children_addrs[0: math.ceil(self.M / 2)]
            # update the child addresses and indexes
            k2 = 0
            for address in left_node.children_addrs:
                child = get_node(address)
                child.index_in_parent = k2
                child.parent_addr = left_node.my_addr
                child.write_back()
                k2 += 1
            left_node.write_back()
            k = 0
            for address in node.children_addrs:
                child = get_node(address)
                child.index_in_parent = k
                child.parent_addr = node.my_addr
                child.write_back()
                k += 1
        if left_node.is_leaf:
            node.keys.append(left_node.keys[math.ceil((self.L+1) / 2)-1])
            node.keys.sort()
            node.write_back()
            # take right half of keys/children and put it back in right node
            right_node.keys = left_node.keys[math.ceil((self.L+1) / 2): self.L+1]
            right_node.data = left_node.data[math.ceil((self.L+1) / 2): self.L+1]
            right_node.write_back()
            # # take left half of keys/children and put it back in left node
            left_node.keys = left_node.keys[0: math.ceil((self.L+1) / 2)]
            left_node.data = left_node.data[0: math.ceil((self.L+1) / 2)]
            left_node.write_back()
            k = 0
            for address in node.children_addrs:
                child = get_node(address)
                child.index_in_parent = k
                child.parent_addr = node.my_addr
                child.write_back()
                k += 1
