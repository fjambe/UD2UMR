# UD2UMR
This repository contains all materials for the UD2UMR converter, which converts any Universal Dependencies (UD) tree
into a Uniform Meaning Representation (UMR) graph. \
The converter only handles sentence-level graphs and alignments; document-level annotation has not been implemented.

## Set up
The UD2UMR converter requires the Python packages `penman`, `udapi` `word2number`, `googletrans==4.0.0-rc1`, `scikit-learn`,
all listed in the `requirements.txt` file.

```commandline
pip install -r requirements.txt
```

The UD2UMR converter has been tested with Python 3.9.5.

## Usage
To run the code, two arguments are required:
* `--treebank`: the name of the input CoNLL-U file (treebank). The converter supports any UD (v2.x) treebank as input.
* `--lang`: the language of the input treebank.

For example, in order to convert the English PUD test file to UMR, run the following:

```commandline
python3 scripts/main.py --treebank en_pud-ud-test.conllu --lang en
```

To convert the English example stored in `data/`, run the following:
```commandline
python3 scripts/main.py --treebank en_example.conllu --lang en
```

The CoNLL-U files to be passed in input are expected to be stored in a `data/` directory;
however, a different directory can be specified using the `--data_dir` command line argument:

```commandline
python3 scripts/main.py --treebank en_pud-ud-test.conllu --lang en --data_dir /directory/with/conllu/file
```

Converted UMRs will be saved in an `output/` folder, which will be created by the converter if it doesn't already exist.
You can also specify a different output directory (either an existing one or one to be created by the converter) using
the `--output_dir` argument:

```commandline
python3 scripts/main.py --treebank en_pud-ud-test.conllu --lang en --output_dir /directory/to/store/umrs
```

By default, variable names are generated using the first letter of the concept (e.g., `h` for `have-mod-91`).
However, for certain languages (such as Chinese), it may be more appropriate to use a generic variable name like `x`.
You can control this behavior using the `--var_naming` argument, which accepts two values:
- `first` (default): use the first letter of the concept as the variable name.
- `x`: use `x` as the default variable name.

```commandline
python3 scripts/main.py --treebank ky_tuecl-ud-test.conllu --lang ky --var_naming x
```

## Structure of this repository

* The `data/` folder contains `en_example.conllu`, a sample input file with a single sentence.
* All main scripts are in the `scripts/` folder. The `prepare_eval/` subdirectory contains scripts used to prepare the
annotation templates.
* External resources providing language-specific lexical information can be found in the `external_resources/` folder.
Each language has its own subdirectory, where the files are named `advcl.csv`, `have-rel-role,txt`, `modality.json`,
`conj.json`. Language-specific material for additional languages should be stored in the same way.
It is not required to include all three files; you may include as many as available. In any case, the converter works
even without any lexical files.
* The `testset/` folder contains materials used for evaluating the converter.

```
UD2UMR
├── requirements.txt                        # required dependencies
├── scripts
│ ├── prepare_eval (...)                    # scripts to prepare the annotation template           
│ ├── main.py                               # main conversion script (to run) 
│ ├── umr_graphs.py
│ ├── umr_node.py
│ ├── preprocess.py    
│ ├── print_structure.py    
│ ├── evaluate_ancast.py                    # for evaluation
│ └── tests_ancast.py    
├── data                                    # folder for input treebanks 
│ └── en_example.txt                        # example conllu
├── external_resources                      # folder for language-specific information
│ ├── cs                                    # materials for Czech
│ │ ├── advcl.csv
│ │ ├── conj.json
│ │ ├── have-rel-role.txt
│ │ └── modality.json
│ ├── en                                    # materials for English
│ │ ├── advcl.csv
│ │ ├── conj.json
│ │ ├── have-rel-role.txt
│ │ └── modality.json
│ ├── fr                                    # materials for French
│ │ ├── advcl.csv
│ │ ├── conj.json
│ │ ├── have-rel-role.txt
│ │ └── modality.json
│ ├── it                                    # materials for Italian
│ │ ├── advcl.csv
│ │ ├── conj.json
│ │ ├── have-rel-role.txt
│ │ └── modality.json
│ ├── la                                    # materials for Latin
│ │ ├── advcl.csv
│ │ ├── conj.json
│ │ ├── have-rel-role.txt
│ │ └── modality.json
├── testsets                                # materials for evaluation
│ ├── converter-output_total_cs_test.txt
│ ├── converter-output_total_en_test.txt
│ ├── converter-output_total_it_test.txt
│ ├── gold_total_cs_test.txt
│ ├── gold_total_en_test.txt
│ ├── gold_total_it_test.txt
│ ├── sent-ids_manual_30_test.txt
│ └── sent-ids_converted_70_test.txt
└── README.md         
```

## Cite
If you use this project in your work, please cite the following paper:

Gamba, F., Palmer, A., and Zeman, D. (forth.). Bootstrapping UMRs from Universal Dependencies for Scalable Multilingual Annotation.

## Contact
* Federica Gamba (ÚFAL, MFF, Charles University, Prague, Czech Republic): `gamba at ufal.mff.cuni.cz`
