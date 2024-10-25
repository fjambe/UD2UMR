def create_person_node(node, variable_name, used_vars: dict, head_var_mapping: dict, triples: list):  # which argument?
    number = {'Sing': 'singular', 'Plur': 'plural'}
    person = {'1': '1st', '2': '2nd', '3': '3rd'}

    var_name = variable_name('person', used_vars, head_var_mapping)
    triples.append((var_name, ':instance', 'person'))
    triples.append((var_name, ':refer-number', number[node.feats[f"Number{'[psor]' if node.upos == 'DET' else ''}"]]))
    triples.append((var_name, ':refer-person', person[node.feats[f"Person{'[psor]' if node.upos == 'DET' else ''}"]]))
    return var_name


def get_number(node, head_var_mapping):
    number = {'Sing': 'singular', 'Plur': 'plural'}
    var_name = list(filter(lambda x: head_var_mapping[x] == node, head_var_mapping))[0]
    return var_name, ':refer-number', number[node.feats['Number']]


def possessives(node, head_var_mapping: dict, used_vars: dict, triples: list, variable_name, role=None):
    """
    Function to handle possessive constructions.
    # 1. easy case: possessive adjectives
    # 2. non-reflexive 3rd person (eius): TODO
    # 3. general possession: undetectable, because it's lexical. NOOO, nmod:poss! But in Perseus?
    """
    if node.lemma in ['meus', 'tuus', 'noster', 'voster', 'vester']:  # + 'suus'
        var_name = create_person_node(node, variable_name, used_vars, head_var_mapping, triples)
        parent = list(filter(lambda x: head_var_mapping[x] == node.parent, head_var_mapping))[0]
        triples.append((parent, 'poss', var_name))
        # the issue is that 'suus' can be singular or plural, and I should extract this info from his parent, since it is reflexive.
        # but where? it's probably simpler to let it go, but fair?

    if node.feats['PronType'] == 'Prs':
        var_name = create_person_node(node, variable_name, used_vars, head_var_mapping, triples)
        parent = list(filter(lambda x: head_var_mapping[x] == node.parent, head_var_mapping))[0]
        triples.append((parent, role, var_name))
