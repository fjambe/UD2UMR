from typing import Callable

def create_node(node,
                variable_name: Callable,
                var_node_mapping: dict,
                triples: list,
                category: str,
                artificial_nodes:dict,
                replace: bool = False,
                reflex: bool = False) -> tuple[str, dict, list, dict]:
    """
    Function that creates a new node. Its type is decided based on 'category'.
    Allowed values for 'category' are: ['person','thing', 'FILL'].
    FILL is used when it is not easy to automatically detect if the newly created node should be person or thing.
    If True, the 'replace' parameter deletes an existing node, which is replaced by a newly created one.
    It's e.g. the case of personal pronouns; yet, sometimes we want to insert a new node without replacing any.
    """

    new_var_name, var_node_mapping = variable_name(category, var_node_mapping)

    if replace:
        old_var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
        var_node_mapping = {k: v for k, v in var_node_mapping.items() if v != node}
        triples = [x for x in triples if x[0] != old_var_name]
        artificial_nodes[new_var_name] = node

    triples.append((new_var_name, 'instance', category))

    if category == 'person':
        triples.append(get_number_person(node, 'person', var_node_mapping, new_var_name))

    if not reflex:
        triples.append(get_number_person(node, 'number', var_node_mapping, new_var_name))

    return new_var_name, var_node_mapping, triples, artificial_nodes


def get_number_person(node,
                      feature: str,
                      var_node_mapping: dict,
                      new_var_name: str = None) -> tuple[str, str, str]:

    feats = {'Sing': 'singular', 'Plur': 'plural', '1': '1st', '2': '2nd', '3': '3rd', 'ille': '3rd', 'hic': '3rd', 'is': '3rd'}

    if not new_var_name:
        var_name = list(filter(lambda x: var_node_mapping[x] == node, var_node_mapping))[0]
    else:
        var_name = new_var_name

    feat = feats.get(node.feats.get(f"{feature.capitalize()}[psor]") or node.feats.get(feature.capitalize()), 'FILL')

    return var_name, f'refer-{feature}', feat


def possessives(node,
                var_node_mapping: dict,
                triples: list,
                variable_name: Callable,
                artificial_nodes: dict,
                find_parent: Callable,
                role) -> tuple[list, bool]:
    """
    Function to handle possessive constructions.
    # 1. basic case: possessive adjectives
    # 2. non-reflexive 3rd person (eius): TODO
    # 3. general possession: undetectable, because it's lexical. nmod:poss does not occur in Perseus.
    """

    numbers = {'Sing': 'singular', 'Plur': 'plural'}
    called = False

    if node.feats['PronType'] == 'Prs':

        if node.parent.upos in ['ADJ', 'NOUN', 'PROPN']:
            called = True
            var_name, var_node_mapping, triples, artificial_nodes = create_node(node,
                                                                    variable_name,
                                                                    var_node_mapping,
                                                                    triples,
                                                                    'person',
                                                                    artificial_nodes,
                                                                    replace=True,
                                                                    reflex=node.lemma=='suus')

            parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
            triples.append((parent, 'poss', var_name))
            if node.lemma == 'suus':
                triples.append((var_name, 'refer-number', numbers.get(node.parent.parent.feats['Number'])))

        elif node.parent.upos == 'VERB':
            called = True
            var_name, var_node_mapping, triples, artificial_nodes = create_node(node,
                                                                    variable_name,
                                                                    var_node_mapping,
                                                                    triples,
                                                                    'thing' if node.feats['Gender'] == 'Neut' else 'FILL',
                                                                    artificial_nodes,
                                                                    reflex=node.lemma=='suus')

            parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
            triples.append((parent, role, var_name))
            if node.lemma == 'suus':
                triples.append((var_name, 'refer-number', numbers.get(node.feats['Number'])))

            # attaching the possessive itself
            poss_var_name, var_node_mapping, triples, artificial_nodes = create_node(node,
                                                                         variable_name,
                                                                         var_node_mapping,
                                                                         triples,
                                                                         'person',
                                                                         artificial_nodes,
                                                                         replace=True,
                                                                         reflex=node.lemma == 'suus')

            triples.append((var_name, 'poss', poss_var_name))
            if node.lemma == 'suus':
                triples.append((poss_var_name, 'refer-number', numbers.get(node.parent.feats['Number'])))

    return triples, called


def personal(node,
             var_node_mapping: dict,
             triples: list,
             variable_name: Callable,
             artificial_nodes: dict,
             find_parent: Callable,
             role) -> tuple[list, dict]:

    """Function to handle personal pronouns"""

    if node.feats['PronType'] == 'Prs':

        var_name, var_node_mapping, triples, artificial_nodes = create_node(node,
                                                                variable_name,
                                                                var_node_mapping,
                                                                triples,
                                                                'person' if node.feats['Gender'] != 'Neut' else 'thing',
                                                                artificial_nodes,
                                                                replace=True)
        parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
        triples.append((parent, role, var_name))

    return triples, var_node_mapping


def quantifiers(node,
                var_node_mapping: dict,
                triples: list,
                variable_name: Callable,
                add_node: Callable,
                artificial_nodes: dict,
                find_parent: Callable,
                role) -> tuple[list, bool]:

    called = False
    if node.feats['PronType'] == 'Tot':  # e.g., omnis

        if node.parent.upos in ['ADJ', 'NOUN', 'PROPN']:
            called = True
            add_node(node,
                     var_node_mapping,
                     triples,
                     artificial_nodes,
                     role)

        elif node.parent.upos == 'VERB':
            called = True
            type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'FILL'
            var_name, var_node_mapping, triples, artificial_nodes = create_node(node,
                                                                    variable_name,
                                                                    var_node_mapping,
                                                                    triples,
                                                                    type_arg,
                                                                    artificial_nodes)

            parent, new_root = find_parent(node.parent,var_node_mapping, artificial_nodes)
            triples.append((parent, role, var_name))

            # attaching the quantifier itself
            add_node(node,
                     var_node_mapping,
                     triples,
                     artificial_nodes,
                     'quant',
                     def_parent=var_name)

    return triples, called


def det_pro_noun(node,
                 var_node_mapping: dict,
                 triples: list,
                 variable_name: Callable,
                 artificial_nodes: dict,
                 find_parent,
                 role) -> tuple[list, bool]:
    """For cases like 'Illi dixerunt' "They said", where an entity node has to be created to replace the DETs."""

    called = False
    if node.deprel != 'det' and node.feats['PronType'] == 'Dem':
        called = True
        type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'person'  # maybe FILL is better
        var_name, var_node_mapping, triples, artificial_nodes = create_node(node,
                                                                variable_name,
                                                                var_node_mapping,
                                                                triples,
                                                                type_arg,
                                                                artificial_nodes,
                                                                replace=True)
        parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
        triples.append((parent, role, var_name))

    return triples, called


def coordination(node,
                 role: str,
                 var_node_mapping: dict,
                 triples: list,
                 already_added: set,
                 artificial_nodes: dict,
                 track_conj: dict,
                 variable_name: Callable,
                 find_parent) -> tuple[list, set, any]:

    conjs = {'or': ['vel', 'uel', 'aut'], 'and': ['que', 'et', 'ac', 'atque', 'nec', 'neque', ',']}
    # 'sed' to be handled differently -> but-91

    root_var = None

    # create one top node for the conjunction governing the coordination
    if node.parent not in track_conj:  # node.parent is the head conjunct
        # identify conjunction type (polysyndeton or asyndeton)
        cc = next((d for d in node.children if d.deprel == 'cc' or (d.deprel == 'punct' and d.lemma == ',')), None)
        cord = next((k for k, v in conjs.items() if cc and cc.lemma in v), None)
        var_node_mapping = {k:v for k,v in var_node_mapping.items() if v != cc}  # remove cc for correct variable naming
        if not cord:  # coordination without conjunction/comma
            cord = 'and'
        if cc:
            triples = [tup for tup in triples if tup[2] != cc.lemma]
        var_name_conj, var_node_mapping = variable_name(cord, var_node_mapping)
        triples.append((var_name_conj, 'instance', cord))

        # create variables for first two conjuncts, to set up the coordination structure
        # node.parent: 1st conjunct (true deprel), node: 2nd conjunct (deprel = conj, #1)
        var_first_conj = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
        var_second_conj = next((k for k, v in var_node_mapping.items() if v == node), None)

        role = role
        parent, new_root = find_parent(node.parent.parent, var_node_mapping, artificial_nodes)
        for tup in triples:  # avoid clashes of abstract concepts and coordination
            if tup[2] == var_first_conj:
                role, parent = tup[1], tup[0]
                break

        triples.append((parent, role, var_name_conj))
        track_conj[node.parent] = var_name_conj

        # Attach first and second conjuncts to the conjunction node
        triples = [tup for tup in triples if not (tup[2] == var_first_conj and tup[1] != 'instance')] # remove previous relation, if any
        triples.append((var_name_conj, 'op1', var_first_conj))
        triples.append((var_name_conj, 'op2', var_second_conj))
        if (node.upos == 'NOUN' and role != 'other') or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj', 'obl']):
            triples.append(get_number_person(node, 'number', var_node_mapping))
        already_added.update({node, node.parent})

        # attach additional conjuncts, if any
        for num, oc in enumerate((d for d in node.siblings if d.deprel == 'conj' and d not in already_added), start=3):
            var_name = next((k for k, v in var_node_mapping.items() if v == oc), None)
            triples.append((var_name_conj, f'op{num}', var_name))
            already_added.add(oc)

        if new_root:
            root_var = var_name_conj

    return triples, already_added, root_var


def copulas(node,
            var_node_mapping: dict,
            triples: list,
            artificial_nodes: dict,
            variable_name: Callable,
            find_parent) -> tuple[list, dict, any]:  # TODO any or string?

    root_var = None  # ??

    if node.parent.upos == 'NOUN' and node.parent.feats['Case'] == 'Nom':
        # identity-91
        var_parent = next((k for k, v in var_node_mapping.items() if v == node.parent), None) # head of the construction -> equated referent
        var_sum = next((k for k, v in var_node_mapping.items() if v == node), None)
        triples = [tup for tup in triples if var_sum not in tup]

        var_concept, var_node_mapping = variable_name('identity-91', var_node_mapping)
        triples.append((var_concept, 'instance', 'identity-91'))

        # reassigning root, if relevant
        for i, tup in enumerate(triples):
            if tup[2] == var_parent and tup[1] == 'root':
                root_var = var_concept
                triples[i] = (tup[0], tup[1], var_concept)

        nsubj = next((d for d in node.parent.children if d.deprel == 'nsubj'), None)
        var_nsubj = next((k for k, v in {**var_node_mapping, **artificial_nodes}.items() if v == nsubj), None)

        triples = [tup for tup in triples if tup[2] != var_nsubj]  # remove previous relation, if any
        triples.extend([
            (var_concept, 'equated_referent', var_parent),
            (var_concept, 'theme', var_nsubj)
        ])

        return triples, var_node_mapping, root_var