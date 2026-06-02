# TomoNet: Research & Evaluation

## Summary

**Status:** Evaluated, **not suitable for current benchmark scope**

TomoNet is a deep-learning-based 3D denoising and artifact-correction package (primarily IsoNet for missing-wedge compensation). While it *could* be adapted for unsupervised classification by building custom convolutional autoencoders, this would require **retraining proprietary models** — contrary to the benchmark goal of evaluating **out-of-the-box classification packages** on realistic CryoET data.

---

## What TomoNet Does (Out-of-Box)

TomoNet provides IsoNet-based missing-wedge compensation for 3D tomographic volumes:
- Trains a 3D U-Net denoiser on synthetic pairs (missing-wedge + corrected)
- Predicts corrected volumes; users then re-extract subtomograms
- **No classification or clustering capability built-in**

The `rlnClassNumber` field exists in its RELION STAR template (`util/metadata.py:48`) but is never populated by any workflow, and there is no PCA, clustering, or heterogeneity analysis code anywhere in the codebase.

---

## Why TomoNet Does Not Meet Requirements

The benchmark evaluates how well **existing off-the-shelf classification packages** distinguish conformational heterogeneity from pre-picked subtomograms. TomoNet's architecture could be extended for this purpose, but only by:

1. **Training custom autoencoders** on domain-specific data
2. **Implementing clustering** (PCA + k-means) post-hoc
3. **Validating that learned representations capture real heterogeneity** (not just reconstruction fidelity)

### Why This Does Not Fit the Benchmark

The benchmark is designed to test **classification packages as supplied by their developers**, under identical preprocessing and evaluation metrics. Custom retraining of TomoNet's encoder-decoder architecture:

- **Introduces development variables** (learning rate, bottleneck dimensionality, training epochs) that are not part of the package's documented workflow
- **Shifts focus** from evaluating the package to engineering a bespoke solution
- **Duplicates effort** already performed by packages like RELION (3D classification), PyTom (class averages), and OPUS-TOMO (deep learning classification) — which *are* designed for this purpose out-of-the-box

---

## Technical Capability (For Reference)

If the benchmark scope ever shifts to *custom model development*, TomoNet provides reusable components:

| Existing component | How it could be reused |
|---|---|
| `EncoderBlock` / `DecoderBlock` in `models/unet_isonet.py` | 3D conv encoder for feature extraction |
| `Predict_sets` in `models/data_sequence.py` | Loads list of .mrc subtomograms |
| `MetaData` in `util/metadata.py` | Reads/writes STAR files with `rlnClassNumber` |
| `preprocessing/cubes.py:normalize` | Per-volume normalisation |
| pytorch-lightning training loop pattern from `models/network_isonet.py` | Autoencoder training scaffolding |

A complete implementation below is preserved for reference if this direction is reconsidered.

---

## Implementation Details (If Reconsidered)

### Step 1: Create the autoencoder model

Create `models/autoencoder.py`. This reuses `EncoderBlock` from
`models/unet_isonet.py` unchanged. The decoder deliberately omits skip
connections so the bottleneck must encode all structural information — skip
connections would allow reconstruction without learning a meaningful latent space.

```python
# models/autoencoder.py
import torch
import torch.nn as nn
import pytorch_lightning as pl
from TomoNet.models.unet_isonet import EncoderBlock, ConvBlock


FILTER_BASES = {
    64: [64, 128, 256, 320, 320, 320],
    32: [32,  64, 128, 256, 320, 320],
    16: [16,  32,  64, 128, 256, 320],
}
UNET_DEPTH = 3   # matches unet_isonet.py


class _Decoder(nn.Module):
    """Symmetric decoder WITHOUT skip connections — forces bottleneck to encode structure."""
    def __init__(self, filter_base):
        super().__init__()
        layers = []
        for n in reversed(range(UNET_DEPTH)):
            layers += [
                nn.ConvTranspose3d(filter_base[n + 1], filter_base[n],
                                   kernel_size=2, stride=2, padding=0),
                nn.LeakyReLU(),
                ConvBlock(filter_base[n], filter_base[n], n_conv=2),
            ]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class SubtomoAutoencoder(pl.LightningModule):
    """
    3D convolutional autoencoder for unsupervised subtomogram classification.
    Encoder: shared with IsoNet U-Net (EncoderBlock from unet_isonet.py).
    Bottleneck: global-average-pool → linear projection to latent_dim.
    Decoder: symmetric upsampling without skip connections.
    """
    def __init__(self, filter_base: int = 32, latent_dim: int = 256,
                 cube_size: int = 64, lr: float = 3e-4):
        super().__init__()
        self.save_hyperparameters()
        fb = FILTER_BASES[filter_base]
        bottleneck_ch = fb[UNET_DEPTH]            # 256 for filter_base=32
        spatial = cube_size // (2 ** UNET_DEPTH)  # 8 for 64³ input

        self.encoder   = EncoderBlock(filter_base=fb, unet_depth=UNET_DEPTH, n_conv=3)
        self.pool      = nn.AdaptiveAvgPool3d(1)
        self.fc_enc    = nn.Linear(bottleneck_ch, latent_dim)

        self.fc_dec    = nn.Linear(latent_dim, bottleneck_ch * spatial ** 3)
        self._spatial  = spatial
        self._btch     = bottleneck_ch
        self.decoder   = _Decoder(fb)
        self.out_conv  = nn.Conv3d(fb[0], 1, kernel_size=3, padding=1)

        self.lr = lr
        self._train_losses: list = []
        self._val_losses:   list = []

    # ------------------------------------------------------------------ encode
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Return latent vector z of shape [B, latent_dim]."""
        enc, _ = self.encoder(x)
        pooled = self.pool(enc).flatten(1)
        return self.fc_enc(pooled)

    # ----------------------------------------------------------------- forward
    def forward(self, x: torch.Tensor):
        enc, _ = self.encoder(x)
        z = self.fc_enc(self.pool(enc).flatten(1))
        h = self.fc_dec(z).view(-1, self._btch,
                                self._spatial, self._spatial, self._spatial)
        return self.out_conv(self.decoder(h)), z

    # -------------------------------------------------------------- pl methods
    def _step(self, batch):
        x = batch if isinstance(batch, torch.Tensor) else batch[0]
        x = x.float()
        if x.ndim == 4:
            x = x.unsqueeze(1)
        recon, _ = self(x)
        return nn.functional.mse_loss(recon, x)

    def training_step(self, batch, _):
        loss = self._step(batch)
        self._train_losses.append(loss.detach())
        return loss

    def validation_step(self, batch, _):
        loss = self._step(batch)
        self._val_losses.append(loss.detach())

    def on_train_epoch_end(self):
        if self._train_losses:
            self.log("train_loss", torch.stack(self._train_losses).mean(), prog_bar=True)
            self._train_losses.clear()

    def on_validation_epoch_end(self):
        if self._val_losses:
            self.log("val_loss", torch.stack(self._val_losses).mean(), prog_bar=True)
            self._val_losses.clear()

    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=self.lr)
```

### Step 2: Training script

Create `bin/train_autoencoder.py`:

```python
#!/usr/bin/env python3
"""Train a 3D convolutional autoencoder on pre-picked subtomograms."""
import glob, json, os, sys
import torch
from torch.utils.data import DataLoader, random_split
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from TomoNet.models.data_sequence import Predict_sets
from TomoNet.models.autoencoder   import SubtomoAutoencoder


def main(param_json: str):
    with open(param_json) as fh:
        p = json.load(fh)

    # Collect .mrc paths -------------------------------------------------------
    mrc_dir  = p["mrc_dir"]          # directory with one .mrc per particle
    mrc_list = sorted(glob.glob(os.path.join(mrc_dir, "*.mrc")))
    assert mrc_list, f"No .mrc files found in {mrc_dir}"
    print(f"Found {len(mrc_list)} subtomograms")

    output_dir   = p.get("output_dir",  "Classify/autoencoder/")
    filter_base  = p.get("filter_base", 32)
    latent_dim   = p.get("latent_dim",  256)
    cube_size    = p.get("cube_size",   64)
    batch_size   = p.get("batch_size",  8)
    num_epochs   = p.get("num_epochs",  100)
    lr           = p.get("lr",          3e-4)
    val_split    = p.get("val_split",   0.1)
    gpus         = [int(g) for g in str(p.get("gpus", "0")).split(",")]

    os.makedirs(output_dir, exist_ok=True)

    # Dataset: Predict_sets normalises and inverts density by default ----------
    # inverted=True flips contrast so density peaks are positive
    full_ds = Predict_sets(mrc_list, inverted=True)
    n_val   = max(1, int(len(full_ds) * val_split))
    train_ds, val_ds = random_split(full_ds, [len(full_ds) - n_val, n_val],
                                    generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False,
                              num_workers=4, pin_memory=True)

    model = SubtomoAutoencoder(filter_base=filter_base, latent_dim=latent_dim,
                               cube_size=cube_size, lr=lr)

    ckpt_cb = ModelCheckpoint(dirpath=output_dir,
                              filename="autoencoder_{epoch:03d}",
                              monitor="val_loss", save_top_k=3, mode="min",
                              save_last=True)

    trainer = pl.Trainer(
        max_epochs=num_epochs,
        accelerator="gpu", devices=gpus,
        callbacks=[ckpt_cb],
        default_root_dir=output_dir,
    )
    trainer.fit(model, train_loader, val_loader)
    print(f"Best checkpoint: {ckpt_cb.best_model_path}")


if __name__ == "__main__":
    main(sys.argv[1])
```

Example parameter file `autoencoder_params.json`:

```json
{
    "mrc_dir":     "/path/to/subtomograms/",
    "output_dir":  "Classify/autoencoder/",
    "filter_base": 32,
    "latent_dim":  256,
    "cube_size":   64,
    "batch_size":  8,
    "num_epochs":  100,
    "lr":          3e-4,
    "val_split":   0.1,
    "gpus":        "0"
}
```

### Step 3: Feature extraction, clustering, and output

Create `bin/classify_unsupervised.py`:

```python
#!/usr/bin/env python3
"""Extract latent features and cluster pre-picked subtomograms into classes."""
import glob, json, os, sys
import numpy as np
import torch
from torch.utils.data import DataLoader
import mrcfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from TomoNet.models.data_sequence import Predict_sets
from TomoNet.models.autoencoder   import SubtomoAutoencoder
from TomoNet.util.metadata        import MetaData


# ----------------------------------------------------------------- feature extraction
def extract_features(model, mrc_list, batch_size, device):
    ds     = Predict_sets(mrc_list, inverted=True)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=4)
    model.eval().to(device)
    feats = []
    with torch.no_grad():
        for batch in loader:
            x = batch.float()
            if x.ndim == 4:
                x = x.unsqueeze(1)
            feats.append(model.encode(x.to(device)).cpu().numpy())
    return np.concatenate(feats, axis=0)   # [N, latent_dim]


# ------------------------------------------------------------------- clustering
def cluster(features, n_classes):
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.cluster       import KMeans

    scaled = StandardScaler().fit_transform(features)
    n_comp = min(50, scaled.shape[0] - 1, scaled.shape[1])
    pca    = PCA(n_components=n_comp, random_state=42)
    pca_feats = pca.fit_transform(scaled)
    var_explained = pca.explained_variance_ratio_.cumsum()[-1] * 100
    print(f"PCA: {n_comp} components, {var_explained:.1f}% variance retained")

    km     = KMeans(n_clusters=n_classes, n_init=20, random_state=42)
    labels = km.fit_predict(pca_feats)
    return labels, pca_feats


# --------------------------------------------------------------- class averages
def write_class_averages(mrc_list, labels, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    n_classes = int(labels.max()) + 1
    for cls in range(n_classes):
        idx   = np.where(labels == cls)[0]
        stack = []
        for i in idx:
            with mrcfile.open(mrc_list[i], permissive=True) as f:
                stack.append(f.data.copy().astype(np.float32))
        avg  = np.mean(stack, axis=0)
        path = os.path.join(out_dir, f"class_avg_{cls + 1:03d}.mrc")
        with mrcfile.new(path, overwrite=True) as f:
            f.set_data(avg)
        print(f"  Class {cls + 1:3d}: {len(idx):6d} particles → {path}")


# -------------------------------------------------------------- STAR file output
def write_star(mrc_list, labels, out_star):
    md = MetaData()
    md.addLabels("rlnSubtomoIndex", "rlnImageName", "rlnClassNumber")
    for i, (path, cls) in enumerate(zip(mrc_list, labels)):
        md.addData({"rlnSubtomoIndex": i,
                    "rlnImageName":    path,
                    "rlnClassNumber":  int(cls) + 1})
    md.write(out_star)
    print(f"Wrote classified STAR: {out_star}")


# ----------------------------------------------------------------------- main
def main(param_json):
    with open(param_json) as fh:
        p = json.load(fh)

    checkpoint  = p["checkpoint"]          # path to .ckpt from train_autoencoder.py
    mrc_dir     = p["mrc_dir"]
    n_classes   = int(p["n_classes"])
    output_dir  = p.get("output_dir",  "Classify/results/")
    batch_size  = p.get("batch_size",  32)
    gpu_id      = str(p.get("gpus",    "0")).split(",")[0]

    mrc_list = sorted(glob.glob(os.path.join(mrc_dir, "*.mrc")))
    assert mrc_list, f"No .mrc files found in {mrc_dir}"

    os.makedirs(output_dir, exist_ok=True)
    device = (torch.device(f"cuda:{gpu_id}")
              if torch.cuda.is_available() else torch.device("cpu"))

    print("Loading model …")
    model = SubtomoAutoencoder.load_from_checkpoint(checkpoint)

    print("Extracting latent features …")
    features = extract_features(model, mrc_list, batch_size, device)
    np.save(os.path.join(output_dir, "features.npy"), features)
    print(f"Features: {features.shape}")

    print(f"Clustering into {n_classes} classes …")
    labels, pca_feats = cluster(features, n_classes)
    np.save(os.path.join(output_dir, "labels.npy"),       labels)
    np.save(os.path.join(output_dir, "features_pca.npy"), pca_feats)

    print("Writing class averages …")
    write_class_averages(mrc_list, labels,
                         os.path.join(output_dir, "class_averages"))

    write_star(mrc_list, labels,
               os.path.join(output_dir, "particles_classified.star"))

    # Summary
    print("\nClass distribution:")
    for cls in range(n_classes):
        n = int((labels == cls).sum())
        print(f"  Class {cls + 1}: {n} particles ({n / len(labels) * 100:.1f}%)")


if __name__ == "__main__":
    main(sys.argv[1])
```

Example parameter file `classify_params.json`:

```json
{
    "checkpoint": "Classify/autoencoder/autoencoder_best.ckpt",
    "mrc_dir":    "/path/to/subtomograms/",
    "n_classes":  3,
    "output_dir": "Classify/results/",
    "batch_size": 32,
    "gpus":       "0"
}
```

### Choosing the Number of Classes

K-means requires `n_classes` upfront. After training, run interactively:

```python
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

features = np.load("Classify/results/features.npy")
scaled   = StandardScaler().fit_transform(features)
pca50    = PCA(n_components=50, random_state=42).fit_transform(scaled)

for k in range(2, 8):
    km  = KMeans(n_clusters=k, n_init=20, random_state=42).fit(pca50)
    sil = silhouette_score(pca50, km.labels_, sample_size=min(5000, len(pca50)))
    print(f"K={k}  inertia={km.inertia_:.2e}  silhouette={sil:.3f}")
```

Choose the K where the silhouette score is highest AND class averages (in 3dmod or ChimeraX) show structurally distinct densities.

### Expected Output

```
Classify/
├── autoencoder/
│   ├── autoencoder_001.ckpt        ← training checkpoints
│   ├── autoencoder_last.ckpt
│   └── lightning_logs/
└── results/
    ├── features.npy                ← [N, latent_dim] raw latent vectors
    ├── features_pca.npy            ← [N, ≤50] PCA-reduced vectors
    ├── labels.npy                  ← [N] integer class labels (0-indexed)
    ├── particles_classified.star   ← STAR file with rlnClassNumber populated
    └── class_averages/
        ├── class_avg_001.mrc
        ├── class_avg_002.mrc
        └── class_avg_003.mrc
```

Inspect class averages with `3dmod` or ChimeraX to confirm classes are structurally meaningful.

---

## Conclusion

**TomoNet is not included in this benchmark.** While IsoNet-based missing-wedge correction could be a pre-processing step for certain datasets, TomoNet does not offer a classification workflow suitable for direct evaluation alongside RELION, OPUS-TOMO, PyTom, and other packages in the benchmark scope.

If future work focuses on *custom classification model development* or *comparing the quality of pre-processing via IsoNet followed by external classification*, this research document captures the technical details needed to construct such a workflow.
