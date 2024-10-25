# TODO - code

### General
1. I think it could be useful to have functions specific to UPOS. E.g., for NOUNs I check refer-number, etc.
For PRONs I build the usual NE structure, and so on.
2. I need to create a node (how can I tell if person or thing?) for unexpressed subjects, that I can tell from verbal agreement.
3. Re-entrancies: how to check that it's the same entity?
Cf. sentence _Votoque tuo tua forma repugnat_: now I have 2 distinct 2nd-person nodes, but it should be the same one.


### Deprel:
- `nsubj`:
  - Only one `nsubj` is allowed, so mapping it to `actor` shouldn't be a problem (univocal).
  - `nsubj:pass` handled like `obj`.
  - think about coordinate subjects.
  - think about `csubj`.
- `obj`:
  - think about `theme`.
  - think about coordinate objects.
- `obl`
  - think about `obl:arg` and possible other subtypes.
- `advmod:lmod` could be mapped to `place`, but it's risky because it could also be `source`, `goal`, depending on the type of adverb.
On top of that, most often this deprel is assigned to adverbs (_unde_, _hinc_), which could also be discourse connectives.
Maybe if they're annotated with the subtype `lmod` is because they're actually still lexicalised, but let's not trust the annotation too much.


### UPOS:
- think about `PRON`s.

### To Penman
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

## Udapi cheatsheet:
1. tree: prints out the technical <ROOT> of the sentence (== tree).
2. tree.text: prints out the actual sentence. So tech_root = tree.
3. tree.children: prints out the single direct children of the technical ROOT, i.e. the actual root.
UD trees are single-rooted, so len(tree.children) == 1, always.
4. tree.descendants: prints out the whole tree, i.e. all the nodes.


## QUESTIONS:
- UD vocative, what in UMR?


## Details:
- advmod = manner --> _ideo_ manner, while I would have either cause or nothing.