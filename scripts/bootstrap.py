#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse
import udapi
import penman
from penman.exceptions import LayoutError
import structure as s
import csv
from typing import Union


def get_external_files(filename: str) -> Union[set, dict]:
    """
    Read a file containing lemmas and return them as a set. Used for:
    1. interpersonal relations (filename: have_rel_role.txt);
    2. SCONJs determining the type of adverbial clauses (advcl.csv).
    """

    extension = filename.split('.')[-1]
    terms = set() if extension == 'txt' else dict()

    try:
        with open(f"./external_resources/{filename}", 'r') as f:
            if extension == 'txt':
                terms = {line.strip() for line in f if line.strip()}
            else:
                reader = csv.reader(f)
                next(reader)
                for line in reader:
                    terms[line[0]] = {'type': line[1], 'constraint': line[2]}

    except FileNotFoundError:
        print(f"File {filename.split('/')[-1]} not found. Lexical information not available.")

    return terms


def dict_to_penman(structure: dict):
    """ Transform the nested dictionary obtained from UD into a Penman graph. """

    triples = []
    var_node_mapping = {}
    track_conj = {}
    extra_level = {}  # node: new_umr_parent, e.g. {var of ARG1: var of roleset-91}
    already_added = set()

    root, relations = next(iter(structure.items()))
    root_var = False

    # First loop: create variables for all (non-function) UD nodes.
    for role, node in relations.items():
        for item in node:
            if item.deprel not in ['aux', 'case', 'punct', 'mark']:
                var_name, var_node_mapping = s.variable_name(item, var_node_mapping)
                triples.append((var_name, 'instance', item.lemma))

    # Second loop: create relations between variables and build the UMR structure.
    for role, node_list in relations.items():
        for item in node_list:
            triples, temp_root_var, var_node_mapping = s.ud_to_umr(item,
                                                                   role,
                                                                   var_node_mapping,
                                                                   extra_level,
                                                                   triples,
                                                                   already_added,
                                                                   track_conj,
                                                                   relations)

            root_var = temp_root_var or root_var

    # delete 'instance' tuples if they are not associated with any role.
    ignored_types = {'instance', 'refer-number', 'refer-person', 'other'}
    root = [t[2] for t in triples if t[1] == 'root'][0] if not root_var else root_var
    valid = {root} | {tup[2] for tup in triples if tup[1] not in ignored_types}
    triples = [tup for tup in triples if tup[1] not in ['root', 'other'] and (tup[1] != 'instance' or tup[0] in valid)]

    try:
        triples, var_node_mapping = s.correct_variable_naming(triples, var_node_mapping)
        g = penman.Graph(triples)

        return penman.encode(g, top=root, indent=4)

    except LayoutError as e:
        print(triples)
        print(f"Skipping sentence due to LayoutError: {e}")


parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank in input.")
interpersonal = get_external_files('have_rel_role.txt')
advcl = get_external_files('advcl.csv')


if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        deprels = {}

        # restricting the scope
        auxs = [d for d in tree.descendants if d.upos == 'AUX']
        verbs = [d for d in tree.descendants if d.upos == 'VERB']
        mix = auxs + verbs
        if len(mix):
        # if ((len(auxs) == 1 and len(verbs) == 0) or (len(verbs) == 1 and len(auxs) == 0)) or (len(mix) == 2 and 'acl:relcl' in [d.deprel for d in tree.descendants if d.upos == 'VERB']):
            print('SNT:', tree.text, '\n')

            # mapping deprels - roles
            deprels['root'] = tree.children  # list with only one element, i.e. the root of the tree
            deprels['actor'] = [d for d in tree.descendants if d.deprel == 'nsubj']
            deprels['patient'] = [d for d in tree.descendants if d.deprel in ['obj', 'nsubj:pass']]
            deprels['mod'] = [d for d in tree.descendants if d.deprel == 'amod']
            deprels['OBLIQUE'] = [d for d in tree.descendants if d.deprel == 'obl' and d.feats['Case'] != 'Dat']
            deprels['det'] = [d for d in tree.descendants if d.deprel == 'det']
            deprels['manner'] = [d for d in tree.descendants if d.deprel == 'advmod']
            deprels['temporal'] = [d for d in tree.descendants if d.deprel == 'advmod:tmod']
            deprels['location'] = [d for d in tree.descendants if d.deprel == 'advmod:lmod']
            deprels['quant'] = [d for d in tree.descendants if d.deprel == 'nummod']
            deprels['vocative'] = [d for d in tree.descendants if d.deprel == 'vocative']
            deprels['affectee'] = [d for d in tree.descendants if d.deprel == 'obl:arg' or (d.deprel == 'obl' and d.feats['Case'] == 'Dat')]
            deprels['MOD/POSS'] = [d for d in tree.descendants if d.deprel == 'nmod' and d.feats['Case'] == 'Gen']
            deprels['poss'] = [d for d in tree.descendants if d.deprel == 'nmod:poss']
            deprels['identity-91'] = [d for d in tree.descendants if d.deprel == 'appos']
            deprels['COPULA'] = [d for d in tree.descendants if d.deprel == 'cop']
            deprels['ADVCL'] = [d for d in tree.descendants if d.deprel == 'advcl']
            deprels['other'] = [d for d in tree.descendants if d.udeprel in ['conj', 'punct', 'cc', 'fixed', 'flat', 'mark', 'csubj', 'ccomp', 'xcomp', 'dislocated', 'aux', 'discourse', 'acl', 'case', 'parataxis', 'dep', 'orphan']]

            umr = dict_to_penman({deprels['root'][0]: {k:v for k,v in deprels.items() if v}})  # removed empty lists
            print(umr, '\n')

            # break  # one sentence at a time

