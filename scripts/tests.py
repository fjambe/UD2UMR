from penman import layout

def coordination(predicted, gold):
    print("Coordination: %")

def abstract(predicted, gold):
    print("Abstract predicates: %")

def modal_strength(predicted, gold):
    """ Calculates precision scores for both the strength and polarity components of `modal-strength` attributes. """
    strength_score, polarity_score, count = 0, 0, 0

    for g_pred, g_gold in zip(predicted, gold):
        modals_pred, modals_gold = ([t for t in g.triples if t[1] == ":modal-strength"] for g in (g_pred, g_gold))
        for m in modals_pred:
            if m[2] != 'MS':
                count += 1
                strength, polarity = m[2].split('-')
                for mg in modals_gold:
                    mg_strength, mg_polarity = mg[2].split('-')
                    if m[0] == mg[0]:
                        if strength == mg_strength:
                            strength_score += 1
                        if polarity == mg_polarity:
                            polarity_score += 1
                        break

    print(f"Modal strength, strength precision: {(f'{strength_score / count:.2f}' if count > 0 else '-')}")
    print(f"Modal strength, polarity precision: {(f'{polarity_score / count:.2f}' if count > 0 else '-')}")

def pronouns(predicted, gold):
    """ Evaluates the precision of `refer-number` and `refer-person` annotations for entity nodes (`person`/`thing`). """
    number_score, person_score, count_number, count_person = 0, 0, 0, 0

    for g_pred, g_gold in zip(predicted, gold):
        number_pred = [t for t in g_pred.triples if t[1] == ":refer-number"]
        number_gold = {t[0]: t[2] for t in g_gold.triples if t[1] == ":refer-number"}
        person_pred = [t for t in g_pred.triples if t[1] == ":refer-person"]
        person_gold = {t[0]: t[2] for t in g_gold.triples if t[1] == ":refer-person"}

        instances = {t[0]: t[2] for t in g_pred.triples if t[1] == ":instance" and t[2] in {"person", "thing"}}

        for r_pred in number_pred:
            if r_pred[0] in instances:
                count_number += 1
                if r_pred[0] in number_gold and number_gold[r_pred[0]] == r_pred[2]:
                    number_score += 1

        for r_pred in person_pred:
            if r_pred[0] in instances:
                count_person += 1
                if r_pred[0] in person_gold and person_gold[r_pred[0]] == r_pred[2]:
                    person_score += 1

    print(f"Refer-number precision: {number_score / count_number:.2f}") if count_number > 0 else "-"
    print(f"Refer-person precision: {person_score / count_person:.2f}") if count_person > 0 else "-"

def inverted_relations(predicted, gold):
    parent_score, parent_count, edge_score, edge_count = 0, 0, 0, 0

    for g_pred, g_gold in zip(predicted, gold):
        inverted_pred = [t for t in g_pred.triples if layout.appears_inverted(g_pred, t)]
        edge_gold = {t[2]: t[1] for t in g_gold.triples if layout.appears_inverted(g_pred, t)}
        parent_gold = {t[2]: t[0] for t in g_gold.triples if layout.appears_inverted(g_pred, t)}

        for t in inverted_pred:
            child = t[2]
            # Is the parent correct, i.e. the same as in the gold triple with the same child?
            if child in parent_gold:
                parent_count += 1
                parent_score += (parent_gold[child] == t[0])
            # Is the inverted edge correct, i.e. the same as in the gold triple with the same child?
            if child in edge_gold:
                edge_count += 1
                edge_score += (edge_gold[child] == t[1])

    print(f"Inverted relations, parent precision: {(f'{parent_score / parent_count:.2f}' if parent_count > 0 else '-')}")
    print(f"Inverted relations, edge precision: {(f'{edge_score / edge_count:.2f}' if edge_count > 0 else '-')}")

