# UD2UMR
This repository contains all materials for the UD2UMR project, which provides a tool to convert any Universal
Dependencies (UD) treebank into a Uniform Meaning Representation (UMR) graph. \
The converter only handles sentence-level graphs and alignments; document-level annotation has not been implemented.

## Set up
The UD2UMR converter requires the Python packages `penman`, `udapi` `word2number`, `googletrans==4.0.0-rc1`, all listed
in the `requirements.txt` file.

```commandline
pip install -r requirements.txt
```

**TODO**: double check udapi.

The UD2UMR converter has been tested with Python 3.9.5.

## Usage
To run the code, two arguments are required:
* `--treebank`: the name of the input CoNLL-U file (treebank). The converter supports any UD (v2.x) treebank as input.
* `--lang`: the language of the input treebank.

For example, in order to convert the English PUD test file to UMR, run the following:

```commandline
python3 main.py --treebank en_pud-ud-test.conllu --lang en
```

To convert the English example stored in `data/`, run the following:
```commandline
python3 main.py --treebank en_example.conllu --lang en
```

The CoNLL-U files to be passed in input are expected to be stored in a `data/` directory;
however, a different directory can be specified using the `--data_dir` command line argument. For example:

```commandline
python3 main.py --treebank en_pud-ud-test.conllu --lang en --data_dir /directory/with/conllu/file
```

Converted UMRs will be saved in an `output/` folder, which will be created by the converter if it doesn't already exist.
You can also specify a different output directory (either an existing one or one to be created by the converter) using
the `--output_dir` argument. For example:

```commandline
python3 main.py --treebank en_pud-ud-test.conllu --lang en --output_dir /directory/to/store/umrs
```

## Structure of this repository

* The `data/` folder contains `en_example.conllu`, a sample input file with a single sentence.
* All necessary python scripts are in the `scripts/` folder.
* External resources providing language-specific lexical information can be found in the `external_resources/` folder.
Each language has its own subdirectory, where the files are named `advcl.csv`, `have-rel-role,txt`, `modality.json`.
Language-specific material for additional languages should be stored in the same way.
It is not required to include all three files; you may include one or two only.

```
UD2UMR
├── requirements.txt                        # required dependencies
├── scripts
│ ├── main.py                               # main conversion script (to run) 
│ ├── umr_graphs.py
│ ├── umr_node.py
│ └── preprocess.py      
├── data                                    # folder for input treebanks 
│ ├── en_example.txt                        # example conllu
├── external_resources                      # folder for language-specific information
│ ├── cs                                    # materials for Czech
│ │ ├── advcl.csv
│ │ ├── have-rel-role.txt
│ ├── en                                    # materials for English
│ │ ├── advcl.csv
│ │ ├── have-rel-role.txt
│ │ ├── modality.json
│ ├── it                                    # materials for Italian
│ │ ├── advcl.csv
│ │ ├── have-rel-role.txt
│ │ ├── modality.json
│ ├── la                                    # materials for Latin
│ │ ├── advcl.csv
│ │ ├── have-rel-role.txt
│ │ ├── modality.json   
├── README.md         
```

## Contact
* Federica Gamba (ÚFAL, MFF, Charles University, Prague, Czech Republic): `gamba at ufal.mff.cuni.cz`