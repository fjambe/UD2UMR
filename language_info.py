def create_node(node, variable_name, used_vars: dict, head_var_mapping: dict, triples: list, category: str):
    """
    Function that creates a new node. Its type is decided based on 'category'.
    Allowed values for 'category' are: ['person','thing', 'FILL'].
    FILL is used when it is not easy to automatically detect if the newly created node should be person or thing.
    """
    number = {'Sing': 'singular', 'Plur': 'plural'}
    person = {'1': '1st', '2': '2nd', '3': '3rd'}

    var_name = variable_name(category, used_vars, head_var_mapping)
    triples.append((var_name, ':instance', category))

    if category == 'person':
        suus_ref = node.parent if node.parent.upos == 'VERB' else node.parent.parent  # attempt to find referent of suus
        triples.append((var_name, ':refer-person', person[node.feats.get(f"Person{'[psor]' if node.upos == 'DET' else ''}")]))
        triples.append((var_name, ':refer-number', number.get(node.feats.get(f"Number{'[psor]' if node.upos == 'DET' else ''}")
                                                              or suus_ref.feats['Number'], 'FILL')))
    else:
        triples.append((var_name, ':refer-number', number.get(node.feats.get('Number'))))

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
    # 3. general possession: undetectable, because it's lexical. Unfortunately, nmod:poss does not occur in Perseus.
    """
    if node.feats['PronType'] == 'Prs':
        var_name = create_node(node, variable_name, used_vars, head_var_mapping, triples, 'person')
        try:
            parent = list(filter(lambda x: head_var_mapping[x] == node.parent, head_var_mapping))[0]
            triples.append((parent, role, var_name))
        except IndexError:
            print('IndexError', node)


def quantifiers(node, head_var_mapping: dict, used_vars: dict, triples: list, variable_name, add_node, role=None):
    """
    Function to handle quantifiers (e.g., omnis).
    """
    if node.feats['PronType'] == 'Tot':
        print(node, node.parent)
        if node.parent.upos in ['ADJ', 'NOUN', 'PROPN']:
            add_node(node, head_var_mapping, used_vars, triples, role)
        elif node.parent.upos == 'VERB':
            type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'FILL'
            var_name = create_node(node, variable_name, used_vars, head_var_mapping, triples, type_arg)

            parent = list(filter(lambda x: head_var_mapping[x] == node.parent, head_var_mapping))[0]
            triples.append((parent, role, var_name))
            # attaching the quantifier itself
            add_node(node, head_var_mapping, used_vars, triples, 'quant', def_parent=var_name)
