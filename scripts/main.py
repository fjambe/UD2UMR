#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import os
import argparse
import udapi
from umr_node import UMRNode
from umr_graph import UMRGraph
import preprocess as pr
from print_structure import print_structure

parser = argparse.ArgumentParser()
parser.add_argument("--treebank", help="Path of the treebank in input.", required=True)
parser.add_argument("--lang", help="Language code of the treebank (e.g., 'en' for English).", required=True)
parser.add_argument("--data_dir",
                    help="Path of the directory where the input treebanks are stored, if not 'data'.", default='./data')
parser.add_argument("--output_dir",
                    help="Path of the directory where converted UMRs are stored, if not 'output'.", default='./output')


if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(f'{args.data_dir}/{args.treebank}')
    sent_num = 0

    interpersonal = pr.load_external_files('have_rel_role.txt', args.lang)
    advcl = pr.load_external_files('advcl.csv', args.lang)
    modals = pr.load_external_files('modality.json', args.lang)
    conjunctions = pr.load_external_files('conj.json', args.lang)

    # with open("testset/converted_70_test_sent_ids.txt", "r", encoding="utf8") as for_test_file:  # to produce the test set only
    #     test = for_test_file.read().splitlines()

    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, f"{args.treebank.split('.')[0]}.umr"), "w",  encoding="utf-8") as output:
    # with open(f"testset/converted_{args.lang}_test.txt", "w", encoding="utf-8") as output:  # to produce the test set only

        for tree in doc.trees:

            # if tree.address() in test:

                sent_num += 1

                deprels_to_relations = pr.get_deprels(tree)
                sent_tree = UMRGraph(tree, sent_num, deprels_to_relations, args.lang, interpersonal, advcl, modals, conjunctions)

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

                # Fourth pass: replace nodes that are supposed to correspond to a UMR entity (PRON, PROPN).
                # They are processed separately to avoid clashes with layered constructions (e.g., abstract rolesets).
                for n in sent_tree.nodes:
                    n.replace_entities()

                umr, root = sent_tree.to_penman()

                # Print out the UMR structure
                print_structure(tree, sent_tree, umr, root, sent_num, output, print_in_file=True)

                # break

