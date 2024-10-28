def create_node(node, variable_name, var_node_mapping: dict, triples: list, category: str, replace=False):
    """
    Function that creates a new node. Its type is decided based on 'category'.
    Allowed values for 'category' are: ['person','thing', 'FILL'].
    FILL is used when it is not easy to automatically detect if the newly created node should be person or thing.
    If True, the 'replace' parameter deletes an existing node, which is replaced by a newly created one.
    It's e.g. the case of personal pronouns; yet, sometimes we want to insert a new node without replacing any.
    """
    number = {'Sing': 'singular', 'Plur': 'plural'}
    person = {'1': '1st', '2': '2nd', '3': '3rd', 'ille': '3rd', 'hic': '3rd', 'is': '3rd'}

    new_var_name, var_node_mapping = variable_name(category, var_node_mapping)

    if replace:
        old_var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
        var_node_mapping = {k: v for k, v in var_node_mapping.items() if v != node}
        triples = [x for x in triples if x[0] != old_var_name]


    triples.append((new_var_name, ':instance', category))

    if category == 'person':
        suus_ref = node.parent if node.parent.upos == 'VERB' else node.parent.parent  # attempt to find referent of suus
        triples.append((new_var_name, ':refer-person', person.get(node.feats.get(f"Person{'[psor]' if node.feats['Person[psor]'] else ''}")
                                                              or suus_ref.feats['Person'], 'FILL')))
        triples.append((new_var_name, ':refer-number', number.get(node.feats.get(f"Number{'[psor]' if node.feats['Number[psor]'] else node.feats['NUmber']}")
                                                              or suus_ref.feats['Number'], 'FILL')))
    else:
        triples.append((new_var_name, ':refer-number', number.get(node.feats.get('Number'))))

    return new_var_name, var_node_mapping, triples


def get_number(node, var_node_mapping):
    number = {'Sing': 'singular', 'Plur': 'plural'}
    var_name = list(filter(lambda x: var_node_mapping[x] == node, var_node_mapping))[0]
    return var_name, ':refer-number', number[node.feats['Number']]


def possessives(node, var_node_mapping: dict, triples: list, variable_name, artificial_nodes, find_parent, role=None):
    """
    Function to handle possessive constructions.
    # 1. easy case: possessive adjectives
    # 2. non-reflexive 3rd person (eius): TODO
    # 3. general possession: undetectable, because it's lexical. Unfortunately, nmod:poss does not occur in Perseus.
    """
    if node.feats['PronType'] == 'Prs':
        var_name, var_node_mapping, triples = create_node(node, variable_name, var_node_mapping, triples, 'person', replace=True)
        try:
            parent = find_parent(node, var_node_mapping, artificial_nodes)
            triples.append((parent, role, var_name))
        except IndexError:
            print('IndexError', node)
    return triples



def quantifiers(node, var_node_mapping: dict, triples: list, variable_name, add_node, artificial_nodes, find_parent, role=None):
    """
    Function to handle quantifiers (e.g., omnis).
    """
    if node.feats['PronType'] == 'Tot':
        if node.parent.upos in ['ADJ', 'NOUN', 'PROPN']:
            add_node(node, var_node_mapping, triples, artificial_nodes, role)
        elif node.parent.upos == 'VERB':
            type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'FILL'
            var_name, var_node_mapping, triples = create_node(node, variable_name, var_node_mapping, triples, type_arg)
            parent = find_parent(node, var_node_mapping, artificial_nodes)
            triples.append((parent, role, var_name))
            # attaching the quantifier itself
            add_node(node, var_node_mapping, triples, artificial_nodes, role='quant', def_parent=var_name)

    return triples


def det_pro_noun(node, var_node_mapping: dict, triples: list, variable_name, artificial_nodes, find_parent, role=None):
    """
    For cases like 'Illi negaverunt', where an entity node (person/thing) has to be creaated to replace the DETs.
    """
    if node.deprel != 'det' and node.feats['PronType'] == 'Dem':
        type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'person'
        var_name, var_node_mapping, triples = create_node(node, variable_name, var_node_mapping, triples, type_arg, replace=True)
        parent = find_parent(node, var_node_mapping, artificial_nodes)
        triples.append((parent, role, var_name))
    return triples