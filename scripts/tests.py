from penman import layout
from sklearn.metrics import accuracy_score

from preprocess import load_external_files

def coordination(predicted, gold, lang):
    """ Evaluates the accuracy of coordination relations. """
    conjunctions = load_external_files('conj.json', lang)
    for g_pred, g_gold in zip(predicted, gold):
        # print(g_pred.triples)
        coord_pred = [t for t in g_pred.instances() if t[2] in conjunctions] if conjunctions else \
            [t for t in g_pred.instances() if t[2] == 'and']
        coord_pred = [t for t in coord_pred if any('ARG' in c[1] for c in g_pred.edges(source=t[0])) or
                 any('op' in c[1] for c in g_pred.edges(source=t[0]))]
        coord_gold = [t for t in g_gold.instances() if t[2] in conjunctions] if conjunctions else\
            [t for t in g_gold.instances() if t[2] == 'and']
        coord_gold = [t for t in coord_gold if any('ARG' in c[1] for c in g_gold.edges(source=t[0])) or
                 any('op' in c[1] for c in g_gold.edges(source=t[0]))]

    # TODO: ASK HOWTO
    # 1. I wanted to check if the correct conjunction has been selected, but I can't just do 'if t_pred[2] == t_gold[2],
    # where both are 'and', because I could match two different and.
    # Possible solution: I constrained the 'and' on its dependents, i.e. the two conjs are the same only if they share
    # the dependent nodes. Issue: UMR freedom in lemmatizing concepts.
    # So, not doable! I can't check if the conjunction is correct.

    # 2. I wanted to check if all opX dependents have been retrieved. Again, same issues as above. Can't do it.

    # 3. About the nodes that have been attached as opX to the conjunction: are they supposed to be attached as
    # coordinated items? Again, not really doable due to the issues described above.

def abstract(predicted, gold):
    """
    Evaluates the accuracy of abstract predicates and their dependent ARGs, by checking:
    - if the abstract concept label has been correctly selected (e.g., have-mod-91 both in predicted and gold);
    - how many correct relations having the abstract predicate as parent have been retrieved;
    - if ARG relations are assigned to the correct nodes.
    """
    # TODO: it might be necessary to re-think this function radically.
    children_edges_score, children_edges_count = 0, 0
    predicate_gold, predicate_pred = [], []
    arg_score_gold, arg_score_pred = [], []

    for g_pred, g_gold in zip(predicted, gold):

        abstract_pred = [t for t in g_pred.instances() if t[2].endswith("-91") or t[2].endswith("-92")]
        abstract_gold = {t[0]: t[2] for t in g_gold.instances() if t[2].endswith(("-91", "-92"))}

        for t in abstract_pred:
            children_pred = g_pred.edges(source=t[0])
            children_gold = None
            abs_variable = None

            # Is the abstract predicate correct?
            if t[2] == abstract_gold[t[0]]:  # finds only matching predicates
                abs_variable = t[0]
                children_gold = children_pred
                predicate_gold.append(abstract_gold[t[0]])
                predicate_pred.append(t[2])
            else:
                # find first ARG among dependent nodes and check if its parent is a different abstract predicate
                # not perfect. TODO: think about how to retrieve more mistakes in assigning the abstract concept label.
                first_arg = next((c for c in children_pred if 'ARG' in c[1]), None)
                if first_arg:
                    matching_gold = next((g for g in g_gold.triples if first_arg[2] == g[2]), None)
                    if matching_gold:
                        abs_variable_gold = next(
                            (l for l in g_gold.instances() if l[0] == matching_gold[0] and l[2].endswith(("-91", "-92"))),
                            None)
                        if abs_variable_gold:
                            abs_variable = abs_variable_gold
                            children_gold = g_gold.edges(source=matching_gold[0])
                            predicate_gold.append(abs_variable[2])
                            predicate_pred.append(t[2])

            # How many correct relations having the abstract predicate as parent have been retrieved?
            if abs_variable:
                children_edges_count += len(children_gold)
                children_edges_score += sum(1 for x in children_pred if x in children_gold)

            # # Are ARGs assigned to the correct nodes?  # TODO: not sure it makes sense given UMR freedom in naming concepts.
            for a in [c for c in children_pred if 'ARG' in c[1]]:
                arg_score_gold.append(a[2])
                match = next((g for g in g_gold.edges(source=a[0]) if a[1] == g[1]), None)
                arg_score_pred.append(match[2] if match else None)

    return (f"{accuracy_score(predicate_gold, predicate_pred):.2f}" if predicate_gold else "-",
            f"{children_edges_score / children_edges_count:.2f}" if children_edges_count else "-",
            f"{accuracy_score(arg_score_gold, arg_score_pred):.2f}" if arg_score_gold else "-")

def modal_strength(predicted, gold):
    """ Evaluates the accuracy for both the strength and polarity components of `modal-strength` attributes. """
    strength_gold, strength_pred, polarity_gold, polarity_pred = [], [], [], []

    for g_pred, g_gold in zip(predicted, gold):
        modals_pred = [t for t in g_pred.attributes(role=":modal-strength") if t[2] != 'MS']
        modals_gold = {t[0]: t[2].split('-') for t in g_gold.attributes(role=":modal-strength")}

        for m in modals_pred:
            strength, polarity = m[2].split('-')
            mg_strength, mg_polarity = modals_gold.get(m[0], (None, None))

            if mg_strength is not None:
                strength_gold.append(mg_strength)
                strength_pred.append(strength)
                polarity_gold.append(mg_polarity)
                polarity_pred.append(polarity)

    return (f"{accuracy_score(strength_gold, strength_pred):.2f}" if strength_gold else "-",
            f"{accuracy_score(polarity_gold, polarity_pred):.2f}" if polarity_gold else "-")


def pronouns(predicted, gold):
    """ Evaluates the accuracy of `refer-number` and `refer-person` annotations for entity nodes (`person`/`thing`). """
    number_gold, number_pred, person_gold, person_pred = [], [], [], []

    for g_pred, g_gold in zip(predicted, gold):
        number_pred_instances = g_pred.attributes(role=":refer-number")
        person_pred_instances = g_pred.attributes(role=":refer-person")

        number_gold_dict = {t[0]: t[2] for t in g_gold.attributes(role=":refer-number")}
        person_gold_dict = {t[0]: t[2] for t in g_gold.attributes(role=":refer-person")}

        instances = {t[0]: t[2] for t in g_pred.instances() if t[2] in {"person", "thing"}}

        # `:refer-number`
        for pr in number_pred_instances:
            if pr[0] in instances:
                number_pred.append(pr[2])
                number_gold.append(number_gold_dict[pr[0]])

        # `:refer-person`
        for pr in person_pred_instances:
            if pr[0] in instances:
                person_pred.append(pr[2])
                person_gold.append(person_gold_dict[pr[0]])

    return (f"{accuracy_score(number_gold, number_pred):.2f}" if number_gold else "-",
            f"{accuracy_score(person_gold, person_pred):.2f}" if person_gold else "-")


def inverted_relations(predicted, gold):
    """ Evaluates the accuracy of inverted relations in the predicted UMR graphs. """
    parent_pred, parent_gold, edge_pred, edge_gold = [], [], [], []

    for g_pred, g_gold in zip(predicted, gold):
        inverted_pred = [t for t in g_pred.triples if layout.appears_inverted(g_pred, t)]
        edge_gold_dict, parent_gold_dict = {}, {}
        for t in g_gold.triples:
            if layout.appears_inverted(g_gold, t):
                child = t[2]
                parent_gold_dict[child] = t[0]
                edge_gold_dict[child] = t[1]

        for t in inverted_pred:
            child = t[2]
            # Is the parent correct, i.e. the same as in the gold triple with the same child?
            if child in parent_gold_dict:
                parent_gold.append(parent_gold_dict[child])
                parent_pred.append(t[0])
            # Is the inverted edge correct, i.e. the same as in the gold triple with the same child?
            if child in edge_gold_dict:
                edge_gold.append(edge_gold_dict[child])
                edge_pred.append(t[1])

    return (f"{accuracy_score(parent_gold, parent_pred):.2f}" if parent_gold else "-",
            f"{accuracy_score(edge_gold, edge_pred):.2f}" if edge_gold else "-")