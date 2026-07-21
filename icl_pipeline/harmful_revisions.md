# Harmful revisions — RadGraph-F1 regressions

Worst 30 of 1268 real revisions, ranked by RadGraph-F1 drop (draft − revised). Across the whole set: **470 hurt, 371 helped, 427 flat**.

Diff markup: `[-removed-]` `{+added+}`. Failure-mode tags are heuristic hypotheses to check by reading, not ground truth.

## Failure-mode tally (worst cases only)

- changed sentences examined: **55**
- changed but NOT comparison-flagged: **0** (these should be zero — revise.py only rewrites flagged sentences, so any nonzero count means the splice or the classifier is misbehaving)

- `verbose`: 25
- `added-vague-prior-ref`: 13
- `negation-changed`: 5
- `added-hedging`: 3
- `truncated`: 2

---

## #1 — study 57940242 (change)

**RadGraph-F1: 0.5625 (draft) → 0.1875 (revised)  |  Δ -0.3750  [HARMFUL]**  
CheXbert guardrail: **reject**  |  RadGraph guardrail: **reject**

### Changed sentences (2)

**sentence 2** (comparison-flagged)  `added-vague-prior-ref`

- draft:   There is a small right pleural effusion, unchanged from the prior exam.
- revised: There is a small right pleural effusion, unchanged from the prior examination.
- diff:    There is a small right pleural effusion, unchanged from the prior [-exam.-] {+examination.+}

**sentence 4** (comparison-flagged)  `verbose`

- draft:   The cardiomediastinal silhouette is stable.
- revised: Heart size and mediastinal structures are stable.
- diff:    [-The cardiomediastinal silhouette is-] {+Heart size and mediastinal structures are+} stable.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _54978088_: "As compared to prior chest radiograph from ___, there has been interval decrease of the right-sided pleural effusion."
- _54978088_: "There has been interval increase of the left-sided pleural effusion."
- _57651692_: "Heart size and mediastinal structures are unchanged."
- _57651692_: "The previously identified right-sided obliteration of the diaphragmatic contour and blunting of the right lateral pleural sinus persists and appears rather unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Right internal jugular line ends at lower SVC whereas the dialysis catheter through the left
> subclavian approach ends at mid SVC. Moderate right pleural effusion and bilateral lower lung
> atelectasis are unchanged. Mild pulmonary vascular congestion is stable. Enlarged heart size,
> mediastinal and hilar contours are unchanged. No pneumothorax.

**DRAFT (MAIRA-2)**

> The left PICC has been pulled back and now terminates in the upper SVC. The right hemodialysis
> catheter has been removed. There is a small right pleural effusion, unchanged from the prior exam.
> There is no pneumothorax. The cardiomediastinal silhouette is stable.

**REVISED (Qwen)**

> The left PICC has been pulled back and now terminates in the upper SVC. The right hemodialysis
> catheter has been removed. There is a small right pleural effusion, unchanged from the prior
> examination. There is no pneumothorax. Heart size and mediastinal structures are stable.

**REFERENCE (ground truth current)**

> The PICC ends in the upper SVC. The cardiomediastinal silhouette is normal, although evaluation is
> somewhat limited by patient's rotation. There is a moderate right pleural effusion, similar in
> size from the previous study on ___. No left pleural effusion is present. There is no
> consolidation or pneumothorax.

</details>

---

## #2 — study 58916510 (change)

**RadGraph-F1: 0.8824 (draft) → 0.6667 (revised)  |  Δ -0.2157  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 0** (comparison-flagged)  `negation-changed`

- draft:   Frontal radiograph of the chest demonstrates interval removal of endotracheal tube and nasogastric tube since the prior study.
- revised: As compared to the prior study, there is no relevant change noted regarding the endotracheal tube and nasogastric tube placement.
- diff:    [-Frontal radiograph of-] {+As compared to+} the [-chest demonstrates interval removal of-] {+prior study, there is no relevant change noted regarding the+} endotracheal tube and nasogastric tube [-since the prior study.-] {+placement.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _51040926_: "Cardiomediastinal silhouette appears unchanged allowing for slight differences in technique."
- _52387484_: "Stable elevation of the right hemidiaphragm noted though there is slight increase in bibasilar atelectasis."
- _52387484_: "Cardiomediastinal silhouette appears grossly unchanged though the right heart border is stably effaced due to right hemidiaphragmatic elevation."
- _50070545_: "As compared to the previous radiograph, there is no relevant change."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In the interval, the patient has been intubated. The tip of the endotracheal tube projects
> approximately 4.5 cm above the carina. In addition, the patient has received a nasogastric tube.
> The course of the tube is unremarkable, the tip of the tube is not included in the image. There is
> no evidence of complications, notably no pneumothorax. Moderate cardiomegaly with signs of minimal
> fluid overload. No pleural effusions.

**DRAFT (MAIRA-2)**

> Frontal radiograph of the chest demonstrates interval removal of endotracheal tube and nasogastric
> tube since the prior study. There is no evidence of pneumothorax or pleural effusion. There is no
> evidence of focal pneumonia. There is some atelectasis at the left lung base. There is no evidence
> of pulmonary edema. The cardiomediastinal silhouette is unremarkable.

**REVISED (Qwen)**

> As compared to the prior study, there is no relevant change noted regarding the endotracheal tube
> and nasogastric tube placement. There is no evidence of pneumothorax or pleural effusion. There is
> no evidence of focal pneumonia. There is some atelectasis at the left lung base. There is no
> evidence of pulmonary edema. The cardiomediastinal silhouette is unremarkable.

**REFERENCE (ground truth current)**

> PA and lateral views of the chest are obtained. There is mild atelectasis at the left lung base.
> The previously seen endotracheal tube and nasogastric tube are no longer present on this study.
> There is no evidence of pneumonia, pleural effusion or pulmonary edema. The cardiomediastinal
> silhouette is unremarkable.

</details>

---

## #3 — study 58756659 (change)

**RadGraph-F1: 0.2128 (draft) → 0.0000 (revised)  |  Δ -0.2128  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the extent of the known left apical pneumothorax is unchanged.
- revised: The extent of the known left apical pneumothorax is unchanged as compared to the previous radiograph.
- diff:    [-As compared to the previous radiograph, the-] {+The+} extent of the known left apical pneumothorax is [-unchanged.-] {+unchanged as compared to the previous radiograph.+}

**sentence 3** (comparison-flagged)  `verbose`

- draft:   Unchanged moderate cardiomegaly.
- revised: Moderate cardiomegaly is unchanged.
- diff:    [-Unchanged moderate cardiomegaly.-] {+Moderate cardiomegaly is unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50142831_: "The right internal jugular central venous catheter is unchanged position ending in the SVC."
- _50142831_: "A left chest tube is unchanged."
- _58705437_: "PA and lateral radiographs of the chest demonstrate interval growth in the size of the right apical pneumothorax when compared to the most recent prior study."
- _58705437_: "The small right pleural effusion is unchanged in size."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In comparison with the study of ___, there is again a small apical pneumothorax. Areas of
> opacification in the right lower and left upper lung are decreasing.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the extent of the known left apical pneumothorax is
> unchanged. There is no evidence of tension. The areas of atelectasis at the right lung base and in
> the left upper lobe are constant in appearance. Unchanged moderate cardiomegaly.

**REVISED (Qwen)**

> The extent of the known left apical pneumothorax is unchanged as compared to the previous
> radiograph. There is no evidence of tension. The areas of atelectasis at the right lung base and
> in the left upper lobe are constant in appearance. Moderate cardiomegaly is unchanged.

**REFERENCE (ground truth current)**

> In comparison with the study of ___, the sharp pleural line is no longer seen in the left apical
> region. There may be a residual tiny pneumothorax in the left apex. Continued enlargement of the
> cardiac silhouette. Mild indistinctness of pulmonary vessels suggests some elevated pulmonary
> venous pressure. Retrocardiac opacification persists, consistent with some volume loss in the
> lower lobe. Overlying wires obscure the lower portion of the right hemithorax.

</details>

---

## #4 — study 54607940 (change)

**RadGraph-F1: 0.4615 (draft) → 0.2632 (revised)  |  Δ -0.1984  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 3** (comparison-flagged)

- draft:   On the right, the effusion has also decreased.
- revised: On the right, the effusion has also decreased in extent.
- diff:    On the right, the effusion has also [-decreased.-] {+decreased in extent.+}

**sentence 6** (comparison-flagged)  `verbose`

- draft:   Unchanged size of the cardiac silhouette.
- revised: The size of the cardiac silhouette remains unchanged.
- diff:    [-Unchanged-] {+The+} size of the cardiac [-silhouette.-] {+silhouette remains unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50489076_: "AICD device is unchanged."
- _50489076_: "Opacities in the bilateral lower lungs are again noted with an effusion on the right."
- _57200051_: "As compared to the previous radiograph, the position of the right pigtail catheter in the pleural space is slightly changed."
- _57200051_: "The effusion on the right appears to have minimally increased."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> As compared to the previous radiograph, the pre-existing left pleural effusion has massively
> increased in extent. The effusion occupies approximately half of the left hemithorax and causes
> substantial basal atelectasis. On the right, a small-to-moderate pleural effusion has newly
> occurred. In the ventilated parts of the lung parenchyma, there is no evidence of pneumonia. No
> pneumothorax.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the effusion on the left has substantially decreased in
> extent. The left lung is better ventilated than before. However, there is still a remnant small-
> to-moderate pleural effusion. On the right, the effusion has also decreased. The monitoring and
> support devices are constant. No new parenchymal opacities. Unchanged size of the cardiac
> silhouette.

**REVISED (Qwen)**

> As compared to the previous radiograph, the effusion on the left has substantially decreased in
> extent. The left lung is better ventilated than before. However, there is still a remnant small-
> to-moderate pleural effusion. On the right, the effusion has also decreased in extent. The
> monitoring and support devices are constant. No new parenchymal opacities. The size of the cardiac
> silhouette remains unchanged.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, there is no relevant change. Unchanged extent of moderate
> bilateral pleural effusions and moderate pulmonary edema. Unchanged monitoring and support
> devices. Unchanged size of the cardiac silhouette. No pneumothorax.

</details>

---

## #5 — study 54434117 (change)

**RadGraph-F1: 0.3636 (draft) → 0.1905 (revised)  |  Δ -0.1732  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 0** (comparison-flagged)  `added-vague-prior-ref`

- draft:   As compared to _, there is improved aeration of the left upper lobe with persistent left lower lobe atelectasis and pleural effusion.
- revised: As compared to the prior study, there is improved aeration of the left upper lobe with persistent left lower lobe atelectasis and pleural effusion.
- diff:    As compared to [-_,-] {+the prior study,+} there is improved aeration of the left upper lobe with persistent left lower lobe atelectasis and pleural effusion.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _54164922_: "Resolution of the hydropneumothorax in the right apex which is now replaced with pleural effusion."
- _54164922_: "There has been interval expansion of the right lung with decrease in observed right lower zone atelectasis."
- _57298633_: "In comparison with the study of ___, there is again a substantial amount of fluid in the right pleural space, probably even more prominent than on previous examination."
- _50771762_: "The cardiomediastinal silhouette and hilar contours appear stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> PA and lateral images of the chest demonstrate interval worsening of left lung opacity. The entire
> left hemithorax is now again opacified. Opacification is likely due to a large left pleural fluid
> collection in the setting of lobectomy versus less likely left lung collapse. There is persistent
> significant elevation of the left hemidiaphragm. The right lung is clear. There is no right
> pleural effusion. Cardiac size cannot be assessed due to obscuration by the left hemithorax
> opacification. The mediastinum is not shifted.

**DRAFT (MAIRA-2)**

> As compared to _, there is improved aeration of the left upper lobe with persistent left lower
> lobe atelectasis and pleural effusion. The right lung remains clear. No pneumothorax.

**REVISED (Qwen)**

> As compared to the prior study, there is improved aeration of the left upper lobe with persistent
> left lower lobe atelectasis and pleural effusion. The right lung remains clear. No pneumothorax.

**REFERENCE (ground truth current)**

> In comparison with the study of ___, there is some improved aeration in the medial aspect of the
> left lung. However, substantial opacification persists in this hemithorax. Right lung remains
> clear.

</details>

---

## #6 — study 50043351 (change)

**RadGraph-F1: 0.5405 (draft) → 0.3684 (revised)  |  Δ -0.1721  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 4** (comparison-flagged)  `added-hedging verbose`

- draft:   Cardiomediastinal silhouette is unchanged.
- revised: Cardiomediastinal contours are stable in appearance.
- diff:    Cardiomediastinal [-silhouette is unchanged.-] {+contours are stable in appearance.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _56808071_: "Cardiomediastinal contours are stable in appearance."
- _56808071_: "Bibasilar opacities are present, with interval worsening in the right lower lobe and slight improved aeration in left retrocardiac region."
- _56150432_: "The cardiac and mediastinal silhouettes are stable."
- _53861819_: "Multiple opacities are again seen in the bilateral lungs, consistent with known metastatic disease and grossly stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Stable post-treatment changes related to known small cell lung carcinoma. No superimposed acute
> cardiopulmonary process.

**DRAFT (MAIRA-2)**

> There is a new right lower lung opacity which may represent pneumonia or atelectasis. There is
> elevation of the right hemidiaphragm, which is likely due to the patient's known subpulmonic
> effusion. The left lung is clear. There is no pneumothorax. Cardiomediastinal silhouette is
> unchanged.

**REVISED (Qwen)**

> There is a new right lower lung opacity which may represent pneumonia or atelectasis. There is
> elevation of the right hemidiaphragm, which is likely due to the patient's known subpulmonic
> effusion. The left lung is clear. There is no pneumothorax. Cardiomediastinal contours are stable
> in appearance.

**REFERENCE (ground truth current)**

> There is a right pleural effusion which is unchanged since prior exam. Again seen is a right hilar
> opacity consistent with fibrosis, better assessed on recent CT. A subtle left lower lobe opacity
> is seen, which may represent atelectasis, but pneumonia cannot be excluded. The lungs are
> otherwise clear. The cardiomediastinal silhouette is unchanged from prior exam. Visualized osseus
> structures are unremarkable.

</details>

---

## #7 — study 50955371 (change)

**RadGraph-F1: 0.4571 (draft) → 0.2857 (revised)  |  Δ -0.1714  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Moderate bibasilar and retrocardiac atelectasis is increased.
- revised: Bibasilar and retrocardiac atelectasis is now moderate and increased compared to the prior study.
- diff:    [-Moderate bibasilar-] {+Bibasilar+} and retrocardiac atelectasis is [-increased.-] {+now moderate and increased compared to the prior study.+}

**sentence 2** (comparison-flagged)  `verbose`

- draft:   The heart size is unchanged.
- revised: Heart size remains unchanged compared to the previous radiograph.
- diff:    [-The heart-] {+Heart+} size [-is unchanged.-] {+remains unchanged compared to the previous radiograph.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53733637_: "Small right apical hemothorax has decreased in size."
- _53733637_: "Linear lucency outlining the aortic knob and the upper mediastinal surface which is likely a small pneumomediastinum, unchanged in appearance."
- _58021503_: "Bilateral perihilar opacities are stable."
- _52044510_: "Compared to the previous radiograph, the upper lung opacity on the right has substantially increased in severity and extent."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Compared the prior study, there is increase in opacity at the right mid to lower lung difficult to
> exclude small left pleural effusion. Pneumonia pneumothorax is seen. The cardiac and mediastinal
> silhouettes are stable. Chronic deformity of the posterior right fourth rib.

**DRAFT (MAIRA-2)**

> Since _, new heterogeneous opacities are seen in the right lower lung, concerning for aspiration
> or pneumonia. Moderate bibasilar and retrocardiac atelectasis is increased. The heart size is
> unchanged. No pneumothorax.

**REVISED (Qwen)**

> Since _, new heterogeneous opacities are seen in the right lower lung, concerning for aspiration
> or pneumonia. Bibasilar and retrocardiac atelectasis is now moderate and increased compared to the
> prior study. Heart size remains unchanged compared to the previous radiograph. No pneumothorax.

**REFERENCE (ground truth current)**

> Persistence of right middle lobe opacities obscuring the right heart border since ___ is
> concerning for pneumonia. The rest of the lungs appear unchanged since ___. Moderate bibasilar
> atelectasis is slightly improved. The heart size is exaggerated by compressive atelectasis. No
> pneumothorax. Note is made of partial resection of the ___ posterior rib.

</details>

---

## #8 — study 58095298 (change)

**RadGraph-F1: 0.4687 (draft) → 0.3000 (revised)  |  Δ -0.1687  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (3)

**sentence 1** (comparison-flagged)  `negation-changed`

- draft:   Other indwelling devices are unchanged in position.
- revised: Other indwelling devices show no change in position.
- diff:    Other indwelling devices [-are unchanged-] {+show no change+} in position.

**sentence 2** (comparison-flagged)

- draft:   Cardiac silhouette is mildly enlarged and accompanied by pulmonary vascular congestion and slight improvement in pulmonary edema.
- revised: The cardiac silhouette remains mildly enlarged with persistent pulmonary vascular congestion and minimal improvement in pulmonary edema.
- diff:    [-Cardiac-] {+The cardiac+} silhouette [-is-] {+remains+} mildly enlarged [-and accompanied by-] {+with persistent+} pulmonary vascular congestion and [-slight-] {+minimal+} improvement in pulmonary edema.

**sentence 4** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Small right pleural effusion is unchanged.
- revised: A small right pleural effusion is noted, unchanged from the prior study.
- diff:    [-Small-] {+A small+} right pleural effusion is [-unchanged.-] {+noted, unchanged from the prior study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _51733106_: "Cardiomegaly is unchanged."
- _51733106_: "There is evidence of CHF, with upper zone redistribution, vascular plethora, interstitial edema and diffuse vascular blurring, unchanged."
- _53994753_: "In comparison with the study of ___, there is again enlargement of the cardiac silhouette with pulmonary edema."
- _53994753_: "Monitoring and support devices are essentially unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> As compared to a previous radiograph, the tube is still relatively high and could be advanced by 1
> to 2 cm. Unchanged bilateral pleural effusions, unchanged moderate pulmonary edema and mild
> cardiomegaly. The nasogastric tube shows normal course.

**DRAFT (MAIRA-2)**

> Swan-Ganz catheter has been repositioned, with tip now terminating in the right main pulmonary
> artery. Other indwelling devices are unchanged in position. Cardiac silhouette is mildly enlarged
> and accompanied by pulmonary vascular congestion and slight improvement in pulmonary edema.
> Improving left retrocardiac atelectasis or consolidation is likely due to improving left pleural
> effusion, which remains small in size. Small right pleural effusion is unchanged.

**REVISED (Qwen)**

> Swan-Ganz catheter has been repositioned, with tip now terminating in the right main pulmonary
> artery. Other indwelling devices show no change in position. The cardiac silhouette remains mildly
> enlarged with persistent pulmonary vascular congestion and minimal improvement in pulmonary edema.
> Improving left retrocardiac atelectasis or consolidation is likely due to improving left pleural
> effusion, which remains small in size. A small right pleural effusion is noted, unchanged from the
> prior study.

**REFERENCE (ground truth current)**

> Endotracheal tube and nasogastric tube remain in standard position. Swan-Ganz catheter has been
> slightly withdrawn, with tip terminating in the central right hilar region. Left sided catheter
> has been removed, with no visible pneumothorax. Cardiac silhouette remains mildly enlarged, but
> previously reported mild edema has nearly resolved. Bibasilar retrocardiac atelectasis is present
> with some improvement on the left, and small left pleural effusion is unchanged.

</details>

---

## #9 — study 57911714 (change)

**RadGraph-F1: 0.2642 (draft) → 0.1000 (revised)  |  Δ -0.1642  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 0** (comparison-flagged)  `truncated`

- draft:   Single portable view of the chest demonstrates interval retraction of the endotracheal tube, which is now approximately 3 cm from the carina.
- revised: Interval retraction of the endotracheal tube is noted, now approximately 3 cm from the carina.
- diff:    [-Single portable view of the chest demonstrates interval-] {+Interval+} retraction of the endotracheal [-tube, which-] {+tube+} is {+noted,+} now approximately 3 cm from the carina.

**sentence 3** (comparison-flagged)

- draft:   Otherwise, there is no significant change in the appearance of the chest with right mid lung surgical chain sutures, and streaky right mid lung and left lung base opacities which may represent atelectasis.
- revised: Otherwise, there is no significant change in the appearance of the chest with right mid lung surgical chain sutures and streaky opacities in the right mid lung and left lung bases, which may represent atelectasis.
- diff:    Otherwise, there is no significant change in the appearance of the chest with right mid lung surgical chain [-sutures,-] {+sutures+} and streaky {+opacities in the+} right mid lung and left lung [-base opacities-] {+bases,+} which may represent atelectasis.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _54478380_: "Again seen is a hazy opacity of the right lower lung which remains unchanged from prior examination and is likely a pleural effusion."
- _54478380_: "The cardiomediastinal silhouette is unchanged from prior examination."
- _59663727_: "There is an persistent increased opacification of the bilateral bases, which likely represents atelectasis or aspiration."
- _59663727_: "The cardiomediastinal and hilar contours are unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Single portable view of the chest is compared to previous film from earlier the same day at 12:59.
> New right IJ line is seen with tip projecting over the mid SVC. There is no visualized
> pneumothorax. Endotracheal tube is approximately 1.5 cm from the carina and should be withdrawn
> several centimeters for optimal positioning. Enteric tube is also slightly withdrawn with side
> port just proximal to the GE junction and should be advanced. Right mid lung surgical chain
> sutures again seen. Streaky right mid lung and left lung base opacities may be due to atelectasis.
> Fullness of the soft tissues in the right hilar region are seen, the etiology of which is
> uncertain. Given prior surgery there could be scarring or post-treatment changes, although
> underlying mass is possible, and dedicated imaging should be performed when patient is amenable.
> Mediastinal clips with median sternotomy wires again noted. Filter projecting over the IVC.

**DRAFT (MAIRA-2)**

> Single portable view of the chest demonstrates interval retraction of the endotracheal tube, which
> is now approximately 3 cm from the carina. The enteric tube is also slightly advanced with side
> port now in the stomach. A right IJ central venous catheter is seen with tip in the mid SVC.
> Otherwise, there is no significant change in the appearance of the chest with right mid lung
> surgical chain sutures, and streaky right mid lung and left lung base opacities which may
> represent atelectasis.

**REVISED (Qwen)**

> Interval retraction of the endotracheal tube is noted, now approximately 3 cm from the carina. The
> enteric tube is also slightly advanced with side port now in the stomach. A right IJ central
> venous catheter is seen with tip in the mid SVC. Otherwise, there is no significant change in the
> appearance of the chest with right mid lung surgical chain sutures and streaky opacities in the
> right mid lung and left lung bases, which may represent atelectasis.

**REFERENCE (ground truth current)**

> Endotracheal tube tip is still within 1 cm of the carina. Enteric tube seen with tip at the
> gastric fundus, side port not clearly identified on the current exam. Right IJ line in stable
> position. The appearance of the lungs is unchanged with hazy bilateral opacities, the streaky left
> basilar likely atelectasis and post-op changes in the right mid lung. Prominence of the right
> hilum is unchanged.

</details>

---

## #10 — study 53481703 (change)

**RadGraph-F1: 0.4348 (draft) → 0.2727 (revised)  |  Δ -0.1621  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 1** (comparison-flagged)

- draft:   The cardiomediastinal silhouette is unchanged with top normal heart size.
- revised: Cardiac and mediastinal silhouettes are unchanged with normal heart size.
- diff:    [-The cardiomediastinal silhouette is-] {+Cardiac and mediastinal silhouettes are+} unchanged with [-top-] normal heart size.

**sentence 2** (comparison-flagged)

- draft:   Bilateral hilar vascular prominence is unchanged from the prior study.
- revised: Bilateral hilar vascular markings are unchanged from the prior study.
- diff:    Bilateral hilar vascular [-prominence is-] {+markings are+} unchanged from the prior study.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _51956692_: "Cardiac and mediastinal silhouettes are grossly stable."
- _56059931_: "Cardiomegaly is unchanged in chest radiograph ___."
- _56059931_: "Median sternotomy wires are again noted."
- _51036683_: "Mediastinal and hilar contours are unchanged and within normal limits."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> There has been interval placement of a right central dialysis catheter. Bilateral hilar vascular
> prominence is re- demonstrated with subtle nodularity in the left upper lung likely representing
> confluence of vasculature though a true nodule difficult to exclude. There is no convincing sign
> of pneumonia or overt edema. Small left effusion is present with basilar atelectasis. The
> cardiomediastinal silhouette is unchanged.

**DRAFT (MAIRA-2)**

> There is no focal consolidation, pleural effusion, pulmonary edema, or pneumothorax. The
> cardiomediastinal silhouette is unchanged with top normal heart size. Bilateral hilar vascular
> prominence is unchanged from the prior study. A calcified granuloma is again noted in the right
> lower lung.

**REVISED (Qwen)**

> There is no focal consolidation, pleural effusion, pulmonary edema, or pneumothorax. Cardiac and
> mediastinal silhouettes are unchanged with normal heart size. Bilateral hilar vascular markings
> are unchanged from the prior study. A calcified granuloma is again noted in the right lower lung.

**REFERENCE (ground truth current)**

> There is no focal consolidation, PE pulmonary edema, or pneumothorax. The lateral view radiograph
> suggests small bilateral pleural effusions in the posterior costophrenic sulcus. The
> cardiomediastinal silhouette, including mild cardiomegaly, is unchanged. A vascular stent projects
> over the left axilla, new from prior studies.

</details>

---

## #11 — study 55157144 (change)

**RadGraph-F1: 0.4706 (draft) → 0.3125 (revised)  |  Δ -0.1581  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Right basal atelectatic bands are unchanged.
- revised: Right basal atelectatic bands are unchanged compared to the prior study.
- diff:    Right basal atelectatic bands are [-unchanged.-] {+unchanged compared to the prior study.+}

**sentence 3** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Esophageal stent is in unchanged position.
- revised: The esophageal stent is in an unchanged position compared to the prior study.
- diff:    [-Esophageal-] {+The esophageal+} stent is in {+an+} unchanged [-position.-] {+position compared to the prior study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _52837143_: "The previously demonstrated bilateral pleural effusions and atelectasis are unchanged since the prior study."
- _52837143_: "Likewise, the previously seen loculated right fissural effusion is unchanged in size since the prior study."
- _51727715_: "Compared to prior study from ___, there has been no significant interval change."
- _51727715_: "Right basilar atelectasis is unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Frontal and lateral views of the chest were obtained. The lungs are hyperinflated. An esophageal
> stent is in place. A right basilar opacity is significantly improved from ___. Mild residual
> opacity may be scarring. No new opacity. Cardiac and mediastinal silhouettes and hilar contours
> are stable. Blunting of the right costophrenic sulcus is unchanged. No left effusion or
> pneumothorax. Loss of vertebral body height in the mid thoracic spine is unchanged.

**DRAFT (MAIRA-2)**

> The lungs are hyperinflated. Right basal atelectatic bands are unchanged. There is no new lung
> consolidation. Esophageal stent is in unchanged position. There is no pneumothorax or pleural
> effusion.

**REVISED (Qwen)**

> The lungs are hyperinflated. Right basal atelectatic bands are unchanged compared to the prior
> study. There is no new lung consolidation. The esophageal stent is in an unchanged position
> compared to the prior study. There is no pneumothorax or pleural effusion.

**REFERENCE (ground truth current)**

> There is no new consolidation. Right lower lobe pneumonia that was present in prior exams has
> significantly improved. Esophageal stent is in unchanged position. There is no pneumomediastinum
> or pneumothorax. There is no pleural effusion. Mediastinal and cardiac contours are stable.

</details>

---

## #12 — study 57681546 (change)

**RadGraph-F1: 0.5556 (draft) → 0.4211 (revised)  |  Δ -0.1345  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 2** (comparison-flagged)

- draft:   Unchanged size of the cardiac silhouette.
- revised: The cardiac silhouette is stable in size.
- diff:    [-Unchanged size of the-] {+The+} cardiac [-silhouette.-] {+silhouette is stable in size.+}

**sentence 3** (comparison-flagged)  `verbose`

- draft:   Unchanged bilateral areas of atelectasis.
- revised: The bilateral areas of atelectasis are unchanged.
- diff:    [-Unchanged-] {+The+} bilateral areas of [-atelectasis.-] {+atelectasis are unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53213768_: "Cardiac silhouette is stable."
- _53213768_: "Median sternotomy wires and mediastinal clips are again noted."
- _57681965_: "As compared to the previous radiograph, the lung volumes have overall increased."
- _57681965_: "The ventilation of the left lung has improved."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> No significant interval change from the prior study with continued right basilar fibrotic changes.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the right venous introduction sheath has been removed. The
> pleural effusions are unchanged in extent and distribution. Unchanged size of the cardiac
> silhouette. Unchanged bilateral areas of atelectasis. No new parenchymal opacities.

**REVISED (Qwen)**

> As compared to the previous radiograph, the right venous introduction sheath has been removed. The
> pleural effusions are unchanged in extent and distribution. The cardiac silhouette is stable in
> size. The bilateral areas of atelectasis are unchanged. No new parenchymal opacities.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, the right and left pleural effusions are virtually
> unchanged. They are mild-to-moderate in extent. The effusions are at the source of bilateral areas
> of compression atelectasis. Unchanged borderline size of the cardiac silhouette. No evidence of
> pneumonia. Unchanged right internal jugular vein catheter and left pectoral pacemaker. No
> pneumothorax.

</details>

---

## #13 — study 50141921 (change)

**RadGraph-F1: 0.1935 (draft) → 0.0606 (revised)  |  Δ -0.1329  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (3)

**sentence 1** (comparison-flagged)

- draft:   There has been interval placement of a right internal jugular central venous catheter, ending in the mid-to-low SVC.
- revised: There has been interval placement of a right internal jugular central venous catheter terminating in the mid-to-low superior vena cava.
- diff:    There has been interval placement of a right internal jugular central venous [-catheter, ending-] {+catheter terminating+} in the mid-to-low [-SVC.-] {+superior vena cava.+}

**sentence 4** (comparison-flagged)

- draft:   A small area of focal consolidation in the right lower lung is not significantly changed compared to the study from earlier today.
- revised: A small area of focal consolidation in the right lower lung is not significantly altered compared to the study from earlier today.
- diff:    A small area of focal consolidation in the right lower lung is not significantly [-changed-] {+altered+} compared to the study from earlier today.

**sentence 5** (comparison-flagged)

- draft:   The remainder of the exam is unchanged.
- revised: The remainder of the examination is unchanged.
- diff:    The remainder of the [-exam-] {+examination+} is unchanged.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50052515_: "As compared to the previous radiograph, the patient has undergone the right thoracocentesis."
- _50052515_: "The right pleural effusion has substantially decreased in extent."
- _56926583_: "There has been interval improvement in the left-sided pneumothorax with residual apical pneumothorax still seen."
- _56926583_: "There is partial reinflation of the left lower lobe compared to the prior radiograph."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Single frontal view of the chest was obtained. The heart is of normal size with stable
> cardiomediastinal contours. A small right pleural effusion is similar to the exam 10 hours prior.
> No focal consolidation or pneumothorax. There is small atelectasis at the right base. Chronic-
> appearing right rib fractures are similar to prior. Sternotomy wires and mediastinal clips are
> intact.

**DRAFT (MAIRA-2)**

> A single portable radiograph of the chest was acquired. There has been interval placement of a
> right internal jugular central venous catheter, ending in the mid-to-low SVC. There is no
> pneumothorax. A small right pleural effusion is not significantly changed. A small area of focal
> consolidation in the right lower lung is not significantly changed compared to the study from
> earlier today. The remainder of the exam is unchanged.

**REVISED (Qwen)**

> A single portable radiograph of the chest was acquired. There has been interval placement of a
> right internal jugular central venous catheter terminating in the mid-to-low superior vena cava.
> There is no pneumothorax. A small right pleural effusion is not significantly changed. A small
> area of focal consolidation in the right lower lung is not significantly altered compared to the
> study from earlier today. The remainder of the examination is unchanged.

**REFERENCE (ground truth current)**

> Portable AP upright chest radiograph obtained. Midline sternotomy wires and mediastinal clips are
> again noted. There has been interval placement of a right IJ central venous catheter with its tip
> located in the distal SVC or cavoatrial junction. No pneumothorax. Otherwise, no change.

</details>

---

## #14 — study 53886138 (change)

**RadGraph-F1: 0.5926 (draft) → 0.4615 (revised)  |  Δ -0.1311  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 2** (comparison-flagged)

- draft:   Otherwise, exam is unchanged from earlier the same day.
- revised: Otherwise, the exam is stable from earlier the same day.
- diff:    Otherwise, {+the+} exam is [-unchanged-] {+stable+} from earlier the same day.

**sentence 4** (comparison-flagged)  `added-hedging`

- draft:   The cardiomediastinal silhouette is unchanged from prior exam.
- revised: The cardiomediastinal silhouette appears unchanged from the prior exam.
- diff:    The cardiomediastinal silhouette [-is-] {+appears+} unchanged from {+the+} prior exam.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _54565542_: "The in median sternotomy wires are again noted, and appear intact."
- _54565542_: "The cardiac, mediastinal, and hilar contours appear stable."
- _55883179_: "Endotracheal tube is unchanged in position projecting over approximately 4.7 cm above the carina."
- _55883179_: "Allowing for differences in technique and positioning, cardiomediastinal silhouette is stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Single portable upright AP image of the chest. The right IJ central line terminates in the right
> atrium. The lungs are well expanded and clear. There is no pleural effusion or pneumothorax. The
> cardiomediastinal silhouette is unchanged from prior exam.

**DRAFT (MAIRA-2)**

> Right IJ central line is now in the low SVC. There is no evidence of pneumothorax. Otherwise, exam
> is unchanged from earlier the same day. There is no pleural effusion or pneumothorax. The
> cardiomediastinal silhouette is unchanged from prior exam.

**REVISED (Qwen)**

> Right IJ central line is now in the low SVC. There is no evidence of pneumothorax. Otherwise, the
> exam is stable from earlier the same day. There is no pleural effusion or pneumothorax. The
> cardiomediastinal silhouette appears unchanged from the prior exam.

**REFERENCE (ground truth current)**

> Single portable supine AP image of the chest. The right IJ central line has been pulled back in
> the interval, but still terminates in the right atrium. The lungs are well expanded and clear.
> There is no pleural effusion or pneumothorax. The cardiomediastinal silhouette is stable.

</details>

---

## #15 — study 59202511 (change)

**RadGraph-F1: 0.4167 (draft) → 0.2857 (revised)  |  Δ -0.1310  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 2** (comparison-flagged)  `verbose`

- draft:   Unchanged normal size of the cardiac silhouette.
- revised: The size of the cardiac silhouette remains unchanged and is within normal limits.
- diff:    [-Unchanged normal-] {+The+} size of the cardiac [-silhouette.-] {+silhouette remains unchanged and is within normal limits.+}

**sentence 3** (comparison-flagged)  `verbose`

- draft:   Unchanged normal appearance of the lung parenchyma.
- revised: The appearance of the lung parenchyma remains unchanged and is within normal limits.
- diff:    [-Unchanged normal-] {+The+} appearance of the lung [-parenchyma.-] {+parenchyma remains unchanged and is within normal limits.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _55909281_: "As compared to the previous radiograph, all evidence of preexisting pneumomediastinum has completely resolved."
- _51221430_: "Since a recent chest x-ray of a few hours earlier, a tiny right apical pneumothorax has nearly resolved."
- _55700188_: "As compared to the previous radiograph, the patient has received a left-sided chest tube."
- _59662299_: "As compared to the previous radiograph, the left chest tube has been removed."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In comparison with the study of earlier on this date, there is slightly less subcutaneous gas
> along the right chest wall. Little change in the small amount of subcutaneous gas along the left
> chest wall.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the pre-existing pneumothorax on the right has completely
> resolved. No pneumothorax on the left. Unchanged normal size of the cardiac silhouette. Unchanged
> normal appearance of the lung parenchyma. The soft tissue air collections have almost completely
> resolved.

**REVISED (Qwen)**

> As compared to the previous radiograph, the pre-existing pneumothorax on the right has completely
> resolved. No pneumothorax on the left. The size of the cardiac silhouette remains unchanged and is
> within normal limits. The appearance of the lung parenchyma remains unchanged and is within normal
> limits. The soft tissue air collections have almost completely resolved.

**REFERENCE (ground truth current)**

> Status post thoracic closure. No evidence of pneumothorax. No pleural effusions. Normal size of
> the cardiac silhouette. Unchanged bilateral soft tissue air collections.

</details>

---

## #16 — study 53749286 (change)

**RadGraph-F1: 0.2581 (draft) → 0.1290 (revised)  |  Δ -0.1290  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 1** (comparison-flagged)  `verbose`

- draft:   Moderate to severe cardiomegaly is unchanged.
- revised: The size of the cardiac silhouette remains moderate to severe but is unchanged.
- diff:    [-Moderate-] {+The size of the cardiac silhouette remains moderate+} to severe [-cardiomegaly-] {+but+} is unchanged.

**sentence 2** (comparison-flagged)  `verbose`

- draft:   Mild pulmonary edema is unchanged.
- revised: There is mild pulmonary edema which remains unchanged.
- diff:    [-Mild-] {+There is mild+} pulmonary edema [-is-] {+which remains+} unchanged.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53395094_: "The size of the cardiac silhouette is enlarged but unchanged."
- _53395094_: "There is mild hilar congestion and pulmonary edema, decreased since the prior radiograph."
- _54458624_: "Heart size remains moderately enlarged but unchanged."
- _54458624_: "There is mild perihilar haziness with vascular indistinctness and increased interstitial markings compatible with mild interstitial pulmonary edema."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Compared with the earlier study, a new endotracheal tube terminates 4.0 cm above the carina. Lobe
> lung volumes are re- demonstrated, with cardiomegaly, mild to moderate pulmonary edema, and
> persistent hilar congestion. No large pleural effusions or pneumothorax on this limited scan. A
> presumed enteric tube courses be low the left hemidiaphragm another view.

**DRAFT (MAIRA-2)**

> Enteric tube has been removed. Moderate to severe cardiomegaly is unchanged. Mild pulmonary edema
> is unchanged. No large pleural effusions. No pneumothorax.

**REVISED (Qwen)**

> Enteric tube has been removed. The size of the cardiac silhouette remains moderate to severe but
> is unchanged. There is mild pulmonary edema which remains unchanged. No large pleural effusions.
> No pneumothorax.

**REFERENCE (ground truth current)**

> Since the prior study performed on ___, lungs are now better aerated. Bibasilar opacities persist,
> although or less consolidated in appearance compared to the prior radiograph. There is no new
> consolidation. Mild pulmonary vascular congestion. No pneumothorax. Marked cardiomegaly is stable.

</details>

---

## #17 — study 53943549 (change)

**RadGraph-F1: 0.2951 (draft) → 0.1695 (revised)  |  Δ -0.1256  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 2** (comparison-flagged)  `truncated`

- draft:   There is mild cardiomegaly, unchanged.
- revised: Cardiomegaly is unchanged.
- diff:    [-There-] {+Cardiomegaly+} is [-mild cardiomegaly,-] unchanged.

**sentence 3** (comparison-flagged)

- draft:   Mild pulmonary edema is improved.
- revised: Pulmonary edema has improved.
- diff:    [-Mild pulmonary-] {+Pulmonary+} edema [-is-] {+has+} improved.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53353512_: "Cardiomegaly is unchanged with stable moderate pulmonary edema and small bilateral effusions."
- _59756691_: "A right subclavian approach dialysis catheter terminates within the right atrium in unchanged position."
- _59756691_: "Median sternotomy wires are surgical clips are again noted."
- _55479271_: "Supporting tubes and lines are in stable position."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Compared with the recent radiographs, there has been interval improvement in the degree of
> pulmonary edema. The heart remains enlarged. No focal consolidation or pleural effusion. Left-
> sided pacemaker remains in place.

**DRAFT (MAIRA-2)**

> A portable frontal chest radiograph demonstrates an endotracheal tube terminating in the mid
> thoracic trachea, left chest wall pacer device with a single lead terminating in the right
> ventricle, and a right internal jugular approach central catheter terminating in the mid SVC. An
> enteric tube courses below the diaphragm and terminates in the proximal stomach. There is mild
> cardiomegaly, unchanged. Mild pulmonary edema is improved. No focal consolidation or pneumothorax
> is appreciated. There may be a trace left pleural effusion.

**REVISED (Qwen)**

> A portable frontal chest radiograph demonstrates an endotracheal tube terminating in the mid
> thoracic trachea, left chest wall pacer device with a single lead terminating in the right
> ventricle, and a right internal jugular approach central catheter terminating in the mid SVC. An
> enteric tube courses below the diaphragm and terminates in the proximal stomach. Cardiomegaly is
> unchanged. Pulmonary edema has improved. No focal consolidation or pneumothorax is appreciated.
> There may be a trace left pleural effusion.

**REFERENCE (ground truth current)**

> The endotracheal tube, left IJ line, and transvenous right atrial biventricular pacer leads are
> unchanged in position. Mild cardiomegaly, mild pulmonary edema, and low lung volumes are stable.
> No new pneumothorax or pleural effusion.

</details>

---

## #18 — study 59243134 (change)

**RadGraph-F1: 0.5238 (draft) → 0.4000 (revised)  |  Δ -0.1238  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (2)

**sentence 1** (comparison-flagged)

- draft:   There are bilateral diffuse interstitial opacities, which are unchanged from prior exam.
- revised: There are bilateral diffuse interstitial opacities, which are unchanged compared to the prior exam.
- diff:    There are bilateral diffuse interstitial opacities, which are unchanged [-from-] {+compared to the+} prior exam.

**sentence 2** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Additionally, there is a more focal opacity in the right upper lobe, which is stable.
- revised: Additionally, there is a more focal opacity in the right upper lobe, which is stable compared to the prior study.
- diff:    Additionally, there is a more focal opacity in the right upper lobe, which is [-stable.-] {+stable compared to the prior study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50955765_: "Redemonstrated are bilateral interstitial opacities with lower lobe predominance that are grossly unchanged compared to the prior radiograph, thought to represent NSIP on the most recent CT."
- _51810656_: "Focal patchy opacity within the right lower lobe is unchanged compared to the prior study."
- _50776567_: "Widespread bilateral lung opacities, not significantly changed since ___ slightly improved since ___."
- _50776567_: "Moderate cardiomegaly is unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Lung volumes are reduced. The left internal jugular central venous catheter has been removed. The
> heart size is borderline enlarged, but accentuated due to low inspiratory lung volumes. There is
> crowding of the bronchovascular structures with probable mild pulmonary vascular congestion.
> Worsening consolidative opacity in the right upper lung field as well as focal opacities within
> the left upper and bilateral lower lung fields are concerning for multifocal pneumonia. No pleural
> effusion or pneumothorax is seen. No acute osseous abnormalities visualized. Clips are
> demonstrated within the left upper quadrant of the abdomen.

**DRAFT (MAIRA-2)**

> The lung volumes are low. There are bilateral diffuse interstitial opacities, which are unchanged
> from prior exam. Additionally, there is a more focal opacity in the right upper lobe, which is
> stable. There is no pleural effusion or pneumothorax. The cardiomediastinal silhouette is normal.

**REVISED (Qwen)**

> The lung volumes are low. There are bilateral diffuse interstitial opacities, which are unchanged
> compared to the prior exam. Additionally, there is a more focal opacity in the right upper lobe,
> which is stable compared to the prior study. There is no pleural effusion or pneumothorax. The
> cardiomediastinal silhouette is normal.

**REFERENCE (ground truth current)**

> The lung volumes are low and there is chronic lung disease, which is relatively unchanged since
> ___. No new focal opacities are seen compared to the ___ chest radiograph; however, right upper
> lobe consolidation is unchanged and may represent old pneumonia. There is no pleural effusion or
> pneumothorax. The heart and mediastinal contours are normal.

</details>

---

## #19 — study 50879902 (change)

**RadGraph-F1: 0.4348 (draft) → 0.3111 (revised)  |  Δ -0.1237  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (3)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, there is no relevant change.
- revised: As compared to the previous radiograph, no relevant change is seen.
- diff:    As compared to the previous radiograph, [-there is-] no relevant [-change.-] {+change is seen.+}

**sentence 5** (comparison-flagged)  `verbose`

- draft:   Unchanged size of the cardiac silhouette.
- revised: The size of the cardiac silhouette remains unchanged.
- diff:    [-Unchanged-] {+The+} size of the cardiac [-silhouette.-] {+silhouette remains unchanged.+}

**sentence 6** (comparison-flagged)  `verbose`

- draft:   Unchanged course of the nasogastric tube.
- revised: The course of the nasogastric tube is unchanged.
- diff:    [-Unchanged-] {+The+} course of the nasogastric [-tube.-] {+tube is unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _54143436_: "As compared to the previous examination, tracheostomy tube is in unchanged position."
- _54143436_: "Also unchanged is the nasogastric tube."
- _53067670_: "In comparison with the earlier study of this date, there is again diffuse opacification of the right lung that could reflect hemorrhage or aspiration."
- _57535765_: "As compared to the previous radiograph, no relevant change is seen."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In comparison with the study of ___, there is little overall change in the peribronchial
> thickening and impaction with extensive bibasilar bronchiectasis. This is again extremely well
> seen on the lateral radiograph. Hyperexpansion of the lungs is consistent with emphysema and the
> cardiac size is normal. No evidence of pulmonary edema. No evidence of acute focal pneumonia.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, there is no relevant change. The lung parenchyma is
> overinflated and shows signs of massive bronchiectasis, predominantly in the lower lungs. These
> changes are better appreciated on the lateral than on the frontal radiograph. No new parenchymal
> opacities. No larger pleural effusions. Unchanged size of the cardiac silhouette. Unchanged course
> of the nasogastric tube.

**REVISED (Qwen)**

> As compared to the previous radiograph, no relevant change is seen. The lung parenchyma is
> overinflated and shows signs of massive bronchiectasis, predominantly in the lower lungs. These
> changes are better appreciated on the lateral than on the frontal radiograph. No new parenchymal
> opacities. No larger pleural effusions. The size of the cardiac silhouette remains unchanged. The
> course of the nasogastric tube is unchanged.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, there is a subtle but new opacity at the right lung base,
> in the medial aspect of the lung. The opacities located in an area of bronchiectasis. Given the
> clinical presentation, pneumonia must be suspected. The referring physician, ___. ___ was paged
> for notification at the time of dictation, 3:18 p.m. on ___ and the findings were discussed over
> the telephone. Otherwise, the radiograph is unchanged, extensive overinflation with bronchiectasis
> but no pleural effusions or other parenchymal changes. Normal size of the cardiac silhouette.
> Unchanged position of the nasogastric tube.

</details>

---

## #20 — study 51664027 (change)

**RadGraph-F1: 0.4000 (draft) → 0.2857 (revised)  |  Δ -0.1143  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 0** (comparison-flagged)

- draft:   There is a moderate left pleural effusion, increased compared to the prior study from _.
- revised: There is a moderate left pleural effusion, increased compared to the prior study.
- diff:    There is a moderate left pleural effusion, increased compared to the prior [-study from _.-] {+study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _52092383_: "There is increased lucency of the right hemithorax with right upper lung chain sutures, consistent with history of lobectomy."
- _52092383_: "Hazy left upper lung opacity is new since the prior exam."
- _57314804_: "Compare to ___, the lung volumes have increased."
- _57314804_: "There is residual moderate left pleural effusion with atelectasis, less compared to prior."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Since ___, there has been continued progressive consolidation involving the left lung with
> asymmetric opacification distributed throughout the right hemithorax most compatible with
> multifocal pneumonia. There are superimposed areas of bibasilar atelectasis. There are no pleural
> effusions or pneumothorax. The cardiomediastinal and hilar contours are stable, with the heart
> borderline enlarged. There is tortuosity and atherosclerotic calcification within the thoracic
> aorta.

**DRAFT (MAIRA-2)**

> There is a moderate left pleural effusion, increased compared to the prior study from _.
> Heterogeneous opacities in the left mid to lower lung are likely secondary to compressive
> atelectasis, although infection cannot be excluded. There is minimal right lower lung atelectasis.
> The heart size is difficult to assess given the moderate left effusion, although likely mildly
> enlarged. The mediastinal contours are normal. There is no pneumothorax.

**REVISED (Qwen)**

> There is a moderate left pleural effusion, increased compared to the prior study. Heterogeneous
> opacities in the left mid to lower lung are likely secondary to compressive atelectasis, although
> infection cannot be excluded. There is minimal right lower lung atelectasis. The heart size is
> difficult to assess given the moderate left effusion, although likely mildly enlarged. The
> mediastinal contours are normal. There is no pneumothorax.

**REFERENCE (ground truth current)**

> Heterogeneous opacities in the right upper lung and left lower lung are new compared to
> radiographs from ___ and concerning for infection. A small to moderate left pleural effusion is
> substantially increased. There is no definite right pleural effusion. Heart size is top normal.
> Unfolding of the thoracic aorta is unchanged. Aortic calcifications are again noted. Segmental
> left rib fractures are unchanged.

</details>

---

## #21 — study 52978683 (change)

**RadGraph-F1: 0.4000 (draft) → 0.2857 (revised)  |  Δ -0.1143  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (3)

**sentence 0** (comparison-flagged)  `negation-changed`

- draft:   As compared to the previous radiograph, there is no relevant change.
- revised: In comparison with the previous radiograph, there is little change.
- diff:    [-As compared to-] {+In comparison with+} the previous radiograph, there is [-no relevant-] {+little+} change.

**sentence 1** (comparison-flagged)

- draft:   The sternal wires are in unchanged position.
- revised: The sternal wires maintain their unchanged position.
- diff:    The sternal wires [-are in-] {+maintain their+} unchanged position.

**sentence 3** (comparison-flagged)

- draft:   Unchanged appearance of the lung parenchyma and the cardiac silhouette.
- revised: The lung parenchyma and the cardiac silhouette have an unchanged appearance.
- diff:    [-Unchanged appearance of the-] {+The+} lung parenchyma and the cardiac [-silhouette.-] {+silhouette have an unchanged appearance.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50509154_: "Diffuse asymmetric interstitial changes, worse on the left and at the right apex, are unchanged over multiple prior studies."
- _50509154_: "The cardiac silhouette is stable."
- _50040442_: "In comparison with study of ___, there is little change."
- _54403128_: "Mediastinal contour appears grossly stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Status post thoracic closure. No evidence of pneumothorax. No pleural effusions. Normal size of
> the cardiac silhouette. Unchanged bilateral soft tissue air collections.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, there is no relevant change. The sternal wires are in
> unchanged position. There is no evidence of pneumothorax or other complications. Unchanged
> appearance of the lung parenchyma and the cardiac silhouette.

**REVISED (Qwen)**

> In comparison with the previous radiograph, there is little change. The sternal wires maintain
> their unchanged position. There is no evidence of pneumothorax or other complications. The lung
> parenchyma and the cardiac silhouette have an unchanged appearance.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, there is no relevant change. No current evidence of
> pneumothorax. Unchanged aspect of the cardiac silhouette. Unchanged mild bilateral air inclusion
> in the soft tissues.

</details>

---

## #22 — study 54505002 (change)

**RadGraph-F1: 0.3636 (draft) → 0.2500 (revised)  |  Δ -0.1136  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   The left-sided PICC line is in unchanged position.
- revised: The left-sided PICC line is in an unchanged position compared to the prior examination.
- diff:    The left-sided PICC line is in {+an+} unchanged [-position.-] {+position compared to the prior examination.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _55990041_: "There are moderate bilateral pleural effusions, slightly increased in size compared to prior exam."
- _55990041_: "Tracheostomy tube is unchanged."
- _53994753_: "In comparison with the study of ___, there is again enlargement of the cardiac silhouette with pulmonary edema."
- _53994753_: "Monitoring and support devices are essentially unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> As compared to the previous radiograph, the patient has a left-sided PICC line. The tip of the
> line is at the level of the mid SVC. A nasogastric tube is new, the tip is not visible on the
> image but the sidehole projects 4-5 cm below the gastroesophageal junction. Mild fluid overload
> with small left pleural effusion. Mild cardiomegaly.

**DRAFT (MAIRA-2)**

> The NG tube is seen to pass below the diaphragm and is curled up in the fundus of the stomach. The
> left-sided PICC line is in unchanged position. The patient is in steep dorsal, recumbent position.
> This explains the crowded appearance of the pulmonary vasculature. The heart size is mildly
> enlarged and there is some fluid overload present. Small bilateral pleural effusions are present.

**REVISED (Qwen)**

> The NG tube is seen to pass below the diaphragm and is curled up in the fundus of the stomach. The
> left-sided PICC line is in an unchanged position compared to the prior examination. The patient is
> in steep dorsal, recumbent position. This explains the crowded appearance of the pulmonary
> vasculature. The heart size is mildly enlarged and there is some fluid overload present. Small
> bilateral pleural effusions are present.

**REFERENCE (ground truth current)**

> AP single view of the chest has been obtained with patient in semi-upright position. Comparison is
> made with the next preceding similar study of ___. Previously identified left-sided PICC line
> remains in unchanged position. An NG tube is seen to be curled up in the epipharynx area and the
> tip of the line reaches just in the upper portion of the esophagus, terminating 3 to 4 cm above
> the level of the carina. Adjustment of NG tube is required. Ref. physician was paged at 4:30 p.m.
> Case was discussed and tube had been withdrawn completely.

</details>

---

## #23 — study 50810335 (no-change)

**RadGraph-F1: 0.5926 (draft) → 0.4800 (revised)  |  Δ -0.1126  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 1** (comparison-flagged)  `verbose negation-changed`

- draft:   Mild cardiomegaly is unchanged.
- revised: As compared to prior chest radiograph from ___, there has been no significant change in mild cardiomegaly.
- diff:    [-Mild cardiomegaly is unchanged.-] {+As compared to prior chest radiograph from ___, there has been no significant change in mild cardiomegaly.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _58599102_: "Bibasilar opacities which may represent pulmonary edema are improved."
- _58599102_: "Stable mediastinal widening due to vascular engorgement."
- _50635928_: "A calcified/bony structure projects inferior to the right coracoid, unchanged."
- _57343028_: "As compared to prior chest radiograph from ___, there has been no significant change."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Comparison is made to the prior study from ___. There is a right IJ catheter with distal lead tip
> in the proximal right atrium. Heart size is mildly enlarged but unchanged. There is a left
> retrocardiac opacity and bilateral pleural effusions which are small. There is mild pulmonary
> fluid overload. Overall, these findings are stable.

**DRAFT (MAIRA-2)**

> One portable AP upright view of the chest. Mild cardiomegaly is unchanged. There is mild pulmonary
> vascular congestion. There is no evidence of pneumonia. No pleural effusion or pneumothorax.

**REVISED (Qwen)**

> One portable AP upright view of the chest. As compared to prior chest radiograph from ___, there
> has been no significant change in mild cardiomegaly. There is mild pulmonary vascular congestion.
> There is no evidence of pneumonia. No pleural effusion or pneumothorax.

**REFERENCE (ground truth current)**

> AP and lateral views of the chest. Bibasilar atelectasis is mild. No pleural effusion or
> pneumothorax. Moderate cardiomegaly, severe pulmonary artery dilatation and moderate pulmonary
> vascular congestion are similar.

</details>

---

## #24 — study 50124332 (change)

**RadGraph-F1: 0.3922 (draft) → 0.2800 (revised)  |  Δ -0.1122  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 2** (comparison-flagged)  `added-hedging`

- draft:   Hilar and mediastinal silhouettes are unchanged.
- revised: The hila and mediastinum appear stable.
- diff:    [-Hilar-] {+The hila+} and [-mediastinal silhouettes are unchanged.-] {+mediastinum appear stable.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _56055083_: "Unchanged degenerative change of the thoracic spine."
- _55838771_: "Heart size remains mildly enlarged but unchanged."
- _54145358_: "The cardiomediastinal silhouette is stable."
- _51616176_: "Prominence of the pulmonary arteries bilaterally is unchanged suggesting underlying pulmonary hypertension."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Pulmonary edema is mild and new since ___. Increased opacity at left lung base is either
> atelectasis and/or combination of atelectasis and edema. Left pleural effusion is presumed and
> small and is also new since ___. Heart size is normal. Cardiomediastinal silhouette is
> unremarkable. Mild-to-moderate atherosclerotic calcification is present in the aortic arch.

**DRAFT (MAIRA-2)**

> Upright portable view of the chest demonstrates hyperexpanded lungs. There is no pleural effusion,
> focal consolidation or pneumothorax. Hilar and mediastinal silhouettes are unchanged. The
> descending aorta is tortuous. Heart is mildly enlarged. There is no pulmonary edema. Port-A-Cath
> tip projects over cavoatrial junction.

**REVISED (Qwen)**

> Upright portable view of the chest demonstrates hyperexpanded lungs. There is no pleural effusion,
> focal consolidation or pneumothorax. The hila and mediastinum appear stable. The descending aorta
> is tortuous. Heart is mildly enlarged. There is no pulmonary edema. Port-A-Cath tip projects over
> cavoatrial junction.

**REFERENCE (ground truth current)**

> Portable upright view of the chest demonstrates low lung volumes. There is no pleural effusion or
> pneumothorax. Heart size is top normal. Hilar and mediastinal silhouettes are unchanged. There is
> perihilar vascular congestion. Interstitial markings are prominent, suggest possible mild
> interstitial pulmonary edema. Right-sided Port-A-Cath is stable position projecting over
> cavoatrial junction.

</details>

---

## #25 — study 59847128 (change)

**RadGraph-F1: 0.3704 (draft) → 0.2593 (revised)  |  Δ -0.1111  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (3)

**sentence 1** (comparison-flagged)

- draft:   Cardiomediastinal contours are stable in appearance.
- revised: Cardiomediastinal silhouette is unchanged in appearance.
- diff:    Cardiomediastinal [-contours are stable-] {+silhouette is unchanged+} in appearance.

**sentence 2** (comparison-flagged)

- draft:   Moderate-to-large right pleural effusion has increased in size with associated worsening atelectasis in the right middle and right lower lobes.
- revised: There is an increase in the size of the moderate-to-large right pleural effusion with associated worsening atelectasis in the right middle and right lower lobes.
- diff:    [-Moderate-to-large-] {+There is an increase in the size of the moderate-to-large+} right pleural effusion [-has increased in size-] with associated worsening atelectasis in the right middle and right lower lobes.

**sentence 3** (comparison-flagged)

- draft:   Small left pleural effusion has slightly increased in size with adjacent minor left basilar atelectasis.
- revised: The small left pleural effusion has slightly increased in size with adjacent minor left basilar atelectasis.
- diff:    [-Small-] {+The small+} left pleural effusion has slightly increased in size with adjacent minor left basilar atelectasis.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _55130730_: "There is blunting of the left costophrenic angle, likely representing a combination of atelectasis and pleural fluid, overall unchanged from ___."
- _55130730_: "Cardiomediastinal silhouette is unchanged."
- _57463787_: "Stable postoperative appearance of cardiomediastinal contours."
- _57463787_: "Lung volumes are improved compared to the prior study."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Left PICC enters a left-sided superior vena cava and subsequently courses vertically to terminate
> in the lower left hemithorax, just above the level of the diaphragm. Withdrawal by approximately 8
> cm could be performed to ensure positioning within the lower left superior vena cava. Cardiac
> silhouette remains enlarged. Opacities involving the right middle and right lower lobe appear
> slightly improved and may reflect atelectasis and/or infectious consolidation. Moderate right
> pleural effusion with subpulmonic and intrafissural components is unchanged as well as a small
> left pleural effusion.

**DRAFT (MAIRA-2)**

> Left PICC has been re-positioned, with tip now terminating in the lower superior vena cava.
> Cardiomediastinal contours are stable in appearance. Moderate-to-large right pleural effusion has
> increased in size with associated worsening atelectasis in the right middle and right lower lobes.
> Small left pleural effusion has slightly increased in size with adjacent minor left basilar
> atelectasis.

**REVISED (Qwen)**

> Left PICC has been re-positioned, with tip now terminating in the lower superior vena cava.
> Cardiomediastinal silhouette is unchanged in appearance. There is an increase in the size of the
> moderate-to-large right pleural effusion with associated worsening atelectasis in the right middle
> and right lower lobes. The small left pleural effusion has slightly increased in size with
> adjacent minor left basilar atelectasis.

**REFERENCE (ground truth current)**

> Left PICC is unchanged in position compared to the prior radiograph. It enters via a left-sided
> approach, and makes a vertical descent at the level of the aortic arch, in keeping with known
> left-sided superior vena cava. The tip of the catheter continues to terminate just above the level
> of the diaphragm to the left of midline, and could be withdrawn approximately 8 cm to ensure
> positioning within the lower left superior vena cava. Cardiomediastinal contours are stable in
> appearance. Moderate right pleural effusion with subpulmonic component has slightly increased in
> size. Adjacent area of opacity within the right middle and lower lobe has also slightly worsened.

</details>

---

## #26 — study 57823021 (change)

**RadGraph-F1: 0.1111 (draft) → 0.0000 (revised)  |  Δ -0.1111  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 0** (comparison-flagged)  `negation-changed`

- draft:   As compared to the previous radiograph, there is no relevant change.
- revised: As compared to the previous radiograph, the findings are unchanged.
- diff:    As compared to the previous radiograph, [-there is no relevant change.-] {+the findings are unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50282600_: "The right dialysis catheter terminates in the right atrium, unchanged from prior."
- _50282600_: "The pulmonary venous congestion is unchanged."
- _57544796_: "As compared to the previous radiograph, the monitoring and support devices are unchanged."
- _57544796_: "There is unchanged evidence of hyperlucency at the right base of the hemithorax without clear morphological attributes."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Compared to prior study there is no significant interval change.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, there is no relevant change. The monitoring and support
> devices are constant. Moderate cardiomegaly with retrocardiac atelectasis. Mild fluid overload. No
> larger pleural effusions.

**REVISED (Qwen)**

> As compared to the previous radiograph, the findings are unchanged. The monitoring and support
> devices are constant. Moderate cardiomegaly with retrocardiac atelectasis. Mild fluid overload. No
> larger pleural effusions.

**REFERENCE (ground truth current)**

> Compared to the prior exam there is no significant interval change.

</details>

---

## #27 — study 50753069 (change)

**RadGraph-F1: 0.2222 (draft) → 0.1111 (revised)  |  Δ -0.1111  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 0** (comparison-flagged)  `verbose`

- draft:   As compared to prior chest radiograph from _, there is increased pulmonary vascular congestion and mild interstitial edema.
- revised: As compared to the prior chest radiograph from _, there has been an interval increase in the degree of pulmonary vascular congestion and mild interstitial edema.
- diff:    As compared to {+the+} prior chest radiograph from _, there [-is increased-] {+has been an interval increase in the degree of+} pulmonary vascular congestion and mild interstitial edema.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _52863500_: "Sternotomy wires are intact and unchanged in position."
- _52863500_: "There is no significant change compared the study on ___."
- _55243087_: "As compared to the prior examination, there has been an interval increase in the degree of prominence of the interstitial markings, compatible with an acute on chronic process."
- _58978409_: "Mild cardiomegaly is stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Low lung volumes. The lungs are clear. Mild enlargement of the cardiac silhouette. The hila are
> normal. There is no pleural effusion and no pneumothorax.

**DRAFT (MAIRA-2)**

> As compared to prior chest radiograph from _, there is increased pulmonary vascular congestion and
> mild interstitial edema. There is no definite focal consolidation, pleural effusion, or
> pneumothorax. Moderate cardiomegaly is stable.

**REVISED (Qwen)**

> As compared to the prior chest radiograph from _, there has been an interval increase in the
> degree of pulmonary vascular congestion and mild interstitial edema. There is no definite focal
> consolidation, pleural effusion, or pneumothorax. Moderate cardiomegaly is stable.

**REFERENCE (ground truth current)**

> The heart is mildly enlarged. The mediastinal and hilar contours are within normal limits. There
> is an area of increased density which projects over the left cardiac border. Otherwise, remaining
> lungs are clear. There are no pleural effusions, pulmonary edema, or pneumothorax.

</details>

---

## #28 — study 57356552 (change)

**RadGraph-F1: 0.3571 (draft) → 0.2500 (revised)  |  Δ -0.1071  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   This is accompanied by worsening bibasilar atelectasis and increasing small bilateral pleural effusions.
- revised: This is accompanied by worsening bibasilar atelectasis and increasing small bilateral pleural effusions compared to the prior study.
- diff:    This is accompanied by worsening bibasilar atelectasis and increasing small bilateral pleural [-effusions.-] {+effusions compared to the prior study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53913149_: "Loculated hydropneumothoraces are present in the left hemithorax anteromedially, and are overall probably not appreciably changed compared to the prior study allowing for positional differences."
- _53913149_: "Post-operative small left pleural effusion is similar to the prior study, and a very small right pleural effusion is also unchanged."
- _50399528_: "As compared to the previous radiograph, the chest tube and the right internal jugular vein catheter has been removed."
- _50399528_: "Otherwise, the radiograph is unchanged, no evidence of acute changes."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> As compared to the previous radiograph, the right-sided chest tube is in unchanged position. No
> evidence of pneumothorax, no pleural effusion. Minimal atelectasis at the left lung base. Normal
> size of the cardiac silhouette. No pulmonary edema.

**DRAFT (MAIRA-2)**

> Following removal of a right-sided chest tube, a small right apical pneumothorax has developed.
> This is accompanied by worsening bibasilar atelectasis and increasing small bilateral pleural
> effusions.

**REVISED (Qwen)**

> Following removal of a right-sided chest tube, a small right apical pneumothorax has developed.
> This is accompanied by worsening bibasilar atelectasis and increasing small bilateral pleural
> effusions compared to the prior study.

**REFERENCE (ground truth current)**

> Right-sided chest tube remains in place, with slight increase in size of a small right pleural
> effusion, but no visible pneumothorax. Bibasilar linear atelectasis has slightly worsened, and
> there is a persistent small left pleural effusion.

</details>

---

## #29 — study 57774874 (change)

**RadGraph-F1: 0.2609 (draft) → 0.1538 (revised)  |  Δ -0.1070  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (3)

**sentence 0** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Increased hazy opacification of the right lower lung may suggest aspiration or developing pneumonia.
- revised: There is increased hazy opacification of the right lower lung which may suggest aspiration or developing pneumonia compared to the prior study.
- diff:    [-Increased-] {+There is increased+} hazy opacification of the right lower lung {+which+} may suggest aspiration or developing [-pneumonia.-] {+pneumonia compared to the prior study.+}

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Stable mild interstitial edema.
- revised: Mild interstitial edema is stable compared to the prior study.
- diff:    [-Stable mild-] {+Mild+} interstitial [-edema.-] {+edema is stable compared to the prior study.+}

**sentence 4** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Stable positioning of atrioventricular ICD leads.
- revised: Atrioventricular ICD leads are stable in their positioning compared to the prior study.
- diff:    [-Stable-] {+Atrioventricular ICD leads are stable in their+} positioning [-of atrioventricular ICD leads.-] {+compared to the prior study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _58215875_: "The cardiomediastinal and hilar contours are stable and within normal limits."
- _50012059_: "There has been interval placement of right internal jugular central venous catheter terminating at the cavoatrial junction without evidence of pneumothorax."
- _50012059_: "In the interval since the prior study, there has been mild increase in pulmonary edema."
- _53692558_: "Chronic changes at the right lung apex are grossly stable surgical bronchiectasis with artifactual disc portion, scarring, and calcifications with superior retraction of the right hila."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Frontal and lateral chest radiographs demonstrate mediastinal and hilar contours are unremarkable.
> Stable mild cardiomegaly identified. Mild interstitial edema noted No pleural effusion or
> pneumothorax. No osseous abnormality identified. Stable positioning of atrioventricular ICD leads.
> Abandoned leads again noted in the right chest wall. Surgical clips project over the upper
> mediastinum.

**DRAFT (MAIRA-2)**

> Increased hazy opacification of the right lower lung may suggest aspiration or developing
> pneumonia. Stable mild interstitial edema. No pleural effusion or pneumothorax evident.
> Mediastinal and hilar contours are unremarkable. Stable positioning of atrioventricular ICD leads.

**REVISED (Qwen)**

> There is increased hazy opacification of the right lower lung which may suggest aspiration or
> developing pneumonia compared to the prior study. Mild interstitial edema is stable compared to
> the prior study. No pleural effusion or pneumothorax evident. Mediastinal and hilar contours are
> unremarkable. Atrioventricular ICD leads are stable in their positioning compared to the prior
> study.

**REFERENCE (ground truth current)**

> Chest PA and lateral radiographs redemonstrate mild interstitial edema and mild cardiomegaly. No
> signs of aspiration and no change from prior CXR.

</details>

---

## #30 — study 53558787 (change)

**RadGraph-F1: 0.2692 (draft) → 0.1633 (revised)  |  Δ -0.1060  [HARMFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **reject**  ← guardrails disagree

### Changed sentences (1)

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Left lower lobe collapse is unchanged since yesterday.
- revised: Left lower lobe collapse is unchanged as compared to the previous study.
- diff:    Left lower lobe collapse is unchanged [-since yesterday.-] {+as compared to the previous study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _51392164_: "In comparison with the study of ___, the monitoring and support devices are unchanged."
- _51392164_: "Unchanged postoperative appearance on the right with diffuse prominence of engorged and indistinct pulmonary vessels consistent with elevated pulmonary venous pressure."
- _56397196_: "As compared to the previous radiograph, there is substantial improvement with substantially improved ventilation of the left lung."
- _58744295_: "As compared to the previous radiograph, the nasogastric tube is now better visible."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> As compared to the previous radiograph, there is increasing opacity in the left hemithorax, likely
> reflecting post-surgical changes. Extensive gas collection in the soft tissues on the left is
> unchanged. Unchanged position of the left chest tube. The right lung and the cardiac silhouette
> are constant in shape, the right lung remains normal.

**DRAFT (MAIRA-2)**

> Patient had recent left lower lobe lobectomy for lung mass. Left lower lobe collapse is unchanged
> since yesterday. Right lung is unremarkable. ET tube ends 5.4 cm above carina. Left jugular line
> is in mid SVC. There is no pneumothorax.

**REVISED (Qwen)**

> Patient had recent left lower lobe lobectomy for lung mass. Left lower lobe collapse is unchanged
> as compared to the previous study. Right lung is unremarkable. ET tube ends 5.4 cm above carina.
> Left jugular line is in mid SVC. There is no pneumothorax.

**REFERENCE (ground truth current)**

> ET tube ends 4.5 cm above carina. NG tube is in the stomach, and left jugular line ends in upper
> SVC. There is no pneumothorax, and left chest tube is in unchanged position in upper hemithorax.
> Left upper lobe that was collapsed yesterday is more aerated and left lung pulmonary edema has
> significantly improved. There is some residual small basilar atelectasis and small pleural
> effusion, if any. Mild subcutaneous air has improved. Right lung is unremarkable. Mediastinal and
> cardiac contours are unchanged.

</details>

---

# Biggest improvements (for contrast)

## #1 — study 58789310 (change)

**RadGraph-F1: 0.3704 (draft) → 0.5714 (revised)  |  Δ +0.2011  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (1)

**sentence 3** (comparison-flagged)  `verbose`

- draft:   The cardiomediastinal silhouette is stable.
- revised: The cardiac and mediastinal silhouettes are stable.
- diff:    The [-cardiomediastinal silhouette is-] {+cardiac and mediastinal silhouettes are+} stable.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _51211390_: "The cardiac and mediastinal silhouettes are stable."
- _59923808_: "The cardiac and mediastinal silhouettes are stable."
- _58063055_: "The cardiac and mediastinal silhouettes are stable."
- _56768274_: "The cardiac and mediastinal silhouettes are stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Frontal radiograph of the chest demonstrates stable mild enlargement of the cardiac silhouette.
> Normal mediastinal and hilar contours. Compared to the prior study of ___ the bilateral pleural
> effusions have resolved. No focal consolidation or pneumothorax present. No pulmonary edema. The
> lungs remain hyperinflated.

**DRAFT (MAIRA-2)**

> Single portable AP upright chest radiograph. Lungs are hyperinflated. There is no focal
> consolidation, pleural effusion, or pneumothorax. The cardiomediastinal silhouette is stable.

**REVISED (Qwen)**

> Single portable AP upright chest radiograph. Lungs are hyperinflated. There is no focal
> consolidation, pleural effusion, or pneumothorax. The cardiac and mediastinal silhouettes are
> stable.

**REFERENCE (ground truth current)**

> The lungs are hyperinflated but without focal consolidation. No pleural effusion or pneumothorax
> is seen. Minor left basilar linear atelectasis/scarring is again seen. The cardiac and mediastinal
> silhouettes are stable and unremarkable.

</details>

---

## #2 — study 54675277 (change)

**RadGraph-F1: 0.0741 (draft) → 0.2667 (revised)  |  Δ +0.1926  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (2)

**sentence 0** (comparison-flagged)  `added-vague-prior-ref`

- draft:   There has been interval placement of a right internal jugular central venous catheter with its tip in the upper SVC.
- revised: There has been interval placement of a right internal jugular central venous catheter with its tip in the upper SVC compared to the prior study.
- diff:    There has been interval placement of a right internal jugular central venous catheter with its tip in the upper [-SVC.-] {+SVC compared to the prior study.+}

**sentence 2** (comparison-flagged)  `added-vague-prior-ref`

- draft:   Otherwise, no significant change from earlier this morning with stable appearance of the cardiomediastinal silhouette, left basilar opacity, and biapical opacities.
- revised: Otherwise, no significant change from earlier this morning with stable appearance of the cardiomediastinal silhouette, left basilar opacity, and biapical opacities compared to the prior study.
- diff:    Otherwise, no significant change from earlier this morning with stable appearance of the cardiomediastinal silhouette, left basilar opacity, and biapical [-opacities.-] {+opacities compared to the prior study.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _56765219_: "Single portable view of the chest is compared to previous exam from earlier the same day."
- _56765219_: "Vascular markings appear less distinct compared to prior, suggesting fluid overload."
- _51587388_: "Bilateral parenchymal opacities are unchanged."
- _54421128_: "Bilateral opacities are not worsened compared to the radiographs from ___ but are improved compared to the radiographs from ___."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Cardiac silhouette size remains mildly enlarged and multiple mediastinal clips from prior CABG are
> again noted. The aorta remains tortuous and diffusely calcified. Pulmonary vasculature is not
> engorged. Hilar contours are similar. Ill-defined focal opacities are again noted within both
> upper lobes as well as within the left lower lobe, not substantially changed in the interval, and
> better assessed on the previous CT. No new focal consolidation, pleural effusion or pneumothorax
> is present. No acute osseous abnormalities detected. Clips are noted within the midline upper
> abdomen.

**DRAFT (MAIRA-2)**

> There has been interval placement of a right internal jugular central venous catheter with its tip
> in the upper SVC. No pneumothorax. Otherwise, no significant change from earlier this morning with
> stable appearance of the cardiomediastinal silhouette, left basilar opacity, and biapical
> opacities.

**REVISED (Qwen)**

> There has been interval placement of a right internal jugular central venous catheter with its tip
> in the upper SVC compared to the prior study. No pneumothorax. Otherwise, no significant change
> from earlier this morning with stable appearance of the cardiomediastinal silhouette, left basilar
> opacity, and biapical opacities compared to the prior study.

**REFERENCE (ground truth current)**

> The right internal jugular central venous catheter is malpositioned, coursing cephalad within the
> right internal jugular vein, tip off of the superior borders of the film. Remainder of the exam is
> unchanged.

</details>

---

## #3 — study 51788121 (change)

**RadGraph-F1: 0.0000 (draft) → 0.1765 (revised)  |  Δ +0.1765  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (1)

**sentence 1** (comparison-flagged)  `verbose`

- draft:   Stable cardiomegaly and tortuous aorta.
- revised: Moderately enlarged heart is stable from prior.
- diff:    [-Stable cardiomegaly and tortuous aorta.-] {+Moderately enlarged heart is stable from prior.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _58432977_: "Left chest AICD leads terminate within the right ventricle and atrium, in unchanged positions."
- _54399983_: "Tripolar pacer again seen unchanged in position."
- _54232257_: "Relative to prior study, there is been little interval change in the overall appearance of the thorax."
- _58683763_: "Moderately enlarged heart is stable from before."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Moderate cardiomegaly is unchanged compared to exams dating back to ___, however appears slightly
> increased compared to exams from ___. There has been interval increase in moderate pulmonary
> vascular congestion and diffuse bilateral interstitial lung markings as well as peribronchiolar
> cuffing concerning for pulmonary edema. Widening of the superior mediastinum is due to mediastinal
> lipomatosis and tortuous vessels as seen on the prior CT from ___. Right-sided Morgagni hernia is
> unchanged. There is no large pleural effusion or pneumothorax. Compression deformities of the mid
> thoracic spine are unchanged compared to the prior exam.

**DRAFT (MAIRA-2)**

> The previously seen left-sided PICC line is no longer visualized. Stable cardiomegaly and tortuous
> aorta. There is no focal consolidation, pleural effusion or pneumothorax.

**REVISED (Qwen)**

> The previously seen left-sided PICC line is no longer visualized. Moderately enlarged heart is
> stable from prior. There is no focal consolidation, pleural effusion or pneumothorax.

**REFERENCE (ground truth current)**

> When compared to prior, there are persistent but potentially slightly less conspicuous bilateral
> increased interstitial markings throughout the lungs. There is no new consolidation or effusion.
> The cardiomediastinal silhouette is enlarged but stable. No acute osseous abnormalities
> identified, compression deformities in the thoracic spine were better seen on prior exam. Old mid
> left clavicular fracture is again noted.

</details>

---

## #4 — study 57873452 (change)

**RadGraph-F1: 0.1026 (draft) → 0.2727 (revised)  |  Δ +0.1702  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (3)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the monitoring and support devices are unchanged.
- revised: In comparison with the previous radiograph, the monitoring and support devices remain unchanged.
- diff:    [-As compared to-] {+In comparison with+} the previous radiograph, the monitoring and support devices [-are-] {+remain+} unchanged.

**sentence 1** (comparison-flagged)  `verbose`

- draft:   The lung volumes have decreased.
- revised: In comparison with the previous radiograph, the lung volumes have decreased.
- diff:    [-The-] {+In comparison with the previous radiograph, the+} lung volumes have decreased.

**sentence 2** (comparison-flagged)  `verbose`

- draft:   There is increasing evidence of atelectasis at the left lung bases.
- revised: In comparison with the previous radiograph, there is increasing evidence of atelectasis at the left lung bases.
- diff:    [-There-] {+In comparison with the previous radiograph, there+} is increasing evidence of atelectasis at the left lung bases.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _59517278_: "In comparison with the study of ___, the monitoring and support devices remain in place."
- _57135047_: "In comparison with the study of ___, the right IJ catheter has been removed."
- _57135047_: "Other monitoring and support devices are essentially unchanged."
- _53999072_: "Lung volumes remain increased, in keeping with severe emphysema."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Indwelling support and monitoring devices are unchanged in position, and cardiomediastinal
> contours are stable allowing for positional differences. Left retrocardiac atelectasis has
> improved, but an area of confluent increased opacity in the right infrahilar region is new. The
> latter may reflect atelectasis, aspiration, or developing infection.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the monitoring and support devices are unchanged. The lung
> volumes have decreased. There is increasing evidence of atelectasis at the left lung bases. In
> addition, the pre-existing opacity at the right lung base is slightly more extensive than on the
> previous image. Mild fluid overload. No other changes.

**REVISED (Qwen)**

> In comparison with the previous radiograph, the monitoring and support devices remain unchanged.
> In comparison with the previous radiograph, the lung volumes have decreased. In comparison with
> the previous radiograph, there is increasing evidence of atelectasis at the left lung bases. In
> addition, the pre-existing opacity at the right lung base is slightly more extensive than on the
> previous image. Mild fluid overload. No other changes.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, the monitoring and support devices are constant in
> position. The pre-existing right basal opacity, with maximum in the infrahilar area, is not
> substantially changed. On the left, there is decreased visibility of the left hemidiaphragm,
> suggesting the appearance of either atelectasis or small left pleural effusion. Unchanged moderate
> cardiomegaly. The right costophrenic sinus is unremarkable.

</details>

---

## #5 — study 56483572 (change)

**RadGraph-F1: 0.0526 (draft) → 0.2051 (revised)  |  Δ +0.1525  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (2)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the monitoring and support devices are constant.
- revised: As compared to the previous radiograph, the monitoring and support devices are unchanged.
- diff:    As compared to the previous radiograph, the monitoring and support devices are [-constant.-] {+unchanged.+}

**sentence 2** (comparison-flagged)

- draft:   The right lung base shows minimally increasing signs of atelectasis.
- revised: The right lung base demonstrates minimally increased signs of atelectasis.
- diff:    The right lung base [-shows-] {+demonstrates+} minimally [-increasing-] {+increased+} signs of atelectasis.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50048338_: "In comparison with the study of earlier in this date, the monitoring and support devices are unchanged, except for placement of a nasogastric tube that extends to the stomach with the side hole at the level of the esophagogastric junction and a right IJ catheter with its tip in the mid SVC with no evidence of pneumothorax."
- _51411674_: "As compared to the previous radiograph, the patient has an unchanged right-sided PIC line."
- _51411674_: "Otherwise, normal chest radiograph, with the exception of a small atelectasis at the right lung base that is unchanged compared to the prior image."
- _54670228_: "As compared to a previous radiograph, the tip of the endotracheal tube is not substantially changed, the tip projects 4.5 cm above the carina."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Comparison is made to prior study from ___. The Swan-Ganz catheter, left-sided pacemaker,
> endotracheal tube, feeding tube and mediastinal wires are all unchanged in position. There is a
> confluent area of opacity in the left upper lobe which is stable. There is an increase in opacity
> at the right base, which may be due to developing infiltrate or atelectasis. There is an unchanged
> left retrocardiac area which may represent underlying infiltrate and/or pleural effusion. There is
> a left ventricular prominence. No pneumothoraces are present.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the monitoring and support devices are constant. The
> extensive left-sided pneumonia, notably in the left upper lobe, is unchanged in severity and
> extent. The right lung base shows minimally increasing signs of atelectasis. No other changes.

**REVISED (Qwen)**

> As compared to the previous radiograph, the monitoring and support devices are unchanged. The
> extensive left-sided pneumonia, notably in the left upper lobe, is unchanged in severity and
> extent. The right lung base demonstrates minimally increased signs of atelectasis. No other
> changes.

**REFERENCE (ground truth current)**

> In comparison with the study of ___, the monitoring and support devices remain in place. There may
> be mild increased aeration in the left upper zone. Retrocardiac opacification is consistent with
> volume loss in the left lower lobe. Hazy opacification bilaterally is consistent with pleural
> effusions, and there is some increase in pulmonary venous pressure.

</details>

---

## #6 — study 53708518 (change)

**RadGraph-F1: 0.2143 (draft) → 0.3636 (revised)  |  Δ +0.1494  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (1)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the patient has developed a left lower lobe pneumonia.
- revised: In comparison with the previous radiograph, there is now a finding of left lower lobe pneumonia.
- diff:    [-As compared to-] {+In comparison with+} the previous radiograph, [-the patient has developed-] {+there is now+} a {+finding of+} left lower lobe pneumonia.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53288934_: "In comparison with the study of ___, there is again mild hyperexpansion of the lungs suggesting underlying chronic pulmonary disease."
- _51540539_: "There are unchanged signs of marked overinflation."
- _51540539_: "Newly appeared are relatively extensive parenchymal opacities in the right upper lobe and in the left upper lobe."
- _55534471_: "In comparison with study of ___, there is again hyperexpansion of the lungs consistent with chronic pulmonary disease."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> The lungs are clear without focal consolidation. No pleural effusion or pneumothorax is seen.
> Cardiac and mediastinal silhouettes are unremarkable. Suggestion of mitral anulus calcification is
> seen.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the patient has developed a left lower lobe pneumonia. The
> pneumonia is seen on both the frontal and the lateral radiograph. No other parenchymal changes. No
> pleural effusions. No hilar or mediastinal abnormalities. At the time of dictation and
> observation, 1:59 p.m., on _, the referring physician, _. _ was paged for notification.

**REVISED (Qwen)**

> In comparison with the previous radiograph, there is now a finding of left lower lobe pneumonia.
> The pneumonia is seen on both the frontal and the lateral radiograph. No other parenchymal
> changes. No pleural effusions. No hilar or mediastinal abnormalities. At the time of dictation and
> observation, 1:59 p.m., on _, the referring physician, _. _ was paged for notification.

**REFERENCE (ground truth current)**

> PA and lateral views of the chest. There are new opacities in the superior segment of the left
> lower lobe and in the right lower lobe, most consistent with multifocal pneumonia. No pleural
> effusion or pneumothorax. Cardiomediastinal and hilar contours are normal.

</details>

---

## #7 — study 50955589 (change)

**RadGraph-F1: 0.0976 (draft) → 0.2439 (revised)  |  Δ +0.1463  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (2)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the right chest tube is in unchanged position.
- revised: As compared to the previous radiograph, the right chest tube is in an unchanged position.
- diff:    As compared to the previous radiograph, the right chest tube is in {+an+} unchanged position.

**sentence 3** (comparison-flagged)  `verbose`

- draft:   Unchanged appearance of the left lung.
- revised: The appearance of the left lung is unchanged.
- diff:    [-Unchanged-] {+The+} appearance of the left [-lung.-] {+lung is unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _57839188_: "Left chest wall Port-A-Cath is again noted, catheter tip not clearly delineated but likely in the region of the RA SVC junction."
- _53520390_: "Left-sided pleural effusion appears to be improved but could also relate to a more erect positioning of the patient."
- _50717958_: "The small right effusion is slightly larger on the current study and there is increased volume loss in the right lower lobe the remainder the appearance of the chest is unchanged"
- _57146192_: "Heart size unchanged."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> There has been interval increase in the pulmonary edema, greater on the right than on the left.
> There are bilateral small pleural effusions with compressive atelectasis. There is stable widening
> of the mediastinum. A right chest tube is seen and unchanged from the prior exams. There are
> multiple overlying wires. The cardiomediastinal silhouette is unchanged.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the right chest tube is in unchanged position. The right
> lung base is minimally better ventilated than on the previous image. However, a right pleural
> effusion and a right lower lung consolidation persists. Unchanged appearance of the left lung.

**REVISED (Qwen)**

> As compared to the previous radiograph, the right chest tube is in an unchanged position. The
> right lung base is minimally better ventilated than on the previous image. However, a right
> pleural effusion and a right lower lung consolidation persists. The appearance of the left lung is
> unchanged.

**REFERENCE (ground truth current)**

> In comparison with the study of ___, the pulmonary vascular congestion has decreased.
> Opacification at the right base is again consistent with effusion and volume loss. Less prominent
> effusion and atelectasis is seen at the left base. Right chest tube remains in place without
> pneumothorax. Extensive opacification in the right paratracheal region is consistent with the
> known invasive esophageal tumor.

</details>

---

## #8 — study 55667092 (change)

**RadGraph-F1: 0.0645 (draft) → 0.2000 (revised)  |  Δ +0.1355  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (4)

**sentence 1** (comparison-flagged)

- draft:   Unchanged appearance of the right basal atelectasis.
- revised: The right basal atelectasis has an unchanged appearance.
- diff:    [-Unchanged appearance of the-] {+The+} right basal [-atelectasis.-] {+atelectasis has an unchanged appearance.+}

**sentence 2** (comparison-flagged)

- draft:   Unchanged appearance of the cardiac silhouette.
- revised: The cardiac silhouette maintains a stable appearance.
- diff:    [-Unchanged appearance of the-] {+The+} cardiac [-silhouette.-] {+silhouette maintains a stable appearance.+}

**sentence 3** (comparison-flagged)  `verbose`

- draft:   Unchanged alignment of the sternal wires.
- revised: The alignment of the sternal wires remains unchanged.
- diff:    [-Unchanged-] {+The+} alignment of the sternal [-wires.-] {+wires remains unchanged.+}

**sentence 4** (comparison-flagged)  `verbose`

- draft:   Unchanged appearance of the left hemithorax.
- revised: The appearance of the left hemithorax is unchanged.
- diff:    [-Unchanged-] {+The+} appearance of the left [-hemithorax.-] {+hemithorax is unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _54305038_: "As compared to the previous radiograph, there is unchanged evidence of minimal atelectasis at the right lung bases."
- _54305038_: "The pleural effusions that pre-existed have not substantially increased as compared to the previous examination."
- _54874874_: "Mediastinal contours are stable."
- _54874874_: "A left single lead pacemaker is unchanged in appearance."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In comparison with study of ___, there is little overall change in the appearance of the
> cardiomediastinal silhouette. Mild atelectatic changes are seen especially at the right base.
> Little change in the degree of pleural fluid. Central catheter has been removed.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the extent of the known right pleural effusion is
> unchanged. Unchanged appearance of the right basal atelectasis. Unchanged appearance of the
> cardiac silhouette. Unchanged alignment of the sternal wires. Unchanged appearance of the left
> hemithorax.

**REVISED (Qwen)**

> As compared to the previous radiograph, the extent of the known right pleural effusion is
> unchanged. The right basal atelectasis has an unchanged appearance. The cardiac silhouette
> maintains a stable appearance. The alignment of the sternal wires remains unchanged. The
> appearance of the left hemithorax is unchanged.

**REFERENCE (ground truth current)**

> In comparison with study of ___, there has been a substantial increase in the degree of right
> pleural effusion, which extends upward on the frontal view to almost the level of the carina.
> There may be mild shift of the mediastinum to the left, though there is probably substantial
> volume loss in the right lower lung. The left lung is essentially clear. Otherwise, little change.

</details>

---

## #9 — study 58778783 (change)

**RadGraph-F1: 0.2222 (draft) → 0.3571 (revised)  |  Δ +0.1349  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (1)

**sentence 3** (comparison-flagged)  `verbose`

- draft:   The cardiomediastinal silhouette is stable.
- revised: The cardiomediastinal and hilar contours are stable.
- diff:    The cardiomediastinal [-silhouette is-] {+and hilar contours are+} stable.

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _57032366_: "There has been interval resolution of the right medial lung base opacification."
- _57032366_: "The cardiomediastinal and hilar contours are stable."
- _50145769_: "The mediastinal and hilar contours appear unchanged aside from the fact that the hiatal hernia was quite small before in retrospect, so it may be partly reducible."
- _55961438_: "The cardiac, mediastinal and hilar contours appear stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> The lung volumes are slightly low, causing accentuation of the pulmonary vasculature and
> exaggeration of the heart size. Persistent right middle lobe heterogeneous opacity is concerning
> for chronic aspiration, although pneumonia could have a similar appearance. The lungs are
> otherwise clear. The cardiac and mediastinal contours are normal. There are no pleural
> abnormalities.

**DRAFT (MAIRA-2)**

> AP chest radiograph. The lungs are clear. There is no pleural effusion or pneumothorax. The
> cardiomediastinal silhouette is stable.

**REVISED (Qwen)**

> AP chest radiograph. The lungs are clear. There is no pleural effusion or pneumothorax. The
> cardiomediastinal and hilar contours are stable.

**REFERENCE (ground truth current)**

> The heart is normal in size. The mediastinal and hilar contours appear within normal limits. There
> is no pleural effusion or pneumothorax. There is a new opacity in the right lower lobe concerning
> for pneumonia, superimposed on preexisting patchy medial right middle lobe opacification that
> appears more chronic, also comparing to ___, although the lungs had been clear on earlier
> radiographs from ___.

</details>

---

## #10 — study 56581797 (change)

**RadGraph-F1: 0.0000 (draft) → 0.1333 (revised)  |  Δ +0.1333  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (2)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the patient has received a Dobbhoff catheter.
- revised: In comparison with the previous radiograph, a Dobbhoff catheter has been placed.
- diff:    [-As compared to-] {+In comparison with+} the previous radiograph, [-the patient has received-] a Dobbhoff [-catheter.-] {+catheter has been placed.+}

**sentence 3** (comparison-flagged)  `truncated`

- draft:   Otherwise, the radiograph is unchanged.
- revised: Unchanged radiograph otherwise.
- diff:    [-Otherwise, the-] {+Unchanged+} radiograph [-is unchanged.-] {+otherwise.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _58217535_: "In comparison with study of ___, there has been a CABG procedure performed with intact midline sternal wires."
- _50014647_: "As compared to the previous image, the malpositioned right-sided PICC line has been pulled back."
- _50014647_: "Unchanged right basal opacity."
- _53923846_: "In comparison with the study of ___, there is a fiducial clip placed post-posteromedially at the right base."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> INDICATION: ___-year-old male with chest pain and achalasia with a foreign body sensation in the
> throat, evaluate. COMPARISONS: Chest radiograph ___ and ___. CT torso ___. PA AND LATERAL VIEWS OF
> THE CHEST: A large dilated, debris-filled, possibly fluid filled esophagus is again appreciated,
> abutting the right mediastinum, in this patient with known achalasia. The finding appears more
> prominent as compared to the right study of ___ but similar to ___. There is a questionable air-
> fluid level in the proximal thoracic esophagus. The possibility of progressed slowed emptying of
> the esophagus is raised. There is no evidence of aspiration. There is no pleural effusion or
> pneumothorax. The cardiac silhouette is difficult to assess.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the patient has received a Dobbhoff catheter. The catheter
> is coiled in the middle parts of the esophagus and needs to be re-positioned. There is no evidence
> of complications such as pneumothorax. Otherwise, the radiograph is unchanged. At the time of
> dictation and observation, 4:38 p.m., on _, the referring physician, _. _, was paged for
> notification.

**REVISED (Qwen)**

> In comparison with the previous radiograph, a Dobbhoff catheter has been placed. The catheter is
> coiled in the middle parts of the esophagus and needs to be re-positioned. There is no evidence of
> complications such as pneumothorax. Unchanged radiograph otherwise. At the time of dictation and
> observation, 4:38 p.m., on _, the referring physician, _. _, was paged for notification.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, the nasogastric tube is likely coursing through the
> dilated esophagus and terminates near the gastroesophageal junction. The course is better
> appreciated on the lateral than on the frontal radiograph and best correlated with a CT torso
> examination from ___, to reflect abnormal anatomy.

</details>

---

## #11 — study 57478725 (change)

**RadGraph-F1: 0.2553 (draft) → 0.3750 (revised)  |  Δ +0.1197  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (4)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the patient has been intubated.
- revised: In comparison to the previous radiograph, the patient has been intubated.
- diff:    [-As compared-] {+In comparison+} to the previous radiograph, the patient has been intubated.

**sentence 3** (comparison-flagged)  `verbose`

- draft:   The lung volumes have decreased.
- revised: Lung volumes have decreased as compared to the prior radiograph.
- diff:    [-The lung-] {+Lung+} volumes have [-decreased.-] {+decreased as compared to the prior radiograph.+}

**sentence 4** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   There are increasing bilateral pleural effusions with subsequent areas of atelectasis at the lung bases.
- revised: Bilateral pleural effusions are increasing with subsequent areas of atelectasis at the lung bases as compared to the prior study.
- diff:    [-There-] {+Bilateral pleural effusions+} are increasing [-bilateral pleural effusions-] with subsequent areas of atelectasis at the lung [-bases.-] {+bases as compared to the prior study.+}

**sentence 5** (comparison-flagged)  `verbose`

- draft:   Unchanged moderate cardiomegaly.
- revised: Moderate cardiomegaly is unchanged.
- diff:    [-Unchanged moderate cardiomegaly.-] {+Moderate cardiomegaly is unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _58806985_: "In comparison to the prior radiograph on ___, there has been worsening of the substantial left-sided pleural effusion with adjacent atelectasis."
- _58806985_: "Severe cardiomegaly is unchanged."
- _56875500_: "There is no change as compared to the previous image, the Dobbhoff catheter tip is curled in the stomach, the tip points upwards to the proximal stomach."
- _56875500_: "Unchanged evidence of moderate cardiomegaly, atelectasis at the left lung base and a moderate left pleural effusion."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> ONE PORTABLE SUPINE AP VIEW OF THE CHEST. Right internal jugular catheter ends near the cavoatrial
> junction. NG tube is seen in the stomach with last side port below the GE junction. The lung
> findings are unchanged compared to study done two hours prior.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the patient has been intubated. The tip of the
> endotracheal tube projects 3.5 cm above the carina. The other monitoring and support devices are
> constant. The lung volumes have decreased. There are increasing bilateral pleural effusions with
> subsequent areas of atelectasis at the lung bases. Unchanged moderate cardiomegaly. No
> pneumothorax.

**REVISED (Qwen)**

> In comparison to the previous radiograph, the patient has been intubated. The tip of the
> endotracheal tube projects 3.5 cm above the carina. The other monitoring and support devices are
> constant. Lung volumes have decreased as compared to the prior radiograph. Bilateral pleural
> effusions are increasing with subsequent areas of atelectasis at the lung bases as compared to the
> prior study. Moderate cardiomegaly is unchanged. No pneumothorax.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, the endotracheal tube is in unchanged position. The
> nasogastric tube and the right central venous access line are also unchanged. There are
> bilaterally increasing pleural effusions with subsequent increasing areas of basal atelectasis.
> The overall lung volumes remain low. Moderate cardiomegaly is unchanged. Known pulmonary
> metastatic disease.

</details>

---

## #12 — study 54626336 (change)

**RadGraph-F1: 0.2353 (draft) → 0.3529 (revised)  |  Δ +0.1176  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (3)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, there is no relevant change.
- revised: As compared to the previous radiograph, there is no significant change.
- diff:    As compared to the previous radiograph, there is no [-relevant-] {+significant+} change.

**sentence 2** (comparison-flagged)  `verbose`

- draft:   The course of the nasogastric tube is unchanged.
- revised: In comparison with the prior radiograph, the course of the nasogastric tube remains unchanged.
- diff:    [-The-] {+In comparison with the prior radiograph, the+} course of the nasogastric tube [-is-] {+remains+} unchanged.

**sentence 5** (comparison-flagged)

- draft:   No newly appeared focal parenchymal opacity suggesting pneumonia.
- revised: No new focal parenchymal opacities suggestive of pneumonia are noted.
- diff:    No [-newly appeared-] {+new+} focal parenchymal [-opacity suggesting pneumonia.-] {+opacities suggestive of pneumonia are noted.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _57544796_: "As compared to the previous radiograph, the monitoring and support devices are unchanged."
- _57544796_: "There is unchanged evidence of hyperlucency at the right base of the hemithorax without clear morphological attributes."
- _54329597_: "In comparison with the study of ___, there is little overall change."
- _51386763_: "As compared to the prior radiograph, the patient's fluid overload has improved."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> Compared to the prior exam there is no significant interval change.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, there is no relevant change. The tip of the endotracheal
> tube projects 4.7 cm above the carina. The course of the nasogastric tube is unchanged. Moderate
> cardiomegaly with retrocardiac atelectasis. Minimal fluid overload. No newly appeared focal
> parenchymal opacity suggesting pneumonia.

**REVISED (Qwen)**

> As compared to the previous radiograph, there is no significant change. The tip of the
> endotracheal tube projects 4.7 cm above the carina. In comparison with the prior radiograph, the
> course of the nasogastric tube remains unchanged. Moderate cardiomegaly with retrocardiac
> atelectasis. Minimal fluid overload. No new focal parenchymal opacities suggestive of pneumonia
> are noted.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, there is no relevant change. Moderate atelectasis in the
> retrocardiac lung regions. No new parenchymal opacities. Unchanged position of the endotracheal
> tube and nasogastric tube.

</details>

---

## #13 — study 59488278 (change)

**RadGraph-F1: 0.0000 (draft) → 0.1143 (revised)  |  Δ +0.1143  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (3)

**sentence 0** (comparison-flagged)

- draft:   Portable frontal radiograph of the chest demonstrates interval decrease in left pleural effusion with stable right pleural effusion.
- revised: The portable frontal radiograph of the chest demonstrates an interval decrease in the left pleural effusion with stable right pleural effusion.
- diff:    [-Portable-] {+The portable+} frontal radiograph of the chest demonstrates {+an+} interval decrease in {+the+} left pleural effusion with stable right pleural effusion.

**sentence 1** (comparison-flagged)  `verbose added-vague-prior-ref`

- draft:   Stable right upper lobe opacification and volume loss status post right upper lobe lobectomy and radiation therapy.
- revised: As compared to the prior study, the right upper lobe opacification and volume loss status post right upper lobe lobectomy and radiation therapy are stable.
- diff:    [-Stable-] {+As compared to the prior study, the+} right upper lobe opacification and volume loss status post right upper lobe lobectomy and radiation [-therapy.-] {+therapy are stable.+}

**sentence 3** (comparison-flagged)  `verbose`

- draft:   Unchanged mediastinal and hilar contours.
- revised: The mediastinal and hilar contours remain unchanged.
- diff:    [-Unchanged-] {+The+} mediastinal and hilar [-contours.-] {+contours remain unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _50478904_: "The rounded opacity at the right lung base has improved."
- _50478904_: "Although improved, there is persistent patchy opacification."
- _52527350_: "As compared to the previous radiograph, there is no relevant change."
- _54245595_: "Retrocardiac opacity present on ___ has improved."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In comparison with the earlier study of this date, there is little overall change in the degree of
> aeration of the lungs. Some suggested increased opacification at the left costophrenic angle could
> reflect some increasing effusion. No evidence of pneumothorax. Evidence of prior right upper lobe
> lobectomy and radiation therapy, better demonstrated on recent CT scan.

**DRAFT (MAIRA-2)**

> Portable frontal radiograph of the chest demonstrates interval decrease in left pleural effusion
> with stable right pleural effusion. Stable right upper lobe opacification and volume loss status
> post right upper lobe lobectomy and radiation therapy. Normal heart size. Unchanged mediastinal
> and hilar contours. No pneumothorax.

**REVISED (Qwen)**

> The portable frontal radiograph of the chest demonstrates an interval decrease in the left pleural
> effusion with stable right pleural effusion. As compared to the prior study, the right upper lobe
> opacification and volume loss status post right upper lobe lobectomy and radiation therapy are
> stable. Normal heart size. The mediastinal and hilar contours remain unchanged. No pneumothorax.

**REFERENCE (ground truth current)**

> Cardiomediastinal contours appear unchanged from ___. Patient is status post right upper
> thoracoplasty with rib resections. Left lung shows no focal consolidation. Pulmonary edema is
> improved since the prior exam.

</details>

---

## #14 — study 53225437 (change)

**RadGraph-F1: 0.3333 (draft) → 0.4444 (revised)  |  Δ +0.1111  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (2)

**sentence 0** (comparison-flagged)  `added-vague-prior-ref`

- draft:   Left lung volume loss with apical pleural thickening, pleural effusion and lower lung atelectasis is stable since _.
- revised: Left lung volume loss with apical pleural thickening, pleural effusion, and lower lung atelectasis is unchanged since prior study.
- diff:    Left lung volume loss with apical pleural thickening, pleural [-effusion-] {+effusion,+} and lower lung atelectasis is [-stable-] {+unchanged+} since [-_.-] {+prior study.+}

**sentence 3** (comparison-flagged)

- draft:   Mediastinal and cardiac contours are unchanged.
- revised: Mediastinal and cardiac contours are stable.
- diff:    Mediastinal and cardiac contours are [-unchanged.-] {+stable.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _57142064_: "Right lower lung atelectasis has completely resolved."
- _57142064_: "Left residual basal atelectatic bands are unchanged."
- _55503748_: "Elevation of the right hemidiaphragm is stable."
- _55503748_: "Heart size and cardiomediastinal contours are stable."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> There is continued elevation of the left hemidiaphragm with left pleural abnormality, unchanged
> since the prior exam. There is no evidence of pneumonia, pneumothorax or pulmonary edema. The
> heart is top normal in size.

**DRAFT (MAIRA-2)**

> Left lung volume loss with apical pleural thickening, pleural effusion and lower lung atelectasis
> is stable since _. There is no new lung consolidation. The right lung is unremarkable. Mediastinal
> and cardiac contours are unchanged.

**REVISED (Qwen)**

> Left lung volume loss with apical pleural thickening, pleural effusion, and lower lung atelectasis
> is unchanged since prior study. There is no new lung consolidation. The right lung is
> unremarkable. Mediastinal and cardiac contours are stable.

**REFERENCE (ground truth current)**

> The patient had left lower lobe lobectomy in ___. Expected stable surgical changes are seen in the
> left lung with volume loss and mild pleural thickening. There is no pneumothorax. The right lung
> is unremarkable. Mediastinal and cardiac contours are not enlarged.

</details>

---

## #15 — study 54670469 (change)

**RadGraph-F1: 0.1905 (draft) → 0.3000 (revised)  |  Δ +0.1095  [HELPFUL]**  
CheXbert guardrail: **accept**  |  RadGraph guardrail: **accept**

### Changed sentences (4)

**sentence 0** (comparison-flagged)

- draft:   As compared to the previous radiograph, the patient has been extubated.
- revised: Compared to the previous radiograph, the patient has been extubated.
- diff:    [-As compared-] {+Compared+} to the previous radiograph, the patient has been extubated.

**sentence 2** (comparison-flagged)

- draft:   The left internal jugular vein catheter is in unchanged position.
- revised: The left internal jugular vein catheter maintains its previous position.
- diff:    The left internal jugular vein catheter [-is in unchanged-] {+maintains its previous+} position.

**sentence 3** (comparison-flagged)

- draft:   The pleural effusion on the right has minimally increased.
- revised: There has been a minimal increase in the right pleural effusion.
- diff:    [-The pleural effusion on-] {+There has been a minimal increase in+} the right [-has minimally increased.-] {+pleural effusion.+}

**sentence 5** (comparison-flagged)  `verbose`

- draft:   Unchanged size of the cardiac silhouette.
- revised: The size of the cardiac silhouette remains unchanged.
- diff:    [-Unchanged-] {+The+} size of the cardiac [-silhouette.-] {+silhouette remains unchanged.+}

<details><summary>Retrieved exemplars shown to Qwen</summary>

- _53464564_: "In comparison with the earlier study of this date, there has been a right thoracentesis with drainage of a substantial amount of fluid from the right hemithorax."
- _53464564_: "The appearance of the heart and lungs is otherwise essentially unchanged."
- _56346564_: "In comparison to the chest radiograph obtained 1 day prior, there is been a substantial in the right pleural effusion, now small to moderate, after interval placement of a right-sided chest tube."
- _52484419_: "Compared to the previous radiograph, the patient shows unchanged monitoring and support devices."

</details>

<details><summary>Full texts (prior / draft / revised / reference)</summary>

**PRIOR (ground truth)**

> In comparison with the previous study, there is now an endotracheal tube in place with its tip
> only about 1.5 cm above the carina. This information wasd conveyed to Dr. ___. Intestinal tube
> extends well into the stomach. Left IJ catheter tip is unchanged. The extensive right apical
> lateral consolidation has substantially cleared. The opacification involving much of the left lung
> has decreased. It is unclear whether this represents clearing pneumonia or possible decrease in
> asymmetric pulmonary edema. Opacification at the left base silhouetting the hemidiaphragm is
> consistent with pleural effusion. Right hemidiaphragmatic contour is elevated, possibly relating
> to pleural effusion, with streaks of atelectasis at the base.

**DRAFT (MAIRA-2)**

> As compared to the previous radiograph, the patient has been extubated. The nasogastric tube has
> been removed. The left internal jugular vein catheter is in unchanged position. The pleural
> effusion on the right has minimally increased. The atelectasis at the left lung base is constant.
> Unchanged size of the cardiac silhouette. No pneumothorax.

**REVISED (Qwen)**

> Compared to the previous radiograph, the patient has been extubated. The nasogastric tube has been
> removed. The left internal jugular vein catheter maintains its previous position. There has been a
> minimal increase in the right pleural effusion. The atelectasis at the left lung base is constant.
> The size of the cardiac silhouette remains unchanged. No pneumothorax.

**REFERENCE (ground truth current)**

> As compared to the previous radiograph, the patient has been extubated. The nasogastric tube has
> been removed. There are moderate bilateral pleural effusions with relatively substantial areas of
> atelectasis. Size of the cardiac silhouette cannot be determined. No evidence of new parenchymal
> opacities suggesting pneumonia. A left internal jugular vein catheter remains in situ.

</details>

---
