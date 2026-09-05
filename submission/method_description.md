---
title: "A frugal voxel-wise method for isointense infant brain segmentation"
subtitle: "iSeg-2017 method description"
author:
  - Jules Lange
  - Arthur Goullet de Rugy
date: "September 2026"
lang: en
documentclass: article
papersize: a4
fontsize: 10pt
geometry:
  - margin=1.7cm
mainfont: "Latin Modern Roman"
monofont: "Latin Modern Mono"
numbersections: true
colorlinks: true
linkcolor: black
urlcolor: black
---

# Summary and what is distinctive

Each voxel is classified independently by a **multinomial logistic regression** reading a
151-column description built from hand-designed, non-learned descriptors; a second stage of the
same classifier then reads the first stage's probability map through fixed Gaussian
neighbourhoods (auto-context).

What is worth reporting is not the accuracy but the **model size**: the whole segmenter is
**939 learned parameters**, about 2.5 kB on disk. Every descriptor is recomputed from the
subject being segmented and carries no learned parameter; the only quantities transported from
training to inference are the two sets of regression weights.

We are a two-person student team and expect to be well below the leaderboard on accuracy; we
submit because the accuracy/size trade-off is the point of the work and cannot be assessed
without a score on the held-out subjects.

# Required information

**Automatic or semi-automatic.** Fully automatic. No user input of any kind: no seed point, no
manual initialisation, no per-subject parameter, no quality control step.

**Sequences used.** Both T1 and T2, both required. The most informative single column is the
**ratio of the two normalised intensities**: at 6 months gray and white matter overlap heavily
within each modality taken separately (overlap coefficient $0.70$ in T1, $0.87$ in T2, measured
on the 10 annotated subjects) while their joint behaviour separates.

**Training data.** Only the 10 annotated subjects provided by iSeg-2017. **No external data of
any kind**: no pre-training, no transfer from adult or other infant cohorts, no atlas, no
template, no registration. The brain mask comes from the images themselves (T1 $\neq 0$).

**Other datasets.** The method has not been evaluated on any dataset other than iSeg-2017.
**Runtime and system:** see the last section.

# Algorithm, step by step

## Step 0 — Pre-processing

Essentially none: no registration, resampling, bias correction, denoising or skull-stripping.
The brain mask is $\mathrm{T1} \neq 0$, which on all 10 annotated subjects coincides
voxel-for-voxel with the non-background region of the reference segmentation.

## Step 1 — Voxel description (151 columns, 0 learned parameters)

Each masked voxel becomes one row of 151 columns, in six blocks. No block is fitted on the
training set; all are recomputed on the subject at hand. A test enforces this mechanically:
every block is computed with the true label map, with a permuted one, and with none at all, and
the three outputs must be bit-for-bit identical.

- **Intensity (6).** T1 and T2 z-scored within the mask, their ratio after normalisation by the
  intra-mask median, and percentile ranks.
- **Gaussian (68).** For $\sigma \in \{0.5, 1, 2, 4, 8\}$ mm and each modality: smoothed value,
  gradient magnitude, Laplacian, sorted Hessian eigenvalues (sorting gives rotation invariance),
  and differences of Gaussians. Convolutions are mask-normalised so the border is not diluted.
- **Spatial (9).** Normalised and spherical coordinates, distance to the mask boundary, and
  distance to the mid-sagittal plane estimated by PCA on the mask — an anatomical prior at no
  parameter cost.
- **Morphology (52).** The distinctive block. We compute the **self-dual tree of shapes** of the
  3-D volume: the components of the upper and lower thresholdings, holes filled, are pairwise
  nested or disjoint and form a single inclusion tree. For each voxel we take the attributes
  (area, contrast, elongation, depth) of the smallest shape containing it, then **climb its
  branch** to the ancestors of area $\geq 10^2, 10^3, 10^4, 10^5$ voxels and take theirs too —
  multi-scale non-local shape context at zero learned parameters, in one pass over the tree.
  Built with Higra on intensities quantised to 256 linear levels; that quantisation costs the
  contrast invariance of the tree of shapes, leaving only affine invariance.
- **Symmetry (4).** Intensity at the mirror point across the estimated mid-sagittal plane, and
  the deviation from it.
- **Context (12).** Local mean and standard deviation of percentile ranks at radii 1, 2 and 4
  voxels.

The rationale: blocks 1 to 3 are local, whereas at 6 months the gray/white boundary is not
visible locally. What distinguishes a cortical ribbon from the white matter beneath it is that
it is a thin shape enveloping a much larger one — inclusion across scales, which no local filter
expresses.

## Step 2 — Per-subject standardisation

Each column is centred and scaled with statistics computed over **the mask of the subject being
segmented**, at training and inference alike. Nothing is carried over from the training set, so
we do not count these as parameters. Under the opposite convention the first stage would be
456 + 302 parameters instead of 456; we give the figure so a reader who disagrees with our
convention can use their own.

## Step 3 — First-stage classifier

Multinomial logistic regression, $C = 1$, 300 iterations, both fixed a priori and never chosen
on the labels. **456 parameters**: $3 \times (151 + 1)$.

Training voxels are drawn balanced, 5000 per tissue per subject; because that distribution is
balanced while the true one is not, predicted probabilities are corrected at inference by the
ratio of the true class priors (estimated on training subjects only) to the sampled priors.

## Step 4 — Auto-context (second stage)

The first stage produces a probability map. We read its local mean in normalised Gaussian
neighbourhoods of 1, 2 and 4 mm, for the three tissues, giving **9 additional columns**. A
second logistic regression is trained on the original 151 columns plus these 9. **483
parameters**: $3 \times (160 + 1)$.

The point requiring care: a second stage trained on maps the first stage produced *on its own
training data* would learn to over-trust it, those maps being unrealistically good. We therefore
build the context columns through an **internal 3-fold cross-validation over the training
subjects**, so a subject's context columns always come from a model that never saw it. The
inner-fold models are then discarded; only the final first stage (refit on all training
subjects) and the second stage are transported, hence 456 + 483 = **939 parameters**.

## Step 5 — Decision and post-processing

Argmax over the three corrected probabilities, then mapping to the required label values.

**No post-processing is applied.** We implemented and measured spatial smoothing,
small-component removal and a topological constraint; all three degrade the result on our
cross-validation, so none is used. (The constraint assumed the cortical ribbon separates white
matter from CSF everywhere — true at the cortex, false at the ventricles.)

# Internal evaluation

Leave-one-out over the 10 annotated subjects, metrics computed per class and per subject and
never pooled. This is our only evaluation, which is precisely why we are submitting.

| | CSF | GM | WM | mean |
|:---|---:|---:|---:|---:|
| Dice | 0.891 ± 0.015 | 0.834 ± 0.009 | 0.795 ± 0.015 | **0.840** |
| ASD / MHD (mm) | 0.23 / 1.12 | 0.30 / 1.21 | 0.59 / 2.44 | |

We report MHD as the 95th percentile of symmetric surface distances; two definitions circulate
and we implement both, so if the organisers use Dubuisson–Jain instead our MHD row is not
comparable to theirs. Note also that the submitted model is trained on **all 10** annotated
subjects while the table comes from 10 models each trained on 9.

# Runtime and system

Measured on a **2-core Intel Xeon at 2.10 GHz, 7 GB of RAM**, Python 3.11 with NumPy, SciPy,
scikit-learn and Higra. No GPU is used, and the method has no GPU code path.

Training the submitted model on the 10 annotated subjects takes **320 s**. **Segmenting one new
subject, end to end, takes 87 s on average** (74 s to 112 s across the 13 test subjects). The
model occupies 2.5 kB on disk and about 3 GB of peak memory per subject.

The 87 seconds cover everything from reading the two volumes to writing the label map;
**descriptor extraction dominates by far**, the classifier itself accounting for about two
seconds. Our frugality claim is therefore about parameters and memory, not speed. Source,
configurations and results are in a public repository and the archive is regenerated by one
command with fixed seeds — a command that re-reads what it wrote and checks it against this
specification before producing the archive at all.
