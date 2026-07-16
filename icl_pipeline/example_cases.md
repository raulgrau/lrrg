# ICL pipeline: end-to-end example cases

## 52805540  (change case)

**Guardrail outcome:** ACCEPTED (revision kept)  
**draft_f1** = 0.3333  |  **revised_f1** = 0.3333

**Prior report (ground truth):**
    Chest PA and lateral radiograph demonstrates a markedly elevated right hemidiaphragm with
    adjacent compressive atelectasis or consolidation. Minimal blunting of the posterior
    costophrenic angle may indicate a small right pleural effusion. Left lung is clear.
    Cardiomediastinal borders are unremarkable.

**MAIRA-2 draft:**
    Single portable chest radiograph demonstrates stable mild cardiomegaly. There is a large right
    pleural effusion with associated compressive atelectasis of the right middle and lower lobes.
    The left lung is clear. No pneumothorax.

**Retrieved exemplars shown to Qwen:**
  - _52933934_: "Cardiac silhouette is mildly enlarged, unchanged from prior examination with mild tortuosity of the thoracic aorta."
  - _52933934_: "There is stable elevation of the left hemidiaphragm with left lung base atelectasis."
  - _55463629_: "As compared to the previous radiograph, the pre-existing bilateral pleural effusions have moderately increased in extent."
  - _55463629_: "Bilateral areas of atelectasis at the lung bases are also increasing."

**Qwen's revision:**
    Single portable chest radiograph demonstrates stable mild cardiomegaly compared to the prior
    examination. There is a large right pleural effusion with associated compressive atelectasis of
    the right middle and lower lobes. The left lung is clear. No pneumothorax.

**Final text (what the pipeline actually output):**
    Single portable chest radiograph demonstrates stable mild cardiomegaly compared to the prior
    examination. There is a large right pleural effusion with associated compressive atelectasis of
    the right middle and lower lobes. The left lung is clear. No pneumothorax.

**Ground-truth reference (current report):**
    In comparison with the study of earlier in this date, there is increasing indistinctness of
    engorged pulmonary vessels, consistent with worsening vascular congestion. Continued elevation
    of the right hemidiaphragmatic contour. It is unclear whether this represents a subpulmonic
    effusion or an intrinsic diaphragmatic abnormality or enlarged liver. Left lung is essentially
    unchanged except for worsening pulmonary vascular congestion.

---

## 51887095  (change case)

**Guardrail outcome:** ACCEPTED (revision kept)  
**draft_f1** = 0.5714  |  **revised_f1** = 0.5714

**Prior report (ground truth):**
    1. ET tube terminating 5.1 cm above the carina. Orogastric tube terminating within the stomach.
    2. Interval worsening of mild-to-moderate pulmonary edema. 3. Unchanged marked right
    hemidiaphragm elevation.

**MAIRA-2 draft:**
    Endotracheal tube again terminates 5.1 cm above the carina. Orogastric tube courses through the
    stomach. A left internal jugular approach central venous catheter terminates in the mid SVC.
    There is no pneumothorax. A moderate-to-large right pleural effusion is unchanged. There is
    continued mild pulmonary edema, also unchanged. There is continued elevation of the right
    hemidiaphragm.

**Retrieved exemplars shown to Qwen:**
  - _59286832_: "Right PICC line and feeding tubes are unchanged in position."
  - _59286832_: "Mild pulmonary vascular congestion and small bilateral pleural effusions are unchanged."
  - _50980783_: "There is a persistent pulmonary edema, right lung worse than left."
  - _50980783_: "Lines and tubes are unchanged."

**Qwen's revision:**
    Endotracheal tube again terminates 5.1 cm above the carina. Orogastric tube courses through the
    stomach. A left internal jugular approach central venous catheter terminates in the mid SVC.
    There is no pneumothorax. A moderate-to-large right pleural effusion is unchanged from the prior
    study. Mild pulmonary edema is noted, which is unchanged from the prior study. There is
    continued elevation of the right hemidiaphragm.

**Final text (what the pipeline actually output):**
    Endotracheal tube again terminates 5.1 cm above the carina. Orogastric tube courses through the
    stomach. A left internal jugular approach central venous catheter terminates in the mid SVC.
    There is no pneumothorax. A moderate-to-large right pleural effusion is unchanged from the prior
    study. Mild pulmonary edema is noted, which is unchanged from the prior study. There is
    continued elevation of the right hemidiaphragm.

**Ground-truth reference (current report):**
    There is persistent opacification of the right lower lung field, likely due to known pleural
    effusion and atelectasis. Small left pleural effusion is again noted. Overall, there has been no
    significant interval change. Endotracheal tube, left internal jugular catheter, and esophageal
    catheter are again seen in similar positions with esophageal catheter tip out of view. No
    pneumothorax is detected.

---

## 53825501  (change case)

**Guardrail outcome:** REJECTED (reverted to draft)  
**draft_f1** = 0.7500  |  **revised_f1** = 0.5714

**Prior report (ground truth):**
    A frontal upright view of the chest was obtained portably. Interval removal of the right pigtail
    catheter with replacement with a right chest tube within the loculated right basilar
    pneumothorax, which is unchanged. Volume loss in the right lung with surrounding pleural fluid
    is unchanged. The left lung is well expanded and clear without pneumothorax or effusion.
    Surgical clips project over the epigastrium. Aortic contour and left heart border are unchanged.

**MAIRA-2 draft:**
    A frontal upright view of the chest was obtained portably. The right chest tube is unchanged in
    position. The loculated right basilar pneumothorax is slightly increased in size. There is
    increased right lung volume loss with surrounding pleural fluid. The left lung is well expanded
    and clear without pneumothorax or effusion. Surgical clips project over the epigastrium. Aortic
    contour and heart borders are stable.

**Retrieved exemplars shown to Qwen:**
  - _56945878_: "Allowing for differences in patient positioning, there is redemonstration of a right-sided pleural effusion with fluid tracking into the minor fissure."
  - _56945878_: "The cardiomediastinal silhouette is unchanged."
  - _54513711_: "Since the previous radiograph of several hours earlier, a Dobbhoff tube has been replaced and coils within the stomach, with distal tip directed cephalad."
  - _54513711_: "Moderate bilateral pneumothoraces are in retrospect unchanged from the prior radiograph, with bilateral chest tubes in place."

**Qwen's revision:**
    A frontal upright view of the chest was obtained portably. The right chest tube remains in the
    same position. The loculated right basilar pneumothorax shows slight increase in size. There is
    increased right lung volume loss with surrounding pleural fluid noted. The left lung is well
    expanded and clear without pneumothorax or effusion. Surgical clips project over the
    epigastrium. The aortic contour and heart borders appear stable.

**Final text (what the pipeline actually output):**
    A frontal upright view of the chest was obtained portably. The right chest tube is unchanged in
    position. The loculated right basilar pneumothorax is slightly increased in size. There is
    increased right lung volume loss with surrounding pleural fluid. The left lung is well expanded
    and clear without pneumothorax or effusion. Surgical clips project over the epigastrium. Aortic
    contour and heart borders are stable.

**Ground-truth reference (current report):**
    Right-sided chest tube has been removed. There is a hydropneumothorax in the inferior right
    chest. The amount of fluid has increased compared to the study from two days prior. The thick
    irregular pleural disease around the right lung is again visualized. The left lung is clear.
    Cardiac and mediastinal silhouettes are unchanged.

---

## 51835823  (change case)

**Guardrail outcome:** REJECTED (reverted to draft)  
**draft_f1** = 0.4000  |  **revised_f1** = 0.0000

**Prior report (ground truth):**
    Vascular stents are again seen and stable from ___. There is no focal opacity, pleural effusions
    or overt signs of pulmonary edema. The cardiac and mediastinal contours are stable. The bones
    are diffusely sclerotic, likely secondary to renal osteodystrophy.

**MAIRA-2 draft:**
    AP portable upright chest radiograph provided. Vascular stents are again seen projecting over
    the right axilla and right lung apex. There is interval development of subtle opacity in the
    right lower lung which could represent a developing pneumonia. There is also retrocardiac
    opacity which could also represent a developing pneumonia. No large effusion or pneumothorax is
    seen. The heart and mediastinal contour appear stable. The bony structures are diffusely
    sclerotic as on prior compatible with renal osteodystrophy.

**Retrieved exemplars shown to Qwen:**
  - _56358714_: "The lungs are hyperinflated with persistent peripheral poorly defined opacities which could reflect persistent atypical pneumonia."
  - _56358714_: "There is minimal interval change from prior exam."
  - _59894940_: "Cardiac and mediastinal silhouettes are stable."
  - _58834536_: "Moderate aortic tortuosity is unchanged."

**Qwen's revision:**
    AP portable upright chest radiograph provided. Vascular stents are noted to project over the
    right axilla and right lung apex, as previously described. There is interval development of
    subtle opacities in the right lower lung, which could represent developing pneumonia. There is
    also retrocardiac opacity which could also represent a developing pneumonia. No large effusion
    or pneumothorax is seen. The cardiac and mediastinal contours appear stable compared to the
    prior examination. The bony structures are diffusely sclerotic as on prior compatible with renal
    osteodystrophy.

**Final text (what the pipeline actually output):**
    AP portable upright chest radiograph provided. Vascular stents are again seen projecting over
    the right axilla and right lung apex. There is interval development of subtle opacity in the
    right lower lung which could represent a developing pneumonia. There is also retrocardiac
    opacity which could also represent a developing pneumonia. No large effusion or pneumothorax is
    seen. The heart and mediastinal contour appear stable. The bony structures are diffusely
    sclerotic as on prior compatible with renal osteodystrophy.

**Ground-truth reference (current report):**
    There are diffusely increased interstitial markings throughout the lungs which are
    hyperinflated. There is no effusion or pneumothorax. Cardiac silhouette is enlarged but
    unchanged. Multiple vascular stents are again identified. Numerous punctate calcifications in
    the left upper quadrant are compatible with splenic granulomas. No acute osseous abnormalities
    identified.

---

## 56389746  (change case)

**Guardrail outcome:** ACCEPTED (revision kept)  
**draft_f1** = 0.5714  |  **revised_f1** = 0.5714

**Prior report (ground truth):**
    As compared to the previous radiograph, the patient has been extubated. The nasogastric tube has
    been removed. There are moderate bilateral pleural effusions with relatively substantial areas
    of atelectasis. Size of the cardiac silhouette cannot be determined. No evidence of new
    parenchymal opacities suggesting pneumonia. A left internal jugular vein catheter remains in
    situ.

**MAIRA-2 draft:**
    Portable AP chest radiograph demonstrates low lung volumes with bilateral pleural effusions,
    right greater than left, with associated atelectasis. There is mild pulmonary vascular
    engorgement. The cardiomediastinal silhouette is not well visualized. There is no pneumothorax.

**Retrieved exemplars shown to Qwen:**
  - _59843891_: "The left side of the cardiomediastinal silhouette is stable as compared to the prior study but the right-sided is more prominent."
  - _50011680_: "Compared to ___, small bilateral pleural effusions appear stable.Previously seen fluid in the right minor fissure is no longer present."
  - _50011680_: "Cardiac, hilar, and mediastinal silhouettes are grossly unchanged."
  - _53223691_: "Interval improvement in extent of bibasilar atelectasis."

**Final text (what the pipeline actually output):**
    Portable AP chest radiograph demonstrates low lung volumes with bilateral pleural effusions,
    right greater than left, with associated atelectasis. There is mild pulmonary vascular
    engorgement. The cardiomediastinal silhouette is not well visualized. There is no pneumothorax.

**Ground-truth reference (current report):**
    Compared to the previous radiograph, the left IJ catheter has been removed. There are persistent
    bilateral pleural effusions along with unchanged opacification of right lung base. This suggests
    right middle and lower lobe collapse. Comparison is limited by patient rotation on current
    imaging. Opacification at the left lung base is unchanged, and pneumonia cannot be excluded.

---
