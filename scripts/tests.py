from penman import layout
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

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


def into_binary_labels(predictions, golds):
    # True labels: 1 if correct, 0 if incorrect
    y_true = [1] * len(golds)  # Every gold label must be predicted
    y_pred = [1 if pred == golds[i] else 0 for i, pred in enumerate(predictions)]
    return y_true, y_pred


def pad_predictions(pred, gold, original, removal, dictio=False):
    """ Pad predictions with a placeholder ("NULL") if some gold labels were not predicted. """
    remaining = {g: v for g, v in original.items() if g not in removal} if dictio else\
        [x for x in original if x not in removal]
    pred.extend(['NULL'] * (len(remaining)))
    gold.extend([v for v in remaining.values()] if dictio else [r[2] for r in remaining])
    assert len(pred) == len(gold)


def abstract(predicted, gold):
    """
    Evaluates the accuracy of abstract predicates and their dependent ARGs, by checking:
    - if the abstract concept label has been correctly selected (e.g., have-mod-91 both in predicted and gold);
    - how many correct relations having the abstract predicate as parent have been retrieved;
    - if ARG relations are assigned to the correct nodes.
    """
    predicate_pred, predicate_gold = [], []
    children_list_pred, children_list_gold = [], []
    args_pred, args_gold = [], []

    def compare_sorted_lists(list1, list2):
        """ Compares two lists of graph tuples by their second element (edge). """
        sorted_list1 = sorted(list1)
        sorted_list2 = sorted(list2)

        i, j = 0, 0  # Pointers for both lists

        while i < len(sorted_list1) and j < len(sorted_list2):
            tr_p, tr_g = sorted_list1[i], sorted_list2[j]

            if tr_p[1] == tr_g[1]:  # edges
                args_pred.append(tr_p[2])
                corresponding_child = t_graph.matched_alignment.get(tr_g[2], 'NULL')
                args_gold.append(corresponding_child)
                i += 1
                j += 1  # Move both pointers
            elif tr_p[1] < tr_g[1]:  # `edge_p` comes first, so it's missing from `list2`
                i += 1  # Move pointer for `list1`
            else:  # `edge_g` comes first, so it's missing from `list1`
                j += 1  # Move pointer for `list2`

        # Handle any remaining elements
        while i < len(sorted_list1):  # sorted_list1[i][1] has no match
            args_pred.append(sorted_list1[i][2])
            args_gold.append('NULL')
            i += 1
        while j < len(sorted_list2):  # sorted_list2[j][1] has no match
            args_pred.append('NULL')
            args_gold.append(sorted_list2[j][2])
            j += 1

        assert len(args_gold) == len(args_pred)

    for t_graph, g_graph in zip(predicted, gold):

        t_abstract = {t[0]: t[2] for t in t_graph.penman_graph[0].instances() if t[2].endswith(("-91", "-92")) and t[2] != 'but-91'}
        g_abstract = {t[0]: t[2] for t in g_graph.penman_graph[0].instances() if t[2].endswith(("-91", "-92")) and t[2] != 'but-91'}

        to_remove_predicate_g = set()

        # Test 1: Is the abstract predicate correct?
        for ab in t_abstract:
            gold = t_graph.matched_alignment.get(ab, '')  # corresponding (i.e. aligned) abstract predicate

            predicate_pred.append(t_abstract.get(ab))
            predicate_gold.append(g_abstract.get(gold, 'NULL'))
            to_remove_predicate_g.add(gold)

        pad_predictions(predicate_pred, predicate_gold, g_abstract, to_remove_predicate_g, dictio=True)

        # Test 2 and 3
        for ab in t_abstract:
            children_pred = t_graph.penman_graph[0].edges(source=ab)
            children_gold = g_graph.penman_graph[0].edges(source=gold)

            # Test 2: How many of the abstract predicate's dependents have been correctly retrieved (UAS)?
            to_remove_children_g = set()

            for triple_p in children_pred[:]:  # Iterate over a copy to avoid modification issues
                cp = triple_p[2]
                cg = t_graph.matched_alignment.get(cp, '')

                for triple_g in children_gold:
                    if triple_g in to_remove_children_g:  # Skip already matched gold elements
                        continue

                    if cg == triple_g[2]:
                        children_list_pred.append(cp)
                        children_list_gold.append(cp)
                        to_remove_children_g.add(triple_g)
                        break

                else:  # Runs only if no match was found (loop completed without`break`)
                    children_list_pred.append(cp)
                    children_list_gold.append('NULL')

            pad_predictions(children_list_pred, children_list_gold, children_gold, to_remove_children_g)

            # Test 3: Are correct ARGs assigned to the correct nodes?
            compare_sorted_lists([c for c in children_pred if 'ARG' in c[1]], [c for c in children_gold if 'ARG' in c[1]])

    y_true, y_pred = into_binary_labels(predicate_pred, predicate_gold)
    predicate_prec, predicate_recall, predicate_f1, _ = precision_recall_fscore_support(y_true, y_pred, zero_division=0, average="macro")
    # y_true, y_pred = into_binary_labels(children_list_pred, children_list_gold)
    # children_prec, children_recall, children_f1, _ = precision_recall_fscore_support(y_true, y_pred, zero_division=0, average="macro")
    children_prec, children_recall, children_f1, _ = precision_recall_fscore_support(children_list_gold, children_list_pred, zero_division=0, average="macro")
    # TODO: very different results with and without conversion to binary format. Figure out why and which one is correct.
    args_prec, args_recall, args_f1, _ = precision_recall_fscore_support(args_gold, args_pred, zero_division=0, average="macro")

    return (f"{predicate_prec:.2f}", f"{predicate_recall:.2f}", f"{predicate_f1:.2f}",
            f"{children_prec:.2f}", f"{children_recall:.2f}", f"{children_f1:.2f}",
            f"{args_prec:.2f}", f"{args_recall:.2f}", f"{args_f1:.2f}")


def modal_strength(predicted, gold):
    """ Evaluates the accuracy for both the strength and polarity components of `modal-strength` attributes. """
    strength_gold, strength_pred, polarity_gold, polarity_pred = [], [], [], []

    for t_graph, g_graph in zip(predicted, gold):
        t_modals = [t for t in t_graph.penman_graph[0].attributes(role=":modal-strength") if t[2] != 'MS']
        g_modals = {t[0]: t[2].split('-') for t in g_graph.penman_graph[0].attributes(role=":modal-strength")}

        for m in t_modals:
            t_strength, t_polarity = m[2].split('-')
            g_node = t_graph.matched_alignment.get(m[0], None)  # gold var aligned to pred var
            if t_strength != 'MS':
                g_strength, g_polarity = g_modals.get(g_node, ('', ''))
            else:
                _, g_polarity = g_modals.get(g_node, ('', ''))
                g_strength = None

            if g_strength:
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
                gold = t_graph.matched_alignment.get(tnum, '')
                number_gold.append(g_number_dict.get(gold, ''))

        # `:refer-person`
        for tper in t_person_dict:
            if tper in t_instances:
                person_pred.append(t_person_dict[tper])
                gold = t_graph.matched_alignment.get(tper, '')
                person_gold.append(g_person_dict.get(gold, ''))

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
            corresponding_child = t_graph.matched_alignment.get(child, None)
            if corresponding_child in parent_gold_dict:
                g_parent = parent_gold_dict[corresponding_child]
                parent_gold.append(g_graph.matched_alignment.get(g_parent, g_parent))  # t_node aligned with g_parent, else g_parent
                parent_pred.append(t[0])
            # Is the inverted edge correct, i.e. the same as in the gold triple with the same child?
            if corresponding_child in edge_gold_dict:
                g_edge = edge_gold_dict[corresponding_child]
                edge_gold.append(g_graph.matched_alignment.get(g_edge, g_edge))  # t_edge aligned with g_edge, else g_edge
                edge_pred.append(t[1])

    return (f"{accuracy_score(parent_gold, parent_pred):.2f}" if parent_gold else "-",
            f"{accuracy_score(edge_gold, edge_pred):.2f}" if edge_gold else "-")