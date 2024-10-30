from typing import Callable

def create_node(node,
                variable_name: Callable,
                var_node_mapping: dict,
                triples: list,
                category: str,
                get_number: Callable,
                elided: bool = False,
                replace: bool = False,
                reflex: bool = False) -> tuple[str, dict, list]:
    """
    Function that creates a new node. Its type is decided based on 'category'.
    Allowed values for 'category' are: ['person','thing', 'FILL'].
    FILL is used when it is not easy to automatically detect if the newly created node should be person or thing.
    If True, the 'replace' parameter deletes an existing node, which is replaced by a newly created one.
    It's e.g. the case of personal pronouns; yet, sometimes we want to insert a new node without replacing any.
    The 'elided' arg is True when we are dealing with e.g. elided subjects, so we want to create a brand-new entity.
    """
    person = {'1': '1st', '2': '2nd', '3': '3rd', 'ille': '3rd', 'hic': '3rd', 'is': '3rd'}
    suus_ref = None

    new_var_name, var_node_mapping = variable_name(category, var_node_mapping)

    if replace:
        old_var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
        var_node_mapping = {k: v for k, v in var_node_mapping.items() if v != node}
        triples = [x for x in triples if x[0] != old_var_name]

    if not elided: # suus va qui ??
        if category == 'person':
            suus_ref = node.parent if node.parent.upos == 'VERB' else node.parent.parent  # attempt to find referent of reflexive ADJ
            triples.append((new_var_name, 'refer-person', person.get(node.feats.get(f"Person{'[psor]' if node.feats['Person[psor]'] else ''}")
                                                                  or suus_ref.feats['Person'], 'FILL')))

    else:
        if category == 'person':
            triples.append((new_var_name, 'refer-person', person.get(node.feats.get('Person'), 'FILL')))


    triples.append((new_var_name, 'instance', category))

    if not reflex:
        triples.append(get_number(node, var_node_mapping, new_var_name, suus_ref))

    return new_var_name, var_node_mapping, triples


def get_number(node,
               var_node_mapping: dict,
               new_var_name: str = False,
               custom: any = False) -> tuple[str, str, str]:

    numbers = {'Sing': 'singular', 'Plur': 'plural'}

    if not new_var_name:
        var_name = list(filter(lambda x: var_node_mapping[x] == node, var_node_mapping))[0]

    else:
        var_name = new_var_name

    number_psor = node.feats.get("Number[psor]")
    number_main = node.feats.get("Number") or (custom.feats.get("Number") if custom else 'FILL')
    number = numbers.get(number_psor if number_psor else number_main, 'FILL')

    return var_name, 'refer-number', number


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
            var_name, var_node_mapping, triples = create_node(node,
                                                              variable_name,
                                                              var_node_mapping,
                                                              triples,
                                                              'person',
                                                              get_number,
                                                              replace=True,
                                                              reflex=node.lemma=='suus')

            parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
            triples.append((parent, 'poss', var_name))
            if node.lemma == 'suus':
                triples.append((var_name, 'refer-number', numbers.get(node.parent.parent.feats['Number'])))

        elif node.parent.upos == 'VERB':
            called = True
            var_name, var_node_mapping, triples = create_node(node,
                                                              variable_name,
                                                              var_node_mapping,
                                                              triples,
                                                              'thing' if node.feats['Gender'] == 'Neut' else 'FILL',
                                                              get_number,
                                                              elided=True,
                                                              reflex=node.lemma=='suus')

            parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
            triples.append((parent, role, var_name))
            if node.lemma == 'suus':
                triples.append((var_name, 'refer-number', numbers.get(node.feats['Number'])))

            # attaching the possessive itself
            poss_var_name, var_node_mapping, triples = create_node(node,
                                                                   variable_name,
                                                                   var_node_mapping,
                                                                   triples,
                                                                   'person',
                                                                   get_number,
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
                role) -> list:

    """Function to handle personal pronouns"""

    if node.feats['PronType'] == 'Prs':

        var_name, var_node_mapping, triples = create_node(node,
                                                          variable_name,
                                                          var_node_mapping,
                                                          triples,
                                                          'person',
                                                          get_number,
                                                          replace=True)
        parent, new_root = find_parent(node.parent, var_node_mapping, artificial_nodes)
        triples.append((parent, role, var_name))

    return triples


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
            var_name, var_node_mapping, triples = create_node(node,
                                                              variable_name,
                                                              var_node_mapping,
                                                              triples,
                                                              type_arg,
                                                              get_number)

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
                 variable_name,
                 artificial_nodes: dict,
                 find_parent,
                 role) -> tuple[list, bool]:
    """For cases like 'Illi dixerunt' "They said", where an entity node has to be created to replace the DETs."""

    called = False
    if node.deprel != 'det' and node.feats['PronType'] == 'Dem':
        called = True
        type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'person'  # maybe FILL is better
        var_name, var_node_mapping, triples = create_node(node,
                                                          variable_name,
                                                          var_node_mapping,
                                                          triples,
                                                          type_arg,
                                                          get_number,
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
                 variable_name,
                 find_parent) -> tuple[list, set, any]:

    conjs = {'or': ['vel', 'uel', 'aut'], 'and': ['que', 'et', 'ac', 'atque', 'nec', 'neque', ',']}

    root_var = None

    # create one top node for the conjunction governing the coordination
    if node.parent not in track_conj:  # node.parent is the head conjunct
        # identify conjunction type (polysyndeton or asyndeton)
        cc = next((d for d in node.children if d.deprel == 'cc' or (d.deprel == 'punct' and d.lemma == ',')), None)
        cord = next((k for k, v in conjs.items() if cc and cc.lemma in v), None)
        var_name_conj, var_node_mapping = variable_name(cord, var_node_mapping)
        triples.append((var_name_conj, 'instance', cord))

        parent, new_root = find_parent(node.parent.parent, var_node_mapping, artificial_nodes)
        # node is the 2nd conjunct, first with deprel conj
        # node.parent is the 1st conjunct, with the actual deprel
        triples.append((parent, role, var_name_conj))
        track_conj[node.parent] = var_name_conj

        # Attach all conjuncts to the conjunction node
        # Handle the first conjunct (node.parent)
        var_name = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
        triples = [tup for tup in triples if not (tup[2] == var_name and tup[1] != 'instance')] # remove previous relation, if any (always except if it's root)
        triples.append((var_name_conj, 'op1', var_name))
        already_added.add(node.parent)

        # handle the second conjunct (node itself)
        var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
        triples.append((var_name_conj, 'op2', var_name))
        if (node.upos == 'NOUN' and role != 'other') or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj', 'obl']):
            triples.append(get_number(node, var_node_mapping))
        already_added.add(node)

        # attach additional conjuncts, if any
        for num, oc in enumerate((d for d in node.siblings if d.deprel == 'conj' and d not in already_added), start=3):
            var_name = next((k for k, v in var_node_mapping.items() if v == oc), None)
            triples.append((var_name_conj, f'op{num}', var_name))

        if new_root:
            root_var = var_name_conj

    return triples, already_added, root_var