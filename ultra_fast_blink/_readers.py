from pathlib import Path
import numpy as np
from astropy.io import fits
from ._models import FITS_SUFFIXES

class RawFitsPlane:
    """Map a supported plane and release all mapping references on exit.

    Only owned copies of small sections may escape this context.
    """
    def __init__(self, path):
        self.path = str(path)
        self.hdul = None
        self.data = None

    def __enter__(self):
        if Path(self.path).suffix.lower() not in FITS_SUFFIXES:
            raise ValueError('Unsupported format: use uncompressed FITS (.fits/.fit/.fts)')
        try:
            self.hdul = fits.open(self.path, memmap=True, do_not_scale_image_data=True,
                                  lazy_load_hdus=True)
            if self.hdul.fileinfo(0)['file'].compression:
                raise ValueError('Compressed FITS is not supported')
            for hdu in self.hdul:
                if isinstance(hdu, fits.CompImageHDU):
                    raise ValueError('Compressed FITS is not supported')
                if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU)):
                    hdr = hdu.header
                    if hdr.get('NAXIS') != 2:
                        continue
                    w, h = int(hdr.get('NAXIS1', 0)), int(hdr.get('NAXIS2', 0))
                    if min(w, h) < 8:
                        continue
                    info = hdu.fileinfo()
                    expected = w * h * (abs(int(hdr['BITPIX'])) // 8)
                    if info['datLoc'] + expected > Path(self.path).stat().st_size:
                        raise ValueError('Truncated FITS pixel data')
                    self.header = self.hdul[0].header.copy()
                    self.header.update(hdr)
                    self.scale = float(hdr.get('BSCALE', 1))
                    self.zero = float(hdr.get('BZERO', 0))
                    if not np.isfinite([self.scale, self.zero]).all() or self.scale == 0:
                        raise ValueError('Invalid FITS scaling')
                    self.blank = hdr.get('BLANK') if hdr['BITPIX'] > 0 else None
                    self.bayer = bool(str(self.header.get('BAYERPAT', '')).strip())
                    self.data = hdu.data
                    return self
            raise ValueError('No supported 2D FITS image (minimum 8 × 8 pixels)')
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        self.data = None
        if self.hdul is not None:
            self.hdul.close()
            self.hdul = None

    def patch(self, y, x, h, w):
        raw = self.data[y:y+h, x:x+w]
        out = raw.astype(np.float32)
        if self.blank is not None:
            out[raw == self.blank] = np.nan
        out *= self.scale
        out += self.zero
        return out

    @property
    def shape(self):
        return self.data.shape

    def sampled(self, step, dy=0, dx=0):
        return self.data[dy::step, dx::step].astype(np.float32)


class RawXisfPlane:
    """Map uncompressed attachments; decode compressed/inline images via xisf.

    RGB is reduced to luminance only for requested patches/display samples.
    The first image is used, matching the application's regular XISF loader.
    """
    def __init__(self, path):
        self.path = str(path)
        self.data = None
        self.mapping = None
        self.scale, self.zero, self.blank = 1.0, 0.0, None

    def __enter__(self):
        from xisf import XISF

        try:
            reader = XISF(self.path)
            images = reader.get_images_metadata()
            if not images:
                raise ValueError('XISF contains no images')
            meta = images[0]
            w, h, channels = meta['geometry']
            if min(w, h) < 8 or channels not in (1, 3):
                raise ValueError('XISF requires mono or RGB, minimum 8 × 8 pixels')
            dtype = np.dtype(meta['dtype'])
            if dtype.kind not in 'uif':
                raise ValueError('Unsupported XISF sample format')
            dtype = dtype.newbyteorder('>' if meta.get('byteOrder', 'little') == 'big' else '<')
            storage = meta.get('pixelStorage', 'planar')
            if storage not in ('planar', 'normal'):
                raise ValueError('Unsupported XISF pixel storage')
            shape = (channels, h, w) if storage == 'planar' else (h, w, channels)
            location = meta['location']
            if location[0] == 'attachment' and not meta.get('compression'):
                _, offset, length = location
                expected = w * h * channels * dtype.itemsize
                if offset < 0 or length < expected or offset + expected > Path(self.path).stat().st_size:
                    raise ValueError('Truncated XISF pixel data')
                self.mapping = np.memmap(self.path, mode='r', dtype=dtype,
                                         offset=offset, shape=shape)
                data = self.mapping
            else:
                # The XISF library decodes the whole block for compressed data.
                data = reader.read_image(0, data_format='channels_first').view(dtype).reshape(shape)
            self.data = np.moveaxis(data, -1, 0) if storage == 'normal' else data
            self.header = {key: values[0]['value']
                           for key, values in meta.get('FITSKeywords', {}).items() if values}
            self.bayer = channels == 1 and bool(self.header.get('BAYERPAT', '').strip())
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        self.data = None
        if self.mapping is not None:
            self.mapping._mmap.close()
            self.mapping = None

    @property
    def shape(self):
        return self.data.shape[1:]

    @staticmethod
    def _luminance(data):
        if data.shape[0] == 1:
            return data[0].astype(np.float32)
        result = data[0].astype(np.float32) * .2126
        result += data[1].astype(np.float32) * .7152
        result += data[2].astype(np.float32) * .0722
        return result

    def patch(self, y, x, h, w):
        return self._luminance(self.data[:, y:y+h, x:x+w])

    def sampled(self, step, dy=0, dx=0):
        return self._luminance(self.data[:, dy::step, dx::step])


def open_plane(path):
    return RawXisfPlane(path) if Path(path).suffix.lower() == '.xisf' else RawFitsPlane(path)

