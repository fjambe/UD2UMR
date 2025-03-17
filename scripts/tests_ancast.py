from penman import layout
from preprocess import load_external_files


def metrics(correct, pred_total, gold_total):
    precision = correct / pred_total
    recall = correct / gold_total
    fscore = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return precision, recall, fscore

def coordination(predicted, gold, lang):
    """ Evaluates the accuracy of coordination relations. """
    conjunctions = load_external_files('conj.json', lang)
    for t_graph, g_graph in zip(predicted, gold):
        t_coord = [t for t in t_graph.penman_graph[0].instances() if t[2] in conjunctions] if conjunctions else \
            [t for t in t_graph.penman_graph[0].instances() if t[2] == 'and']

        g_coord = [t for t in g_graph.penman_graph[0].instances() if t[2] in conjunctions] if conjunctions else\
            [t for t in g_graph.penman_graph[0].instances() if t[2] == 'and']


def abstract(predicted, gold):
    """
    Evaluates the accuracy of abstract predicates and their dependent ARGs, by checking:
    - if the abstract concept label has been correctly selected (e.g., have-mod-91 both in predicted and gold);
    - how many correct relations having the abstract predicate as parent have been retrieved;
    - if ARG relations are assigned to the correct nodes.
    """
    correct_concept, correct_children, correct_args = 0, 0, 0
    t_concept_total, g_concept_total = 0, 0
    t_children_total, g_children_total = 0, 0
    t_args_total, g_args_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        print(g_graph.matched_alignment)

        t_abstract = {t[0]: t[2] for t in t_graph.penman_graph[0].instances() if t[2].endswith(("-91", "-92")) and t[2] != 'but-91'}
        g_abstract = {t[0]: t[2] for t in g_graph.penman_graph[0].instances() if t[2].endswith(("-91", "-92")) and t[2] != 'but-91'}

        t_concept_total += len(t_abstract)
        g_concept_total += len(g_abstract)

        for ab, t_label in t_abstract.items():
            gold = t_graph.matched_alignment.get(ab, '')
                        # Test 1: Is the abstract predicate correct?
            g_label = g_abstract.get(gold, '')
            correct_concept += (t_label == g_label)

            children_pred = t_graph.penman_graph[0].edges(source=ab)
            children_gold = g_graph.penman_graph[0].edges(source=gold)

            t_children_total += len(children_pred)
            g_children_total += len(children_gold)

            pred_args = {c[1]: c[2] for c in children_pred if c[1].startswith(":ARG")}
            gold_args = {c[1]: c[2] for c in children_gold if c[1].startswith(":ARG")}

            t_args_total += len(pred_args)
            g_args_total += len(gold_args)

            # Test 2: How many of the abstract predicate's dependents have been correctly retrieved (UAS)?
            matched_children = {t_graph.matched_alignment.get(c[2], '') for c in children_pred}
            correct_children += sum(1 for c in children_gold if c[2] in matched_children)

            # Test 3: Are correct ARGs assigned to the correct nodes?
            for role, t_target in pred_args.items():
                g_target = gold_args.get(role, None)
                if g_target and t_graph.matched_alignment.get(t_target, '') == g_target:
                    correct_args += 1

    concept_precision, concept_recall, concept_fscore = metrics(correct_concept, t_concept_total, g_concept_total)
    children_precision, children_recall, children_fscore = metrics(correct_children, t_children_total, g_children_total)
    args_precision, args_recall, args_fscore = metrics(correct_args, t_args_total, g_args_total)

    return (
        "Abstract predicates", "concept", f"{concept_precision:.3f}", f"{concept_recall:.3f}", f"{concept_fscore:.3f}",
        "Abstract predicates", "dependents (UAS)", f"{children_precision:.3f}", f"{children_recall:.3f}", f"{children_fscore:.3f}",
        "Abstract predicates", "ARG nodes", f"{args_precision:.3f}", f"{args_recall:.3f}", f"{args_fscore:.3f}"
    )


def modal_strength(predicted, gold):
    """ Evaluates the accuracy for both the strength and polarity components of `modal-strength` attributes. """
    correct_polarity, correct_strength = 0, 0
    t_total, g_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        t_modals = {t[0]: t[2] for t in t_graph.penman_graph[0].attributes(role=":modal-strength")}
        g_modals = {t[0]: t[2].split('-') for t in g_graph.penman_graph[0].attributes(role=":modal-strength")}

        for tm_var, tm_modstr in t_modals.items():
            if '-' in tm_modstr:  # if not, it's not going to be correct anyway
                t_strength, t_polarity = tm_modstr.split('-')
                g_node = t_graph.matched_alignment.get(tm_var, '')  # gold var aligned to pred var
                g_strength, g_polarity = g_modals.get(g_node, ('', ''))
                correct_polarity += t_polarity == g_polarity
                correct_strength += t_strength == g_strength

        t_total += len(t_modals)
        g_total += len(g_modals)

    polarity_precision, polarity_recall, polarity_fscore = metrics(correct_polarity, t_total, g_total)
    strength_precision, strength_recall, strength_fscore = metrics(correct_strength, t_total, g_total)

    return (
        "Modal-strength", "polarity", f"{polarity_precision:.3f}", f"{polarity_recall:.3f}", f"{polarity_fscore:.3f}",
        "Modal-strength", "strength", f"{strength_precision:.3f}", f"{strength_recall:.3f}", f"{strength_fscore:.3f}"
    )


def pronouns(predicted, gold):
    """ Evaluates the accuracy of `refer-number` and `refer-person` annotations for entity nodes (`person`/`thing`). """
    correct_person, correct_number = 0, 0
    t_pers_total, g_pers_total = 0, 0
    t_num_total, g_num_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        t_number_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-number")}
        t_person_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-person")}
        g_number_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-number")}
        g_person_dict = {t[0]: t[2] for t in g_graph.penman_graph[0].attributes(role=":refer-person")}

        t_instances = {t[0]: t[2] for t in t_graph.penman_graph[0].instances() if t[2] in {"person", "thing"}}
        g_instances = {g[0]: g[2] for g in g_graph.penman_graph[0].instances() if g[2] in {"person", "thing"}}

        # `:refer-number`
        for tnum in t_number_dict:
            if tnum in t_instances:
                gold = t_graph.matched_alignment.get(tnum, '')
                correct_number += t_number_dict[tnum] == g_number_dict.get(gold, '')

        # `:refer-person`
        for tper in t_person_dict:
            if tper in t_instances:
                gold = t_graph.matched_alignment.get(tper, '')
                correct_person += t_person_dict[tper] == g_person_dict.get(gold, '')

        t_pers_total += sum(1 for t in t_person_dict if t in t_instances)
        g_pers_total += sum(1 for g in g_person_dict if g in g_instances)
        t_num_total += sum(1 for t in t_number_dict if t in t_instances)
        g_num_total += sum(1 for g in g_number_dict if g in g_instances)

    person_precision, person_recall, person_fscore = metrics(correct_person, t_pers_total, g_pers_total)
    number_precision, number_recall, number_fscore = metrics(correct_number, t_num_total, g_num_total)

    return (
        "refer-number (entities)", "", f"{number_precision:.3f}", f"{number_recall:.3f}", f"{number_fscore:.3f}",
        "refer-person (entities)", "", f"{person_precision:.3f}", f"{person_recall:.3f}", f"{person_fscore:.3f}"
    )


def inverted_relations(predicted, gold):
    """ Evaluates the accuracy of inverted relations in the predicted UMR graphs. """
    correct_edge, correct_parent = 0, 0
    t_inverted_total, g_inverted_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        parent_gold_dict, edge_gold_dict = {}, {}
        for g_parent, g_edge, g_child in g_graph.penman_graph[0].edges():
            if layout.appears_inverted(g_graph.penman_graph[0], (g_parent, g_edge, g_child)):
                parent_gold_dict.setdefault(g_child, []).append(g_parent)
                edge_gold_dict.setdefault(g_child, []).append(g_edge)

        parent_pred_dict, edge_pred_dict = {}, {}
        for t_parent, t_edge, t_child in t_graph.penman_graph[0].edges():
            if layout.appears_inverted(t_graph.penman_graph[0], (t_parent, t_edge, t_child)):
                parent_pred_dict.setdefault(t_child, []).append(t_parent)
                edge_pred_dict.setdefault(t_child, []).append(t_edge)

        for child, pred_parents in parent_pred_dict.items():
            matched_child = t_graph.matched_alignment.get(child, '')
            if matched_child in parent_gold_dict:
                gold_parents = [g_graph.matched_alignment.get(gp, '') for gp in parent_gold_dict[matched_child]]
                correct_parent += sum(p in gold_parents for p in pred_parents)

            if matched_child in edge_gold_dict:
                gold_edges = edge_gold_dict[matched_child]
                correct_edge += sum(e in gold_edges for e in edge_pred_dict.get(child, []))

        t_inverted_total += sum(len(p) for p in parent_pred_dict.values())
        g_inverted_total += sum(len(p) for p in parent_gold_dict.values())

    parent_precision, parent_recall, parent_fscore = metrics(correct_parent, t_inverted_total, g_inverted_total)
    edge_precision, edge_recall, edge_fscore = metrics(correct_edge, t_inverted_total, g_inverted_total)

    return (
        "Inverted relations", "parent", f"{parent_precision:.3f}", f"{parent_recall:.3f}", f"{parent_fscore:.3f}",
        "Inverted relations", "edge", f"{edge_precision:.3f}", f"{edge_recall:.3f}", f"{edge_fscore:.3f}"
    )


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
#                             correct += g[1] == t[1]
#
#         if total:
#             print(f"Category: {rel.upper()}, {total}")
#             print(f"Correctly retrieved edge: {correct} out of {total}.\n",
#                   f"LDS: {(correct / total):.2f}\n")
#         else:
#             print('zero category', rel)

def filter_edges(graph, category):
    """Filter edges based on category."""
    category_rels = {
        'arguments': {':ARG0', ':ARG1', ':ARG2', ':ARG3', ':ARG4'},
        'operands': {':op1', ':op2', ':op3', ':op4', ':op5'},
        'participants': {':actor', ':undergoer', ':theme', ':recipient', ':affectee'},
        'non-participants': {':mod', ':manner', ':OBLIQUE', ':temporal', ':ADVCL', ':name', ':possessor',
                             ':condition', ':vocative', ':concession'}
    }
    edges = graph.penman_graph[0].edges()
    if category and category in category_rels:
        return [edge for edge in edges if edge[1] in category_rels[category]]
    return edges


def las(predicted, gold, category=None):

    correct = 0
    t_total, g_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        t_edges = filter_edges(t_graph, category)  # or triples?
        g_edges = filter_edges(g_graph, category)  # or triples?

        # for g in g_edges:  # or triples?
        #     if g[0] in g_graph.matched_alignment:
        #         # if g[2] in g_graph.penman_graph[0].variables():
        #         g_total += g[2] in g_graph.matched_alignment
        #         # else:
        #         #     g_total += 1
        #
        # for t_parent, t_edge, t_child in t_edges:  # or triples?
        #     if t_parent in t_graph.matched_alignment:
        #         # if t[2] in t_graph.penman_graph[0].variables():
        #         t_total += t_child in t_graph.matched_alignment
        #         # else:
        #         #     t_total += 1
        #
        # for g in g_edges:  # or triples?
        #     g_parent = t_graph.matched_alignment.get(t_parent, '')
        #     g_child = t_graph.matched_alignment.get(t_child, '') if t_child in t_graph.penman_graph[0].variables() else t_child
        #     if g_parent and g_child:
        #         correct += g_parent == g[0] and t_edge == g[1] and g_child == g[2]

        g_total += sum(g[2] in g_graph.matched_alignment for g in g_edges if g[0] in g_graph.matched_alignment)
        t_total += sum(t[2] in t_graph.matched_alignment for t in t_edges if t[0] in t_graph.matched_alignment)
        correct += sum(
            1 for t in t_edges for g in g_edges
            if t_graph.matched_alignment.get(t[0], '') == g[0] and t[1] == g[1] and
            t_graph.matched_alignment.get(t[2], '') == g[2]
        )

    precision, recall, fscore = metrics(correct, t_total, g_total)
    return "LAS", category or '', f"{precision:.3f}", f"{recall:.3f}", f"{fscore:.3f}"


def uas(predicted, gold, category=None):

    correct = 0
    t_total, g_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        t_edges = filter_edges(t_graph, category)
        g_edges = filter_edges(g_graph, category)

        g_total += sum(g[2] in g_graph.matched_alignment for g in g_edges if g[0] in g_graph.matched_alignment)
        t_total += sum(t[2] in t_graph.matched_alignment for t in t_edges if t[0] in t_graph.matched_alignment)
        correct += sum(
            1 for t in t_edges for g in g_edges
            if t_graph.matched_alignment.get(t[0], '') == g[0] and
            t_graph.matched_alignment.get(t[2], '') == g[2]
        )

    precision, recall, fscore = metrics(correct, t_total, g_total)
    return "UAS", category or '', f"{precision:.3f}", f"{recall:.3f}", f"{fscore:.3f}"


def child_label(predicted, gold):

    correct = 0
    t_total, g_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        g_edges = g_graph.penman_graph[0].edges()
        t_edges = t_graph.penman_graph[0].edges()

        # Excluding attributes and instances because the edge is always correct
        g_total += sum(g[2] in g_graph.matched_alignment for g in g_edges if g[0] in g_graph.matched_alignment)
        t_total += sum(t[2] in t_graph.matched_alignment for t in t_edges if t[0] in t_graph.matched_alignment)

        gold_already_checked = set()  # because of re-entrancies
        # e.g., both the following would be counted as correct
        # Edge(source='s2c', role=':actor', target='s2p2') Edge(source='s2c', role=':actor', target='s2p2')
        # Edge(source='s2c', role=':actor', target='s2p2') Edge(source='s2p3', role=':actor', target='s2p2')

        for t_parent, t_edge, t_child in t_edges:
            for g in g_edges:
                g_parent = t_graph.matched_alignment.get(t_parent, '')
                g_child = t_graph.matched_alignment.get(t_child, '')
                if g_parent and g_child and g not in gold_already_checked:
                    if t_edge == g[1] and g_child == g[2]:
                        correct += 1
                        gold_already_checked.add(g)

    precision, recall, fscore = metrics(correct, t_total, g_total)
    return "Child-label", "", f"{precision:.3f}", f"{recall:.3f}", f"{fscore:.3f}"


def parent_label(predicted, gold):

    correct = 0
    t_total, g_total = 0, 0

    for t_graph, g_graph in zip(predicted, gold):

        g_triples = g_graph.penman_graph[0].triples
        t_triples = t_graph.penman_graph[0].triples

        g_total += sum(
            g[2] in g_graph.matched_alignment if g[2] in g_graph.penman_graph[0].variables() else 1
            for g in g_triples if g[0] in g_graph.matched_alignment
        )
        t_total += sum(
            t[2] in t_graph.matched_alignment if t[2] in t_graph.penman_graph[0].variables() else 1
            for t in t_triples if t[0] in t_graph.matched_alignment
        )

        for t_parent, t_edge, t_child in t_triples:
            for g in g_triples:
                g_parent = t_graph.matched_alignment.get(t_parent, '')
                g_child = t_graph.matched_alignment.get(t_child, '') if t_child in t_graph.penman_graph[0].variables() else t_child
                if g_parent and g_child:
                    correct += g_parent == g[0] and t_edge == g[1]

    precision, recall, fscore = metrics(correct, t_total, g_total)
    return "Parent-label", "", f"{precision:.3f}", f"{recall:.3f}", f"{fscore:.3f}"