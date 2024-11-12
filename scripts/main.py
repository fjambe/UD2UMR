#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse
import udapi
from umr_node import UMRNode
from umr_graph import UMRGraph
import preprocess as pr

parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank in input.")


if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        deprels_to_relations = pr.get_deprels(tree)
        sent_tree = UMRGraph(tree, deprels_to_relations)

        # First pass: create variables for UD nodes.
        for node in tree.descendants:
            if node.deprel not in ['aux', 'case', 'punct', 'mark']:
                role = pr.get_role_from_deprel(node, deprels_to_relations)
                item = UMRNode(node, sent_tree, role=role)

        # Second pass: assign initial parents after all nodes have been created.
        for n in sent_tree.nodes:
            n.parent = n.find_by_ud_node(sent_tree, n.ud_node.parent)

        # Third pass: create relations between variables and build the UMR structure.
        for n in sent_tree.nodes:
            if not isinstance(n.ud_node, str):
                n.ud_to_umr()

        # Fourth pass: replace pronouns and determiners that are supposed to correspond to a UMR entity.
        # They are processed separately to avoid clashes with layered constructions (e.g., abstract rolesets).
        for n in sent_tree.nodes:
            n.replace_entities()

        umr = sent_tree.to_penman()

        # Print out the UMR graph
        sent_tree.display_text()
        print(umr, '\n')

        # break

