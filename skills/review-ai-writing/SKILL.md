---
name: review-ai-writing
description: Review prose (blog post, article, doc, README, LinkedIn post) for signs of AI writing — the tells catalogued in Wikipedia's "Signs of AI writing", plus French-specific ones — and propose rewrites in the author's voice as numbered diffs the author approves or refuses one by one. Use when asked to review a text for AI-isms, "AI-ismes", "slop", "does this sound like ChatGPT", "make it sound less AI", or before publishing a text drafted with an LLM.
---

# Review AI writing

Find the passages a careful reader would notice as machine-written, and propose a rewrite
for each that keeps the meaning and sounds like the author. The author decides; this skill
does not edit the text until told which suggestions to apply.

## Reference

Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
is the catalogue. The tells below are the ones that apply to prose in general; the page has
more (markup, citations) that rarely matter outside Wikipedia.

## Process

1. **Read the whole text, and something the author wrote before** (an earlier post, their
   emails) for voice. An earlier text may itself be AI-assisted: use it as a rough
   reference, not ground truth.
2. **Leave alone what the author wrote by hand.** If they rewrote passages in this session
   or say a passage is theirs, flag only clear grammar errors there.
3. **Check every claim tied to a source.** Open the link and read what it actually says.
   A figure that is real but comes from a study about something else, an "explanation la
   plus répandue" with no source, a study that measures X presented as proving Y: these
   are the most damaging tells, because a reader who clicks loses trust in the whole text.
4. **Apply the tells below.** Be selective: report what a careful native reader would
   notice, not every stylistic choice. One "crucial" is coincidence; a cluster is a tell.
5. **Report** as numbered diffs in reading order (see Report).
6. **Apply** only the numbers the author accepts. When they redirect one ("for 4, rather
   say…"), write the new version from their words and show it before committing.

## The tells

**Content**
- **Inflated significance** — tying a detail to a broader theme: "marque un tournant",
  "reflète une tendance de fond", "pivotal moment", "reflects broader…".
- **Trailing -ing / participle analysis** — "…, soulignant l'importance de…",
  "highlighting…, underscoring…, fostering…".
- **Vague attribution** — "les experts", "l'explication la plus répandue", "observers have
  noted", with no one named and no link.
- **Over-claiming** — a statement more certain than its source; a hedge immediately
  retracted ("je le prends comme un indice. Il va tout de même dans le sens de…").
- **Formulaic conclusion** — "despite challenges… the future looks…", or a closing
  paragraph that re-lists every section.
- **Promotional tone** — "incontournable", "riche", "au cœur de", "groundbreaking",
  "vibrant", "boasts".

**Language**
- **AI vocabulary in clusters** — EN: delve, crucial, pivotal, tapestry, underscore,
  showcase, intricate, landscape, leverage. FR: crucial, essentiel, enjeu(x), levier,
  dispositif, trajectoire, écosystème, naviguer, plonger dans, "un véritable…".
- **Avoiding plain verbs** — "constitue", "s'inscrit dans", "serves as", "stands as",
  "features" where "est" or "a" would do.
- **Negative parallelism** — "ce n'est pas X, c'est Y", "il ne s'agit pas de… mais de…",
  "not just X, but Y", "no X, no Y, just Z".
- **"Y plutôt que X"** used to manufacture insight from a reversed claim.
- **Rule of three** — three adjectives, three short phrases, three examples, by reflex.
- **Balanced pairs** — "c'est un avantage… mais cela apporte aussi…", "loin d'être
  parfait, mais il constitue…": every point weighed on both sides.
- **Calques from English** — "adresser un problème", "impacter", "inconsistance" (for
  *inconsistency*), "construire l'intuition de quand", "faire du sens".

**Structure and rhythm**
- **Signposting** — "Ici, je regarde…", "Voyons maintenant…", "Il existe une technique
  pour…", "Let's dive in".
- **Mechanical transitions** — a paragraph opening with a sentence that only announces
  the topic ("Pour la délégation, c'est un obstacle de plus.").
- **Tidy closers** — a final sentence restating the paragraph, or tying it back to an
  earlier section ("…alimente directement la peur du premier point.").
- **Uniform paragraphs** — every paragraph the same length and shape.
- **Generic headings** — "Ce qui se joue", "Conclusion", "Key takeaways", title case,
  "X and Y" pairs.
- **Formatting leftovers** — bold key terms in running text, "Label: description" bullet
  lists, emoji before headings, a horizontal rule between every section, chatbot phrases
  ("J'espère que cela vous aide", "Certainly!"), placeholders ("[Votre nom]").

## Report

A ranked summary first: a one-line verdict (low / medium / high AI flavour, and where the
tells cluster), then the findings in **reading order**, numbered so the author can answer
"ok 1-5, 7; refuse 6". Each finding:

**N. Section: the tell, in a few words** (line)
```diff
- the exact current sentence(s), only those that change
+ the proposed rewrite
```

A finding that touches separate places (a heading and a paragraph) gets one diff block per
place under the same number, and says the parts can be taken separately.

Write the rewrites in the text's language, in the author's register: shorter, more
concrete, one example rather than an abstract category. Keep links, figures and formatting
intact unless the finding is about them.
