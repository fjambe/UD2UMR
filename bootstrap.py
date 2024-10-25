#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse

import udapi
import penman
from penman.exceptions import LayoutError

import language_info as l

parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank in input.")


def variable_name(node, used_vars: dict, var_node_mapping: dict) -> str:
    """
    Function that assigns variable names according to UMR conventions.
    Either the first letter of the string or, if already assigned, letter and progressive numbering.
    """
    first_letter = node.lemma[0].lower() if not isinstance(node, str) else node[0].lower()
    count = used_vars.get(first_letter, 0) + 1
    used_vars[first_letter] = count
    var_name = first_letter if count == 1 else f'{first_letter}{count}'
    var_node_mapping[var_name] = node
    return var_name


def add_node(node, var_node_mapping: dict, triples: list, artificial_nodes, find_parent, role=None, return_var_name=False, def_parent=None):
    """
    Function that creates and adds a new node. Steps:
    1. Create a variable name and store it with the node it refers to
    3. Associate the node lemma and its var_name, as it will be in the UMR graph
    4. Link the var_name to its parent node via their relation (called 'role'), if the node is not the root
    5. If the node is the root, its variable name is also returned
    """
    # var_name = variable_name(node, used_vars, var_node_mapping)
    # triples.append((var_name, ':instance', node.lemma))
    var_name = next((k for k, v in var_node_mapping.items() if v == node), None)  # ragionare su questo None
    if return_var_name:
        return var_name
    else:
        try:
            if not def_parent:
                parent = find_parent(node, var_node_mapping, artificial_nodes)
            else:
                parent = def_parent
            triples.append((parent, role, var_name))
        except IndexError:
            print('Problem:', node)


def find_parent(node, var_node_mapping: dict, artificial_nodes: dict):
    try:
        parent = list(filter(lambda x: var_node_mapping[x] == node.parent, var_node_mapping))[0]
    except IndexError:
        parent = list(filter(lambda x: artificial_nodes[x] == node.parent, var_node_mapping))[0]
    return parent


def dict_to_penman(structure):
    """Function to transform the nested dictionary to a Penman graph."""
    used_vars = {}  # serve?
    var_node_mapping = {}
    artificial_nodes = {}  # to keep track of which artificial nodes (e.g. person) correspond to real ones
    already_added = []
    triples = []

    root, relations = next(iter(structure.items()))  # e.g.: root is 'addresses', relations is a dictionary like  {':actor': 'teacher', ':patient': 'student'}

    # Create the root node
    root_var = variable_name(tree.children[0], used_vars, var_node_mapping)
    triples.append((root_var, ':instance', tree.children[0].lemma))

    # First loop: create variables for all UD nodes.
    for role, node in relations.items():
        # 'node' is a list, hence create a triple for each item in the list
        for item in node:
            var_name = variable_name(item, used_vars, var_node_mapping)
            triples.append((var_name, ':instance', item.lemma))

    # Second loop: create relations between variables.
    # That's where the UMR structure is actually built.
    for role, node in relations.items():
        for item in node:
            if item.upos == 'PRON' and item.feats['PronType'] == 'Prs':
                triples = l.possessives(item, var_node_mapping, used_vars, triples, variable_name, artificial_nodes, find_parent, role=role)
                already_added.append(node)

            elif item.upos == 'NOUN' or (item.upos == 'ADJ' and item.deprel in ['nsubj', 'obj', 'obl']):
                add_node(item, var_node_mapping, triples, artificial_nodes, find_parent, role)
                triples.append(l.get_number(item, var_node_mapping))
                already_added.append(node)

            elif item.upos == 'DET':
                # check for PronType=Prs is inside the function
                triples = l.possessives(item, var_node_mapping, used_vars, triples, variable_name, artificial_nodes, find_parent, role='poss')
                # now check for quantifiers (PronType=Tot)
                triples = l.quantifiers(item, var_node_mapping, used_vars, triples, variable_name, add_node, artificial_nodes, find_parent, role=role if role != 'det' else 'quant')
                # check if they substitute for nouns
                triples = l.det_pro_noun(item, var_node_mapping, used_vars, triples, variable_name, artificial_nodes, find_parent, role=role)
                if item.deprel == 'det':
                    add_node(item, var_node_mapping, triples, artificial_nodes, find_parent, 'mod')
                already_added.append(node)

            elif item not in already_added:
                add_node(item, var_node_mapping, triples, artificial_nodes, find_parent, role)
                already_added.append(node)

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

        # To restrict the scope, I'm currently focusing on single-verb sentences with the verb as root.
        if [d.upos for d in tree.descendants].count('VERB') == 1 and tree.children[0].upos == 'VERB':
            print('SNT:', tree.text, '\n')

            # mapping deprels - roles
            deprels['actor'] = [d for d in tree.descendants if d.deprel == 'nsubj']
            deprels['patient'] = [d for d in tree.descendants if d.deprel in ['obj', 'nsubj:pass']]
            deprels['mod'] = [d for d in tree.descendants if d.deprel == 'amod']
            deprels['OBLIQUE'] = [d for d in tree.descendants if d.deprel == 'obl' and d.feats['Case'] != 'Dat']
            deprels['det'] = [d for d in tree.descendants if d.deprel == 'det']
            deprels['manner'] = [d for d in tree.descendants if d.deprel == 'advmod']
            deprels['temporal'] = [d for d in tree.descendants if d.deprel == 'advmod:tmod']
            deprels['quant'] = [d for d in tree.descendants if d.deprel == 'nummod']
            deprels['affectee'] = [d for d in tree.descendants if d.deprel == 'obl:arg' or (d.deprel == 'obl' and d.feats['Case'] == 'Dat')]
            deprels['MOD/POSS'] = [d for d in tree.descendants if d.deprel == 'nmod']
            deprels['CLAUSE'] = [d for d in tree.descendants if d.deprel == 'advcl']  # patch to avoid crashes
            deprels['CONJ'] = [d for d in tree.descendants if d.deprel == 'conj']  # patch to avoid crashes


            umr = dict_to_penman({tree.children[0]: {k:v for k,v in deprels.items() if v}})  # removed empty lists from deprels
            print(umr, '\n')

            # break  # one sentence at a time


