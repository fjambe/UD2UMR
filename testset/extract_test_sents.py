import random

def select_sentences(dataset):
    news = {"01": [], "02": [], "03": [], "04": [], "05": []}
    wiki = {"01": [], "02": [], "03": [], "04": [], "05": []}

    for snt in dataset:
        lang_code = snt[1:3]

        if snt[0] == 'n':
            news[lang_code].append(snt)
        elif snt[0] == 'w':
            wiki[lang_code].append(snt)

    selected = []

    # Select 35 sentences from news and 35 from Wikipedia, distributed across all languages
    for language in ["01", "02", "03", "04", "05"]:
        # Randomly choose 7 news sentences and 7 wiki sentences for each language
        selected.extend(random.sample(news[language], 7))
        selected.extend(random.sample(wiki[language], 7))
    return selected


with open("../data/en_pud-ud-test.conllu") as file:
    sent_ids = []
    for line in file:
        if line.startswith("# sent_id"):
            code = line.split(" = ")[1].strip()
            sent_ids.append(code)

selected_sentences = sorted(select_sentences(sent_ids))

with open("converted_70_test_sent_ids.txt", "w") as output:
    for s in selected_sentences:
        output.write(s + '\n')