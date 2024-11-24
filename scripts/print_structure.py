import sys

def numbered_line_with_alignment(tree, output_file=None):
    """
    Prints a line of words with progressive numbering centered above each word for visual alignment. It takes in input
    a Udapi tree (tree), and prints out two lines:
      - `Words`: A single line with the words separated by spaces.
      - `Index`: A single line with indexes aligned to appear centered below each word.
    """
    destination = output_file if output_file else sys.stdout
    words = [t.form for t in tree.descendants]

    word_line = ' '.join(words)

    index_line_parts = []
    current_pos = 0

    for i, word in enumerate(words, start=1):
        word_length = len(word)
        word_center = word_length // 2
        index_position = current_pos + word_center
        index_line_parts.append(' ' * (index_position - len(''.join(index_line_parts))) + str(i))

        current_pos += word_length + 1

    index_line = ''.join(index_line_parts)

    print(f'Index: {index_line}', file=destination)
    print(f'Words: {word_line}', file=destination)


def print_structure(tree, sent_tree, umr, sent_num, output_file=None, print_in_file=False):
    """
    Prints a structured UMR representation, including the sentence id, text, sentence-level graph, and alignments.
    Takes in input:
    - tree: Udapi tree.
    - sent_tree: UMRGraph
    - umr: the UMR graph itself.
    - sent_num: the progressive number of the sentence.
    """

    destination = output_file if print_in_file else sys.stdout

    if umr:
        print(f'# sent_id = {tree.address()}', file=destination)
        print(f'# :: snt {sent_num}', file=destination)
        numbered_line_with_alignment(tree, destination)
        print(f'Sentence: {tree.text}', '\n', file=destination)
        print('# sentence level graph:', file=destination)
        print(umr, '\n', file=destination)
        print('# alignment:', file=destination)
        sent_tree.alignments(output_file)
        print('\n', file=destination)
    else:
        print(f'# sent_id = {tree.address()}', file=destination)
        print(f'# :: snt {sent_num}', file=destination)
        print(f'Sentence: {tree.text}', file=destination)
        print('Skipping sentence...', '\n', file=destination)

