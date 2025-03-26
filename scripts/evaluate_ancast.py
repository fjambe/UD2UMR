#!/usr/bin/env python3
# Copyright © 2025 Federica Gamba <gamba@ufal.mff.cuni.cz>

import sys, os
import regex as re
import argparse
import penman
import pandas as pd

sys.path.append(os.path.abspath('scripts/ancast/src'))
from ancast.src.document import DocumentMatch, Match_resolution
from ancast.src.param_fun import parse_alignment, protected_divide
from ancast.src.sentence import Sentence
from ancast.src.word import *

import tests_ancast

# params
Cneighbor = 1

# adapted from Ancast
class UMRSentence(Sentence):

    def __init__(self, sent, semantic_text, alignment, sent_num, penman_graph, matched_alignment=None):
        super().__init__(sent, semantic_text, alignment, sent_num, format="umr")

        self.penman_graph = penman_graph
        self.matched_alignment = matched_alignment

    # @timer_decorator
    def parse(self, semantic_text, format):

        void_var = defaultdict(list)
        var2node = {}

        sense_re = re.compile(r"-[0-9]{2}")

        def parse_brackets(text, i):
            result = []

            bracket_match = False

            while i < len(text):
                if text[i] == '(':
                    cur_node, i = parse_var_content(text, i + 1)
                    result.append(cur_node)
                elif text[i] == ')':
                    i += 1
                    bracket_match = True
                    break
                else:
                    i += 1
            try:
                assert len(result) == 1, f"Multiple heads identified in semantic graph in sentence {self.sent_num}!"
            except AssertionError as error:
                print(f"Format Error: {error.args[0]}")
                raise
            try:
                assert bracket_match, f"Brackets aren't matched, please check the format in semantic graph in {self.sent_num}!"
            except AssertionError as error:
                print(f"Format Error: {error.args[0]}")
                raise

            return cur_node, i

        # @timer_decorator
        def parse_var_content(text, i):

            head = re.search(r'([\w0-9_\-]+\s*\/\s*[^)\s]+)', text[i:]).group(1)  # FG: include non-English characters
            var, txt = head.split("/")
            var = var.strip()
            txt = txt.strip()

            sense_pos_match = sense_re.search(txt)

            if sense_pos_match:
                pos = sense_pos_match.span()
                sense_id = int(txt[pos[0] + 1:pos[1]])
                real_name = txt[:pos[0]]
            else:

                sense_id = 0
                real_name = txt

            i += len(head)

            this_node = Word(raw_name=real_name, var=var, sense_id=sense_id)

            try:
                assert var not in var2node, "Duplicated variable declaration, ignoring new declaration."
                var2node[var] = this_node
            except AssertionError as e:
                warnings.warn(str(e), category=RuntimeWarning)

            # early-reentrancy
            if var in void_var.keys():
                for node, rel in void_var[var]:
                    node[(rel, self.parse_tags.copy())] = this_node
                del void_var[var]

            while (i < len(text)) and (text[i] != ')'):
                if text[i] == ':':
                    voided_var = False

                    space_1 = text.find(' ', i)
                    tab_1 = text.find('\t', i)

                    end = space_1 if space_1 != -1 else tab_1
                    relation = text[i + 1:end]
                    i = end

                    while (text[i] == ' ') or (text[i] == '\t'):
                        i += 1

                    if text[i] == '(':
                        sub_node, end = parse_brackets(text, i)


                    elif text[i] == '"':

                        end = text.find('"', i + 1)
                        text_part = text[i + 1:end]

                        # this is an ill-formed scene where variables are quoted

                        if text_part in var2node.keys():
                            sub_node = var2node[text_part]
                            print(f"Quoted reentrancy handled in sentence {self.sent_num}")
                        else:
                            sub_node = Attribute(text_part, quoted=True)
                    else:

                        firstspace = text.find(' ', i)
                        firstspace = 1e10 if firstspace == -1 else firstspace
                        firsttab = text.find('\t', i)
                        firsttab = 1e10 if firsttab == -1 else firsttab
                        firstline = text.find('\n', i)
                        firstline = 1e10 if firstline == -1 else firstline

                        next_space = min(firstline, firsttab, firstspace)
                        next_right_bracket = text.find(')', i)

                        if next_right_bracket == -1:
                            next_right_bracket = 1e10

                        end = min(next_space, next_right_bracket)

                        tt = text[i:end].strip()

                        if tt in var2node.keys():

                            # if it is a valid re-entrancy

                            sub_node = var2node[tt]

                        elif (re.fullmatch(r"s[0-9]+\w+[0-9]*", tt) and (format == "umr")) or \
                               ((format == "amr") and (tt not in {"imperative", "expressive"}) and (
                               not re.fullmatch(r"^[0-9.:+-]+$", tt))):  # FG: include non-English characters

                            # handling of early reentrancy, where the variable is not declared yet

                            void_var[tt].append((this_node, relation))
                            voided_var = True

                        else:
                            # attributes are not quoted.
                            sub_node = Attribute(tt)

                    i = end

                    if not voided_var:
                        this_node[(relation, self.parse_tags.copy())] = sub_node

                else:
                    if text[i].isalnum(): # FG: include non-English characters
                        print(text[i - 5:i + 5])
                        raise RuntimeError(f"a colon is missing in {self.sent_num}.")

                    i += 1

            return this_node, i

        if len(void_var) > 0:
            for v in void_var.keys():
                print(v + " is not specified!")

                # Leave the unspecified variable out for now

        return parse_brackets(semantic_text, 0)[0], var2node  # [1] is "i"


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
                #
                # t_alignment = t_buff[0].strip()
                # g_alignment = g_buff[0].strip()
                #
                # t_alignment = parse_alignment(t_alignment)
                # g_alignment = parse_alignment(g_alignment)
                #
                # for ga, gv in g_alignment.items():
                #     if ',' in gv:
                #         gv = gv.split(',')
                #         g_alignment[ga] = gv[1]
                # for ta, tv in t_alignment.items():
                #     if ',' in tv:
                #         tv = tv.split(',')
                #         t_alignment[ta] = tv[1]
                # print(g_alignment)

                t_pm_graph = penman.loads(''.join(t_graph))
                g_pm_graph = penman.loads(''.join(g_graph))

                tumr = UMRSentence(sent=t_sent, semantic_text=t_graph, alignment={}, sent_num=name,
                                   penman_graph=t_pm_graph)  # alignment=t_alignment,{}
                gumr = UMRSentence(sent=g_sent, semantic_text=g_graph, alignment={}, sent_num=name,
                                   penman_graph=g_pm_graph)  # alignment=g_alignment,{}

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
            f"Number of gold graphs ({len(gold)}) and converted graphs ({len(predicted)}) do not match."
        )

        data = [
            tests_ancast.las(predicted, gold),
            tests_ancast.uas(predicted, gold),
            tests_ancast.child_label(predicted, gold),
            tests_ancast.parent_label(predicted, gold),
            (tests_ancast.pronouns(predicted, gold)[0:5]),
            (tests_ancast.pronouns(predicted, gold)[5:10]),
            (tests_ancast.modal_strength(predicted, gold)[0:5]),
            (tests_ancast.modal_strength(predicted, gold)[5:10]),
            (tests_ancast.inverted_relations(predicted, gold)[0:5]),
            (tests_ancast.inverted_relations(predicted, gold)[5:10]),
            (tests_ancast.abstract(predicted, gold)[0:5]),
            (tests_ancast.abstract(predicted, gold)[5:10]),
            (tests_ancast.abstract(predicted, gold)[10:15]),
            tests_ancast.las(predicted, gold, category='arguments'),
            tests_ancast.uas(predicted, gold, category='arguments'),
            tests_ancast.las(predicted, gold, category='participants'),
            tests_ancast.uas(predicted, gold, category='participants'),
            tests_ancast.las(predicted, gold, category='non-participants'),
            tests_ancast.uas(predicted, gold, category='non-participants'),
            tests_ancast.las(predicted, gold, category='operands'),
            tests_ancast.uas(predicted, gold, category='operands')
        ]

        df = pd.DataFrame(data, columns=["Type", "Subtype", "Precision", "Recall", "F-score"])
        print(df.to_string(index=False))


parser = argparse.ArgumentParser()
parser.add_argument("--files", type=str, nargs="+", help="Two txt files, one for test and one for gold.")
parser.add_argument("--lang", help="Language code of the graphs (e.g., 'en' for English).", required=True)


if __name__ == "__main__":

    args = parser.parse_args()

    D = UMRDocument("umr")
    D.read_document(args.files[:2])
    # D.read_document(['/home/federica/gold.txt', '/home/federica/pred.txt'])
    D.run_tests()