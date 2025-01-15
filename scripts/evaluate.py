#!/usr/bin/env python3
# Copyright © 2024 Federica Gamba <gamba@ufal.mff.cuni.cz>

import argparse
import penman
import pandas as pd

import tests

def extract_umr_graph(file_path):
    """
    Extracts the UMR graph section from a text file.

    Args:
        file_path (str): The path to the input text file containing the UMR graphs.

    Returns:
        list of penman.Graphs: A list of Penman graphs loaded from the extracted UMR graph section.
    """
    with open(file_path) as file:
        in_graph_section = False
        graph_lines = []

        for line in file:
            stripped_line = line.lstrip()
            if stripped_line.startswith('#'):
                if "sentence level graph" in stripped_line:
                    in_graph_section = True
                elif in_graph_section:
                    # End of UMR graph section at the next comment line
                    in_graph_section = False
            elif in_graph_section:
                graph_lines.append(line)

    graph_data = ''.join(graph_lines)  # join the graph lines into a single string
    return penman.loads(graph_data)

def run_tests(predicted, gold):
    """ Runs the evaluation tests on predicted and gold UMR graphs. """
    # TODO: implement check of sent number (assert snt number is the same) and do something (check, assert?) same number of sentences
    data = [
        ("modal-strength", "strength", "accuracy", tests.modal_strength(predicted, gold)[0]),
        ("modal-strength", "polarity", "accuracy", tests.modal_strength(predicted, gold)[1]),
        ("abstract predicates", "predicate", "accuracy", tests.abstract(predicted, gold)[0]),
        ("abstract predicates", "dependent ARGs", "recall", tests.abstract(predicted, gold)[1]),
        ("abstract predicates", "ARGs nodes", "accuracy", tests.abstract(predicted, gold)[2]),
        ("refer-number (entities)", "-", "accuracy", tests.pronouns(predicted, gold)[0]),
        ("refer-person (entities)", "-", "accuracy", tests.pronouns(predicted, gold)[1]),
        ("inverted relations", "parent", "accuracy", tests.inverted_relations(predicted, gold)[0]),
        ("inverted relations", "edge", "accuracy", tests.inverted_relations(predicted, gold)[1])
    ]
    # tests.coordination(predicted, gold)

    df = pd.DataFrame(data, columns=["Type", "Sub-type", "Metric", "Score"])
    print(df.to_string(index=False))

parser = argparse.ArgumentParser()
parser.add_argument("--converted", help="Path of the converted file to evaluate.", required=True)
parser.add_argument("--gold", help="Path of the gold standard file for evaluation.", required=True)


if __name__ == "__main__":

    args = parser.parse_args()
    converted_data = extract_umr_graph(args.converted)
    gold_data = extract_umr_graph(args.gold)
    run_tests(converted_data, gold_data)