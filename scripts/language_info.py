from typing import Callable
from bootstrap import interpersonal, advcl

def create_node(node,
                variable_name: Callable,
                var_node_mapping: dict,
                triples: list,
                category: str,
                replace: bool = False,
                reflex: bool = False) -> tuple[str, dict, list]:
    """
    Create a new node, whose type is decided based on 'category'. Allowed 'category' values: ['person','thing', 'FILL'].
    FILL is used when it is not easy to automatically detect if the new node should be person or thing.
    If True, the 'replace' parameter deletes an existing node, which is then replaced by the newly created one
    (e.g. the case of personal pronouns).
    If False (default), a new node is inserted without any being replaced.
    """

    new_var_name, var_node_mapping = variable_name(category, var_node_mapping)

    if replace:
        old_var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
        var_node_mapping = {k: v for k, v in var_node_mapping.items() if v != node}
        triples = [x for x in triples if x[0] != old_var_name]
        for i, tup in enumerate(triples):
            triples[i] = tuple(new_var_name if element == old_var_name else element for element in tup)   # remove old rel

        var_node_mapping[new_var_name] = node

    triples.append((new_var_name, 'instance', category))

    if category == 'person':
        triples.append(get_number_person(node, 'person', var_node_mapping, new_var_name))

    if not reflex:
        triples.append(get_number_person(node, 'number', var_node_mapping, new_var_name))

    return new_var_name, var_node_mapping, triples


def get_number_person(node,
                      feature: str,
                      var_node_mapping: dict,
                      new_var_name: str = None) -> tuple[str, str, str]:
    """ Extract refer-number and refer-person attributes. """

    feats = {
        **{k: '3rd' for k in ['3', 'ille', 'hic', 'is', 'ipse']},
        'Sing': 'singular',
        'Plur': 'plural',
        '1': '1st',
        '2': '2nd',
    }

    if not new_var_name:
        var_name = list(filter(lambda x: var_node_mapping[x] == node, var_node_mapping))[0]
    else:
        var_name = new_var_name

    feat = feats.get(node.feats.get(f"{feature.capitalize()}[psor]") or node.feats.get(feature.capitalize()) or node.lemma, 'FILL')

    return var_name, f'refer-{feature}', feat


def possessives(node,
                var_node_mapping: dict,
                triples: list,
                variable_name: Callable,
                find_parent: Callable,
                role) -> tuple[list, dict, bool]:
    """
    Handle possessive constructions.
    1. Basic case: possessive adjectives
    2. Non-reflexive 3rd person (eius): TODO
    3. General possession: encoded by the deprel nmod:poss, not treated here. Otherwise undetectable, because lexical.
    """

    numbers = {'Sing': 'singular', 'Plur': 'plural'}
    called = False

    if node.feats['PronType'] != 'Prs':
        return triples, var_node_mapping, called

    called = True
    is_adj_noun = node.parent.upos in ['ADJ', 'NOUN', 'PROPN'] or [c for c in node.children if c.deprel == 'cop']
    is_reflexive = node.lemma == 'suus'
    parent, _ = find_parent(node.parent, var_node_mapping)

    base_type = 'person' if is_adj_noun else ('thing' if node.parent.upos == 'VERB' and node.feats['Gender'] == 'Neut' else 'FILL')
    var_name, var_node_mapping, triples = create_node(node,
                                                      variable_name,
                                                      var_node_mapping,
                                                      triples,
                                                      base_type,
                                                      replace=is_adj_noun,
                                                      reflex=is_reflexive)

    triples.append((parent, 'poss' if is_adj_noun else role, var_name))

    if is_reflexive:
        refer_number = numbers.get(node.feats['Number'] if not is_adj_noun else node.parent.parent.feats['Number'])
        triples.append((var_name, 'refer-number', refer_number))

    # attaching the possessive itself
    if node.parent.upos == 'VERB':
        poss_var_name, var_node_mapping, triples = create_node(node,
                                                               variable_name,
                                                               var_node_mapping,
                                                               triples,
                                                               'person',
                                                               replace=True,
                                                               reflex=is_reflexive)
        triples.append((var_name, 'poss', poss_var_name))
        if is_reflexive:
            triples.append((poss_var_name, 'refer-number', numbers.get(node.parent.feats['Number'])))

    return triples, var_node_mapping, called


def personal(node,
             var_node_mapping: dict,
             triples: list,
             variable_name: Callable,
             find_parent: Callable,
             role) -> tuple[list, dict, bool]:
    """ Handle personal pronouns. """

    # TODO: could probably be expanded to handle all pronouns.


    if node.feats['PronType'] == 'Prs':
        called = True

        var_name, var_node_mapping, triples = create_node(node,
                                                          variable_name,
                                                          var_node_mapping,
                                                          triples,
                                                          'person' if node.feats['Gender'] != 'Neut' else 'thing',
                                                          replace=True)
        parent, _ = find_parent(node.parent, var_node_mapping)
        triples.append((parent, role, var_name))

        return triples, var_node_mapping, called

    return triples, var_node_mapping, False


def quantifiers(node,
                var_node_mapping: dict,
                triples: list,
                variable_name: Callable,
                add_node: Callable,
                find_parent: Callable,
                role) -> tuple[list, dict, bool]:
    """ Handle quantifiers. """

    if node.feats['PronType'] != 'Tot':
        return triples, var_node_mapping, False

    cop_siblings = [s for s in node.siblings if s.deprel == 'cop']
    has_cop_sibling = len(cop_siblings) > 0
    called = False

    if node.deprel == 'det' and not has_cop_sibling:
        called = True
        add_node(node,
                 var_node_mapping,
                 triples,
                 role)

    elif node.deprel != 'det' or (node.deprel == 'det' and len(cop_siblings) == 1):
        called = True
        type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'FILL'
        var_name, var_node_mapping, triples = create_node(node,
                                                          variable_name,
                                                          var_node_mapping,
                                                          triples,
                                                          type_arg)

        parent, _ = find_parent(node.parent, var_node_mapping)
        triples.append((parent, role, var_name))
        var_node_mapping[var_name] = node

        # attaching the quantifier itself
        add_node(node,
                 var_node_mapping,
                 triples,
                 'quant',
                 def_parent=var_name)

    return triples, var_node_mapping, called


def det_pro_noun(node,
                 var_node_mapping: dict,
                 triples: list,
                 variable_name: Callable,
                 find_parent,
                 role) -> tuple[list, dict, bool]:
    """ Create an entity node that replaces the DETs (e.g. 'Illi negarunt' "They denied"). """

    if node.deprel in ['det', 'root'] or node.feats['PronType'] != 'Dem':
        return triples, var_node_mapping, False

    called = True
    type_arg = 'thing' if node.feats['Gender'] == 'Neut' else 'person'  # maybe FILL is better

    var_name, var_node_mapping, triples = create_node(node,
                                                      variable_name,
                                                      var_node_mapping,
                                                      triples,
                                                      type_arg,
                                                      replace=True)
    parent, _ = find_parent(node.parent, var_node_mapping)
    triples.append((parent, role, var_name))

    return triples, var_node_mapping, called


def coordination(node,
                 role: str,
                 var_node_mapping: dict,
                 triples: list,
                 already_added: set,
                 track_conj: dict,
                 extra_level: dict,
                 variable_name: Callable,
                 find_parent) -> tuple[list, set, dict, any]:
    """ Handle coordination by building the corresponding UMR structures. """

    conjs = {'or': ['vel', 'uel', 'aut'],
             'and': ['que', 'et', 'ac', 'atque', 'nec', 'neque', ','],
             'but-91': ['sed', 'at']}

    root_var = None

    # create one top node for the conjunction governing the coordination
    if node.parent not in track_conj:  # node.parent is the head conjunct
        # identify conjunction type (polysyndeton or asyndeton)
        cc = next((c for c in node.children if c.deprel == 'cc'), None)
        if cc is None:
            cc = next((c for c in node.children if c.deprel == 'punct' and c.lemma == ','), None)
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
        var_node_mapping = dict(reversed(var_node_mapping.items()))  # so that artificial nodes have precedence
        # have to handle abstract predicates - there's probably a smarter way to do this
        var_first_conj = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
        var_second_conj = next((k for k, v in var_node_mapping.items() if v == node), None)

        role = role
        parent, new_root = find_parent(node.parent.parent, var_node_mapping)
        for tup in triples:  # avoid clashes of abstract concepts and coordination
            if tup[2] == var_first_conj:
                if var_first_conj in extra_level and node.parent.deprel == 'root':
                    root_var = var_name_conj
                    break
                role, parent = tup[1], tup[0]
                break

        triples = [tup for tup in triples if not (tup[0] == parent and tup[1] == role)]
        triples.append((parent, role, var_name_conj))
        track_conj[node.parent] = var_name_conj

        # Attach first and second conjuncts to the conjunction node
        if var_first_conj not in extra_level:  # TODO fare un check a tappeto che non abbia sputtanato tutto
            triples = [tup for tup in triples if not (tup[2] == var_first_conj and tup[1] != 'instance')] # remove previous relation, if any
        arg_type = 'op' if cord != 'but-91' else 'ARG'

        for i, vc in enumerate([var_first_conj, var_second_conj], start=1):
            if not extra_level.get(vc, None):
                triples.append((var_name_conj, f'{arg_type}{i}', vc))
            else:
                triples.append((var_name_conj, f'{arg_type}{i}', extra_level[vc]))


        if (node.upos == 'NOUN' and role != 'other') or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj', 'obl']):
            triples.append(get_number_person(node, 'number', var_node_mapping))
        already_added.update({node, node.parent})

        # attach additional conjuncts, if any
        for num, oc in enumerate((s for s in node.siblings if s.deprel == 'conj' and s not in already_added), start=3):
            var_name = next((k for k, v in var_node_mapping.items() if v == oc), None)
            triples.append((var_name_conj, f'op{num}', var_name))
            triples.append(get_number_person(oc, 'number', var_node_mapping))
            already_added.add(oc)

        if new_root:
            root_var = var_name_conj

    return triples, already_added, var_node_mapping, root_var


def copulas(node,
            var_node_mapping: dict,
            extra_level: dict,
            triples: list,
            replace_with_abstract_roleset: Callable,
            copula: bool = True) -> tuple[list, dict, any]:
    """
    Handle copular constructions by assigning the correct abstract roleset to all configurations.
    If a set of relational terms is provided, it is used here to assign have-rel-role-92.
    """

    concept = None
    replace_arg = None

    if node.parent.feats['Case'] in ['Nom', 'Acc'] or (node.parent.upos in ['NOUN', 'ADJ', 'PROPN', 'PRON'] and not node.parent.feats['Case']):

        if node.parent.upos == 'ADJ' or (node.parent.upos == 'DET' and node.parent.feats['PronType'] != 'Prs'):  # TODO: double-check DET (anche ok 'tantus', ma hic sarebbe meglio identity...ma both Dem!!) + remove PRON and do smth with it
            concept = 'have-mod-91'
        elif node.parent.upos == 'DET' and node.parent.feats['PronType'] == 'Prs':
            concept= 'belong-91'
        elif node.parent.upos in ['NOUN', 'PRON']:
            if node.parent.upos == 'NOUN' and node.parent.lemma in interpersonal:
                concept = 'have-rel-role-92'
                replace_arg = 'ARG3'
            else:
                concept = 'identity-91'
        else:
            concept = 'MISSING'

    elif node.parent.feats['NumType'] == 'Card':
        concept = 'have-quant-91'

    elif node.parent.feats['Case'] == 'Dat':
        # double dative if ref_dative else dative of possession
        ref_dative = [s for s in node.siblings if s.feats['Case'] == 'Dat' and s.deprel == 'obl:arg']
        concept = 'have-purpose-91' if ref_dative else 'belong-91'

    elif node.parent.upos == 'VERB' and node.parent.feats['VerbForm'] == 'Inf':
        concept = 'have-identity-91'

    else:
        concept = 'MISSING'

    try:
        triples, var_node_mapping, root_var = replace_with_abstract_roleset(node,
                                                                            triples,
                                                                            var_node_mapping,
                                                                            extra_level,
                                                                            concept,
                                                                            replace_arg,
                                                                            overt=copula)
        return triples, var_node_mapping, root_var


    except (TypeError, AttributeError) as e:
        print(e)
        print(f"Skipping sentence due to missing copular configuration.")


def relative_clauses(node,
                     rel_pron,
                     var_node_mapping: dict,
                     triples: list,
                     role: str,
                     add_node: Callable) -> list:
    """
    Process relative clauses, by handling:
    1. relative pronoun (rel_pron);
    2. predicate (node);
    3. referent of the whole relative clause (referent).
    """

    referent = None

    if rel_pron == node.parent:
        referent = next((k for k, v in var_node_mapping.items() if v == rel_pron), None)
        if rel_pron.deprel == 'root':  # can't do anything about root-of, but I can at least save a root
            triples.append((None, 'root', referent))
    elif rel_pron.parent == node:
        referent = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
        if rel_pron.udeprel in ['nsubj', 'obj', 'obl']:
            var_pron = next((k for k, v in var_node_mapping.items() if v == rel_pron), None)
            triples = [tup for tup in triples if var_pron not in [tup[0], tup[2]]]  # remove rel_pron

    add_node(node,
             var_node_mapping,
             triples,
             role,
             invert=True,
             def_parent=referent)

    for i, tup in enumerate(triples):
        if tup[1] == 'root-of': # issues with head of relative being the root
            # look for other dependants
            if 'nsubj' in [d.deprel for d in node.children]:
                triples[i] = (tup[0], 'actor-of', tup[2])
            elif 'obj' in [d.deprel for d in node.children]:
                triples[i] = (tup[0], 'actor-of', tup[2])

    return triples


def adverbial_clauses(node,
                      role: str,
                      triples: list,
                      var_node_mapping: dict,
                      add_node: Callable):
    """
    Handle adverbial clauses.
    If a dictionary with disambiguated SCONJs is provided, it is used here to assign more fine-grained relations.
    """

    sconj = next((c for c in node.children if c.deprel == 'mark'), None)

    if sconj and sconj.lemma in advcl:
        constraint = advcl.get(sconj.lemma, {}).get('constraint')
        if constraint:
            feat, value = constraint.split('=')
            if sconj.parent.feats[feat] == value:
                role = advcl.get(sconj.lemma, {}).get('type')

    add_node(node,
             var_node_mapping,
             triples,
             role)