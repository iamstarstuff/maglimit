import math
from dataclasses import dataclass

# Typical sky brightness in mag/arcsec^2 for each Bortle class
BORTLE_SQM = {1: 22.0, 2: 21.9, 3: 21.7, 4: 21.0, 5: 20.0, 6: 19.2, 7: 18.7, 8: 18.2, 9: 17.5}


def bortle_to_sqm(bortle):
    """Looks up a typical sky brightness for a Bortle class

    Args:
        bortle: Bortle class, a whole number from 1 (darkest) to 9 (inner city)

    Returns:
        Sky brightness in mag/arcsec^2

    Raises:
        ValueError: if bortle is not a whole number from 1 to 9
    """
    if isinstance(bortle, bool) or bortle not in BORTLE_SQM:
        raise ValueError(f"bortle must be a whole number from 1 to 9, got {bortle}")
    return BORTLE_SQM[bortle]


def naked_eye_limit(sqm):
    """Estimates the faintest star visible to the naked eye under a given sky

    Args:
        sqm: sky brightness in mag/arcsec^2

    Returns:
        Naked-eye limiting magnitude
    """
    return 7.93 - 5*math.log10(10**(4.316 - sqm/5) + 1)


@dataclass(frozen=True)
class Site:
    """Takes in an observing site. Give the sky darkness as bortle or sqm; sqm wins if both.

    Args:
        lat: latitude in degrees, north positive
        lon: longitude in degrees, east positive
        elevation: height above sea level in m
        bortle: Bortle class from 1 to 9
        sqm: measured sky brightness in mag/arcsec^2

    Raises:
        ValueError: if no sky darkness is given or a value is not physically possible
    """
    lat: float = None
    lon: float = None
    elevation: float = 0.0
    bortle: int = None
    sqm: float = None

    def __post_init__(self):
        if self.lat is not None and not -90 <= self.lat <= 90:
            raise ValueError(f"lat must be from -90 to 90, got {self.lat}")
        if self.lon is not None and not -180 <= self.lon <= 180:
            raise ValueError(f"lon must be from -180 to 180, got {self.lon}")
        if self.bortle is None and self.sqm is None:
            raise ValueError("give the sky darkness as bortle or sqm")
        typical_sqm = None if self.bortle is None else bortle_to_sqm(self.bortle)
        if self.sqm is None:
            object.__setattr__(self, "sqm", typical_sqm)
        elif not 16 <= self.sqm <= 23:
            raise ValueError(f"sqm must be from 16 to 23, got {self.sqm}")

    @property
    def nelm(self):
        """Naked-eye limiting magnitude at this site, rounded to 2 decimals
        """
        return round(naked_eye_limit(self.sqm), 2)
