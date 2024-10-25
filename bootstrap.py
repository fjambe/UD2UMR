#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse
import udapi
import penman
from penman.exceptions import LayoutError

import language_info as l

parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank in input.")


def variable_name(node, used_vars: dict, head_var_mapping: dict) -> str:
    """
    Function that assigns variable names according to UMR conventions.
    Either the first letter of the string or, if already assigned, letter and progressive numbering.
    """
    first_letter = node.lemma[0] if not isinstance(node, str) else node[0]
    count = used_vars.get(first_letter, 0) + 1
    used_vars[first_letter] = count
    var_name = first_letter if count == 1 else f'{first_letter}{count}'
    head_var_mapping[var_name] = node
    return var_name


def add_node(node, head_var_mapping: dict, used_vars: dict, triples: list, role=None, return_var_name=False):
    """
    Function that creates and adds a new node. Steps:
    1. Create a variable name and store it with the node it refers to
    3. Associate the node lemma and its var_name, as it will be in the UMR graph
    4. Link the var_name to its parent node via their relation (called 'role'), if the node is not the root
    5. If the node is the root, its variable name is also returned
    """
    var_name = variable_name(node, used_vars, head_var_mapping)
    triples.append((var_name, ':instance', node.lemma))
    if return_var_name:
        return var_name
    else:
        try:
            parent = list(filter(lambda x: head_var_mapping[x] == node.parent, head_var_mapping))[0]
            triples.append((parent, role, var_name))
        except IndexError:
            pass


def dict_to_penman(structure):
    """Function to transform the nested dictionary to a Penman graph."""
    used_vars = {}
    head_var_mapping = {}
    already_added = []
    triples = []

    root, relations = next(iter(structure.items()))  # e.g.: root is 'addresses', relations is a dictionary like  {':actor': 'teacher', ':patient': 'student'}

    # Create the root node
    root_var = add_node(root, head_var_mapping, used_vars, triples, return_var_name=True)

    for role, node in relations.items():
        # Node is a list, hence create a triple for each item in the list
        for item in node:
            if item.upos == 'PRON' and item.feats['PronType'] == 'Prs':
                l.possessives(item, head_var_mapping, used_vars, triples, variable_name, role=role)
                already_added.append(node)

            elif item.upos == 'NOUN' or (item.upos == 'ADJ' and item.deprel in ['nsubj', 'obj', 'obl']):
                add_node(item, head_var_mapping, used_vars, triples, role)
                triples.append(l.get_number(item, head_var_mapping))
                already_added.append(node)

            # for kid in item.descendants:
            #     if kid.upos == 'DET':
            #         l.possessives(kid, head_var_mapping, used_vars, triples, variable_name)
            #         already_added.append(node)

            elif item not in already_added:
                add_node(item, head_var_mapping, used_vars, triples, role)  # that's a risky move, see what happened with prons. TODO something.

    g = penman.Graph(triples)
    try:
        return penman.encode(g, top=root_var, indent=4)
    except LayoutError as e:
        print(f"Skipping sentence due to LayoutError: {e}")
        pass


if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        deprels = {}

        # To restrict the scope, I'm currently focusing on single-verb sentences.
        if [d.upos for d in tree.descendants].count('VERB') == 1:
            print('SNT:', tree.text, '\n')

            actor = [d for d in tree.descendants if d.deprel == 'nsubj']
            patient = [d for d in tree.descendants if d.deprel == 'obj']
            mods = [d for d in tree.descendants if d.deprel == 'amod']
            obliques = [d for d in tree.descendants if d.deprel == 'obl']
            determiners = [d for d in tree.descendants if d.deprel == 'det']

            deprels['actor'] = actor
            deprels['patient'] = patient
            deprels['mod'] = mods
            deprels['OBLIQUE'] = obliques

            umr = dict_to_penman({tree.children[0]: deprels})
            print(umr, '\n\n')

            break  # let's focus on one sentence at a time for now.


