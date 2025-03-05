# TODO - UD2UMR converter

- [coding] Consider implementing adverbs that affect `modal-strength` (already available for Czech, see PDT conversion).
- [coding] Check how negation in coordination is handled.
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

## Improvement in the converter after first eval phase

### Fixed:
- Variable identifiers were missing the sentence id prefix (e.g. "s6").
- Better index/token alignment, now to the left margin and always with a whitespace between two indices.
- Now checking that there are no non-existent alignments listed in the alignment block.
- Alignments are now ordered deterministically based on the word index.
- All variables found in the sentence graph should now be in the alignment block too.
- All variables now start with a letter; "x" is used for anything that is not alphabetical (e.g. years)
- I replaced `experiencer` and `stimulus` with `actor` and `theme` respectively, because their use turned out to be
confusing - syntactic criteria are not solid enough to detect this.
- In English, there was an issue with coordination because the conjunction lemma _and_ and the abstract concept `and`
are identical.
- `det` was used for many possessives, now correctly `possessor`.
- Czech reflexiva tantum (_se_/_si_ attached to a verb as `expl:pv`) now have the reflexive marker as part of the
concept (_smát-se_), in the same way as English phrasal verbs.

### To fix:
- The Americans do not seem to use non-English letters in the variable identifiers ("s18č").
The simplest solution would be to use "x" instead of anything that does not fall in [a-z].
A possible fancier approach would be to convert 'č' --> 'c', 'á' --> 'a' etc. --> ask Boulder.
- Passive participles are ADJ in Czech UD; ideally, they should be converted back to verbs. They can be recognized by
`VerbForm=Part|Voice=Pass` in FEATS. The verbal lemma (infinitive) should be available in the `LDeriv` attribute in MISC.
Since they are passive, the subject is likely to be `:undergoer` (rather than `:actor`).
- Alignment: include prepositions in the alignment of the noun they belong to. Also include auxiliary verbs and SCONJ
marks in the alignment of the main verb [think about it because it's not like that in the eval data].
- snt 10: `full-negative` ended up in the first clause of the coordination, but it belongs to the second clause.

## QUESTIONS:
- [Julia, not asked] Is there something like `foreign-entity`, `foreign...`? I recall something but not much. Otherwise,
how do I include a foreign expression/word in a graph? Don't have a real example because all those I have are actually
supposed to be named entities.

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
  You could e.g. measure the time it takes and discuss differences you end up noticing in graphs.


- [Notes (20.01.2025)]
  - _AnCast_ paper: 2 methods to find anchor pairs. If manual alignment between a graph and the word tokens exist, the
  alignment between a pair of concepts can be inferred from it (a pair of concepts aligned to the same word tokens can be
  considered to be an initial anchor pair). If graphs are not manually aligned to word tokens, the alternative is to
  extract a subset of highly similar pairs from a pair of graphs for the same sentence (FG: not doable).
  - The issue is that then they update the initial anchor matrix in the iterative anchor broadcast step -> FG: not doable.
  - It could be nice if I could use their alignment system, and then just do my evaluation. Seems to be working!
  - "Micro F1 is calculated by averaging all triple-pair scores across the whole dataset."
  - An interesting feature is that it provides precision, recall, F1 scores, which could be an interesting measure (recall)
  of how much information I am losing to avoid graph disconnection.

  - Issue: the AnCast GitHub repo is undergoing some substantial changes, in preparation of the `pypi` release.
  Currently, my code still relies on the old version, because trying to update it according to the new one did not work.
  However, I need to come back to this at some point. \
  Old repo: https://github.com/sxndqc/ancast \
  New repo: https://github.com/umr4nlp/ancast


- [Dan (21.01.2025)]
  - Possible things to evaluate (backbone):
    - How many nodes should have a node and they don't?
    - For nodes that I have, look at the relations between them: is it correct (sort of LAS)?
    - Attributes are approachable similarly to tagging.
  - Interesting phenomena revolve around places of UMR graphs where the structure is very different from the UD one
  (e.g., coordination, any non-verbal predication).

  - TEST SET:
    - Come up with an ordered list of sentences to annotate from scratch (and from converted graphs).
    - In PUD, 2 genres (Wikipedia - w, and news - n) + original langauge of the data (5). E.g., _n01_: English news.
    Cf. "The first 750 sentences are originally English (01). The remaining 250 sentences are originally German (02),
    French (03), Italian (04) or Spanish (05) and they were translated to other languages via English"
    - Manual annotation/correction of converted graphs?
    Start with some (50?) sentences from scratch, note down the time it takes, as well as the `sent_id`.
    - A test set of 200 sentences (per language) would be nice - doable with correction of converted graphs.
    - Preparing the backbone (initial block of comments, block with alignments) is not cheating. Is the annotator going
    to be faster having the backbone with nodes, also in the alignment block? It's a research question itself.
    - At some point, some manual evaluation needs to be done (for the thesis).
    - For the paper, it is fine having 2 languages.


# PAPER
- [Alexis (10.12.2024) + other] \
  Possible venues could be:
  - _6th International Workshop on Designing Meaning Representation_ (4-5 Aug, Prague, deadline: 21 Apr; dual submission allowed).
  - _TLT_ -> _SyntaxFest_ (26-29 Aug 2025, deadline: 15 Apr).
  - _19th Linguistic Annotation Workshop (LAW-XIX)_ (Jul/Aug, ACL, Vienna, deadline via ARR: 25 Mar, direct submission: 04 Apr).
  - _16th International Conference on Computational Semantics (IWCS)_ (22-24 Sep, Heinrich Heine University Düsseldorf, deadline: 06 Jun; dual submission allowed).

    
