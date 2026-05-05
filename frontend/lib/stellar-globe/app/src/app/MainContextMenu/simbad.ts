import { SkyCoord, V3, angle } from "@stellar-globe/stellar-globe"
import { Marker } from "../features/catalog/catalogSlice"


export async function simbadCatalog(center: SkyCoord, radius: number /* radian */) {
  const text = await queryToSimbad(center, radius)
  const catalogSource = parseSymbadText(text)
  return catalogSource
}


async function queryToSimbad(center: SkyCoord, radius: number /* radian */) {
  const radiusDeg = angle.Angle.fromRad(radius).deg
  const centerString = `${center.a.deg} ${center.d.deg}`
  const url = `https://simbad.cds.unistra.fr/simbad/sim-coo?output.format=ASCII&Coord=${centerString}&Radius=${radiusDeg}&Radius.unit=deg`
  const text = await (await fetch(url)).text()
  return text
}

function parseSymbadText(text: string) {
  /*
  C.D.S.  -  SIMBAD4 rel 1.8  -  2024.02.05CET04:12:53

  coord 12 30 +10 20 (ICRS, J2000, 2000.0), radius: 10 arcmin
  -----------------------------------------------------------
  
  Number of objects : 83
  
  # |dist(asec)|            identifier             |typ|       coord1 (ICRS,J2000/2000)        |Mag I |Mag U |  Mag B  |  Mag V  |Mag R |  spec. type   |#bib|#not
  --|----------|-----------------------------------|---|---------------------------------------|------|------|---------|---------|------|---------------|----|----
  1 |     54.79|[RGD2013] J123001.936+102046.897   |G  |12 30 01.9295018544 +10 20 46.815856980|     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  2 |     56.59|[RGD2013] J122958.105+102049.200   |G  |12 29 58.1050 +10 20 49.200            |     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  3 |     91.62|LEDA 41240                         |AG?|12 29 53.8969349904 +10 20 16.819999548|     ~|     ~|16       |     ~   |     ~|~              |  17|   0
  4 |     93.60|[RGD2013] J123004.896+101900.480   |G  |12 30 04.8922423512 +10 19 00.424314984|     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  5 |     97.79|Gaia DR2 3903981407839782528       |WD?|12 29 53.3729869392 +10 20 00.335223024|     ~|     ~|     ~   |     ~   |     ~|~              |   2|   0
  6 |    112.23|[RGD2013] J122955.914+102134.739   |G  |12 29 55.9144087416 +10 21 34.668159120|     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  7 |    133.86|[RGD2013] J122954.112+101818.180   |G  |12 29 54.1120 +10 18 18.180            |     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  8 |    155.26|[RGD2013] J122958.434+102233.529   |G  |12 29 58.4340 +10 22 33.529            |     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  9 |    160.43|[RGD2013] J122958.414+102238.786   |G  |12 29 58.4128720416 +10 22 38.715553092|     ~|     ~|     ~   |     ~   |     ~|~              |   1|   0
  */

  const lines = text.split('\n')
  let i: number
  let fields: string[] = []
  let coordIndex: number = -1
  const markers: Marker[] = []
  const attributes: string[][] = []
  for (i = 0; i < lines.length; ++i) {
    const line = lines[i]
    const cells = line.split('|').map(c => c.trim())
    if (cells[0] === '#') {
      fields = cells
      coordIndex = fields.findIndex(c => c.startsWith('coord1'))
      i += 1
      continue
    }
    if (coordIndex >= 0) {
      let position: V3 | undefined = undefined
      try {
        position = SkyCoord.parse(cells[coordIndex]).xyz
        markers.push({ position })
        attributes.push(cells)
      }
      catch {
        /* */
      }
    }
  }
  return {
    markers,
    attributes,
    fields,
  }
}
