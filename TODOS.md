# TODO - UD2UMR converter

Next steps:
- [Monday morning] Ask for a venue for the conversion work (besides DSM in Prague). Maybe after I figure out something
more about the evaluation.
- [coding] do something about nominal ADVCL (e.g. add abstract concept `have-role-91`/`identity-91`).
Maybe something similar with `stimulus` for nominal `x|ccomp` + nominal `condition`.
- check _città stato di Atene_

## General
1. I think it could be useful to have functions specific to UPOS. E.g., for NOUNs I check `refer-number`, etc.
For PRONs I build the usual NE structure, and so on.

## Notes
Currently disconnected graphs:

| Language        | Disconnected | Empty_triples |
|:----------------|:------------:|--------------:|
| en_pud          |  11 / 1000   |             4 |
| it_pud          |   9 / 1000   |             4 |
| fr_pud          |  12 / 1000   |             5 |
| cs_pud          |   4 / 1000   |             1 |
| la_perseus_test |   22 / 939   |            13 |


### UD deprels:
- `nsubj`:
  - Only one `nsubj` is allowed, so mapping it to `actor` shouldn't be a problem (univocal).
  - `nsubj:pass` handled like `obj` -> `patient`.
- `advmod:lmod` could be mapped to `place`, but it's risky because it could also be `source`, `goal`, depending on the type of adverb.
On top of that, most often this deprel is assigned to adverbs (_unde_, _hinc_), which could also be discourse connectives.
Maybe if they're annotated with the subtype `lmod` is because they're actually still lexicalized, but let's not trust the annotation too much.
- `nmod`: now I have a placeholder `:MOD/POSS`. Impossible to distinguish - UD has `nmod:poss` but not Perseus.
- `appos`: `identity-91`.
Cf. _Homo bellus, tam bonus Chrysanthus animam ebulliit._ "The handsome man, so good, Chrysanthus breathed out his spirit."
_Chysanthus_ `appos` di _homo_.

### UD UPOS:
- NUM. Chosen strategy to convert from string to digit: use EN as pivoting language.
Translate instances to EN, use a Python library like `text2num` or `num2words` (also supporting few other languages -
but it feels less language-dependent to just translate everything to EN) to convert the string into a digit,
and include the obtained digit in the UMR graph.
- PRON. Indefinite pronouns like _something_, _someone_ are annotated as a `person` entity + a `mod` for _some_. Same
for _any_.

### UMR guidelines
- [modal-predicate] English modals (4-3-2) reads
"For example, _want_ is in the `NeutAff` list, which indicates that there is a `NeutAff` link between the want node and
its complement event node in the full dependency structure."
However, in all the graphs in the guidelines the complement event node is not annotated wrt `modal-strength`, but
`modal-predicate`. I assume `modal-predicate` is the correct one (right?), and yet this sentence can be very misleading.
And what am I supposed to do with _hope, fear, worry, dread_? _Need_? All of them, actually.
Apparently BOTH, because `modal-predicate` is just a shortcut to extract the polarity of the modal verb, used by the
UMR Writer and Jin's postprocessing to build up doc-level annotation. Neither `modal-strength` nor `modal-predicate`
are supposed to appear in the sentence-level graph. Also, the `unspecified` value in doc-level is valid only for stage 0.

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

- Negation (`advmod:neg` as `:modal-strength full-negative`). As of now I am following the 80% of the times rule.
There are of course exceptions: now we have negative modality annotated for nouns (which are supposed to be events, but
they are not overt).
C.f., e.g., _Puerum basiavi frugalissimum, **non** propter formal, sed quia frugi est_ (from Perseus_test).
I could also implement an additional check for UPOS (= only VERB), but maybe it would be too restraining.


## QUESTIONS:
- How many sentences do you think I need for evaluation?
- [Julia] Guidelines: "Weak deontic modals, including desire (e.g., want) and permission (e.g., allow), impart NeutAff strength
on their complements. Certain modals may also lexicalize negation, such as doubt, forbid, or wish. These are annotated
with the NeutNeg, PrtNeg, and FullNeg values, respectively." --> why permission == neutral vs forbid partial?
- [Julia] Double negation with modals, or kind of. E.g., I forbid you from not eating.

```
(f / forbid
    :ARG0 (p / person
           :refer-number singular
           :refer-person plural)
    :ARG1 (e / eat
            :aspect ...
            :modal-strength partial-affirmative)   ???
    :aspect ...
    :modal-strength full-affirmative)
```

## For Dan:
- What to do with _nec_ split as _ne_ + _c_? do I merge them in Perseus or handle them in UMR?
Sent tlg0031.tlg027.perseus-lat1.tb.xml@88 in Perseus test.
All other _nec_ s are not split in two as a MWE.
- Is it okay to treat both UD `Degree={Sup,Abs}` as UMR `most`?
- _Consumer Technology Association_ is `flat` in CS but `compound` in EN. In FR è tutto X e `flat:foreign`. 
- What to do in general with `flat:foreign` (FR), `fixed` (FR) and `compound` (CS, EN)?
Maybe for `compound` we could consider `:mod` (idea based on EN). E.g., _winter solstice_.
Cf. EN:
```
21	in	in	ADP	IN	_	24	case	24:case	_
22	Sesto	Sesto	PROPN	NNP	Number=Sing	24	compound	24:compound	_
23	San	San	PROPN	NNP	Number=Sing	24	compound	24:compound	_
24	Giovanni	Giovanni	PROPN	NNP	Number=Sing	19	nmod	19:nmod:in	SpaceAfter=No
```

## Details:
- `advmod` = `manner` --> _ideo_ ends up being `manner`, while I would have either `cause` or maybe even nothing.

# EVALUATION
- Input from Marie (09.12.2024):
  - Subtask evaluation: evaluate specific parts of graphs.
  GRAPES is the best system for sub-scores (https://arxiv.org/pdf/2312.03480).
  - Unlabeled Attachment Score (UAS) on node attachment.
  - ANCAST++: they do some UAS/LAS.
  Paper: https://aclanthology.org/2024.lrec-main.94.pdf.
  - I could measure edge recall, node recall, .... Graph-based evaluation.
  - Besides that, also do some evaluation based on linguistic phenomena.
- So, main steps:
  1. Evaluation comparing UD tree to UMR graph, to show hoe well my parser works. Just UAS, because the labels are
  different so not relevant.
  2. UMR evaluation on single graphs. Gold UMRs needed here.
    I can use some of the Latin ones from Sallust, plus annotate some more, ideally for other languages.
    They don't need to be that many, I guess.
- In any case, before the final evaluation, got through converted UMRS with Dan / UMR team  + refine external resources
for languages other than Latin.

- Alexis (10.12.2024):
  - You could add some time evaluation, e.g. by involving Czech annotators and measuring how much time it takes for them
  to build a UMR from scratch vs. having the converted graphs.

- Dan (12.12.2024):
  - I can take UMR released data, parse them to get UMRs, and then run the evaluation.
  - If you start annotating from the output of the conversion, you need to state very clearly the reasons to convince
  the reviewer of the thesis. Otherwise the evaluation might look unfair. You might say that annotating from scratch is
  extremely time-consuming and labour-intensive, and also that starting from a converted backbone ensures you to have a
  comparable UMRs, since many different UMR structures can be equally correct (e.g. _Lennart Mari_, _kandidovat_).
  But you also need to compare how the annotation from scratch differs from that from backbone, e.g. on Latin data.
  You could e.g. measure the time it takes and discuss differences you end up noticing in grpahs,

# PAPER
- Alexis (10.12.2024): possible venues could be:
  - Designing Meaning Representation Workshop (4-5 Aug, Prague).
  - TLT -> SyntaxFest (26-29 Aug 2025, deadline in April)
  - Linguistic Annotation Workshop (LAW) - TBA