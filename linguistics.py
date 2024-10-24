def pronouns(node):
    pass


def get_number(node, head_var_mapping):
    numbers = {'Sing': 'singular', 'Plur': 'plural'}
    return head_var_mapping[node], ':refer-number', numbers[node.feats['Number']]


def possessives(node, add_node, head_var_mapping, used_vars, triples):
    """
    Function to handle possessive constructions.
    # 1. easy case: possessive adjectives
    # 2. non-reflexive 3rd person (eius): TODO
    # 3. general possession: undetectable, because it's lexical.
    """
    if node.lemma in ['meus', 'tuus', 'suus', 'noster', 'voster', 'vester']:
        add_node(node, head_var_mapping, used_vars, triples, ':poss')
