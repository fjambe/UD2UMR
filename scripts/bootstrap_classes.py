#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse
import udapi
from classes import UMRNode, UDTree


parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank in input.")


def get_deprels(ud_tree) -> dict:
    """ Map UD deprels to UMR roles. """

    deprels = {}

    deprels['root'] = ud_tree.children  # list with only one element, i.e. the root of the ud_tree
    deprels['actor'] = [d for d in ud_tree.descendants if d.deprel == 'nsubj']
    deprels['patient'] = [d for d in ud_tree.descendants if d.deprel in ['obj', 'nsubj:pass']]
    deprels['mod'] = [d for d in ud_tree.descendants if d.deprel == 'amod']
    deprels['OBLIQUE'] = [d for d in ud_tree.descendants if d.deprel == 'obl' and d.feats['Case'] != 'Dat']
    deprels['det'] = [d for d in ud_tree.descendants if d.deprel == 'det']
    deprels['manner'] = [d for d in ud_tree.descendants if d.deprel == 'advmod']
    deprels['temporal'] = [d for d in ud_tree.descendants if d.deprel == 'advmod:tmod']
    deprels['location'] = [d for d in ud_tree.descendants if d.deprel == 'advmod:lmod']
    deprels['quant'] = [d for d in ud_tree.descendants if d.deprel == 'nummod']
    deprels['vocative'] = [d for d in ud_tree.descendants if d.deprel == 'vocative']
    deprels['affectee'] = [d for d in ud_tree.descendants if
                           d.deprel == 'obl:arg' or (d.deprel == 'obl' and d.feats['Case'] == 'Dat')]
    deprels['MOD/POSS'] = [d for d in ud_tree.descendants if d.deprel == 'nmod' and d.feats['Case'] == 'Gen']
    deprels['poss'] = [d for d in ud_tree.descendants if d.deprel == 'nmod:poss']
    deprels['identity-91'] = [d for d in ud_tree.descendants if d.deprel == 'appos']
    deprels['COPULA'] = [d for d in ud_tree.descendants if d.deprel == 'cop']
    deprels['ADVCL'] = [d for d in ud_tree.descendants if d.deprel == 'advcl']
    deprels['other'] = [d for d in ud_tree.descendants if
                        d.udeprel in ['conj', 'punct', 'cc', 'fixed', 'flat', 'mark', 'csubj', 'ccomp', 'xcomp',
                                      'dislocated', 'aux', 'discourse', 'acl', 'case', 'parataxis', 'dep', 'orphan']]

    return {k:v for k,v in deprels.items() if v}


def get_role_from_deprel(ud_node, deprels):
    """
    Check if a node is in any of the value lists in the deprels dictionary.
    If it is, return the corresponding key. If not, return None.

    Parameters:
    - node: The node to search for in the deprels dictionary.
    - deprels: A dictionary where keys are roles and values are lists of nodes.
    """
    for mapped_role, nodes in deprels.items():
        if ud_node in nodes:
            return mapped_role
    return None



if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        sent_tree = UDTree(tree)
        deprels_to_relations = get_deprels(tree)
        for node in tree.descendants:
            role = get_role_from_deprel(node, deprels_to_relations)
            item = UMRNode(node, sent_tree, role=role)

        sent_tree.display_text()

