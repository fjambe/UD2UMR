#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

"""
Udapi cheatsheet:
1. tree: prints out the technical <ROOT> of the sentence (== tree).
2. tree.text: prints out the actual sentence. So tech_root = tree.
3. tree.children: prints out the single direct children of the technical ROOT, i.e. the actual root.
UD trees are single-rooted, so len(tree.children) == 1, always.
4. tree.descendants: prints out the whole tree, i.e. all the nodes.
"""


"""
TODOS
1. I think it could be useful to have function specific to UPOS. E.g., for NOUNs I check refer-number, etc.
For PRONs I build the usual NE structure, and so on.
For now, however,  it's not implemented.
"""

import argparse
import udapi
import penman
import linguistics as l


parser = argparse.ArgumentParser()
parser.add_argument("--treebank", default=False, help="Path of the treebank to parse in input.")


def variable_name(node, used_vars: dict) -> str:
    """
    Function that assigns a name to a variable and returns it.
    In UMR, it is usually the first letter of the string, except if the letter has already been assigned.
    In that case, progressive numbering is implemented, according to UMR conventions.
    Example: e.g. a, a2, b, a3, b2, ...
    """
    first_letter = node.lemma[0]

    # If the letter has not been used, assign it
    if first_letter not in used_vars:
        used_vars[first_letter] = 1
        return first_letter
    # Otherwise, increment the count and use a numbered version
    else:
        used_vars[first_letter] += 1
        return f'{first_letter}{used_vars[first_letter]}'


def add_node(node, role, head_var_mapping, used_vars, triples):
    """
    Function that creates and adds a new node. Steps:
    1. Create a variable name
    2. Store the var_name together with the node (in Udapi sense) it refers to
    3. Associate the node lemma and its var_name, as it will be in the UMR graph
    4. Link the var_name to its parent node via their relation (called role).

    It does not return anything, instead it appends items directly to the 'triples' list.
    """
    var_name = variable_name(node, used_vars)
    head_var_mapping[node] = var_name
    triples.append((var_name, ':instance', node.lemma))
    triples.append((head_var_mapping[node.parent], role, var_name))


# def sentence_to_dict(root, subj, obj, mods, obliques) -> dict:
def sentence_to_dict(root, dep_relations) -> dict:
    """
    Function that takes a dependency tree and stores it as a nested dictionary, as needed to encode in penman.
    TODO: I need to redefine parameters, it's too specific as it is now.
    TODO: of course, I also need to expand the dictionary to cover more deprels.
    Actually, most probably it will not be doable to compose the dictionary explicitly. it will be a for loop.
    """
    # return {
    #     root: {
    #         ":actor": subj,
    #         ":patient": obj,
    #         "mod": [mod for mod in mods],
    #         "OBLIQUE": [obl for obl in obliques]
    #     }
    # }
    return {
        root: dep_relations
    }


def dict_to_penman(tree):
    """
    Function to transform the nested dictionary to a Penman graph.
    It takes aas input the nested dictionary returned by sentence_to_dict() and returns a Penman graph, i.e. the UMR.
    """
    used_vars = {}
    head_var_mapping = {}
    triples = []

    root, relations = next(iter(tree.items()))  # e.g.: root is 'addresses', relations is a dictionary like  {':actor': 'teacher', ':patient': 'student'}

    # Create the root node
    root_var = root.lemma[0]
    used_vars[root_var] = 1
    head_var_mapping[root] = root_var
    triples.append((root_var, ':instance', root.lemma))

    for role, node in relations.items():
        if isinstance(node, list):
            # If node is a list, create a triple for each item in the list (e.g. multiple modifiers)
            for item in node:
                add_node(item, role, head_var_mapping, used_vars, triples)

                if item.upos == 'NOUN' or (item.upos == 'ADJ' and item.deprel in ['nsubj', 'obj']):
                    triples.append(l.get_number(item, head_var_mapping))
                # if item.descendants:
                    for kid in item.descendants:
                        if kid.upos == 'DET':
                            l.possessives(kid, add_node, head_var_mapping, used_vars, triples)

        else:
            add_node(node, role, head_var_mapping, used_vars, triples)

            if node.upos == 'NOUN' or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj']):
                triples.append(l.get_number(node, head_var_mapping))
            if node.descendants:
                for kid in node.descendants:
                    if kid.upos == 'DET':
                        l.possessives(kid, add_node, head_var_mapping, used_vars, triples)

    g = penman.Graph(triples)
    return penman.encode(g, top=root_var, indent=4)

if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(args.treebank)

    for tree in doc.trees:

        deprels = {}

        # To restrict the scope, I'm currently focusing on single-verb sentences.
        if [d.upos for d in tree.descendants].count('VERB') == 1:
            print(tree.text)

            # actor - nsubj
            # I'll worry later about nsubj:pass and passive sentences. I think only one nsubj is allowed, so it should be univocal.
            # also about coordinate subjects.
            # also about csubj.
            actor = [d for d in tree.descendants if d.deprel == 'nsubj'][0]
            # patient - obj
            # I'll worry later about theme and about coordinate objects.
            # also about pronouns.
            patient = [d for d in tree.descendants if d.deprel == 'obj'][0]
            mods = [d for d in tree.descendants if d.deprel == 'amod']
            # obl - OBLIQUE placeholder
            # I'll worry later about obl:arg and possible other subtypes.
            obliques = [d for d in tree.descendants if d.deprel == 'obl']
            determiners = [d for d in tree.descendants if d.deprel == 'det']
            # I DEFINITELY NEED TO GENERALISE THIS, AND THE FOLLOWING LINE AS WELL.

            deprels['actor'] = actor
            deprels['patient'] = patient
            deprels['mods'] = mods
            deprels['obliques'] = obliques


            # tree = sentence_to_dict(tree.children[0], actor, patient, mods, obliques)
            tree = sentence_to_dict(tree.children[0], deprels)
            umr = dict_to_penman(tree)
            print(umr)

            break  # let's focus on one sentence at a time for now.


