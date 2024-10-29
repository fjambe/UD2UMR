def create_node(node,
                variable_name,
                var_node_mapping: dict,
                triples: list,
                category: str,
                elided: bool = False,
                replace: bool = False) -> tuple[str, dict, list]:
    """
    Function that creates a new node. Its type is decided based on 'category'.
    Allowed values for 'category' are: ['person','thing', 'FILL'].
    FILL is used when it is not easy to automatically detect if the newly created node should be person or thing.
    If True, the 'replace' parameter deletes an existing node, which is replaced by a newly created one.
    It's e.g. the case of personal pronouns; yet, sometimes we want to insert a new node without replacing any.
    The 'elided' arg is True when we are dealing with e.g. elided subjects, so we want to create a brand-new entity.
    """
    number = {'Sing': 'singular', 'Plur': 'plural'}
    person = {'1': '1st', '2': '2nd', '3': '3rd', 'ille': '3rd', 'hic': '3rd', 'is': '3rd'}

    new_var_name, var_node_mapping = variable_name(category,
                                                   var_node_mapping)

    if not elided:
        if replace:
            old_var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
            var_node_mapping = {k: v for k, v in var_node_mapping.items() if v != node}
            triples = [x for x in triples if x[0] != old_var_name]

        triples.append((new_var_name, ':instance', category))

        if category == 'person':
            suus_ref = node.parent if node.parent.upos == 'VERB' else node.parent.parent  # attempt to find referent of suus
            triples.append((new_var_name, ':refer-person', person.get(node.feats.get(f"Person{'[psor]' if node.feats['Person[psor]'] else ''}")
                                                                  or suus_ref.feats['Person'], 'FILL')))
            triples.append((new_var_name, ':refer-number', number.get(node.feats.get(f"Number{'[psor]' if node.feats['Number[psor]'] else node.feats['Number']}")
                                                                  or suus_ref.feats['Number'], 'FILL')))
        else:
            triples.append((new_var_name, ':refer-number', number.get(node.feats.get('Number'))))

    else:
        triples.append((new_var_name, ':instance', category))

        if category == 'person':
            triples.append((new_var_name, ':refer-person', person.get(node.feats.get('Person'), 'FILL')))
        triples.append((new_var_name, ':refer-number', number.get(node.feats.get('Number'), 'FILL')))

    return new_var_name, var_node_mapping, triples


def get_number(node,
               var_node_mapping: dict) -> tuple[str, str, str]:
    number = {'Sing': 'singular', 'Plur': 'plural'}
    var_name = list(filter(lambda x: var_node_mapping[x] == node, var_node_mapping))[0]

    return var_name, ':refer-number', number[node.feats['Number']]


def possessives(node,
                var_node_mapping: dict,
                triples: list,
                variable_name,
                artificial_nodes,
                find_parent,
                role) -> tuple[list, bool]:
    """
    Function to handle possessive constructions.
    # 1. easy case: possessive adjectives
    # 2. non-reflexive 3rd person (eius): TODO
    # 3. general possession: undetectable, because it's lexical. Unfortunately, nmod:poss does not occur in Perseus.
    """

    called = False
    if node.feats['PronType'] == 'Prs':
        called = True
        var_name, var_node_mapping, triples = create_node(node,
                                                          variable_name,
                                                          var_node_mapping,
                                                          triples,
                                                          'person',
                                                          replace=True)
        parent = find_parent(node.parent,
                             var_node_mapping,
                             artificial_nodes)
        triples.append((parent, role, var_name))

    return triples, called


def quantifiers(node,
                var_node_mapping: dict,
                triples: list,
                variable_name,
                add_node,
                artificial_nodes: dict,
                find_parent,
                role) -> tuple[list, bool]:
    """Function to handle quantifiers (e.g., omnis)."""

    called = False
    if node.feats['PronType'] == 'Tot':

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
                                                              type_arg)
            parent = find_parent(node.parent,
                                 var_node_mapping,
                                 artificial_nodes)
            triples.append((parent, role, var_name))

            # attaching the quantifier itself
            add_node(node,
                     var_node_mapping,
                     triples,
                     artificial_nodes,
                     'quant',  #role=
                     def_parent=var_name)

    return triples, called


def det_pro_noun(node,
                 var_node_mapping: dict,
                 triples: list,
                 variable_name,
                 artificial_nodes: dict,
                 find_parent,
                 role) -> tuple[list, bool]:
    """For cases like 'Illi dixerunt' "They said", where an entity node (person/thing) has to be created to replace the DETs."""

    called = False
    if node.deprel != 'det' and node.feats['PronType'] == 'Dem':
        called = True
        type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'person'
        var_name, var_node_mapping, triples = create_node(node,
                                                          variable_name,
                                                          var_node_mapping,
                                                          triples,
                                                          type_arg,
                                                          replace=True)
        parent = find_parent(node.parent,
                             var_node_mapping,
                             artificial_nodes)
        triples.append((parent, role, var_name))

    return triples, called


def coordination(node,
                 role: str,
                 var_node_mapping: dict,
                 triples: list,
                 already_added: list,
                 artificial_nodes: dict,
                 variable_name,
                 find_parent) -> tuple[list, list]:

    conjs = {'or': ['vel', 'uel', 'aut'], 'and': ['et', 'ac', 'atque', 'nec', 'neque', ',']}

    # create a top node for the conjunction

    # NOW the issue is that the conjunction gets created twice if I have multiple conjuncts

    cc = [d for d in node.children if d.deprel == 'cc']  # polysyndeton
    cc = cc[0] if cc else [d for d in node.children if d.deprel == 'punct' and d.lemma == ','][0]  # asyndeton
    cord = next((k for k, v in conjs.items() if cc.lemma in v), None)
    var_name_conj, var_node_mapping = variable_name(cord, var_node_mapping)
    triples.append((var_name_conj, ':instance', cord))
    parent = find_parent(node.parent,
                         var_node_mapping,
                         artificial_nodes)
    triples.append((parent, role, var_name_conj))

    # attach all conjuncts to the newly create conjunction node
    # first conjunct - need to delete the existing relational (not instance) triple created when it was not known that it is a conjunct
    # first conjunct == parent of second conjunct --> node.parent
    var_name = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
    triples = [tup for tup in triples if var_name != tup[2]]
    # now we can attach it correctly
    triples.append((var_name_conj, ':op1', var_name))
    if node.parent not in already_added:
        already_added.append(node.parent)

    # second conjunct, i.e. first one with 'conj' deprel
    var_name, var_node_mapping = variable_name(node, var_node_mapping)
    # triples.append((var_name, ':instance', node.lemma))
    triples.append((var_name_conj, ':op2', var_name))
    if node not in already_added:
        already_added.append(node)

    # check here for more conjuncts
    other_conjuncts = [d for d in node.siblings if d.deprel == 'conj']
    if other_conjuncts:
        # numbering of opX, starting from the third conjunct (first 2 already handled)
        num = 2
        for oc in other_conjuncts:
            if oc not in already_added:
                num += 1
                var_name, var_node_mapping = variable_name(oc, var_node_mapping)
                # triples.append((var_name, ':instance', oc.lemma))
                triples.append((var_name_conj, f':op{num}', var_name))

    print(triples)

    return triples, already_added