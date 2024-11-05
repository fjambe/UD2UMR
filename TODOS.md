# TODO - code

Next steps:
- [TUE] clean the code, e.g. from comments!
- [decision-making, QUICK] Elided subjects: how can I tell if person or thing?
IGT said: if in 80% of the cases it's `person`, just go for `person`. Right now I have `FILL`.
Have to decide, need to go through the data.
- [decision-making + coding] Generalize `identity-91` > abstract concepts.
- [coding] Big things to work on next: relative clauses, advcl, general structure for pronouns.
- [coding] `flat` di NUMs: single number? In any case I didn't implement quantities yet. But it has to be implemented soon:
Cf. _Fluminis erat altitudo pedum circiter trium_

## General
1. I think it could be useful to have functions specific to UPOS. E.g., for NOUNs I check refer-number, etc.
For PRONs I build the usual NE structure, and so on.

## Notes

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
- `appos`: `identity-91`.
Cf. _Homo bellus, tam bonus Chrysanthus animam ebulliit._ "The handsome man, so good, Chrysanthus breathed out his spirit."
_Chysanthus_ now `appos` di _homo_.

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

### Udapi cheatsheet:
1. `tree`: prints out the technical `<ROOT>` of the sentence (== `tree`).
2. `ree.text`: prints out the actual sentence. So tech_root = tree.
3. `tree.children`: prints out the single direct children of the technical `<ROOT>`, i.e. the actual root.
UD trees are single-rooted, so `len(tree.children)` == 1, always.
4. `tree.descendants`: prints out the whole tree, i.e. all the nodes.


## Unresolved/postponed issues:
- re-entrancies: since it's coreference, it wasn't handled in IGT. It's hard to check that it's the same entity.
I could do it for 1st and 2nd person PRONs/ADJs, if they belong to the same subtree, but it would be a dirty hack. 
The simplest option as of now is just postponing it, as done in IGT.
Cf. _Hoc mihi dicit fatus meus_: now I have 2 distinct 1st/2nd-person nodes, but it should be the same one.


## QUESTIONS:
- Do you think it would be better to have the `aspect` attribute in the sentence, although without any value (just the string `:aspect` ready for the annotator to fill in the value) or not having anything at all?
Given that I cannot extract automatically the aspect value.
- [Matt]: do you have a smart way to reorder ARGs? For the purpose of clarity, I'd like to rearrange the order e.g. in:

```
(h / have-mod-91
    :ARG2 (s / sucossus
        :manner (v / validus))
    :aspect state
    :ARG1 (f / FILL
        :refer-number plural)) 
```

- [Julia] `flat` di NUMs: single number? In any case I didn't implement quantities yet.
- [Julia] abstract rolesets seem to always have `:aspect state`: correct?

## For Dan:
- what to do with _nec_ split as _ne_ + _c_? o li unisco in Perseus o li tratto in UMR.
- show him the Appendix 3 about copular constructions. 

## Details:
- `advmod` = `manner` --> _ideo_ ends up being `manner`, while I would have either `cause` or maybe even nothing.

## ERRORS TO FIX:
1. Brand-new entities + coordination: the parent is fucked up.
```SNT: Ergo omnes magno circum clamore fremebant, praecipue pius Aeneas. 

(f / fremo
    :actor (f2 / FILL
        :quant (a2 / and
            :op1 (o / omnis)
            :op2 (a / Aeneas
                :mod (p / pius)
                :manner (p2 / praecipuus)))
        :refer-number plural)
    :OBLIQUE (c / clamor
        :refer-number singular
        :mod (m / magnus))
    :manner (c2 / circum))
```