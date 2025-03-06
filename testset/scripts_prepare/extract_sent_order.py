import udapi


if __name__ == "__main__":

    treebank = 'it_pud-ud-test.conllu'

    doc = udapi.Document(f'../data/{treebank}')

    with open("../converted_70_test_sent_ids.txt", "r") as selection:
        sents = [s.rstrip() for s in selection.readlines()]

    for tree in doc.trees:
        if tree.address() in sents:
            print(tree.address())
