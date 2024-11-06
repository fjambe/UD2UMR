import re
from penman.models.amr import model as pm
import language_info as l


def variable_name(node,
                  var_node_mapping: dict) -> tuple[str, dict]:
    """
    Function that assigns variable names according to UMR conventions.
    Either the first letter of the string or, if already assigned, letter + progressive numbering.
    """
    first_letter = node.lemma[0].lower() if not isinstance(node, str) else node[0].lower()
    count = 2

    if first_letter in var_node_mapping:
        while f"{first_letter}{count}" in var_node_mapping:
            count += 1

    var_name = first_letter if first_letter not in var_node_mapping else f"{first_letter}{count}"
    var_node_mapping[var_name] = node

    return var_name, var_node_mapping


def correct_variable_naming(triples: list,
                            var_node_mapping: dict) -> tuple[list, dict]:

    """ Function that returns a list of triples with corrected variable naming, if necessary. """

    var_pattern = re.compile(r"^([a-z])(\d*)$")
    var_groups = {}

    for var in var_node_mapping.keys():
        match = var_pattern.match(var)
        if match:
            base_letter = match.group(1)
            number = int(match.group(2)) if match.group(2) else 1
            var_groups.setdefault(base_letter, []).append((number, var))

    renaming_map = {}

    for base_letter, variables in var_groups.items():
        variables.sort()

        for new_number, (current_number, var) in enumerate(variables, start=1):
            new_var = f"{base_letter}{new_number if new_number > 1 else ''}"

            if new_var != var:
                renaming_map[var] = new_var
                var_node_mapping[new_var] = var_node_mapping.pop(var)

    corrected_triples = [
        (renaming_map.get(var, var), relation, renaming_map.get(value, value))
        for var, relation, value in triples
    ]

    return corrected_triples, var_node_mapping


def add_node(node,
             var_node_mapping: dict,
             triples: list,
             role,
             return_var_name: bool = False,
             invert: bool = False,
             def_parent=None):
    """
    Function that creates and adds a new node. Steps:
    1. Associate the node lemma and its var_name, as it will be in the UMR graph
    2. If the node is the root, its variable name is returned
    3. Link the var_name to its parent node via their relation (called 'role'), if the node is not the root
    """

    var_name = next((k for k, v in var_node_mapping.items() if v == node), None)

    if return_var_name:
        return var_name

    parent = def_parent or find_parent(node.parent, var_node_mapping)[0]

    if not invert:
        triples.append((parent, role, var_name))
    else:
        var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
        triples.append(pm.invert((var_name, role, def_parent)))


def introduce_abstract_roleset(node,
                     triples: list,
                     var_node_mapping: dict,
                     role_aka_concept: any) -> tuple[list, dict]:

    # TODO: it should also work for reification in general, so it could be renamed. Decide later.
    # double check also that role inversion can be generalized.

    var_name = next((k for k, v in var_node_mapping.items() if v == node), None)
    var_parent = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
    triples = [tup for tup in triples if tup[1] != role_aka_concept]
    var_concept, var_node_mapping = variable_name(role_aka_concept, var_node_mapping)
    triples.extend([
        (var_concept, 'instance', role_aka_concept),
        (var_concept, 'ARG2', var_name),
        (var_concept, 'aspect', 'state'),
        pm.invert((var_concept, 'ARG1', var_parent))
    ])

    return triples, var_node_mapping


def replace_with_abstract_roleset(node,
                                  triples: list,
                                  var_node_mapping: dict,
                                  extra_level: dict,
                                  role_aka_concept: any,
                                  replace_arg=None,
                                  overt=True) -> tuple[list, dict, any]:

        # TODO: Figure out whether it can be merged with introduce_abstract_roleset().

        second_arg = 'ARG2' if not replace_arg else replace_arg
        root_var = None

        var_parent = next((k for k, v in var_node_mapping.items() if v == node.parent), None)
        var_sum = next((k for k, v in var_node_mapping.items() if v == node), None) if overt else None
        triples = [tup for tup in triples if var_sum not in tup]

        var_concept, var_node_mapping = variable_name(role_aka_concept, var_node_mapping)
        triples.append((var_concept, 'instance', role_aka_concept))

        nsubj = next((d for d in node.siblings if d.deprel == 'nsubj'), None)
        if overt:
            var_nsubj = next((k for k, v in var_node_mapping.items() if v == nsubj), None)
        else:
            var_nsubj = next((k for k, v in var_node_mapping.items() if v == node), None)

        extra_level[var_nsubj] = var_concept
        extra_level[var_parent] = var_concept

        for i, tup in enumerate(triples):
            # reassigning root, if relevant
            if tup[2] == var_parent and tup[1] == 'root':
                root_var = var_concept
                triples[i] = (tup[0], tup[1], var_concept)
            if tup[2] == var_parent and tup[1] == 'ARG2':
                triples[i] = (tup[0], tup[1], var_concept)
            # reassigning nsubj (previously actor)
            elif tup[2] == var_nsubj and tup[1] == 'actor':
                triples[i] = (var_concept, 'ARG1', tup[2])

        if var_nsubj not in [t[2] for t in triples]:
            triples.append((var_concept, 'ARG1', var_nsubj))

        triples = [tup for tup in triples if tup[2] != var_parent]  # remove old role
        triples.extend([
            (var_concept, second_arg, var_parent),
            (var_concept, 'aspect', 'state')
        ])

        # reattach non-core (+ obl:arg) dependents of UD root to UMR abstract predicate
        for n in node.siblings:
            if n.udeprel in ['vocative', 'obl', 'advmod', 'discourse', 'advmod']:
                var_n = next((k for k, v in var_node_mapping.items() if v == n), None)
                if var_n:
                    triples = [(var_concept, tup[1], tup[2]) if tup[2] == var_n else tup for tup in triples]

        # elided subjects to be restored
        if overt and nsubj is None and node.parent.deprel != 'root':  # root check is a bit random
            arg_type = 'person' if node.feats['Person'] in ['1', '2'] else 'FILL'
            var_name, var_node_mapping, triples = l.create_node(node,
                                                                variable_name,
                                                                var_node_mapping,
                                                                triples,
                                                                arg_type)
            triples.append((var_concept, 'ARG1', var_name))

        return triples, var_node_mapping, root_var


def find_parent(node_parent,
                var_node_mapping: dict) -> tuple[any, bool]:

    if node_parent.is_root():
        return None, True

    parent = next((k for k, v in var_node_mapping.items() if v == node_parent), None)

    return parent, False


def ud_to_umr(node,
              role: str,
              var_node_mapping: dict,
              extra_level: dict,
              triples: list,
              already_added: set,
              track_conj: dict,
              relations: dict) -> tuple[list, any, dict]:

    """Function that maps UD information to UMR structures."""

    root_var = None

    if node.deprel == 'root':
        add_node(node,
                 var_node_mapping,
                 triples,
                 role)

        already_added.add(node)

    ### checking UPOS ###
    if node.upos == 'PRON':
        triples, var_node_mapping, called_pron = l.personal(node,
                                                             var_node_mapping,
                                                             triples,
                                                             variable_name,
                                                             find_parent,
                                                             role)

        # TODO: do something with non-personal pronouns, here.

        if called_pron:
            already_added.add(node)

    elif (node.upos == 'NOUN' and role != 'other') or (node.upos == 'ADJ' and node.deprel in ['nsubj', 'obj', 'obl']):
        add_node(node,
                 var_node_mapping,
                 triples,
                 role)
        triples.append(l.get_number_person(node, 'number', var_node_mapping))
        already_added.add(node)

    elif node.upos == 'DET':
        # check for PronType=Prs is inside the function
        triples, var_node_mapping, called_possessives = l.possessives(node,
                                                                      var_node_mapping,
                                                                      triples,
                                                                      variable_name,
                                                                      find_parent,
                                                                      role)
        # now check for quantifiers (PronType=Tot)
        triples, var_node_mapping, called_quantifiers = l.quantifiers(node,
                                                                      var_node_mapping,
                                                                      triples,
                                                                      variable_name,
                                                                      add_node,
                                                                      find_parent,
                                                                      role if role != 'det' else 'quant')

        # check if they substitute for nouns
        triples, var_node_mapping, called_det_pro_noun = l.det_pro_noun(node,
                                                                        var_node_mapping,
                                                                        triples,
                                                                        variable_name,
                                                                        find_parent,
                                                                        role)

        if called_possessives or called_quantifiers or called_det_pro_noun:
            already_added.add(node)

        elif node.deprel == 'det':
            add_node(node,
                     var_node_mapping,
                     triples,
                     'mod')
            already_added.add(node)

    elif node.upos == 'VERB':
        # elided subjects to be restored
        if 'nsubj' not in [d.udeprel for d in node.children] and node.parent.deprel != 'root':  # root check is a bit random
            if node.feats['Voice'] != 'Pass':
                arg_type = 'person' if node.feats['Person'] in ['1', '2'] else 'FILL'
                var_name, var_node_mapping, triples = l.create_node(node,
                                                                    variable_name,
                                                                    var_node_mapping,
                                                                    triples,
                                                                    arg_type)
                parent, _ = find_parent(node, var_node_mapping)
                triples.append((parent, 'actor', var_name))

    ### checking deprel ###
    if node.deprel == 'conj':
        role = next((k for k, v in relations.items() for item in v if item == node.parent), None)
        triples, already_added, var_node_mapping, root_var = l.coordination(node,
                                                                            role,
                                                                            var_node_mapping,
                                                                            triples,
                                                                            already_added,
                                                                            track_conj,
                                                                            extra_level,
                                                                            variable_name,
                                                                            find_parent)

    elif node.deprel == 'appos':
        triples, var_node_mapping = introduce_abstract_roleset(node,
                                                               triples,
                                                               var_node_mapping,
                                                               role)
        already_added.add(node)

    elif node.deprel == 'cop':
        triples, var_node_mapping, root_var = l.copulas(node,
                                                        var_node_mapping,
                                                        extra_level,
                                                        triples,
                                                        replace_with_abstract_roleset)
        already_added.add(node)

    # copular constructions with no overt copula
    elif node.deprel == 'nsubj' and node.parent.upos != 'VERB' and not [d for d in node.siblings if d.deprel == 'cop']:
        triples, var_node_mapping, root_var = l.copulas(node,
                                                        var_node_mapping,
                                                        extra_level,
                                                        triples,
                                                        replace_with_abstract_roleset,
                                                        copula=False)
        already_added.add(node)

    elif node.deprel == 'acl:relcl':
        rel_pron = next((d for d in node.descendants if d.feats.get('PronType') == 'Rel'), None)
        if not rel_pron:
            rel_pron = node.parent if node.parent.feats.get('PronType') == 'Rel' else None
        role = next((k for k, v in relations.items() if rel_pron in v), None)

        triples = l.relative_clauses(node,
                                     rel_pron,
                                     var_node_mapping,
                                     triples,
                                     role,
                                     add_node)
        already_added.add(node)
        already_added.add(rel_pron)

    if node not in already_added:
        add_node(node,
                 var_node_mapping,
                 triples,
                 role)
        already_added.add(node)

    return triples, root_var, var_node_mapping