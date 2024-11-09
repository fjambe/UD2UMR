import csv
from typing import Union


def get_deprels(ud_tree) -> dict:
    """ Map UD deprels to UMR roles, mostly based on UD deprels. """

    mapping_conditions = {
        'root': lambda d: d.deprel == 'root',  # All children are included for 'root'
        'actor': lambda d: d.deprel == 'nsubj',
        'patient': lambda d: d.deprel in ['obj', 'nsubj:pass'],
        'mod': lambda d: d.deprel == 'amod',
        'OBLIQUE': lambda d: d.deprel == 'obl' and d.feats.get('Case') != 'Dat',
        'det': lambda d: d.deprel == 'det',
        'manner': lambda d: d.deprel == 'advmod',
        'temporal': lambda d: d.deprel == 'advmod:tmod',
        'location': lambda d: d.deprel == 'advmod:lmod',
        'quant': lambda d: d.deprel == 'nummod',
        'vocative': lambda d: d.deprel == 'vocative',
        'affectee': lambda d: d.deprel == 'obl:arg' or (d.deprel == 'obl' and d.feats.get('Case') == 'Dat'),
        'MOD/POSS': lambda d: d.deprel == 'nmod' and d.feats.get('Case') == 'Gen',
        'poss': lambda d: d.deprel == 'nmod:poss',
        'identity-91': lambda d: d.deprel == 'appos',
        'COPULA': lambda d: d.deprel == 'cop',
        'ADVCL': lambda d: d.deprel == 'advcl',
        'other': lambda d: d.udeprel in ['conj', 'punct', 'cc', 'fixed', 'flat', 'mark', 'csubj', 'ccomp',
                                         'xcomp', 'dislocated', 'aux', 'discourse', 'acl', 'case',
                                         'parataxis', 'dep', 'orphan']
    }

    deprels = {rel: [d for d in ud_tree.descendants if condition(d)] for rel, condition in mapping_conditions.items()}

    return {k: v for k, v in deprels.items() if v}


def get_role_from_deprel(ud_node, deprels):
    """
    Check if a node is in any of the value lists in the deprels dictionary.
    If it is, return the corresponding key. If not, return None.

    Parameters:
    - ud_node:  node to search for in the deprels dictionary.
    - deprels: dictionary where keys are roles and values are lists of nodes.
    """
    for mapped_role, nodes in deprels.items():
        if ud_node in nodes:
            return mapped_role
    return None


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

#########################################################

interpersonal = get_external_files('have_rel_role.txt')
advcl = get_external_files('advcl.csv')