def numbered_line_with_alignment(tree):
    """
    Prints a line of words with progressive numbering centered above each word for visual alignment. It takes in input
    a Udapi tree (tree), and prints out two lines:
      - `Words`: A single line with the words separated by spaces.
      - `Index`: A single line with indexes aligned to appear centered below each word.
    """
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

    print(f'Index: {index_line}')
    print(f'Words: {word_line}')


def print_structure(tree, sent_tree, umr):
    """
    Prints a structured UMR representation, including the sentence id, text, sentence-level graph, and alignments.
    Takes in input:
    - tree: Udapi tree.
    - sent_tree: UMRGraph
    - umr: the UMR graph itself.
    """

    print(f'# sent_id = {tree.address()}')
    print('# :: snt')  # progressive numbering to be implemented
    numbered_line_with_alignment(tree)
    print(f'Sentence: {tree.text}', '\n')
    print('# sentence level graph:')
    print(umr, '\n')
    print('# alignment:')
    sent_tree.alignments()
    print('\n')
