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

    def compare_alignments(self, predicted_umr):
        matches = {}
        zero_aligned = {"gold": [], "pred": []}

        for gold_var, gold_ranges in self.alignments.items():
            if "0-0" in gold_ranges:
                zero_aligned["gold"].append(gold_var)
                self.unaligned.discard(gold_var)
                continue

            for pred_var, pred_ranges in predicted_umr.alignments.items():
                if "0-0" in pred_ranges:
                    zero_aligned["pred"].append(pred_var)
                    predicted_umr.unaligned.discard(pred_var)
                if any(g_range in pred_ranges or p_range in gold_ranges for g_range in gold_ranges for p_range in
                       pred_ranges):
                    # matches.append((gold_var, gold_ranges, pred_var, pred_ranges))  # matches was a list
                    matches[gold_var] = pred_var
                    self.unaligned.discard(gold_var)
                    predicted_umr.unaligned.discard(pred_var)

        # print("Unaligned in Gold:", self.unaligned)
        # print("Unaligned in Predicted:", predicted_umr.unaligned)
        #
        # for x in self.unaligned:
        #     print('GOLD:', x, self.alignments[x])
        # for y in predicted_umr.unaligned:
        #     print('PRED:', y, predicted_umr.alignments[y])

        return matches, zero_aligned

    def aligned(self, value, zero_aligned, key):
        return value not in zero_aligned[key] and value not in self.unaligned


def is_variable(s):
    pattern = r'^s\d+[a-zA-Z](\d+)?$'
    return bool(re.match(pattern, s))


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

    g_total, p_total, correct = 0, 0, 0
    # g_total_uas, p_total_uas, correct_uas = 0, 0, 0
    # g_total_las, p_total_las, correct_las = 0, 0, 0
    # g_total_lds, p_total_lds, correct_lds = 0, 0, 0

    for gumr, pumr in zip(gold, predicted):

        assert gumr.sent_num == pumr.sent_num, f"Sentence number mismatch: {gumr.sent_num}, {pumr.sent_num}"

        g_to_p_matches, zero_aligned, = gumr.compare_alignments(pumr)
        p_to_g_matches = {value: key for key, value in g_to_p_matches.items()}

        print(g_to_p_matches)

        number_g = sum(1 for g in gumr.graph.triples if gumr.aligned(g[0], zero_aligned, "gold") and gumr.aligned(g[2], zero_aligned, "gold"))
        number_p = sum(1 for p in pumr.graph.triples if pumr.aligned(p[0], zero_aligned, "pred") and pumr.aligned(p[2], zero_aligned, "pred"))

        g_total += (len(gumr.graph.triples) - number_g)
        p_total += (len(pumr.graph.triples) - number_p)

        for p in pumr.graph.triples:  # then also distinguish gumr.graph.edges, gumr.graph.attributes, gumr.graph.istances
            p_parent, p_edge, p_child = p

            # p_parent is always a variable
            if p_child:  # check that is not None is only due to 23:45, so temp
                if is_variable(p_child):  # the alternative would be to check if the p triple is of type Edge
                    if pumr.aligned(p_parent, zero_aligned, "pred") and pumr.aligned(p_child, zero_aligned, "pred"):
                        for g in gumr.graph.triples:
                            g_parent, g_child = p_to_g_matches.get(p_parent, '404'), p_to_g_matches.get(p_child, '404')
                            if p_parent == g_parent and p_edge == g[1] and p_child == g_child:
                                correct += 1
                                # break  # needed or not?
                else:  # child is attribute or instance
                    if pumr.aligned(p_parent, zero_aligned, "pred"):
                        g_parent = p_to_g_matches.get(p_parent, '404')
                        if g_parent == '404' and gumr.aligned(g_parent, zero_aligned, "gold"):
                            print('QUA', p_parent)  # TODO investigate

                        if p_parent == g_parent and p_edge == g[1] and p_child == g[2]:
                            correct += 1
                            break  # same results without it

    print(correct / g_total)

    data = []

    df = pd.DataFrame(data, columns=["Type", "Sub-type", "Precision", "Recall", "F-score"])
    print(df.to_string(index=False))


