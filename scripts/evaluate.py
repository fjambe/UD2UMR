#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import sys, os
import re
import argparse
import penman
import pandas as pd

sys.path.append(os.path.abspath('scripts/ancast/src'))
from ancast.src.document import DocumentMatch, Match_resolution
from ancast.src.param_fun import parse_alignment, protected_divide
from ancast.src.sentence import Sentence

import tests

# params
Cneighbor = 1

# adapted from AnCast
class UMRSentence(Sentence):
    def __init__(self, sent, semantic_text, alignment, sent_num, penman_graph, matched_alignment=None):
        super().__init__(sent, semantic_text, alignment, sent_num, format="umr")

        self.penman_graph = penman_graph
        self.matched_alignment = matched_alignment


class UMRDocument(DocumentMatch):
    def __init__(self, *args):
        super().__init__(*args)
        self.sents = []

    # adapted from AnCast
    def read_document(self, file, output_csv=None):

        if isinstance(file, list):

            name = 0

            l_test = open(file[0], "r").read()
            l_gold = open(file[1], "r").read()

            blocks_test = l_test.strip().split("# :: snt")[1:]
            blocks_gold = l_gold.strip().split("# :: snt")[1:]

            assert len(blocks_test) == len(blocks_gold), \
                (f"Number of gold graphs ({len(blocks_gold)}) and converted graphs ({len(blocks_test)}) do not match. "
                 f"Make sure that test and gold files contain the same number of sentences."
            )

            for bt, bg in zip(blocks_test, blocks_gold):

                name += 1

                try:
                    assert ("sentence" in bt) and ("sentence" in bg), f"Keyword `sentence` is not found in block {name}"
                except AssertionError as error:
                    print(f"Format Error: {error.args[0]}")
                    raise
                try:
                    assert ("document" in bt) and ("document" in bg), f"Keyword `document` is not found in block {name}"
                except AssertionError as error:
                    print(f"Format Error: {error.args[0]}")
                    raise

                t_buff = bt.split("# sentence level graph:")
                g_buff = bg.split("# sentence level graph:")

                t_sent = re.sub(r'^\d+[\s\t]*', '', t_buff[0]).strip()
                g_sent = re.sub(r'^\d+[\s\t]*', '', g_buff[0]).strip()

                t_buff = t_buff[1].strip().split("# alignment:")
                g_buff = g_buff[1].strip().split("# alignment:")

                t_graph = t_buff[0].strip()
                g_graph = g_buff[0].strip()

                # t_buff = t_buff[1].strip().split("# document level annotation:")
                # g_buff = g_buff[1].strip().split("# document level annotation:")

                # t_alignment = t_buff[0].strip()
                # g_alignment = g_buff[0].strip()

                # t_alignment = parse_alignment(t_alignment)
                # g_alignment = parse_alignment(g_alignment)

                t_pm_graph = penman.loads(''.join(t_graph))
                g_pm_graph = penman.loads(''.join(g_graph))

                tumr = UMRSentence(sent=t_sent, semantic_text=t_graph, alignment={}, sent_num=name,
                                   penman_graph=t_pm_graph)  # alignment=t_alignment
                gumr = UMRSentence(sent=g_sent, semantic_text=g_graph, alignment={}, sent_num=name,
                                   penman_graph=g_pm_graph)  # alignment=g_alignment

                # print(gumr.penman_graph[0].triples)

                if tumr.invalid or gumr.invalid:
                    print(f"Error encountered, skipping sentence {name}")
                    continue

                try:
                    assert tumr.sent_num == gumr.sent_num, f"Sentence number mismatch: {tumr.sent_num}, {gumr.sent_num}"
                except AssertionError as error:
                    print(f"Document Error: {error.args[0]}")
                    raise

                M = Match_resolution(tumr, gumr, Cneighbor=Cneighbor)
                self.add_doct_info(M, test_doc='', gold_doc='')
                self.macro_avg(M)
                tumr.matched_alignment = M.match_list01
                gumr.matched_alignment = M.match_list10
                self.sents.append((tumr, gumr))

            # print AnCast evaluation
            ps, rs = self.semantic_metric_precision.compute("lr"), self.semantic_metric_recall.compute("lr")
            self.sent_fscore = protected_divide(2 * ps * rs, ps + rs)
            print(f"Sent Micro:\tPrecision: {ps:.2%}\tRecall: {rs:.2%}\tFscore: {self.sent_fscore:.2%}\n")

    # UD2UMR-specific
    def run_tests(self):

        predicted = [s[0] for s in self.sents]
        gold = [s[1] for s in self.sents]

        assert len(predicted) == len(gold), (
            f"Number of gold graphs ({len(predicted)}) and converted graphs ({len(gold)}) do not match."
        )

        data = [
            ("modal-strength", "strength", "accuracy", tests.modal_strength(predicted, gold)[0]),
            ("modal-strength", "polarity", "accuracy", tests.modal_strength(predicted, gold)[1]),
            ("abstract predicates", "predicate", "accuracy", tests.abstract(predicted, gold)[0]),
            ("abstract predicates", "dependent ARGs", "recall", tests.abstract(predicted, gold)[1]),
            ("abstract predicates", "ARGs nodes", "accuracy", tests.abstract(predicted, gold)[2]),
            ("refer-number (entities)", "-", "accuracy", tests.pronouns(predicted, gold)[0]),
            ("refer-person (entities)", "-", "accuracy", tests.pronouns(predicted, gold)[1]),
            ("inverted relations", "parent", "accuracy", tests.inverted_relations(predicted, gold)[0]),
            ("inverted relations", "edge", "accuracy", tests.inverted_relations(predicted, gold)[1]),
            # ("coordination", "opX", "accuracy", tests.coordination(predicted, gold, args.lang))
        ]

        df = pd.DataFrame(data, columns=["Type", "Sub-type", "Metric", "Score"])
        print(df.to_string(index=False))


parser = argparse.ArgumentParser()
parser.add_argument("--files", type=str, nargs="+", help="Two txt files, one for test and one for gold.")
parser.add_argument("--lang", help="Language code of the graphs (e.g., 'en' for English).", required=True)


if __name__ == "__main__":

    args = parser.parse_args()

    D = UMRDocument("umr")
    D.read_document(args.files[:2])
    D.run_tests()