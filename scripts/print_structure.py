import sys
import penman
from penman.exceptions import LayoutError

from umr_graph import reorder_triples

def numbered_line_with_alignment(tree, output_file=None):
    """
    Prints a line of words with progressive numbering aligned to the left of each word.
    It takes in input a Udapi tree (tree) and prints out two lines:
      - `Index`: A single line with indexes aligned to appear above each token, aligned to the left.
      - `Words`: A single line with the tokens separated by spaces.
    """
    destination = output_file if output_file else sys.stdout
    words = [t.form for t in tree.descendants]

    word_line = ''.join(
        word + (' ' * 2 if len(word) == 1 and i > 9 else ' ')
        for i, word in enumerate(words, start=1)
    ).strip()

    index_line_parts = []
    current_pos = 0

    for i, word in enumerate(words, start=1):
        index_str = str(i)

        # Ensure the index starts at the correct position
        while len(''.join(index_line_parts)) < current_pos:
            index_line_parts.append(' ')  # Fill spaces until alignment is correct

        index_line_parts.append(index_str)
        min_spacing = 1 if (len(word) > 1 or (len(word) == 1 and len(index_str) == 1)) else 2
        current_pos += len(word) + min_spacing  # Adjust position for the next word

    index_line = ''.join(index_line_parts)

    print(f'Index: {index_line}', file=destination)
    print(f'Words: {word_line}', file=destination)


def print_structure(tree, sent_tree, umr, root, sent_num, output_file=None, print_in_file=False):
    """
    Prints a structured UMR representation, including the sentence id, text, sentence-level graph, and alignments.
    Takes in input:
    - tree: Udapi tree.
    - sent_tree: UMRGraph
    - umr: the UMR graph itself.
    - sent_num: the progressive number of the sentence.
    """

    destination = output_file if print_in_file else sys.stdout

    umr_string = None
    if umr:
        try:
            umr_string = penman.encode(umr, top=root, indent=4)
        except LayoutError as e:
            for n in reorder_triples(sent_tree.triples):
                print(n)
            print(f"Skipping sentence due to LayoutError: {e}")

    print('#' * 80, file=destination)
    print(f'# meta-info :: sent_id = {tree.address()}', file=destination)
    print(f'# :: snt{sent_num}', file=destination)
    numbered_line_with_alignment(tree, destination)
    print(f'Sentence: {tree.text}', file=destination)
    if sent_tree.lang != 'en':
        en_sent = [c for c in tree.comment.split('\n') if c.startswith(" text_en = ")]
        if en_sent:
            print('Sentence Gloss (en):', f"{en_sent[0].lstrip(' text_en = ')}", file=destination)
        print(file=destination)
    else:
        print(file=destination)
    print('# sentence level graph:', file=destination)

    if umr_string and len(umr_string) > 2:
        print(umr_string, file=destination)
        print(file=destination)
        print('# alignment:', file=destination)
        sent_tree.alignments(umr, output_file)
        print(file=destination)
        print('# document level annotation:', file=destination)
        print('\n', file=destination)
    else:
        print(f'({sent_tree.root_var} / sentence)', file=destination)
        print(file=destination)
        print('# alignment:', file=destination)
        print(file=destination)
        print('# document level annotation:', file=destination)
        print('\n', file=destination)
