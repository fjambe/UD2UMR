def create_person_node(variable_name, used_vars: dict, head_var_mapping: dict, triples: list):  # which argument?
    var_name = variable_name('person', used_vars, head_var_mapping)
    triples.append((var_name, ':instance', 'person'))


def get_number(node, head_var_mapping):
    numbers = {'Sing': 'singular', 'Plur': 'plural'}
    node_var = list(filter(lambda x: head_var_mapping[x] == node, head_var_mapping))[0]
    return node_var, ':refer-number', numbers[node.feats['Number']]


def possessives(node, add_node, head_var_mapping, used_vars, triples):
    """
    Function to handle possessive constructions.
    # 1. easy case: possessive adjectives
    # 2. non-reflexive 3rd person (eius): TODO
    # 3. general possession: undetectable, because it's lexical.
    """
    if node.lemma in ['meus', 'tuus', 'suus', 'noster', 'voster', 'vester']:
        add_node(node, head_var_mapping, used_vars, triples, ':poss')
