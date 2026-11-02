from dataclasses import dataclass
import math

VERSION = '1.0'

FITS_SUFFIXES = {'.fits', '.fit', '.fts'}
IMAGE_SUFFIXES = FITS_SUFFIXES | {'.xisf'}
DEFAULT_CUTOFF = 10.0


@dataclass(frozen=True)
class Measurement:
    path: str
    status: str = 'ok'
    error: str = ''
    score: float = 0.0
    star_count: int = 0
    coverage: float = 0.0
    fwhm: float = math.nan
    eccentricity: float = math.nan
    background: float = math.nan
    noise: float = math.nan
    exposure: str = ''
    gain: str = ''
    filter_name: str = ''
    seconds: float = 0.0

    def rejection_reason(self, cutoff=DEFAULT_CUTOFF):
        if self.status != 'ok':
            return self.error
        if self.score >= cutoff:
            return ''
        return 'No stars detected' if not self.star_count else 'Very low star evidence / coverage'

@dataclass
class Frame:
    path: str
    measurement: Measurement | None = None
    override: bool | None = None  # True = reject, False = keep, None = automatic

    def flagged(self, cutoff):
        if self.override is not None:
            return self.override
        return bool(self.measurement and self.measurement.status == 'ok'
                    and self.measurement.score < cutoff)

    def keeper(self, cutoff):
        return bool(self.measurement and self.measurement.status == 'ok'
                    and not self.flagged(cutoff))
