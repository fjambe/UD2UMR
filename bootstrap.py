#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse
import udapi
import penman
from penman.exceptions import LayoutError

import language_info as l

parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank in input.")


def variable_name(node,
                  var_node_mapping: dict) -> tuple[str, dict]:
    """
    Function that assigns variable names according to UMR conventions.
    Either the first letter of the string or, if already assigned, letter + progressive numbering.
    """

    first_letter = node.lemma[0].lower() if not isinstance(node, str) else node[0].lower()
    count = 2

    if first_letter in var_node_mapping:
        while f"{first_letter}{count}" in var_node_mapping:
            count += 1

    var_name = first_letter if first_letter not in var_node_mapping else f"{first_letter}{count}"
    var_node_mapping[var_name] = node

    return var_name, var_node_mapping


def add_node(node,
             var_node_mapping: dict,
             triples: list,
             artificial_nodes: dict,
             role,
             return_var_name=False,
             def_parent=None):
    """
    Function that creates and adds a new node. Steps:
    1. Associate the node lemma and its var_name, as it will be in the UMR graph
    2. If the node is the root, its variable name is returned
    3. Link the var_name to its parent node via their relation (called 'role'), if the node is not the root
    """

    var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
    if return_var_name:
        return var_name
    else:
        if not def_parent:
            parent = find_parent(node.parent,
                                 var_node_mapping,
                                 artificial_nodes)
        else:
            parent = def_parent

        triples.append((parent, role, var_name))


def find_parent(node_parent, var_node_mapping: dict, artificial_nodes: dict) -> str:
    try:
        parent = list(filter(lambda x: var_node_mapping[x] == node_parent, var_node_mapping))[0]
    except IndexError:
        parent = list(filter(lambda x: artificial_nodes[x] == node_parent, var_node_mapping))[0]

    return parent


# def call_and_check(function, *params):
#     result = function(*params)
#     return result, bool(result)


def ud_to_umr(node, role: str, var_node_mapping: dict, triples: list, artificial_nodes: dict, already_added: list) -> list:
    """Function that maps UD information to UMR structures.
    TODO: Maybe move to language_info submodule - but that means adding arguments"""

    if node.upos == 'PRON' and node.feats['PronType'] == 'Prs':
        triples, called_possessives = l.possessives(node,
                                                    var_node_mapping,
                                                    triples,
                                                    variable_name,
                                                    artificial_nodes,
                                                    find_parent,
                                                    role)
        if node not in already_added:
            already_added.append(node)

    elif (node.upos == 'NOUN' and role != 'other') or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj', 'obl']):
        add_node(node,
                 var_node_mapping,
                 triples,
                 artificial_nodes,
                 role)
        triples.append(l.get_number(node, var_node_mapping))
        if node not in already_added:
            already_added.append(node)

    elif node.upos == 'DET':
        # check for PronType=Prs is inside the function
        triples, called_possessives = l.possessives(node,
                                                     var_node_mapping,
                                                     triples,
                                                     variable_name,
                                                     artificial_nodes,
                                                     find_parent,
                                                     'poss')
        # now check for quantifiers (PronType=Tot)
        triples, called_quantifiers = l.quantifiers(node,
                                                     var_node_mapping,
                                                     triples,
                                                     variable_name,
                                                     add_node,
                                                     artificial_nodes,
                                                     find_parent,
                                                     role if role != 'det' else 'quant')
        # check if they substitute for nouns
        triples, called_det_pro_noun = l.det_pro_noun(node,
                                                      var_node_mapping,
                                                      triples,
                                                      variable_name,
                                                      artificial_nodes,
                                                      find_parent,
                                                      role)
        if node.deprel == 'det' and not (called_possessives or called_quantifiers or called_det_pro_noun):
            add_node(node,
                     var_node_mapping,
                     triples,
                     artificial_nodes,
                     'mod')
        if node not in already_added:
            already_added.append(node)

    elif node.upos == 'VERB':
        if 'nsubj' not in [d.deprel for d in node.children]:
            var_name, var_node_mapping, triples = l.create_node(node,
                                                                variable_name,
                                                                var_node_mapping,
                                                                triples,
                                                                'person',  # try, otherwise FILL
                                                                elided=True)
            parent = find_parent(node, var_node_mapping, artificial_nodes)
            triples.append((parent, 'actor', var_name))

            # what to do with nsubj:pass? sometimes it's impersonal rather than passive

    if node.deprel == 'conj':
        triples, already_added = l.coordination(node,
                                 node.parent.deprel,
                                 var_node_mapping,
                                 triples,
                                 already_added,
                                 artificial_nodes,
                                 variable_name,
                                 find_parent)

    if node not in already_added:
        add_node(node,
                 var_node_mapping,
                 triples,
                 artificial_nodes,
                 role)
        if node not in already_added:
            already_added.append(node)

    return triples


def dict_to_penman(structure: dict):
    """Function to transform the nested dictionary into a Penman graph."""

    var_node_mapping = {}
    artificial_nodes = {}  # keep track of which artificial nodes (e.g. person) correspond to real ones
    triples = []
    already_added = [tree.children[0]]  # root

    root, relations = next(iter(structure.items()))

    # Create the root node
    root_var, var_node_mapping = variable_name(tree.children[0], var_node_mapping)
    triples.append((root_var, ':instance', tree.children[0].lemma))
    triples = ud_to_umr(root,
                        '',  # role is not needed here
                        var_node_mapping,
                        triples,
                        artificial_nodes,
                        already_added)

    # First loop: create variables for all UD nodes.
    for role, node in relations.items():
        # 'node' is a list, hence create a triple for each item in the list
        for item in node:
            var_name, var_node_mapping = variable_name(item, var_node_mapping)
            triples.append((var_name, ':instance', item.lemma))

    # Second loop: create relations between variables and build the UMR structure.
    for role, node_list in relations.items():
        for item in node_list:
            triples = ud_to_umr(item,
                                role,
                                var_node_mapping,
                                triples,
                                artificial_nodes,
                                already_added)

    ####
    # delete ':instance' tuples if they are not associated with any role.
    # ignored_types = {':instance', ':refer-number', ':refer-person'}
    # role_vars = {tup for tup in triples if tup[1] not in ignored_types}
    # role_vars.add(triples[0][0])  # root_var

    # for tup in triples:
    #     if tup[1] == ':instance':
    #         if tup[0] not in
    # cleaned_triples = [tup for tup in triples if tup[1] == ':instance' and tup[0] in role_vars]
    to_remove = [tup[2] for tup in triples if tup[1] == 'other']
    # ci devo tornare
    cleaned_triples = [tup for tup in triples if tup[1] != 'other']

    # print('cleaned', cleaned_triples)
    quit()

    # qua devo pulire da other

    g = penman.Graph(triples)
    try:
        return penman.encode(g, top=root_var, indent=4)
    except LayoutError as e:
        print(f"Skipping sentence due to LayoutError: {e}")
        print('printo triple', triples)


if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        deprels = {}

        # To restrict the scope, I'm currently focusing on single-verb sentences with the verb as root.
        if [d.upos for d in tree.descendants].count('VERB') == 1 and tree.children[0].upos == 'VERB' and not 'cop' in [d.deprel for d in tree.descendants] and 'conj' in [d.deprel for d in tree.descendants]:
            print('SNT:', tree.text, '\n')

            # mapping deprels - roles
            descendants = [d for d in tree.descendants if d.upos != 'PUNCT']

            deprels['actor'] = [d for d in descendants if d.deprel == 'nsubj']
            deprels['patient'] = [d for d in descendants if d.deprel in ['obj', 'nsubj:pass']]
            deprels['mod'] = [d for d in descendants if d.deprel == 'amod']
            deprels['OBLIQUE'] = [d for d in descendants if d.deprel == 'obl' and d.feats['Case'] != 'Dat']
            deprels['det'] = [d for d in descendants if d.deprel == 'det']
            deprels['manner'] = [d for d in descendants if d.deprel == 'advmod']
            deprels['temporal'] = [d for d in descendants if d.deprel == 'advmod:tmod']
            deprels['quant'] = [d for d in descendants if d.deprel == 'nummod']
            deprels['vocative'] = [d for d in descendants if d.deprel == 'vocative']
            deprels['affectee'] = [d for d in descendants if d.deprel == 'obl:arg' or (d.deprel == 'obl' and d.feats['Case'] == 'Dat')]
            deprels['MOD/POSS'] = [d for d in descendants if d.deprel == 'nmod']
            deprels['CLAUSE'] = [d for d in descendants if d.deprel == 'advcl']  # patch to avoid crashes
            # deprels['CONJ'] = [d for d in descendants if d.deprel == 'conj']  # patch to avoid crashes
            deprels['other'] = [d for d in descendants if d.udeprel in ['conj', 'appos', 'advcl', 'punct', 'cc', 'fixed', 'flat', 'mark', 'csubj', 'ccomp', 'xcomp', 'dislocated', 'aux', 'cop', 'discourse', 'acl', 'case', 'parataxis', 'dep', 'orphan']]  # patch to avoid crashes

            # print(deprels)
            umr = dict_to_penman({tree.children[0]: {k:v for k,v in deprels.items() if v}})  # removed empty lists from deprels
            print(umr, '\n')

            break  # one sentence at a time


