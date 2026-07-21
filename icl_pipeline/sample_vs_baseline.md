# Approach vs. baseline — random sample

Variant: **none**  ·  n = 15  ·  seed = 0  ·  stratified by change flag

Baseline is the raw MAIRA-2 draft. 12 of 15 sampled cases were altered by the pipeline; the remainder passed through unchanged (no comparison sentence was flagged, or the guardrail reverted the revision).

Diff markup: `[-removed-]` `{+added+}`.

---

## Sample 1 — study 53124891 (change)

**1 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> PA and lateral chest views were obtained with patient in upright position. Comparison is made with
> the next preceding portable chest examination of _. The previously described right-sided basal
> parenchymal densities persist. They have not changed significantly. No new parenchymal
> abnormalities are seen. The previously described esophageal stent remains in unchanged position.
> No pneumothorax has developed.

**Approach — ICL pipeline output**

> PA and lateral chest views were obtained with patient in upright position. Comparison is made with
> the next preceding portable chest examination of _. The previously described right-sided basal
> parenchymal densities persist. They have not changed significantly. No new parenchymal
> abnormalities are seen. The previously described esophageal stent is noted to be in the same
> position. No pneumothorax has developed.

**Reference — ground-truth current report**

> PA and lateral chest views were obtained with patient in upright position. Comparison is made with
> the next preceding AP chest examination of ___. Heart size remains normal. Unremarkable appearance
> of aortic contours. Similar as identified on the previous examination, there is a wide caliber
> (___-mm diameter) stent occupying the esophagus and reaching from the upper thorax clavicular
> level down into the hiatus (see also report on barium examination of neoesophagus of same day).
> There is a right-sided pleural effusion that blunts the right-sided lateral pleural sinus but
> extends into the posterior pleural spaces, occupying the area posterior to the stent prosthesis
> along the right posterior chest wall. The amount of pleural effusion has increased in comparison
> with the preceding AP single view chest examination of ___. The left-sided hemithorax demonstrates
> unchanged findings with regard to pulmonary vasculature and absence of any new acute infiltrates.
> No pneumothorax is identified in the apical area.

<details><summary>Sentence-level diff</summary>

*sentence 5* (comparison-flagged)

    The previously described esophageal stent [-remains-] {+is noted to be+} in [-unchanged-] {+the same+} position.

</details>

<details><summary>Prior report (input context)</summary>

> In comparison with the study of ___, the opacification at the right base has decreased. This could
> reflect improving effusion and atelectasis, or merely be a manifestation of a more upright
> position of the patient. Otherwise, little change.

</details>

---

## Sample 2 — study 55124994 (change)

**3 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> As compared to the previous radiograph, the tip of the endotracheal tube now projects 4.3 cm above
> the carina. The course of the nasogastric tube is unchanged. Unchanged appearance of the lung
> parenchyma and the cardiac silhouette.

**Approach — ICL pipeline output**

> The tip of the endotracheal tube now projects 4.3 cm above the carina as compared to the previous
> radiograph. The course of the nasogastric tube remains unchanged. The appearance of the lung
> parenchyma and the cardiac silhouette is unchanged.

**Reference — ground-truth current report**

> As compared to the previous examination, the patient has been intubated. The tip of the
> endotracheal tube projects 3.7 cm above the carina. The patient also has received a nasogastric
> tube, the course of the tube is unremarkable, the tip of the tube does not display on the image.
> The ventriculoperitoneal shunt and the left subclavian access line are unchanged. There is no
> evidence of complications, notably no pneumothorax. The lung volumes are increased, with
> subsequent decrease in severity and extent of a pre-existing right basal medial parenchymal
> opacity. No newly appeared parenchymal opacities, unchanged size of the cardiac silhouette. No
> pleural effusions.

<details><summary>Sentence-level diff</summary>

*sentence 0* (comparison-flagged)

    [-As compared to the previous radiograph, the-] {+The+} tip of the endotracheal tube now projects 4.3 cm above the [-carina.-] {+carina as compared to the previous radiograph.+}

*sentence 1* (comparison-flagged)

    The course of the nasogastric tube [-is-] {+remains+} unchanged.

*sentence 2* (comparison-flagged)

    [-Unchanged-] {+The+} appearance of the lung parenchyma and the cardiac [-silhouette.-] {+silhouette is unchanged.+}

</details>

<details><summary>Prior report (input context)</summary>

> On the initial image, the Dobbhoff tube tip is seen in the mid portion in the esophagus. On the
> second image, the Dobbhoff tube has been advanced and is appropriately sited within the fundus and
> body of the stomach. There are old healed rib fractures on the right side. There is some
> atelectasis and some increased density at the left lung base. No pneumothoraces are seen. Cardiac
> size is within normal limits.

</details>

---

## Sample 3 — study 52731689 (change)

**No change** — the pipeline returned the baseline draft unaltered.

**Baseline — MAIRA-2 draft**

> AP upright portable chest radiograph provided. Cervical fusion hardware is partially visualized.
> Lungs are clear. There is no focal consolidation, effusion, or pneumothorax. The cardiomediastinal
> silhouette is normal. Imaged osseous structures are intact. No free air below the right
> hemidiaphragm is seen.

**Approach — ICL pipeline output**

> AP upright portable chest radiograph provided. Cervical fusion hardware is partially visualized.
> Lungs are clear. There is no focal consolidation, effusion, or pneumothorax. The cardiomediastinal
> silhouette is normal. Imaged osseous structures are intact. No free air below the right
> hemidiaphragm is seen.

**Reference — ground-truth current report**

> PA and lateral views of the chest provided. Cervical spinal hardware again noted. Clips noted in
> the upper abdomen. There is no focal consolidation, effusion, or pneumothorax. The
> cardiomediastinal silhouette is normal. Imaged osseous structures are intact. No free air below
> the right hemidiaphragm is seen.

<details><summary>Prior report (input context)</summary>

> Heart size and cardiomediastinal contours are normal. Lungs are clear without focal consolidation,
> pleural effusion, or pneumothorax. Cervical spine fusion hardware and clips in the left upper
> abdomen are similar to prior.

</details>

---

## Sample 4 — study 52474242 (change)

**3 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> As compared to the previous radiograph, there is a newly appeared minimal left pleural effusion.
> In addition, the vascular diameters have minimally increased, suggesting mild fluid overload.
> Unchanged moderate cardiomegaly with retrocardiac atelectasis. No focal parenchymal opacity
> suggesting pneumonia.

**Approach — ICL pipeline output**

> As compared to the previous radiograph, there is a newly noted minimal left pleural effusion. In
> comparison with the prior study, the vascular calibers have shown a minimal increase, indicative
> of mild fluid overload. The cardiomegaly remains moderately severe and the retrocardiac
> atelectasis is unchanged. No focal parenchymal opacity suggesting pneumonia.

**Reference — ground-truth current report**

> As compared to the previous examination, the left central venous access line has been removed.
> There is a marked increase in interstitial markings and increase in vascular diameters. Increasing
> retrocardiac atelectasis and likely new left pleural effusion. Overall, moderate predominantly
> interstitial pulmonary edema is present. No other relevant changes. At the time of dictation, 1:49
> p.m., the referring physician, ___. ___ was notified by telephone and the findings were discussed
> on ___.

<details><summary>Sentence-level diff</summary>

*sentence 0* (comparison-flagged)

    As compared to the previous radiograph, there is a newly [-appeared-] {+noted+} minimal left pleural effusion.

*sentence 1* (comparison-flagged)

    In [-addition,-] {+comparison with the prior study,+} the vascular [-diameters-] {+calibers+} have [-minimally increased, suggesting-] {+shown a minimal increase, indicative of+} mild fluid overload.

*sentence 2* (comparison-flagged)

    [-Unchanged moderate-] {+The+} cardiomegaly [-with-] {+remains moderately severe and the+} retrocardiac [-atelectasis.-] {+atelectasis is unchanged.+}

</details>

<details><summary>Prior report (input context)</summary>

> In comparison with study ___, there is continued hyperexpansion of the lungs consistent with
> chronic pulmonary disease. The pulmonary vascular congestion has substantially decreased. Much of
> the prominence of interstitial markings most likely represents chronic lung disease. Atelectatic
> changes are seen at the left base with possible small effusion.

</details>

---

## Sample 5 — study 50344973 (change)

**3 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> As compared to the previous radiograph, the patient has undergone decortication. Two new chest
> tubes are seen on the right. The bases of the right lung is substantially more lucent than on the
> previous image, likely reflecting improved ventilation. However, a small basal pneumothorax is
> still visible. No evidence of tension. Unchanged normal appearance of the left lung.

**Approach — ICL pipeline output**

> Compared to the prior radiograph, decortication has been performed. Two new chest tubes are seen
> on the right. The right lung bases appear more lucent on this image compared to the previous one,
> likely due to improved ventilation. However, a small basal pneumothorax is still visible. No
> evidence of tension. The left lung demonstrates an unchanged normal appearance.

**Reference — ground-truth current report**

> As compared to the previous radiograph, the patient has undergone a right thoracotomy and
> decortication. Three right chest tubes are in situ. There is a minimal right basal pneumothorax at
> the site of chest tube insertion. No evidence of tension. Mild right basal postoperative
> atelectasis. In the interval, the patient has been intubated, the tip of the tube projects 5.3 cm
> above the carina. Moderate cardiomegaly, unremarkable and unchanged left lung.

<details><summary>Sentence-level diff</summary>

*sentence 0* (comparison-flagged)

    [-As compared-] {+Compared+} to the [-previous-] {+prior+} radiograph, [-the patient-] {+decortication+} has [-undergone decortication.-] {+been performed.+}

*sentence 2* (comparison-flagged)

    The [-bases of the-] right lung [-is substantially-] {+bases appear+} more lucent [-than-] on {+this image compared to+} the previous [-image,-] {+one,+} likely [-reflecting-] {+due to+} improved ventilation.

*sentence 5* (comparison-flagged)

    [-Unchanged-] {+The left lung demonstrates an unchanged+} normal [-appearance of the left lung.-] {+appearance.+}

</details>

<details><summary>Prior report (input context)</summary>

> Right lower lobe opacity, possibly atelectasis, with associated moderate sized effusion.

</details>

---

## Sample 6 — study 53481703 (change)

**2 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> There is no focal consolidation, pleural effusion, pulmonary edema, or pneumothorax. The
> cardiomediastinal silhouette is unchanged with top normal heart size. Bilateral hilar vascular
> prominence is unchanged from the prior study. A calcified granuloma is again noted in the right
> lower lung.

**Approach — ICL pipeline output**

> There is no focal consolidation, pleural effusion, pulmonary edema, or pneumothorax. Cardiac and
> mediastinal silhouettes are unchanged with normal heart size. Bilateral hilar vascular markings
> are unchanged from the prior study. A calcified granuloma is again noted in the right lower lung.

**Reference — ground-truth current report**

> There is no focal consolidation, PE pulmonary edema, or pneumothorax. The lateral view radiograph
> suggests small bilateral pleural effusions in the posterior costophrenic sulcus. The
> cardiomediastinal silhouette, including mild cardiomegaly, is unchanged. A vascular stent projects
> over the left axilla, new from prior studies.

<details><summary>Sentence-level diff</summary>

*sentence 1* (comparison-flagged)

    [-The cardiomediastinal silhouette is-] {+Cardiac and mediastinal silhouettes are+} unchanged with [-top-] normal heart size.

*sentence 2* (comparison-flagged)

    Bilateral hilar vascular [-prominence is-] {+markings are+} unchanged from the prior study.

</details>

<details><summary>Prior report (input context)</summary>

> There has been interval placement of a right central dialysis catheter. Bilateral hilar vascular
> prominence is re- demonstrated with subtle nodularity in the left upper lung likely representing
> confluence of vasculature though a true nodule difficult to exclude. There is no convincing sign
> of pneumonia or overt edema. Small left effusion is present with basilar atelectasis. The
> cardiomediastinal silhouette is unchanged.

</details>

---

## Sample 7 — study 56847326 (change)

**2 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> As compared to the previous radiograph, the pre-existing right pleural effusion has completely
> resolved. However, the right lung base continues to show a zone of increased radiodensity. The
> radiodensity is now more homogeneous and shows a rounded component of approximately 2 to 3 cm in
> diameter. The zone of increased radiodensity is otherwise unchanged as compared to the previous
> image. The size of the cardiac silhouette is at the upper range of normal. There is no evidence of
> pulmonary edema and no other changes that could explain the clinical presentation of the patient.
> The referring physician, _. _, was paged for notification at the time of dictation, 1:59 p.m., on
> _.

**Approach — ICL pipeline output**

> As compared to the previous radiograph, the pre-existing right pleural effusion has completely
> resolved. However, the right lung base continues to demonstrate a zone of increased radiodensity.
> The radiodensity is now more homogeneous and shows a rounded component of approximately 2 to 3 cm
> in diameter. This zone of increased radiodensity remains unchanged as compared to the previous
> image. The size of the cardiac silhouette is at the upper range of normal. There is no evidence of
> pulmonary edema and no other changes that could explain the clinical presentation of the patient.
> The referring physician, _. _, was paged for notification at the time of dictation, 1:59 p.m., on
> _.

**Reference — ground-truth current report**

> The heart is normal in size. The mediastinal and hilar contours appear within normal limits.
> Pleural effusions have resolved. There is a patchy new opacity in the lateral segment of the right
> middle lobe, worrisome for pneumonia. However, elsewhere, the lungs appear clear. The osseous
> structures are unremarkable.

<details><summary>Sentence-level diff</summary>

*sentence 1* (comparison-flagged)

    However, the right lung base continues to [-show-] {+demonstrate+} a zone of increased radiodensity.

*sentence 3* (comparison-flagged)

    [-The-] {+This+} zone of increased radiodensity [-is otherwise-] {+remains+} unchanged as compared to the previous image.

</details>

<details><summary>Prior report (input context)</summary>

> The heart is normal in size. The mediastinal contours appear stable. Again seen is a rounded
> opacity superimposed along the right cardiac border that appears similar to decreased and was
> previously shown to correspond to fluid and consolidation on the recent prior chest CT. There is a
> small persistent left-sided pleural effusion, but substantially decreased. A moderate right-sided
> pleural effusion has also decreased in size and is now small to moderate. There is a vague nodular
> opacity projecting over the right upper lung that is similar to better defined compared to the
> recent prior chest radiographs and may correspond to nodular focus along the right minor fissure
> seen on the CT study. Patchy basilar opacities are nonspecific, but could be seen with a resolving
> infection or atelectasis associated with effusions.

</details>

---

## Sample 8 — study 50170739 (no-change)

**No change** — the pipeline returned the baseline draft unaltered.

**Baseline — MAIRA-2 draft**

> A single frontal upright view of the chest was obtained portably. The lungs are clear without
> focal consolidation, pleural effusion or pneumothorax. Heart size is normal. Mediastinal
> silhouette and hilar contours are normal. A left pacemaker is seen with a single lead ending in
> the right ventricle.

**Approach — ICL pipeline output**

> A single frontal upright view of the chest was obtained portably. The lungs are clear without
> focal consolidation, pleural effusion or pneumothorax. Heart size is normal. Mediastinal
> silhouette and hilar contours are normal. A left pacemaker is seen with a single lead ending in
> the right ventricle.

**Reference — ground-truth current report**

> A cardiac conduction device is contiguous with a lead which terminates in the right atrium. There
> is no focal consolidation. There is no pneumothorax. The cardiomediastinal silhouette is
> unremarkable.

<details><summary>Prior report (input context)</summary>

> The lungs appear clear. A pacemaker is seen projecting over the left chest with a wire
> appropriately placed in the right atrium. The cardiomediastinal silhouette, hilar contours, and
> pleural structures are normal. No pneumothorax or pleural effusion. Other than the pacemaker, no
> radio-opaque metallic foreign object is identified in chest radiograph.

</details>

---

## Sample 9 — study 50749866 (change)

**1 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> ET tube is in standard position. Right PICC ends in the low SVC. Left chest wall AICD is in place.
> Feeding tube ends in the stomach. Surgical clips project over the left upper quadrant. Lung
> volumes are low. There is moderate right pleural effusion, layering posteriorly. There is likely a
> small left effusion. There is moderate pulmonary edema. There is persistent left retrocardiac
> opacity.

**Approach — ICL pipeline output**

> ET tube is in standard position. Right PICC ends in the low SVC. Left chest wall AICD is in place.
> Feeding tube ends in the stomach. Surgical clips project over the left upper quadrant. Lung
> volumes are low. There is moderate right pleural effusion, layering posteriorly. There is likely a
> small left effusion. There is moderate pulmonary edema. In comparison to the prior chest
> radiograph, there is persistent left retrocardiac opacity.

**Reference — ground-truth current report**

> Moderate to severe cardiomegaly is stable. Pacer leads are in standard position. ET tube is in
> standard position. Left IJ catheter tip is in the mid SVC . Right PICC is in unchanged position.
> NG tube tip is out of view below the diaphragm. Vascular congestion has improved. Bibasilar
> atelectasis have improved. Bilateral effusions right greater than left are unchanged

<details><summary>Sentence-level diff</summary>

*sentence 9* (comparison-flagged)

    [-There-] {+In comparison to the prior chest radiograph, there+} is persistent left retrocardiac opacity.

</details>

<details><summary>Prior report (input context)</summary>

> Portable semi-upright radiograph of the chest demonstrates low lung volumes with resultant
> bronchovascular crowding. Clearing of the right base is consistent with decrease in size of the
> pleural effusion and improved aeration. Persistent retrocardiac opacity corresponds to atelectasis
> and probable left pleural effusion. There is moderate pulmonary edema. Cardiomediastinal and hilar
> contours are unchanged. Monitoring and support devices are in the appropriate position.

</details>

---

## Sample 10 — study 53282268 (no-change)

**3 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> One portable AP upright view of the chest. A right dialysis catheter ends in the right atrium.
> Moderate pulmonary edema is unchanged compared to prior study. Small bilateral pleural effusions
> are unchanged. No pneumothorax. Cardiomediastinal and hilar contours are stable.

**Approach — ICL pipeline output**

> One portable AP upright view of the chest. A right dialysis catheter ends in the right atrium.
> Moderate pulmonary edema is unchanged compared to the prior study. Small bilateral pleural
> effusions are unchanged compared to the prior study. No pneumothorax. Cardiomediastinal and hilar
> contours are stable compared to the prior study.

**Reference — ground-truth current report**

> One portable AP upright view of the chest. Right hemodialysis catheter ends in the right atrium.
> There is pulmonary edema and pulmonary vascular congestion. There is no focal parenchymal
> opacities concerning for pneumonia. There is no pneumothorax. No definite pleural effusions. The
> cardiac, mediastinal, and hilar contours are normal.

<details><summary>Sentence-level diff</summary>

*sentence 2* (comparison-flagged)

    Moderate pulmonary edema is unchanged compared to {+the+} prior study.

*sentence 3* (comparison-flagged)

    Small bilateral pleural effusions are [-unchanged.-] {+unchanged compared to the prior study.+}

*sentence 5* (comparison-flagged)

    Cardiomediastinal and hilar contours are [-stable.-] {+stable compared to the prior study.+}

</details>

<details><summary>Prior report (input context)</summary>

> In comparison with the study of ___, there is continued diffuse bilateral pulmonary opacifications
> consistent with worsening effusions, volume loss, and increased pulmonary vascular congestion.
> Possibility of supervening pneumonia must be seriously considered in the appropriate clinical
> setting, though this is difficult to evaluate in view of the substrate of extensive pulmonary
> changes.

</details>

---

## Sample 11 — study 54694185 (change)

**1 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> AP chest radiograph. Right upper lobe consolidation with air bronchograms is not significantly
> changed from _. However, there is a new area of consolidation in the right lower lobe abutting the
> right heart border, which may represent a new focus of pneumonia. Multifocal scarring with volume
> loss is unchanged. There is no pleural effusion or pneumothorax. The cardiomediastinal silhouette
> is normal.

**Approach — ICL pipeline output**

> AP chest radiograph. Right upper lobe consolidation with air bronchograms is not significantly
> changed from _. However, there is a new area of consolidation in the right lower lobe abutting the
> right heart border, which may represent a new focus of pneumonia. Multifocal scarring with volume
> loss is unchanged compared to the prior study. There is no pleural effusion or pneumothorax. The
> cardiomediastinal silhouette is normal.

**Reference — ground-truth current report**

> PA and lateral chest radiographs were obtained. A right upper lobe consolidation with air
> bronchograms is similar to ___. Focal tubular lucency within the opacity is new and may reflect
> cavitation, dilated airways or spared lung parenchyma. Opacity in the right lower lobe has
> progressed since the prior study. There is no effusion or pneumothorax. Cardiac and mediastinal
> contours are normal. There is mild thickening of the left major fissure.

<details><summary>Sentence-level diff</summary>

*sentence 3* (comparison-flagged)

    Multifocal scarring with volume loss is [-unchanged.-] {+unchanged compared to the prior study.+}

</details>

<details><summary>Prior report (input context)</summary>

> AP and lateral views of chest demonstrate a right upper lobe consolidation with some areas of air
> bronchogram. Background multifocal opacities with volume loss and chronic scarring are unchanged.
> There is no large pleural effusion. Cardiac size is normal.

</details>

---

## Sample 12 — study 50953777 (change)

**No change** — the pipeline returned the baseline draft unaltered.

**Baseline — MAIRA-2 draft**

> The cardiac silhouette is mildly enlarged. The pulmonary vasculature is not congested. There is no
> evidence of pleural effusion. There is no pneumothorax or acute parenchymal infiltrate.

**Approach — ICL pipeline output**

> The cardiac silhouette is mildly enlarged. The pulmonary vasculature is not congested. There is no
> evidence of pleural effusion. There is no pneumothorax or acute parenchymal infiltrate.

**Reference — ground-truth current report**

> PA and lateral chest views were obtained with patient in upright position. Analysis is performed
> in direct comparison with the next preceding portable chest examination of ___. Heart size is
> unchanged. Previously described moderate pulmonary congestive pattern with some upper zone re-
> distribution has normalized. Presently no evidence of pulmonary interstitial alveolar edema and
> the lateral as well as posterior pleural sinuses are free from any fluid accumulation. No
> pneumothorax in the apical area. No acute infiltrates. Lateral and posterior pleural sinuses are
> free. A previously described old calcified granuloma in the left upper lobe area is unchanged.

<details><summary>Prior report (input context)</summary>

> CHF with interstitial edema and bibasilar atelectasis, improved compared with ___.

</details>

---

## Sample 13 — study 57761141 (change)

**1 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> There are diffuse interstitial opacities, most pronounced at the lung bases, which are unchanged
> from the prior exam. This is consistent with the patient's known chronic interstitial lung
> disease. There is no new opacity, pulmonary edema, pleural effusion, or pneumothorax. The
> cardiomediastinal silhouette is stable with mild cardiomegaly.

**Approach — ICL pipeline output**

> There are diffuse interstitial opacities, most pronounced at the lung bases, which are stable from
> the prior exam. This is consistent with the patient's known chronic interstitial lung disease.
> There is no new opacity, pulmonary edema, pleural effusion, or pneumothorax. The cardiomediastinal
> silhouette is stable with mild cardiomegaly.

**Reference — ground-truth current report**

> Lung volumes are reduced. Diffuse interstitial opacities most pronounced within the periphery and
> lung bases with architectural distortion are unchanged compared to the previous chest CT and
> compatible with chronic interstitial lung disease, previously characterized as UIP or fibrosing
> NSIP. Previously noted hazy opacities in both lungs has resolved. No new areas of focal
> consolidation are demonstrated. There is no pulmonary vascular congestion, pleural effusion or
> pneumothorax. Mild degenerative changes are noted in the thoracic spine. The cardiac and
> mediastinal contours are unchanged.

<details><summary>Sentence-level diff</summary>

*sentence 0* (comparison-flagged)

    There are diffuse interstitial opacities, most pronounced at the lung bases, which are [-unchanged-] {+stable+} from the prior exam.

</details>

<details><summary>Prior report (input context)</summary>

> AP, lateral, and oblique radiographs of the chest are somewhat limited in the determination of the
> exact termination point of the right PICC, which is difficult to visualize amongst the mediastinal
> structures. However, it appears to terminate in the lower portion of the SVC. There has been
> marked improvement in the bilateral effusions and heterogeneous opacities when compared to the
> prior study. Prominent interstitial lung markings reflect the patient's baseline pulmonary
> fibrosis. There is no pneumothorax. The aorta is stably tortuous with atherosclerotic
> calcifications in the arch.

</details>

---

## Sample 14 — study 57330158 (change)

**4 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> Interval placement of endotracheal tube with tip terminating 4 cm above the carina. Nasogastric
> tube terminates below the diaphragm. Stable cardiomegaly and persistent pulmonary vascular
> congestion accompanied by interstitial edema. Asymmetrical right medial basilar opacity has
> slightly improved and continues to be concerning for a developing infection. Small right pleural
> effusion is unchanged, but a left pleural effusion has slightly decreased in size.

**Approach — ICL pipeline output**

> There is an interval placement of the endotracheal tube with the tip terminating 4 cm above the
> carina. Nasogastric tube terminates below the diaphragm. There is stable cardiomegaly and
> persistent pulmonary vascular congestion with interstitial edema, unchanged from the prior study.
> The asymmetrical right medial basilar opacity has slightly improved and remains concerning for a
> developing infection. The small right pleural effusion is unchanged, but the left pleural effusion
> has slightly decreased in size.

**Reference — ground-truth current report**

> Newly placed endotracheal tube terminates approximately 3.6 cm above the carina, and a nasogastric
> tube courses below the diaphragm. A 3-cm diameter rounded lucency is identified lateral to the
> endotracheal tube and nasogastric tube to the left of midline. Although potentially representing
> an over-distended endotracheal tube cuff, the position is more lateral than expected for this
> condition. Alternative possibilities include an air-filled diverticulum arising from the trachea
> or esophagus. Findings were communicated by telephone with Dr. ___ on ___ at 4:00 p.m. at the time
> of discovery. Exam is otherwise remarkable for persistent cardiomegaly and worsening congestive
> heart failure with increasing perihilar edema and persistent small right pleural effusion.

<details><summary>Sentence-level diff</summary>

*sentence 0* (comparison-flagged)

    [-Interval-] {+There is an interval+} placement of {+the+} endotracheal tube with {+the+} tip terminating 4 cm above the carina.

*sentence 2* (comparison-flagged)

    [-Stable-] {+There is stable+} cardiomegaly and persistent pulmonary vascular congestion [-accompanied by-] {+with+} interstitial [-edema.-] {+edema, unchanged from the prior study.+}

*sentence 3* (comparison-flagged)

    [-Asymmetrical-] {+The asymmetrical+} right medial basilar opacity has slightly improved and [-continues to be-] {+remains+} concerning for a developing infection.

*sentence 4* (comparison-flagged)

    [-Small-] {+The small+} right pleural effusion is unchanged, but [-a-] {+the+} left pleural effusion has slightly decreased in size.

</details>

<details><summary>Prior report (input context)</summary>

> Mild-to-moderate cardiomegaly is accompanied by upper zone vascular redistribution, vascular
> indistinctness and mild interstitial edema. A slightly more confluent opacity at the right lung
> base medially may reflect asymmetrical dependent edema, but followup radiographs may be helpful to
> exclude a developing infection in this region. Small bilateral pleural effusions have improved
> since previous study. Calcified right hilar lymph nodes are unchanged.

</details>

---

## Sample 15 — study 52399735 (change)

**3 sentence(s) altered.**

**Baseline — MAIRA-2 draft**

> As compared to the previous radiograph, the extent of the known right pleural effusion is
> constant. Also constant is the appearance of the right lung apex, with known post-operative
> changes. The left lung is unchanged in appearance. Unchanged moderate cardiomegaly.

**Approach — ICL pipeline output**

> Compared to the previous radiograph, the extent of the known right pleural effusion remains
> constant. Also constant is the appearance of the right lung apex, with known post-operative
> changes. The left lung shows no change in appearance. There is persistent moderate cardiomegaly.

**Reference — ground-truth current report**

> As compared to the previous radiograph, the lateral images show that the right pleural effusion
> does not layer, which would be consistent with loculation. Also, there is an increase in adjacent
> atelectasis.

<details><summary>Sentence-level diff</summary>

*sentence 0* (comparison-flagged)

    [-As compared-] {+Compared+} to the previous radiograph, the extent of the known right pleural effusion [-is-] {+remains+} constant.

*sentence 2* (comparison-flagged)

    The left lung [-is unchanged-] {+shows no change+} in appearance.

*sentence 3* (comparison-flagged)

    [-Unchanged-] {+There is persistent+} moderate cardiomegaly.

</details>

<details><summary>Prior report (input context)</summary>

> The cardiac silhouette size remains mildly enlarged. Patient is status post right upper lobectomy
> and right upper chest wall resection with evidence of volume loss in the right lung and
> posttreatment changes in the right upper lung field, unchanged. Left hilar enlargement is
> unchanged, with mild pulmonary vascular congestion present. Moderate to large right pleural
> effusion and small left pleural effusion are again demonstrated, not significantly changed in the
> interval. Right basilar opacification is similar. No pneumothorax is identified. The aorta remains
> tortuous and calcified.

</details>

---
