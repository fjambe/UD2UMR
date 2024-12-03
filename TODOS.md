# TODO - code

Next steps:
- [coding] Poi non resta che analizzare i disconnected graphs e capire perchè, come correggerli, come produrre
UMRs incomplete piuttosto che niente.

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
- PRON. Indefinite pronouns like _something_, _someone_ are annotated as a `person` entity + a `mod` for _some_. Same
for _any_.


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

- [postponed, irrelevant] Do I want to support code-switching? Because I specify the language in input, but it could be
doable to check for UFeat `Foreign=Yes` and `Lang=grc` (e.g.) in MISC, and update `self.lang` for processing of numbers.
Not really urgent, not frequent at all.


## QUESTIONS:
- [all] negation (`advmod:neg` as `:modal-strength full-negative`). As of now I am following the 80% of the times rule.
There are of course exceptions: now we have negative modality annotated for nouns (which are supposed to be events, but
they are not overt).
C.f., e.g., _Puerum basiavi frugalissimum, **non** propter formal, sed quia frugi est_ (from Perseus_test).
I could also implement an additional check for UPOS (= only VERB). What do you prefer?
- [Julia] UMR of _boves, quorum beneficio panem manducamus_ "oxen, thanks to whose service we eat bread"? [mail]
- [observation] In UMR guidelines, 3-1-4 (2):

```
并且 还 有 很多 高层 的 人物 哦 ！
There will even be many VIPs!
(x/ and
     :op2 (e/ exist-91
           :mod (x2/ 还)
           :ARG2 (x3/ 人物
                  :mod (x4/ 高层)
                  :quant (x5/ 很多))
           :mode Expressive
       :aspect State
       :modstr FullAff))
```
But in 3-3-2. Mode it reads:
"`expressive`: used for exclamational words such as hmm, wow, yup etc., which express emotion but don't clearly refer 
to events, objects or properties, as in (1a). This value is not used for mere emphasis, or for exclamation marks."
Confusing. It's maybe because of _even_?

- [Julia, IMP] English modals (4-3-2) reads
"For example, _want_ is in the `NeutAff` list, which indicates that there is a `NeutAff` link between the want node and
its complement event node in the full dependency structure."
However, in all the graphs in the guidelines the complement event node is not annotated wrt `modal-strength`, but
`modal-predicate`. I assume `modal-predicate` is the correct one (right?), and yet this sentence can be very misleading.
And what am I supposed to do with _hope, fear, worry, dread_? _Need_? All of them, actually.
- [Matt] Do you know how to prevent some triples from inverting? E.g., I do not want `modal-predicate-of`, and it keeps
changing every time I rerun the script.


## For Dan:
- What to do with _nec_ split as _ne_ + _c_? do I merge them in Perseus or handle them in UMR?
Sent tlg0031.tlg027.perseus-lat1.tb.xml@88 in Perseus test.
All other _nec_ s are not split in two as a MWE.
- Is it okay to treat both UD `Degree={Sup,Abs}` as UMR `most`?
- What should `compound` be in UMR? We can take CS as an example.
- Eventually I ended up facing the issue of Too many requests (429) for Google Translate, as expected. The stable
library is https://pypi.org/project/google-cloud-translate/, but it comes with quota and more limitations as it is
official. Can you think of an alternative to make it more stable?
- _Consumer Technology Association_ is `flat` in CS but `compound` in EN. In FR è tutto X e `flat:foreign`. Se anche
riuscissimo a riconoscerla come una NE (ma UPOS è quasi sempre NOUN), non avremmo un trattamento omogeneo.
Suggestions?
- What to do in general with `flat:foreign` (FR), `fixed` (FR) and `compound` (CS)?


## Details:
- `advmod` = `manner` --> _ideo_ ends up being `manner`, while I would have either `cause` or maybe even nothing.

## ERRORS TO FIX:
- There is still a problem with coordination, cf. SNT:
_atque ego haec non in M. Tullio neque his temporibus vereor, sed in magna civitate multa et varia ingenia sunt._
Yet, it's a crazy structure, it can most probably be ignored.

