from penman import layout
from sklearn.metrics import accuracy_score

from preprocess import load_external_files


def coordination(predicted, gold, lang):
    """ Evaluates the accuracy of coordination relations. """
    conjunctions = load_external_files('conj.json', lang)
    for t_graph, g_graph in zip(predicted, gold):
        t_coord = [t for t in t_graph.penman_graph[0].instances() if t[2] in conjunctions] if conjunctions else \
            [t for t in t_graph.penman_graph[0].instances() if t[2] == 'and']

        g_coord = [t for t in g_graph.penman_graph[0].instances() if t[2] in conjunctions] if conjunctions else\
            [t for t in g_graph.penman_graph[0].instances() if t[2] == 'and']

        pass


def abstract(predicted, gold):
    """
    Evaluates the accuracy of abstract predicates and their dependent ARGs, by checking:
    - if the abstract concept label has been correctly selected (e.g., have-mod-91 both in predicted and gold);
    - how many correct relations having the abstract predicate as parent have been retrieved;
    - if ARG relations are assigned to the correct nodes.
    """
    t_children_edges_count, g_children_edges_count = 0, 0
    predicate_gold, predicate_pred = [], []
    args_pred, args_gold = [], []

    for t_graph, g_graph in zip(predicted, gold):

        t_abstract = {t[0]: t[2] for t in t_graph.penman_graph[0].instances() if t[2].endswith(("-91", "-92"))}
        g_abstract = {t[0]: t[2] for t in g_graph.penman_graph[0].instances() if t[2].endswith(("-91", "-92"))}

        for ab in t_abstract:

            # Is the abstract predicate correct?
            gold = t_graph.matched_alignment.get(ab, None)

            predicate_pred.append(t_abstract[ab])
            predicate_gold.append(g_abstract[gold])

            # How many correct relations having the abstract predicate as parent have been retrieved?
            children_pred = t_graph.penman_graph[0].edges(source=ab)
            children_gold = g_graph.penman_graph[0].edges(source=gold)

            t_children_edges_count += len(children_pred)
            g_children_edges_count += len(children_gold)

            # # Are ARGs assigned to the correct nodes?
            for a in [c for c in children_pred if 'ARG' in c[1]]:
                args_pred.append(a[1])
                for c in children_gold:
                    print('c', c)
                    if 'ARG' in c[1]:
                        if c[2] == t_graph.matched_alignment.get(a[2], None):
                            args_gold.append(c[1])
                            children_gold.remove(c)
                        else:
                            args_pred.append('')
                            args_gold.append(c[1])

            print(args_pred, args_gold)

    return (f"{accuracy_score(predicate_gold, predicate_pred):.2f}" if predicate_gold else "-",
            f"{t_children_edges_count / g_children_edges_count:.2f}" if g_children_edges_count else "-",
            f"{accuracy_score(args_gold, args_pred):.2f}" if args_gold else "-")

def modal_strength(predicted, gold):
    """ Evaluates the accuracy for both the strength and polarity components of `modal-strength` attributes. """
    strength_gold, strength_pred, polarity_gold, polarity_pred = [], [], [], []

    for t_graph, g_graph in zip(predicted, gold):
        t_modals = [t for t in t_graph.penman_graph[0].attributes(role=":modal-strength") if t[2] != 'MS']
        g_modals = {t[0]: t[2].split('-') for t in g_graph.penman_graph[0].attributes(role=":modal-strength")}

        for m in t_modals:
            t_strength, t_polarity = m[2].split('-')
            g_node = t_graph.matched_alignment.get(m[0], None)
            g_strength, g_polarity = g_modals.get(g_node, ('', ''))

            # TODO: figure out how to compute scores.
            #  (g_strength is None) means that the predicted strength should not be there.
            strength_gold.append(g_strength)
            strength_pred.append(t_strength)
            polarity_gold.append(g_polarity)
            polarity_pred.append(t_polarity)

    return (f"{accuracy_score(strength_gold, strength_pred):.2f}" if strength_gold else "-",
            f"{accuracy_score(polarity_gold, polarity_pred):.2f}" if polarity_gold else "-")


def pronouns(predicted, gold):
    """ Evaluates the accuracy of `refer-number` and `refer-person` annotations for entity nodes (`person`/`thing`). """
    number_gold, number_pred, person_gold, person_pred = [], [], [], []

    for t_graph, g_graph in zip(predicted, gold):

        t_number_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-number")}
        t_person_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-person")}

        g_number_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-number")}
        g_person_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-person")}

        t_instances = {t[0]: t[2] for t in t_graph.penman_graph[0].instances() if t[2] in {"person", "thing"}}

        # `:refer-number`
        for tnum in t_number_dict:
            if tnum in t_instances:
                number_pred.append(t_number_dict[tnum])
                gold = t_graph.matched_alignment.get(tnum, None)
                number_gold.append(g_number_dict[gold])

        # `:refer-person`
        for tper in t_person_dict:
            if tper in t_instances:
                person_pred.append(t_person_dict[tper])
                gold = t_graph.matched_alignment.get(tper, None)
                person_gold.append(g_person_dict[gold])

    return (f"{accuracy_score(number_gold, number_pred):.2f}" if number_gold else "-",
            f"{accuracy_score(person_gold, person_pred):.2f}" if person_gold else "-")


def inverted_relations(predicted, gold):
    """ Evaluates the accuracy of inverted relations in the predicted UMR graphs. """
    parent_pred, parent_gold, edge_pred, edge_gold = [], [], [], []

    for t_graph, g_graph in zip(predicted, gold):
        inverted_pred = [t for t in t_graph.penman_graph[0].triples if layout.appears_inverted(t_graph.penman_graph[0], t)]
        edge_gold_dict, parent_gold_dict = {}, {}
        for t in g_graph.penman_graph[0].triples:
            if layout.appears_inverted(g_graph.penman_graph[0], t):
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