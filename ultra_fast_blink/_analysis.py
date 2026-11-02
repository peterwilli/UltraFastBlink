import math
from time import perf_counter
import numpy as np
import sep
from ._models import Measurement
from ._readers import open_plane

def sample_windows(shape, size=256, grid=5):
    """Evenly spread, disjoint windows, including both image edges."""
    h, w = shape
    ph, pw = min(size, h), min(size, w)
    ny, nx = min(grid, max(1, h // ph)), min(grid, max(1, w // pw))
    ys = np.linspace(0, h - ph, ny, dtype=int)
    xs = np.linspace(0, w - pw, nx, dtype=int)
    return [(int(y), int(x), ph, pw) for y in ys for x in xs]


def _superpixel(z):
    h, w = z.shape
    return z[:h//2*2, :w//2*2].reshape(h//2, 2, w//2, 2).mean(axis=(1, 3))


def measure_file(path):
    start = perf_counter()
    try:
        counts, widths, eccs, backgrounds, noises = [], [], [], [], []
        valid, total = 0, 0
        with open_plane(path) as plane:
            header = plane.header
            factor = 2 if plane.bayer else 1
            for y, x, h, w in sample_windows(plane.shape):
                z = plane.patch(y, x, h, w)
                finite = np.isfinite(z)
                valid += int(finite.sum())
                total += z.size
                if not finite.any():
                    counts.append(0)
                    continue
                z[~finite] = np.median(z[finite])
                if plane.bayer:
                    z = _superpixel(z)
                z = np.ascontiguousarray(z, dtype=np.float32)
                bg = sep.Background(z)
                backgrounds.append(float(bg.globalback))
                noises.append(float(bg.globalrms))
                if bg.globalrms <= 0 or not np.isfinite(bg.globalrms):
                    counts.append(0)
                    continue
                residual = z - bg.back()
                cat = sep.extract(residual, 5.0, err=bg.globalrms,
                                  minarea=3 if plane.bayer else 5)
                a, b = cat['a'], cat['b']
                ratio = b / np.maximum(a, 1e-6)
                mask = ((a > .7) & (b > .7) & (a * factor < 8) & (ratio > .5)
                        & (cat['flag'] == 0) & (cat['x'] >= 3) & (cat['y'] >= 3)
                        & (cat['x'] < z.shape[1]-3) & (cat['y'] < z.shape[0]-3))
                # SEP's detection filter can turn a single hot pixel into a
                # round source. Require support in the *unfiltered* pixels.
                cx = np.clip(np.rint(cat['x']).astype(int), 1, z.shape[1]-2)
                cy = np.clip(np.rint(cat['y']).astype(int), 1, z.shape[0]-2)
                neighbors = np.stack([residual[cy+dy, cx+dx]
                                      for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
                support_threshold = np.maximum(3*bg.globalrms, .1*neighbors.max(axis=0))
                mask &= (neighbors > support_threshold).sum(axis=0) >= 3
                counts.append(int(mask.sum()))
                widths.extend((2.3548 * np.sqrt(a[mask]*b[mask]) * factor).tolist())
                eccs.extend(np.sqrt(np.maximum(0, 1-ratio[mask]**2)).tolist())
        if valid < .95 * total:
            raise ValueError('Too many invalid pixels in sampled data')
        count = sum(counts)
        coverage = sum(n > 0 for n in counts) / len(counts)
        return Measurement(
            path=str(path), score=100 * coverage * min(count / 25, 1),
            star_count=count, coverage=coverage,
            fwhm=float(np.median(widths)) if widths else math.nan,
            eccentricity=float(np.median(eccs)) if eccs else math.nan,
            background=float(np.median(backgrounds)) if backgrounds else math.nan,
            noise=float(np.median(noises)) if noises else math.nan,
            exposure=str(header.get('EXPTIME', header.get('EXPOSURE', ''))),
            gain=str(header.get('GAIN', '')), filter_name=str(header.get('FILTER', '')),
            seconds=perf_counter()-start)
    except Exception as exc:
        return Measurement(path=str(path), status='error', error=str(exc),
                           seconds=perf_counter()-start)


def make_preview(path, max_side=1600):
    """Read sparse raw rows, stretch only the bounded display array, return uint8."""
    with open_plane(path) as plane:
        h, w = plane.shape
        step = max(1, math.ceil(max(h, w) / max_side))
        # Even strides preserve CFA phase; average a local 2x2 for Bayer images.
        if plane.bayer:
            step = max(2, step + step % 2)
        z = plane.sampled(step)
        if plane.blank is not None:
            z[z == plane.blank] = np.nan
        if plane.bayer:
            oh, ow = h // step, w // step
            z = z[:oh, :ow]
            for dy, dx in ((0, 1), (1, 0), (1, 1)):
                other = plane.sampled(step, dy, dx)[:oh, :ow]
                if plane.blank is not None:
                    other[other == plane.blank] = np.nan
                z += other
            z /= 4
        z *= plane.scale
        z += plane.zero
    finite = np.isfinite(z)
    if not finite.any():
        raise ValueError('No finite preview pixels')
    lo, hi = np.percentile(z[finite], [1, 99.8])
    z = np.nan_to_num(z, nan=lo, posinf=hi, neginf=lo)
    z = np.clip((z - lo) / max(float(hi-lo), 1e-12), 0, 1)
    return np.ascontiguousarray(np.arcsinh(20*z) / np.arcsinh(20) * 255, dtype=np.uint8)
