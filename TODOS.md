# TODO - UD2UMR converter

- [coding] Consider implementing adverbs that affect `modal-strength` (already available for Czech, see PDT conversion).
- [coding] Check how negation in coordination is handled.
- [checking] Send cs output to UFAL UMR.
- [deployment] Ask somebody else to run the converter, and see if they encounter new issues. Most probably, first finish
the evaluation, so that it can be tested as well.

## General
- I think it could be useful to have functions specific to UPOS. E.g., for NOUNs I check `refer-number`, etc.
For PRONs I build the usual NE structure, and so on. [don't think so anymore, especially for `refer-number`].

## Notes
Currently disconnected graphs:

| Language        | Disconnected | Empty_triples |             Notes              |
|:----------------|:------------:|--------------:|:------------------------------:|
| en_pud          |   1 / 1000   |             1 | What should the UMR look like? |
| it_pud          |   0 / 1000   |             0 |                                |
| fr_pud          |   0 / 1000   |             0 |                                |
| cs_pud          |   0 / 1000   |             0 |                                |
| la_perseus_test |   1 / 939    |             1 | What should the UMR look like? |


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

- [discussed, no real solution] Double negation with modals, or kind of. E.g., _I forbid you from not eating_.
It is an issue of the guidelines: encoding by default the lexicalized negation is not a valid strategy, because we can
happen a negated complement (e.g., _not eating_). It feels weird to reverse the negation in that case, and have e.g.
`full-affirmative`. Guidelines need refinement. For now, I'll just not do the reversing.
Also, for the specific case of _forbid_: it shouldn't imply a negative modality, but rather a neutral one. Cf.
guidelines: "Weak deontic modals, including desire (e.g., want) and permission (e.g., allow), impart NeutAff strength
on their complements. Certain modals may also lexicalize negation, such as doubt, forbid, or wish. These are annotated
with the NeutNeg, PrtNeg, and FullNeg values, respectively." --> why permission = neutral vs. _forbid_ = partial?

- [postponed, irrelevant] Do I want to support code-switching? Because I specify the language in input, but it could be
doable to check for UFeat `Foreign=Yes` and `Lang=grc` (e.g.) in MISC, and update `self.lang` for processing of numbers.
Not really urgent, not frequent at all.

- Negation (`advmod:neg` as `:modal-strength full-negative`). As of now I am following the 80% of the times rule.
There are of course exceptions: now we have negative modality annotated for nouns (which are supposed to be events, but
they are not overt).
C.f., e.g., _Puerum basiavi frugalissimum, **non** propter formal, sed quia frugi est_ (from Perseus_test).
I could also implement an additional check for UPOS (= only VERB), but maybe it would be too restraining.


## QUESTIONS:
- [Julia, not asked] Is there something like `foreign-entity`, `foreign...`? I recall something but not much. Otherwise, how do I
include a foreign expression/word in a graph? Don't have a real example because all those I have are actually supposed
to be named entities.

## For Dan:
- What to do with _nec_ split as _ne_ + _c_? do I merge them in Perseus or handle them in UMR?
Sent tlg0031.tlg027.perseus-lat1.tb.xml@88 in Perseus test.
All other _nec_ s are not split in two as a MWE.
- Is it okay to treat both UD `Degree={Sup,Abs}` as UMR `most`?

# EVALUATION
- [Marie (09.12.2024)]
  - Subtask evaluation: evaluate specific parts of graphs.
  GRAPES is the best system for sub-scores (https://arxiv.org/pdf/2312.03480).
  - Unlabeled Attachment Score (UAS) on node attachment.
  - ANCAST++: they do some UAS/LAS.
  Paper: https://aclanthology.org/2024.lrec-main.94.pdf.
  - I could measure edge recall, node recall, .... Graph-based evaluation.
  - Besides that, also do some evaluation based on linguistic phenomena.

- So, main steps:
  1. Evaluation comparing UD tree to UMR graph, to show hoe well my parser works. Just UAS, because the labels are
  different and therefore not relevant.
  2. UMR evaluation on single graphs. Gold UMRs needed here.
    I can use some of the Latin ones from Sallust, plus annotate some more, ideally for other languages.
    They don't need to be that many, I guess.
- In any case, before the final evaluation, got through converted UMRS with Dan / UMR team  + refine external resources
for languages other than Latin.

- [Alexis (10.12.2024)]
  - You could add some time evaluation, e.g. by involving Czech annotators and measuring how much time it takes for them
  to build a UMR from scratch vs. having the converted graphs.

- [Dan (12.12.2024)]
  - I can take UMR released data, parse them to get UMRs, and then run the evaluation.
  - If you start annotating from the output of the conversion, you need to state very clearly the reasons to convince
  the reviewer of the thesis. Otherwise, the evaluation might look unfair. You might say that annotating from scratch is
  extremely time-consuming and labour-intensive, and also that starting from a converted backbone ensures you to have a
  comparable UMRs, since many different UMR structures can be equally correct (e.g. _Lennart Mari_, _kandidovat_).
  But you also need to compare how the annotation from scratch differs from that from backbone, e.g. on Latin data.
  You could e.g. measure the time it takes and discuss differences you end up noticing in graphs,

# PAPER
- [Alexis (10.12.2024)] Possible venues could be:
  - _Designing Meaning Representation Workshop_ (4-5 Aug, Prague, no deadline for now).
  - _TLT_ -> _SyntaxFest_ (26-29 Aug 2025, deadline in April)
  - _Linguistic Annotation Workshop (LAW)_ - (Jul/Aug, ACL, Vienna, deadline via ARR: 25 Mar, direct submission: 04 Apr)
  [probably, favourite venue as of now].
