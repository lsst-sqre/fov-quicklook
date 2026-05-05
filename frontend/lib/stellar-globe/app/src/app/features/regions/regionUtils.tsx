import { SkyCoord } from "@stellar-globe/stellar-globe"


export function skyCoordFromCoordDef({ ra, dec }: { ra: number; dec: number }) {
  return SkyCoord.fromRad(ra, dec)
}


export function normalizeSkyCoord(c: SkyCoord) {
  return {
    ra: c.a.rad,
    dec: c.d.rad,
  }
}
