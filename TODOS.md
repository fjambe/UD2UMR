# TODO - code
Those kind of notes I would just put in the code and make it messy :D
So let's be tidy this time!

### General
1. I think it could be useful to have function specific to UPOS. E.g., for NOUNs I check refer-number, etc.
For PRONs I build the usual NE structure, and so on.
2. I need to create a node (how can I tell if person or thing?) for unexpressed subjects, that I can tell from verbal agreement.



### Deprel:
- `nsubj`:
  - Only one `nsubj` is allowed, so mapping it to `actor` shouldn't be a problem (univocal).
  - think about `nsubj:pass` and passive sentences.
  - think about coordinate subjects.
  - think about `csubj`.
- `obj`:
  - think about `theme`.
  - think about coordinate objects.
- `obl`
  - think about `obl:arg` and possible other subtypes.


### UPOS:
- think about `PRON`s.

### TO Penman
To parse my structure into Penman, it has (?) to look like this:
```
    return {
        root: {
            ":actor": subj,
            ":patient": obj,
            "mod": [mod for mod in mods],
            "OBLIQUE": [obl for obl in obliques]
        }
    }
```
It might be useful later on.



## Udapi cheatsheet:
1. tree: prints out the technical <ROOT> of the sentence (== tree).
2. tree.text: prints out the actual sentence. So tech_root = tree.
3. tree.children: prints out the single direct children of the technical ROOT, i.e. the actual root.
UD trees are single-rooted, so len(tree.children) == 1, always.
4. tree.descendants: prints out the whole tree, i.e. all the nodes.


## QUESTIONS:
- UD vocative, what in UMR?

