import csv, json
import re
from typing import Union
from googletrans import Translator
from word2number import w2n

def get_deprels(ud_tree) -> dict:
    """ Map UD deprels to UMR roles, mostly based on UD deprels. """

    mapping_conditions = {
        'root': lambda d: d.deprel == 'root',  # All children are included for 'root'
        'actor': lambda d: d.deprel in ['nsubj', 'csubj', 'obl:agent'],
        'undergoer': lambda d: d.deprel in ['obj', 'nsubj:pass', 'csubj:pass'],
        'theme': lambda d: d.deprel == 'ccomp:reported',
        'stimulus': lambda d: d.deprel in ['xcomp', 'ccomp'],
        'mod': lambda d: d.deprel == 'amod' or (d.udeprel == 'nmod' and d.sdeprel != 'poss' and d.feats.get('Case') != 'Gen'),
        'OBLIQUE': lambda d: d.udeprel == 'obl' and d.sdeprel != 'arg', # and d.feats.get('Case') != 'Dat',
        'det': lambda d: d.udeprel == 'det',
        'manner': lambda d: d.udeprel == 'advmod' and d.sdeprel not in ['neg', 'tmod', 'lmod'] and d.feats['Polarity'] != 'Neg',
        'temporal': lambda d: d.deprel in ['advmod:tmod', 'obl:tmod'],
        'location': lambda d: d.deprel == 'advmod:lmod',
        'quant': lambda d: d.deprel == 'nummod' or d.sdeprel in ['nummod', 'numgov'],
        'vocative': lambda d: d.deprel == 'vocative',
        'affectee': lambda d: d.deprel in ['iobj', 'obl:arg'] or (d.deprel == 'obl' and d.feats.get('Case') == 'Dat'),
        'MOD/POSS': lambda d: d.deprel == 'nmod' and d.feats.get('Case') == 'Gen',
        'possessor': lambda d: d.sdeprel == 'poss',
        'identity-91': lambda d: d.deprel == 'appos',
        'COPULA': lambda d: d.deprel == 'cop',
        'conj': lambda d: d.deprel == 'conj',
        'other': lambda d: d.udeprel in ['advcl', 'punct', 'cc', 'fixed', 'flat', 'mark', 'xcomp', 'dislocated', 'aux',
                                         'discourse', 'acl', 'case', 'compound', 'parataxis', 'dep', 'orphan']
    }

    deprels = {rel: [d for d in ud_tree.descendants if condition(d)] for rel, condition in mapping_conditions.items()}

    return {k: v for k, v in deprels.items() if v}


def get_role_from_deprel(ud_node, deprels):
    """
    Check if a node is in any of the value lists in the deprels dictionary.
    If it is, return the corresponding key. If not, return None.

    Parameters:
    - ud_node:  node to search for in the deprels dictionary.
    - deprels: dictionary where keys are roles and values are lists of nodes.
    """
    for mapped_role, nodes in deprels.items():
        if ud_node in nodes:
            return mapped_role
    return None


def load_external_files(filename: str, language: str) -> Union[set, dict]:
    """
    Store language-specific information. Used for:
    1. interpersonal relations (filename: have_rel_role.txt);
    2. SCONJs determining the type of adverbial clauses (advcl.csv).
    3. VERBs entailing different values for modality (filename: modality.json);
    4. disambiguated conjunctions (filename: conj.json).
    """

    extension = filename.split('.')[-1]
    terms = set() if extension == 'txt' else dict()

    try:
        with open(f"./external_resources/{language}/{filename}", 'r') as f:
            if extension == 'txt':
                terms = {line.strip() for line in f if line.strip()}
            elif extension == 'csv':
                reader = csv.reader(f)
                next(reader)
                for line in reader:
                    terms[line[0]] = {'type': line[1], 'constraint': line[2].split('|') if line[2] else None}
            elif extension == 'json':
                terms = json.load(f)
        return terms

    except FileNotFoundError:
        print(f"File {filename.split('/')[-1]} not found. Lexical information not available.")


def is_number(text):
    """ Regular expression for a valid number with optional commas, decimals, or scientific notation. """
    pattern = r'^[+-]?(\d{1,3}(,\d{3})*|\d+)([\.,]\d+)?([eE][+-]?\d+)?$'
    return bool(re.match(pattern, text))


def translate_number(numeral, input_lang):
    """
    Translates a given numeral from the specified input language to English and converts it to a digit.

    Args:
        numeral (str): The numeral to be translated.
        input_lang (str): The language code of the input numeral.

    Returns:
        int: The numeric value of the translated numeral.
    """
    translator = Translator()

    if input_lang != 'en':
        if not is_number(numeral):
            try:
                translator.raise_Exception = True
                translation = translator.translate(numeral, src=input_lang, dest='en')
                en_text = translation.text
                return w2n.word_to_num(en_text)

            except ValueError: # as e:
                # print(f"Conversion error occurred: {e}")
                return numeral

            except Exception as e:
                print(f"Unexpected error occurred: {e}")
                return numeral
        else:
            return numeral
    else:
        if not is_number(numeral):
            try:
                return w2n.word_to_num(numeral)
            except ValueError:
                return numeral
        else:
            return numeral
