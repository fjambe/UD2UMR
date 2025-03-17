import penman
import re
import pandas as pd


class UMR:
    def __init__(self, sent_num, graph, alignments):
        self.sent_num = sent_num
        self.graph = graph
        self.alignments = alignments
        self.unaligned = set(self.alignments.keys())

    def __repr__(self):
        return f"UMR(sent_num={self.sent_num}, graph={len(self.graph.triples)} triples, alignments={len(self.alignments)} alignments)"

    def overlaps(self, range1, range2):
        """Check if two span ranges overlap."""
        start1, end1 = map(int, range1.split('-'))
        start2, end2 = map(int, range2.split('-'))
        return not (end1 < start2 or end2 < start1)  # Returns True if they overlap

    def compare_alignments(self, predicted_umr):
        matches = {}
        zero_aligned = {"gold": [], "pred": []}

        for pred_var, pred_ranges in predicted_umr.alignments.items():
            if "0-0" in pred_ranges:
                zero_aligned["pred"].append(pred_var)
                predicted_umr.unaligned.discard(pred_var)

        for gold_var, gold_ranges in self.alignments.items():
            if "0-0" in gold_ranges:
                zero_aligned["gold"].append(gold_var)
                self.unaligned.discard(gold_var)
                continue

            matched_pred_vars = []
            for pred_var, pred_ranges in predicted_umr.alignments.items():
                # if pred_var in predicted_umr.unaligned:  # try to keep TODO
                    # if any(g_range in pred_ranges for g_range in gold_ranges):
                    if any(self.overlaps(g_range, p_range) for g_range in gold_ranges for p_range in pred_ranges):
                        matched_pred_vars.append(pred_var)
                        self.unaligned.discard(gold_var)
                        predicted_umr.unaligned.discard(pred_var)

            if matched_pred_vars:
                matches[gold_var] = matched_pred_vars

        for pred_var, pred_ranges in predicted_umr.alignments.items():
            if pred_var not in zero_aligned['pred'] and pred_var not in [item for sublist in matches.values() for item in sublist] and pred_var not in predicted_umr.unaligned:
                print('HELP', pred_var, pred_ranges)

        return matches, zero_aligned

    def aligned(self, value, zero_aligned, key):
        return value not in zero_aligned[key] and value not in self.unaligned


def parse_umr_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    umr_objects = []
    current_graph = []
    current_alignment = {}
    in_graph = False
    in_alignment = False
    sent_id = None

    for line in lines:
        line = line.strip()

        if line.startswith("# sent_id ="):
            sent_id = line.split("=")[1].strip()

        elif line.startswith("# sentence level graph:"):
            in_graph = True
            current_graph = []

        elif in_graph and line.startswith("# alignment:"):
            in_graph = False
            in_alignment = True
            current_alignment = {}

        elif in_graph:
            current_graph.append(line)

        elif in_alignment:
            if line == "" or line.startswith("#"):
                in_alignment = False
                if sent_id and current_graph:
                    graph_str = "\n".join(current_graph)
                    graph = penman.decode(graph_str)
                    umr_objects.append(UMR(sent_id, graph, current_alignment))
            else:
                match = re.match(r"(\S+): (.+)", line)
                if match:
                    key, spans = match.groups()
                    current_alignment[key] = [span.strip() for span in spans.split(",")]

    return umr_objects


def run_tests(gold, predicted):

    assert len(gold) == len(predicted), (
        f"Number of gold graphs ({len(gold)}) and converted graphs ({len(predicted)}) do not match."
    )

    g_total, p_total, correct_total = 0, 0, 0
    # g_total_uas, p_total_uas, correct_uas = 0, 0, 0

    def process_matching_triples(p, parents, children, triples_matched, correctly_retrieved, pumrs, e):
        """ Helper function to check and update matching gold triples. """
        memory = []
        for g in gumr.graph.triples:
            if g not in triples_matched:
                if g[0] in parents and g[1] == p[1] and g[2] in children:
                    pumrs += 1
                    memory.append(g)
                    # print('g', g)

        if len(memory) == 1:
            triples_matched.add(memory[0])
            correctly_retrieved += 1
        elif len(memory) > 1:  # wrong
            for x in memory:
                triples_matched.add(x)
                correctly_retrieved += e

        return correctly_retrieved, pumrs

    for gumr, pumr in zip(gold, predicted):

        correct = 0

        assert gumr.sent_num == pumr.sent_num, f"Sentence number mismatch: {gumr.sent_num}, {pumr.sent_num}"

        g_to_p_matches, zero_aligned, = gumr.compare_alignments(pumr)

        number_g = sum(1 for g in gumr.graph.triples if gumr.aligned(g[0], zero_aligned, "gold") and gumr.aligned(g[2], zero_aligned, "gold"))
        number_p = sum(1 for p in pumr.graph.triples if pumr.aligned(p[0], zero_aligned, "pred") and pumr.aligned(p[2], zero_aligned, "pred"))

        g_total += number_g
        p_total += number_p

        pumrs = 0
        print('TOTALE TRIPLE:', number_p)

        ins = [t for t in pumr.graph.instances() if t[0] not in zero_aligned['pred']]
        att = [t for t in pumr.graph.attributes() if t[0] not in zero_aligned['pred']]
        # print('NON-EDGES', len(ins) + len(att))
        # print('EDGES', len([p for p in pumr.graph.edges() if p[0] not in zero_aligned['pred'] and p[2] not in zero_aligned['pred']]))
        print('EDGES', len([p for p in pumr.graph.edges() if pumr.aligned(p[0], zero_aligned, "pred") and pumr.aligned(p[2], zero_aligned, "pred")]))

        gold_triples_matched = set()

        for p in pumr.graph.triples:
            p_parent, p_edge, p_child = p
            if not p_child:  # Temporary check based on 23:45 issue
                continue

            g_parents = [key for key, p_list in g_to_p_matches.items() if p_parent in p_list]
            epsilon = 1 / max(1, len(g_parents))

            if p in pumr.graph.edges():  # Edges
                if pumr.aligned(p_parent, zero_aligned, "pred") and pumr.aligned(p_child, zero_aligned, "pred"):
                    g_children = [key for key, p_list in g_to_p_matches.items() if p_child in p_list]
                    correct, pumrs = process_matching_triples(p, g_parents, g_children, gold_triples_matched, correct, pumrs, epsilon)

            else:  # Attributes and instances
                if pumr.aligned(p_parent, zero_aligned, "pred"):
                    correct, pumrs = process_matching_triples(p, g_parents, [p_child], gold_triples_matched, correct, pumrs, epsilon)

        correct_total += correct

        # print('Triples retrieved:', pumrs)
        print('correct', correct)
        print('perce', correct / number_g)

        # quit()

    print(correct_total / g_total)

    data = []

    # df = pd.DataFrame(data, columns=["Type", "Sub-type", "Precision", "Recall", "F-score"])
    # print(df.to_string(index=False))


