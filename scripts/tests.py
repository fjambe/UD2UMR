def coordination(predicted, gold):
    print("Coordination: %")

def abstract(predicted, gold):
    print("Abstract predicates: %")

def named_entities(predicted, gold):
    print("Named entities: %")

def modal_strength(predicted, gold):
    """ Calculates precision scores for both the strength and polarity components of modal-strength expressions. """
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
    if count > 0:
        print(f"Modal strength precision: strength {strength_score / count:.2f} | modality {polarity_score / count:.2f}")

def pronouns(predicted, gold):
    """ Evaluates the precision of `refer-number` annotations for entity nodes (`person`/`thing`). """
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

def relatives(predicted, gold):
    print("Relatives: %")