import udapi


if __name__ == "__main__":

    treebank = 'it_pud-ud-test.conllu'

    doc = udapi.Document(f'../data/{treebank}')

    with open("../sent-ids_converted_70_test.txt", "r") as selection:
        sents = [s.rstrip() for s in selection.readlines()]

    for tree in doc.trees:
        if tree.address() in sents:
            print(tree.address())
