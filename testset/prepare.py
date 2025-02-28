### Script to prepare the test set for manual annotation. (30 sentences).

import sys, os
sys.path.append(os.path.abspath('../scripts'))
import argparse
import udapi
from scripts.umr_node import UMRNode
from scripts.umr_graph import UMRGraph
from scripts.print_structure import numbered_line_with_alignment


def assign_variable_name(udtree):
    variables = []
    for token in udtree.descendants:
        if token.deprel not in ['aux', 'case', 'punct', 'mark']:
            first_letter = token.form.lemma[0].lower() if hasattr(token.form, 'lemma') else token.form[0].lower()
            count = 2
            if first_letter in variables:
                while f"{first_letter}{count}" in variables:
                    count += 1
            var_name = first_letter if first_letter not in variables else f"{first_letter}{count}"
            variables.append(var_name)
    return variables

def alignments(variables, sent_num, output_file):
    for v in variables:
        print(f's{sent_num}{v}: ', file=output_file)

def print_structure(tree, sent_tree, sent_num, output_file):
    print(f'# sent_id = {tree.address()}', file=output_file)
    print(f'# :: snt {sent_num}', file=output_file)
    numbered_line_with_alignment(tree, output_file)
    print(f'Sentence: {tree.text}', file=output_file)
    if sent_tree.lang != 'en':
        en_sent = [c for c in tree.comment.split('\n') if c.startswith(" text_en = ")]
        if en_sent:
            print('Sentence Gloss (en):', f"{en_sent[0].lstrip(' text_en = ')}", '\n', file=output_file)
        else:
            print(file=output_file)
    else:
        print(file=output_file)
    print('# sentence level graph:', file=output_file)
    print(f'(s{sent_num} / )\n', file=output_file)
    print('# alignment:', file=output_file)
    variables = assign_variable_name(tree)
    alignments(variables, sent_num, output_file)
    print(file=output_file)
    print('# document level annotation', file=output_file)
    print('\n', file=output_file)


parser = argparse.ArgumentParser()
parser.add_argument("--treebank", help="Path of the treebank in input.", required=True)
parser.add_argument("--data_dir",
                    help="Path of the directory where the input treebanks are stored, if not 'data'.", default='../data')

if __name__ == "__main__":

    args = parser.parse_args()
    doc = udapi.Document(f'{args.data_dir}/{args.treebank}')
    sent_num = 0

    with open("manual_30_test_sent_ids.txt", "r") as selection:
        sents = [s.rstrip() for s in selection.readlines()]

    with open(f"manual_{args.treebank.split('_')[0]}_test.txt", "w",  encoding="utf-8") as output:
        for tree in doc.trees:
            if tree.address() in sents:
                sent_num += 1
                sent_tree = UMRGraph(tree, sent_num, {}, '', set(), {}, {}, {})
                for node in tree.descendants:
                    if node.deprel not in ['aux', 'case', 'punct', 'mark']:
                        item = UMRNode(node, sent_tree, role='')
                umr = sent_tree.to_penman()
                print_structure(tree, sent_tree, sent_num, output)
