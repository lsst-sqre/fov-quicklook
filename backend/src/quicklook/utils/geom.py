from dataclasses import dataclass


@dataclass
class BBox:
    miny: float
    maxy: float
    minx: float
    maxx: float

    def union(self, other: 'BBox'):
        return BBox(
            miny=min(self.miny, other.miny),
            maxy=max(self.maxy, other.maxy),
            minx=min(self.minx, other.minx),
            maxx=max(self.maxx, other.maxx),
        )
