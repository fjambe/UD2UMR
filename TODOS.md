# TODO - code

Next steps:
- [coding] Big things to work on next: `advcl:cmp` + all remaining `advcl`s (e.g., `advcl:abs`) as just `ADVCL`.
- [decision-making] Do I want to support code-switching? Because I specify the language in input, but it could be doable
to check for UFeat `Foreign=Yes` and `Lang=grc` (e.g.) in MISC, and update `self.lang` for processing of numbers.
Not really urgent, not frequent at all.
- [investigation] Reconsider `advmod:lmod`, see below.
- [documentation] Start writing a guide for annotators with a list of the things to check, because they're not perfect
in the automatic conversion (e.g. `patient`/`theme`, `OBLIQUE`, `ADVCL`, `modal-strength`, `aspect`, etc.).
Basically what to pay attention to, what to check.

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
- NUM. Chosen strategy to convert from string to digit: use EN as pivoting language.
Translate instances to EN, use a Python library like `text2num` or `num2words` (also supporting few other languages -
but it feels less language-dependent to just translate everything to EN) to convert the string into a digit,
and include the obtained digit in the UMR graph.


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
- Re-entrancies: since it's coreference, it wasn't handled in IGT. It's hard to check that it's the same entity.
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
I still think it will be confusing when it comes to evaluation, but it's going to be very easy to remove (not add it, 
actually) if I don't want it anymore in my UMRs. It's one line of code. Maybe discuss it with Dan. 


## QUESTIONS:
- [all] negation (`advmod:neg` as `:modal-strength full-negative`). As of now I am following the 80% of the times rule.
There are of course exceptions: now we have negative modality annotated for nouns (which are supposed to be events, but
they are not overt).
C.f., e.g., _Puerum basiavi frugalissimum, **non** propter formal, sed quia frugi est_ (from Perseus_test).
I could also implement an additional check for UPOS (= only VERB). What do you prefer?
- [Julia] How should indefinite pronouns like _somehing_, _someone_ be annotated? I have `person` now, but there's no
mark of (in)definitess now, right?
- [Julia] abstract rolesets seem to always have `:aspect state`: correct? [mail]
- [Julia] UMR of _boves, quorum beneficio panem manducamus_ "oxen, thanks to whose service we eat bread"? [mail]


## For Dan:
- What to do with _nec_ split as _ne_ + _c_? do I merge them in Perseus or handle them in UMR?
Sent tlg0031.tlg027.perseus-lat1.tb.xml@88 in Perseus test.
All other _nec_ s are not split in two as a MWE.
- Is the UFeat _NumValue_ really a thing in UD? Couldn't find much documentation. 
It could be useful for quantities in UMR.
As of now, quantities (`nummod`) are implemented as proper nodes (e.g., `t / ten`), while they should be attributes
(`:quant 10`). The problem is that I cannot extract the number itself if not on a lexical basis, but even so it'd be an
infinite list, so I don't think it's the way to go.
- Participles with `acl` deprel treated as relative clauses - e.g., _the eaten apples_ as _the apples that were eaten_.
For Latin, I have to specify the constraint `Aspect != Prosp`, because otherwise I capture gerund(ive)s - but it does
feel specific to the way Latin is annotated. WHat do you think from a UD perspective: is this true? Solution?
- First implementation of NEs (no NER involved as of now, just detecting PROPNs).
I'm not sure how much adding NER to the pipeline improves the outcome. It would be some effort + it'd be a
language-specific module, while I'm trying to be as language-agnostic as possible (although with limitations).
And in any case I'd end up with very coarse-grained labels (PER, LOC, ORG) that would have to be corrected manually.
- What do I do with `xcomp`? Can you come up with different UMR annotations based on different `xcomp` types (and what
would be the constraints?)?


## Details:
- `advmod` = `manner` --> _ideo_ ends up being `manner`, while I would have either `cause` or maybe even nothing.

## ERRORS TO FIX:
- There is still a problem with coordination, cf. SNT:
_atque ego haec non in M. Tullio neque his temporibus vereor, sed in magna civitate multa et varia ingenia sunt._
Yet, it's a crazy structure, it can most probably be ignored.