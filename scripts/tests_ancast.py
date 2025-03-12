from penman import layout
from sklearn.metrics import precision_recall_fscore_support

from preprocess import load_external_files


def esklearnone(gold, pred):
    tp, fp, fn = 0, 0, 0

    for p, g in zip(pred, gold):
        if p == "NULL":
            fn += 1  # Missed prediction (false negative)
        elif p == g:
            tp += 1  # Correct prediction (true positive)
        else:
            fp += 1  # Incorrect prediction (false positive)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return precision, recall, f1


# def into_binary_labels(predictions, golds):
#     # True labels: 1 if correct, 0 if incorrect
#     y_true = [1] * len(golds)  # Every gold label must be predicted
#     y_pred = [1 if pred == golds[i] else 0 for i, pred in enumerate(predictions)]
#     return y_true, y_pred


def pad_predictions(pred, gold, original, removal, dictio=False):
    """ Pad predictions with a placeholder ("NULL") if some gold labels were not predicted. """
    remaining = {g: v for g, v in original.items() if g not in removal} if dictio else\
        [x for x in original if x not in removal]
    pred.extend(['NULL'] * (len(remaining)))
    gold.extend([v for v in remaining.values()] if dictio else [r[2] for r in remaining])
    assert len(pred) == len(gold)


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
    #
    pp = ['have-mod-91', 'NULL', 'NULL', 'identity-91', 'have-mod-91', 'NULL', 'have-place-91', 'identity-91', 'have-role-91', 'have-rol-92']
    gg = ['have-mod-91', 'say-91', 'have-cause-91', 'identity-91', 'have-91', 'have-rel-role-92', 'have-rel-role-92', 'identity-91', 'have-role-91', 'have-rol-91']
    # # gg = [p for p in predicate_gold][-10:]
    # for p, g in zip(pp, gg):
    #     print(p,g, p==g)

    predicate_prec, predicate_recall, predicate_f1, _ = precision_recall_fscore_support(gg, pp, zero_division=0, average="macro", labels=[l for l in set(gg)])
    # predicate_prec, predicate_recall, predicate_f1 = esklearnone(predicate_gold, predicate_pred)
    # predicate_prec, predicate_recall, predicate_f1 = esklearnone(gg, pp)

    # children_prec, children_recall, children_f1, _ = precision_recall_fscore_support(children_list_gold, children_list_pred, zero_division=0, average="macro", labels=[l for l in set(children_list_gold)]])
    children_prec, children_recall, children_f1 = esklearnone(children_list_gold, children_list_pred)

    # args_prec, args_recall, args_f1, _ = precision_recall_fscore_support(args_gold, args_pred, zero_division=0, average="macro")
    args_prec, args_recall, args_f1 = esklearnone(args_gold, args_pred)

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
            if t_strength != 'MS':  # consider only those that I have tried to predict
                # in this setting, recall is useless (no NULL in pred, only in gold)
                # does this set of metrics make sense?
                g_strength, g_polarity = g_modals.get(g_node, ('NULL', 'NULL'))
                strength_gold.append(g_strength)
                strength_pred.append(t_strength)
            else:
                _, g_polarity = g_modals.get(g_node, ('NULL', 'NULL'))
            polarity_gold.append(g_polarity)
            polarity_pred.append(t_polarity)

    # TODO: if I want recall to make sense, I need to also iterate over gold

    strength_prec, strength_recall, strength_f1 = esklearnone(strength_gold, strength_pred)
    polarity_prec, polarity_recall, polarity_f1 = esklearnone(polarity_gold, polarity_pred)

    return (f"{strength_prec:.2f}", f"{strength_recall:.2f}", f"{strength_f1:.2f}",
            f"{polarity_prec:.2f}", f"{polarity_recall:.2f}", f"{polarity_f1:.2f}")
    # return (f"{accuracy_score(strength_gold, strength_pred):.2f}" if strength_gold else "-",
    #         f"{accuracy_score(polarity_gold, polarity_pred):.2f}" if polarity_gold else "-")


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

    # TODO: if I want recall to make sense, I need to also iterate over gold

    number_prec, number_recall, number_f1 = esklearnone(number_gold, number_pred)
    person_prec, person_recall, person_f1 = esklearnone(person_gold, person_pred)

    return (f"{number_prec:.2f}", f"{number_recall:.2f}", f"{number_f1:.2f}",
            f"{person_prec:.2f}", f"{person_recall:.2f}", f"{person_f1:.2f}")
    # return (f"{accuracy_score(number_gold, number_pred):.2f}" if number_gold else "-",
    #         f"{accuracy_score(person_gold, person_pred):.2f}" if person_gold else "-")


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

        # TODO: if I want recall to make sense, I need to also iterate over gold

    parent_prec, parent_recall, parent_f1 = esklearnone(parent_gold, parent_pred)
    edge_prec, edge_recall, edge_f1 = esklearnone(edge_gold, edge_pred)

    return (f"{parent_prec:.2f}", f"{parent_recall:.2f}", f"{parent_f1:.2f}",
            f"{edge_prec:.2f}", f"{edge_recall:.2f}", f"{edge_f1:.2f}")
    # return (f"{accuracy_score(parent_gold, parent_pred):.2f}" if parent_gold else "-",
    #         f"{accuracy_score(edge_gold, edge_pred):.2f}" if edge_gold else "-")


### OVERVIEW ###

# issue: the alignment strategy seems wild and unreliable

def parent_uas_las(predicted, gold, category=None):

    total_score = 0
    correct_uas, correct_las = 0, 0
    unaligned_nodes = 0

    category_rels = {
        'arguments': {':ARG0', ':ARG1', ':ARG2', ':ARG3', ':ARG4'},
        'operands': {':op1', ':op2', ':op3', ':op4', ':op5'},
        'participants': {':actor', ':undergoer', ':theme', ':recipient', ':affectee'},
        'non-participants': {':mod', ':manner', ':OBLIQUE', ':temporal', ':ADVCL', ':name', ':possessor',
                             ':condition', ':vocative', ':concession'}
    }

    rels = category_rels.get(category)  # None if category not in dictionary

    for t_graph, g_graph in zip(predicted, gold):
        t_edges = t_graph.penman_graph[0].edges()
        g_edges = g_graph.penman_graph[0].edges()

        if rels is not None:  # Filter only relevant edges if a category is specified
            t_edges = [t for t in t_edges if t[1] in rels]
            g_edges = [g for g in g_edges if g[1] in rels]

        for t in t_edges:
            total_score += 1
            gold = t_graph.matched_alignment.get(t[2], '')  # gold aligned node for t[2]
            if not gold.startswith('NULL'):  # unaligned nodes anyway  # ripensare se ha senso
                for g in g_edges:
                    if g[2] == gold:  # this g is the triple I'll compare
                        if t_graph.matched_alignment.get(t[0], '') == g[0]:  # gold_parent
                            correct_uas += 1
                            # print(f't: {t}, g: {g}')
                            if g[1] == t[1]:
                                correct_las += 1
                                break
                            break
            else:
                unaligned_nodes += 1  # it wasn't possible to get any parent anyway

        # mi interessa che il nodo non andasse creato?
        for g in g_edges:
            pass

    effective_total = total_score - unaligned_nodes

    print(f"Category: {category and category.upper()}")
    print(f"Correctly retrieved parent: {correct_uas} out of {total_score} (eff. {effective_total}).\n"
          f"Correctly retrieved parent + edge: {correct_las} out of {total_score} (eff. {effective_total}).\n"
          f"UAS: {(correct_uas / total_score):.2f}, LAS: {(correct_las / total_score):.2f}\n"
          f"Refined scores: UAS {(correct_uas / effective_total):.2f}, LAS {(correct_las / effective_total):.2f}")
    print()


def node_recall(predicted, gold):

    total_score = 0
    recalled_nodes = 0

    for t_graph, g_graph in zip(predicted, gold):

        t_vars = [i[0] for i in t_graph.penman_graph[0].instances()]
        g_vars = [i[0] for i in g_graph.penman_graph[0].instances()]

        for g in g_vars:
            total_score += 1
            t_aligned = g_graph.matched_alignment.get(g, '')
            if t_aligned in t_vars:  # ovvio che sarà in t_vars, because it has been aligned
                # print(g, t_aligned)
                recalled_nodes += 1

    # maybe I simply need to count the number of Instance triples?
    # doesn't seem to be the case, because my converter generates some more. So how do I do this?
    # actually, there seems to be no way to verify this, because I would need to rely on manual alignments.
    # Otherwise, I really cannot: all the available nodes are somehow aligned by Ancast, until there's at least a free
    # node in the other (gold or pred) list of triples.
    # POINTLESS.

    print(f"Recalled nodes: {recalled_nodes} out of {total_score}, i.e. {(recalled_nodes / total_score):.2f}")


# def lds_per_label(predicted, gold):
#     """
#     TODO: LAS for each UMR label.
#     E.g. is every :quant supposed to be a :quant? But what does that even mean?
#     It means at least that t[1] is :quant, okay, Then? I guess I need the same child, otherwise what am I doing,
#     comparing random triples that just happen to have the same edge? Nonsense.
#     Then, I need t[1] == REL, t[2] == g[2]. But I also need t[1] == g[1], otherwise it's the far west.
#     SO, the only thing I don't care about is t[0] and g[0], aka the PARENT.
#
#     --> In other words, it's like a reverse UAS: not Unlabeled Attachment Score, but Labeled Disattachment score.
#     Sounds weird.
#     """
#
#     category_rels = {
#         'arguments': {':ARG0', ':ARG1', ':ARG2', ':ARG3', ':ARG4'},
#         'operands': {':op1', ':op2', ':op3', ':op4', ':op5'},
#         'participants': {':actor', ':undergoer', ':theme', ':recipient', ':affectee'},
#         'non-participants': {':mod', ':manner', ':OBLIQUE', ':temporal', ':ADVCL', ':name', ':possessor',
#                              ':condition', ':vocative', ':concession'}
#     }
#
#     all_rels = [r for rs in category_rels.values() for r in rs]
#
#     print("------------------------- SCORES PER LABEL -------------------------")
#     print()
#
#     for rel in all_rels:
#
#         print(rel)
#
#         total = 0
#         correct = 0
#
#         for t_graph, g_graph in zip(predicted, gold):
#
#             print('hic', t_graph, g_graph)
#
#             t_edges = [t for t in t_graph.penman_graph[0].edges() if t[1] == rel]
#             g_edges = [g for g in g_graph.penman_graph[0].edges() if g[1] == rel]
#
#             if t_edges:
#                 for t in t_edges:
#                     total += 1
#                     gold = t_graph.matched_alignment.get(t[2], '')  # gold aligned node for t[2]
#                     for g in g_edges:
#                         if g[2] == gold:  # this g is the triple I'll compare
#                             if g[1] == t[1]:
#                                 correct += 1
#
#         if total:
#             print(f"Category: {rel.upper()}, {total}")
#             print(f"Correctly retrieved edge: {correct} out of {total}.\n",
#                   f"LDS: {(correct / total):.2f}\n")
#             print()
#         else:
#             print('zero category', rel)