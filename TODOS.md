# TODO - code

### General
1. I think it could be useful to have functions specific to UPOS. E.g., for NOUNs I check refer-number, etc.
For PRONs I build the usual NE structure, and so on.
2. Big things to work on next: copular constructions, relative clauses.


### Deprel:
- `nsubj`:
  - Only one `nsubj` is allowed, so mapping it to `actor` shouldn't be a problem (univocal).
  - `nsubj:pass` handled like `obj`.
  - think about coordinate subjects.
  - think about `csubj`.
- `obj`:
  - think about `theme`.
  - think about coordinate objects.
- `advmod:lmod` could be mapped to `place`, but it's risky because it could also be `source`, `goal`, depending on the type of adverb.
On top of that, most often this deprel is assigned to adverbs (_unde_, _hinc_), which could also be discourse connectives.
Maybe if they're annotated with the subtype `lmod` is because they're actually still lexicalized, but let's not trust the annotation too much.
- `nmod`: now I have a placeholder `:MOD/POSS`. Impossible to distinguish - UD has `nmod:poss` but not Perseus.
- `appos`: what to do with it?

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
1. `tree`: prints out the technical `<ROOT>` of the sentence (== `tree`).
2. `ree.text`: prints out the actual sentence. So tech_root = tree.
3. `tree.children`: prints out the single direct children of the technical `<ROOT>`, i.e. the actual root.
UD trees are single-rooted, so `len(tree.children)` == 1, always.
4. `tree.descendants`: prints out the whole tree, i.e. all the nodes.


## QUESTIONS:
- re-entrancies: how to check that it's the same entity?
Cf. _Hoc mihi dicit fatus meus_, _Votoque tuo tua forma repugnat_: now I have 2 distinct 1st/2nd-person nodes, but it should be the same one.
- elided subjects (how can I tell if person or thing?)
- broken graphs often mean annotation errors [this is a comment]
- `appos`: what to do with it? Cf. _Homo bellus, tam bonus Chrysanthus animam ebulliit._ "The handsome man, so good, Chrysanthus breathed out his spirit."
_Chysanthus_ now `appos` di _homo_.
- Big things to work on next: copular constructions, relative clauses.



## Details:
- `advmod` = `manner` --> _ideo_ ends up being `manner`, while I would have either `cause` or maybe even nothing. Same for _etiam_.