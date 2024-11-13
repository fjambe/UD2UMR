# TODO - code

Next steps:
- [coding] Big things to work on next: **advcl**, general structure for pronouns, quantities, NEs, ccomp/csubj.
- [coding] `advcl:cmp`.
- [coding] `flat` di NUMs: single number?
- [writing] documentation of external resources (put it in Overleaf). Specify that _cum_ + subjunctive (cum narrativo)
is too polysemous to be automatically disambiguated. Same for _ut_ + subjunctive.
- [decision-making] Can I assign `: aspect performance` safely if `Aspect=Perf|Tense=Past`? Re-check Overleaf. Of course
there will be exceptions like _memini_, but the 80% rule should be satisfied by far. [EASY, THU]
- [evaluation / coding] Check if alignments are decent, by going through them and checking. [EASY, THU]

## General
1. I think it could be useful to have functions specific to UPOS. E.g., for NOUNs I check refer-number, etc.
For PRONs I build the usual NE structure, and so on.

## Notes

### Deprel:
- `nsubj`:
  - Only one `nsubj` is allowed, so mapping it to `actor` shouldn't be a problem (univocal).
  - `nsubj:pass` handled like `obj` -> `patient`.
  - think about `csubj`.
- `obj`:
  - think about `theme`.
- `advmod:lmod` could be mapped to `place`, but it's risky because it could also be `source`, `goal`, depending on the type of adverb.
On top of that, most often this deprel is assigned to adverbs (_unde_, _hinc_), which could also be discourse connectives.
Maybe if they're annotated with the subtype `lmod` is because they're actually still lexicalized, but let's not trust the annotation too much.
- `nmod`: now I have a placeholder `:MOD/POSS`. Impossible to distinguish - UD has `nmod:poss` but not Perseus.
- `appos`: `identity-91`.
Cf. _Homo bellus, tam bonus Chrysanthus animam ebulliit._ "The handsome man, so good, Chrysanthus breathed out his spirit."
_Chysanthus_ `appos` di _homo_.

### UPOS:
None

### To Penman
To parse my structure into Penman, it has (?) to look like this:
```
    {
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
2. `tree.text`: prints out the actual sentence. So tech_root = tree.
3. `tree.children`: prints out the single direct children of the technical `<ROOT>`, i.e. the actual root.
UD trees are single-rooted, so `len(tree.children)` == 1, always.
4. `tree.descendants`: prints out the whole tree, i.e. all the nodes.


## Unresolved/postponed issues:
- re-entrancies: since it's coreference, it wasn't handled in IGT. It's hard to check that it's the same entity.
I could do it for 1st and 2nd person PRONs/ADJs, if they belong to the same subtree, but it would be a dirty hack. 
The simplest option as of now is just postponing it, as done in IGT.
Cf. _Hoc mihi dicit fatus meus_: now I have 2 distinct 1st/2nd-person nodes, but it should be the same one.
- How to reorder ARGs: for the purpose of clarity, I'd like to rearrange the order e.g. in:

```
(h / have-mod-91
    :ARG2 (s / sucossus
        :manner (v / validus))
    :aspect state
    :ARG1 (f / FILL
        :refer-number plural)) 
```

Matt said he faced the same issue and there's no straightforward strategy in Penman library to control this.
Now I have a function that kinda does it, although not perfectly - but it's at least way less confusing.

- [discussed, agreed for now] Let's have the `aspect` attribute in the sentence, although without any value (just the
string `:aspect` ready for the annotator to fill in the value), everytime I have a predicate. Given that I cannot
extract automatically the aspect value.
To me, it feels like it depends on what the goal is: make annotators' job easier or claim to get UMRs automatically?
After discussing it with Alexis, we came to the conclusion that it would definitely be beneficial for annotators.
I still think it will be confusing when it comes to evaluation, but it's gonna be very easy to remove (not add it, 
actually) if I don't want it anymore in my UMRs. It's one line of code. Maybe discuss it with Dan. 


## QUESTIONS:
- [all] negation (`advmod:neg` as `:modal-strength full-negative`). As of now I am following the 80% of the times rule.
There are of course exceptions: now we have negative modality annotated for nouns (which are supposed to be events, but
they are not overt).
C.f., e.g., _Puerum basiavi frugalissimum, **non** propter formal, sed quia frugi est_ (from Perseus_test).
I could also implement an additional check for UPOS (= only VERB). What do you prefer?
- [Julia] abstract rolesets seem to always have `:aspect state`: correct? [mail]
- [Julia] UMR of _boves, quorum beneficio panem manducamus_ "oxen, thanks to whose service we eat bread"? [mail]

## For Dan:
- what to do with _nec_ split as _ne_ + _c_? o li unisco in Perseus o li tratto in UMR.
- show him the Appendix 3 about copular constructions. 
- elided arguments: we cannot do anything to restore objects, as they are undetectable, but we can restore subject.
What has been decided so far is that, in the case of elided subjects, I will restore it. However, how can I tell if person or thing?
IGT said: if in 80% of the cases it's `person`, just go for `person`.
However, going through the data, I have the feeling that in the case of 3rd person verbs it's not anywhere close to 80%. Latin topics can be crazy.
So, what I have now is `person` when the verb is a 1st/2nd person form;
otherwise, I have a placeholder `FILL` that the annotator will quickly replace with the correct entity (`person`/`thing`) manually. Ok?
- Do you think it's safe to extend the non-overt-copula processing to all copular constructions?
Basically removing the constraint "no cop in siblings", and merge the two checks.
Result: no relying explicitly on the cop deprel. Explain the whole situation as it is now.
- Empty aspect in UMRs.

## Details:
- `advmod` = `manner` --> _ideo_ ends up being `manner`, while I would have either `cause` or maybe even nothing.

## ERRORS TO FIX:
- There is still a problem with coordination, cf. SNT:
_atque ego haec non in M. Tullio neque his temporibus vereor, sed in magna civitate multa et varia ingenia sunt._
Yet, it's a crazy structure, it can most probably be ignored.