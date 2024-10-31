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
             return_var_name: bool = False,
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
            parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
        else:
            parent = def_parent
        triples.append((parent, role, var_name))


def find_parent(node_parent,
                var_node_mapping: dict,
                artificial_nodes: dict) -> tuple[str, bool]:

    new_root = False
    try:
        parent = list(filter(lambda x: var_node_mapping[x] == node_parent, var_node_mapping))[0]
    except IndexError:
        try:
            parent = list(filter(lambda x: artificial_nodes[x] == node_parent, var_node_mapping))[0]
        except KeyError as e:
            if node_parent.is_root():
                new_root = True
            else:
                print(f'Failed to locate the node parent. Error: {e}')
            parent = None

    return parent, new_root


def ud_to_umr(node,
              role: str,
              var_node_mapping: dict,
              triples: list,
              artificial_nodes: dict,
              already_added: set,
              track_conj: dict,
              relations: dict) -> tuple[list, any]:
    """Function that maps UD information to UMR structures."""

    root_var = None

    if node.upos == 'PRON':
        triples = l.personal(node,
                            var_node_mapping,
                            triples,
                            variable_name,
                            artificial_nodes,
                            find_parent,
                            role)
        already_added.add(node)

    elif (node.upos == 'NOUN' and role != 'other') or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj', 'obl']):
        add_node(node,
                 var_node_mapping,
                 triples,
                 artificial_nodes,
                 role)
        triples.append(l.get_number_person(node, 'number', var_node_mapping))
        already_added.add(node)

    elif node.upos == 'DET':
        # check for PronType=Prs is inside the function
        triples, called_possessives = l.possessives(node,
                                                    var_node_mapping,
                                                    triples,
                                                    variable_name,
                                                    artificial_nodes,
                                                    find_parent,
                                                    role)
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
        already_added.add(node)

    elif node.upos == 'VERB':
        if 'nsubj' not in [d.deprel for d in node.children]: # elided subjects to be restored
            var_name, var_node_mapping, triples = l.create_node(node,
                                                                variable_name,
                                                                var_node_mapping,
                                                                triples,
                                                                'FILL')
            parent, new_root = find_parent(node, var_node_mapping, artificial_nodes)
            triples.append((parent, 'actor', var_name))

            # what to do with nsubj:pass? sometimes it's impersonal rather than passive

    if node.deprel == 'conj':
        role = next((k for k, v in relations.items() for item in v if item == node.parent), None)
        triples, already_added, root_var = l.coordination(node,
                                                          role,
                                                          var_node_mapping,
                                                          triples,
                                                          already_added,
                                                          artificial_nodes,
                                                          track_conj,
                                                          variable_name,
                                                          find_parent)

    if node not in already_added:
        add_node(node,
                 var_node_mapping,
                 triples,
                 artificial_nodes,
                 role)
        already_added.add(node)

    return triples, root_var


def dict_to_penman(structure: dict):
    """Function to transform the nested dictionary into a Penman graph."""

    triples = []
    var_node_mapping = {}
    artificial_nodes = {}  # keep track of which artificial nodes (e.g. person) correspond to which real ones
    track_conj = {}
    already_added = set()

    root, relations = next(iter(structure.items()))
    root_var = False

    # First loop: create variables for all UD nodes.
    for role, node in relations.items():
        # 'node' is a list, hence create a triple for each item in the list
        for item in node:
            var_name, var_node_mapping = variable_name(item, var_node_mapping)
            triples.append((var_name, 'instance', item.lemma))

    # Second loop: create relations between variables and build the UMR structure.
    for role, node_list in relations.items():
        for item in node_list:
            triples, root_var = ud_to_umr(item,
                                          role,
                                          var_node_mapping,
                                          triples,
                                          artificial_nodes,
                                          already_added,
                                          track_conj,
                                          relations)

    # delete 'instance' tuples if they are not associated with any role.
    ignored_types = {'instance', 'refer-number', 'refer-person', 'other'}
    root = [t[2] for t in triples if t[1] == 'root'][0] if not root_var else root_var
    valid = {root} | {tup[2] for tup in triples if tup[1] not in ignored_types}
    triples = [tup for tup in triples if tup[1] not in ['root', 'other'] and (tup[1] != 'instance' or tup[0] in valid)]

    g = penman.Graph(triples)
    try:
        return penman.encode(g, top=root, indent=4)
    except LayoutError as e:
        print(f"Skipping sentence due to LayoutError: {e}")


if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        deprels = {}
        descendants = [d for d in tree.descendants if d.upos != 'PUNCT']

        # To restrict the scope, I'm currently focusing on single-verb sentences with the verb as root.
        if [d.upos for d in descendants].count('VERB') == 1 and tree.children[0].upos == 'VERB' and not 'cop' in [d.deprel for d in descendants]:
            print('SNT:', tree.text, '\n')

            # mapping deprels - roles
            deprels['root'] = tree.children  # list with only one element, i.e. the root of the tree
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
            deprels['other'] = [d for d in descendants if d.udeprel in ['conj', 'appos', 'advcl', 'punct', 'cc', 'fixed', 'flat', 'mark', 'csubj', 'ccomp', 'xcomp', 'dislocated', 'aux', 'cop', 'discourse', 'acl', 'case', 'parataxis', 'dep', 'orphan']]  # patch to avoid crashes

            umr = dict_to_penman({deprels['root'][0]: {k:v for k,v in deprels.items() if v}})  # removed empty lists
            print(umr, '\n')

            # break  # one sentence at a time


