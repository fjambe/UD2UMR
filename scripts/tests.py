from penman import layout
from sklearn.metrics import accuracy_score

def coordination(predicted, gold):
    print("Coordination: %")

def abstract(predicted, gold):
    """ Evaluates the precision of abstract predicates and their dependent ARGs. """  # TODO: improve
    predicate_score, predicate_count = 0, 0
    children_edges_score, children_edges_count = 0, 0
    arg_score, arg_count = 0, 0

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
                predicate_count += 1
                predicate_score += 1
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
                            predicate_count += 1

            # How many relations having the abstract predicate as parent have been retrieved?
            if abs_variable:
                children_edges_count += len(children_gold)
                children_edges_score += sum(1 for x in children_pred if x in children_gold)

            # Are ARGs assigned to the correct nodes?  # TODO: not sure it makes sense given UMR freedom in naming concepts.
            for a in [c for c in children_pred if 'ARG' in c[1]]:
                arg_count += 1
                arg_score += (next((g for g in g_gold.edges(source=a[0]) if a[1] == g[1] and a[2] == g[2]), None) is not None)

    return (f"{predicate_score / predicate_count:.2f}" if predicate_count else "-",
            f"{children_edges_score / children_edges_count:.2f}" if children_edges_count else "-",
            f"{arg_score / arg_count:.2f}" if arg_count else "-")

def modal_strength(predicted, gold):
    """ Evaluates the precision for both the strength and polarity components of `modal-strength` attributes. """
    strength_score, polarity_score, count = 0, 0, 0

    for g_pred, g_gold in zip(predicted, gold):
        modals_pred = [t for t in g_pred.attributes(role=":modal-strength") if t[2] != 'MS']
        modals_gold = {t[0]: t[2].split('-') for t in g_gold.attributes(role=":modal-strength")}

        for m in modals_pred:
            count += 1
            strength, polarity = m[2].split('-')
            mg_strength, mg_polarity = modals_gold.get(m[0], (None, None))
            if mg_strength is not None:
                if strength == mg_strength:
                    strength_score += 1
                if polarity == mg_polarity:
                    polarity_score += 1

    return (f"{strength_score / count:.2f}" if count else "-",
            f"{polarity_score / count:.2f}" if count else "-")

# def modal_strength(predicted, gold):
#     """ Evaluates the precision for both the strength and polarity components of `modal-strength` attributes. """
#     strength_gold, strength_pred, polarity_gold, polarity_pred = [], [], [], []
#
#     for g_pred, g_gold in zip(predicted, gold):
#         modals_pred = [t for t in g_pred.attributes(role=":modal-strength") if t[2] != 'MS']
#         modals_gold = {t[0]: t[2].split('-') for t in g_gold.attributes(role=":modal-strength")}
#
#         for m in modals_pred:
#             strength, polarity = m[2].split('-')
#             mg_strength, mg_polarity = modals_gold.get(m[0], (None, None))
#
#             if mg_strength is not None:
#                 strength_gold.append(mg_strength)
#                 strength_pred.append(strength)
#                 polarity_gold.append(mg_polarity)
#                 polarity_pred.append(polarity)
#
#     strength_precision = accuracy_score(strength_gold, strength_pred)
#     polarity_precision = accuracy_score(polarity_gold, polarity_pred)
#
#     return (f"{strength_precision:.2f}" if strength_pred else "-",
#             f"{polarity_precision:.2f}" if polarity_pred else "-")


# def pronouns(predicted, gold):
#     """ Evaluates the precision of `refer-number` and `refer-person` annotations for entity nodes (`person`/`thing`). """
#     number_score, person_score, count_number, count_person = 0, 0, 0, 0
#
#     for g_pred, g_gold in zip(predicted, gold):
#         number_pred = g_pred.attributes(role=":refer-number")
#         person_pred = g_pred.attributes(role=":refer-person")
#
#         number_gold = {t[0]: t[2] for t in g_gold.attributes(role=":refer-number")}
#         person_gold = {t[0]: t[2] for t in g_gold.attributes(role=":refer-person")}
#
#         instances = {t[0]: t[2] for t in g_pred.instances() if t[2] in {"person", "thing"}}
#
#         def calculate_precision(pred_attr, gold_dict, count, score):
#             """ Function to handle precision calculation for both refer-number and refer-person. """
#             for r_pred in pred_attr:
#                 if r_pred[0] in instances:
#                     count += 1
#                     if r_pred[0] in gold_dict and gold_dict[r_pred[0]] == r_pred[2]:
#                         score += 1
#             return count, score
#
#         count_number, number_score = calculate_precision(number_pred, number_gold, count_number, number_score)
#         count_person, person_score = calculate_precision(person_pred, person_gold, count_person, person_score)
#
#     return (f"{number_score / count_number:.2f}" if count_number else "-",
#             f"{person_score / count_person:.2f}" if count_person else "-")


def pronouns(predicted, gold):
    """ Evaluates the precision of `refer-number` and `refer-person` annotations for entity nodes (`person`/`thing`). """
    number_true, number_pred, person_true, person_pred = [], [], [], []

    for g_pred, g_gold in zip(predicted, gold):
        # Fetch refer-number and refer-person attributes
        number_pred_attr = g_pred.attributes(role=":refer-number")
        person_pred_attr = g_pred.attributes(role=":refer-person")

        number_gold_dict = {t[0]: t[2] for t in g_gold.attributes(role=":refer-number")}
        person_gold_dict = {t[0]: t[2] for t in g_gold.attributes(role=":refer-person")}

        # Identify instances of person and thing
        instances = {t[0]: t[2] for t in g_pred.instances() if t[2] in {"person", "thing"}}

        # Collect true and predicted values for precision calculation
        for r_pred in number_pred_attr:
            if r_pred[0] in instances:
                number_true.append(number_gold_dict.get(r_pred[0], None) == r_pred[2])
                number_pred.append(True)

        for r_pred in person_pred_attr:
            if r_pred[0] in instances:
                person_true.append(person_gold_dict.get(r_pred[0], None) == r_pred[2])
                person_pred.append(True)

    # Calculate precision using sklearn's precision_score
    number_precision = precision_score(number_true, number_pred, zero_division=0)
    person_precision = precision_score(person_true, person_pred, zero_division=0)

    return (f"{number_precision:.2f}" if number_pred else "-",
            f"{person_precision:.2f}" if person_pred else "-")


# def inverted_relations(predicted, gold):
#     """ Evaluates the precision of inverted relations in the predicted UMR graphs. """
#     parent_score, parent_count, edge_score, edge_count = 0, 0, 0, 0
#
#     for g_pred, g_gold in zip(predicted, gold):
#         inverted_pred = [t for t in g_pred.triples if layout.appears_inverted(g_pred, t)]
#         edge_gold, parent_gold = {}, {}
#         for t in g_gold.triples:
#             if layout.appears_inverted(g_gold, t):
#                 child = t[2]
#                 parent_gold[child] = t[0]
#                 edge_gold[child] = t[1]
#
#         for t in inverted_pred:
#             child = t[2]
#             # Is the parent correct, i.e. the same as in the gold triple with the same child?
#             if child in parent_gold:
#                 parent_count += 1
#                 parent_score += (parent_gold[child] == t[0])
#             # Is the inverted edge correct, i.e. the same as in the gold triple with the same child?
#             if child in edge_gold:
#                 edge_count += 1
#                 edge_score += (edge_gold[child] == t[1])
#
#     return ((f"{parent_score / parent_count:.2f}" if parent_count else "-"),
#             (f"{edge_score / edge_count:.2f}" if edge_count else "-"))


def inverted_relations(predicted, gold):
    """Evaluates the precision of inverted relations in the predicted UMR graphs."""
    parent_true, parent_pred, edge_true, edge_pred = [], [], [], []

    for g_pred, g_gold in zip(predicted, gold):
        # Collect inverted triples for the predicted and gold data
        inverted_pred = [t for t in g_pred.triples if layout.appears_inverted(g_pred, t)]

        # Create dictionaries for the gold data (parent and edge mappings)
        edge_gold = {t[2]: t[1] for t in g_gold.triples if layout.appears_inverted(g_gold, t)}
        parent_gold = {t[2]: t[0] for t in g_gold.triples if layout.appears_inverted(g_gold, t)}

        # For each predicted inverted triple, check against the gold data
        for t in inverted_pred:
            child = t[2]

            # Checking for parent correctness (same child and matching parent)
            if child in parent_gold:
                parent_true.append(True)
                parent_pred.append(parent_gold[child] == t[0])

            # Checking for edge correctness (same child and matching edge)
            if child in edge_gold:
                edge_true.append(True)
                edge_pred.append(edge_gold[child] == t[1])

    parent_precision = precision_score(parent_true, parent_pred, zero_division=0)
    edge_precision = precision_score(edge_true, edge_pred, zero_division=0)

    return (f"{parent_precision:.2f}" if parent_pred else "-",
            f"{edge_precision:.2f}" if edge_pred else "-")
