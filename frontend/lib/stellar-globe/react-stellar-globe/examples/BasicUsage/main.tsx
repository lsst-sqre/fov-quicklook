import { BillboardText, Globe, MarkerType, SkyCoord, TractTileLayer, V3, V4, markerTypes } from '@stellar-globe/stellar-globe'
import { produce } from 'immer'
import React, { useMemo, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { ClickableMarkerLayer$, ConstellationLayer$, EsoMilkyWayLayer$, Globe$, GridLayer$, HipparcosCatalogLayer$, HipsSimpleLayer$, TractTileLayer$, TextLayer$, DomLayer$ } from '../../src'
import { LogScaleRange } from '../../src/LogScaleRange'
import './style.scss'


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)


type GlobeOptions = NonNullable<ConstructorParameters<typeof Globe>[1]>


function App() {
  const [visibility, setVisibility] = useState({
    constellation: true,
    constellationNames: false,
    catalog: true,
    area: true,
    milkyway: true,
    dud: true,
  })
  const [baseType, setBaseType] = useState<'hips' | 'tile'>('tile')
  const { constellation, constellationNames, catalog, area, milkyway, dud } = visibility
  const [colorParams, setColorParams] = useState(() => TractTileLayer.defaultParams({ type: 'sdssTrueColor' }))
  const globeOptions = useMemo<GlobeOptions>(() => ({
    viewOptions: {
      retina: false,
    }
  }), [])

  const texts = useMemo<BillboardText[]>(() => {
    return [
      { position: [1, 0, 0], text: 'x', color: 'red' },
      { position: [0, 1, 0], text: 'y', color: 'green' },
      { position: [0, 0, 1], text: 'z', color: 'blue' },
      { position: [-1, 0, 0], text: 'X', color: 'red' },
      { position: [0, -1, 0], text: 'Y', color: 'green' },
      { position: [0, 0, -1], text: 'Z', color: 'blue' },
    ]
  }, [])

  const [history, setHistory] = useState<number[]>([])

  const clickableMarkerLayerProps: Parameters<typeof ClickableMarkerLayer$>[0] = useMemo(() => ({
    defaultColor: [1, 2, 1, 1],
    defaultType: 'circle',
    dimmAlpha: 0.75,
    markers: Array.from({ length: 1000 }, (_, i) => ({
      position: SkyCoord.fromDeg(randomInRange(-1, 1), randomInRange(-1, 1)).xyz,
      color: [...hsvToRgb(Math.random(), 0.75, 1), 0.75] as V4,
      type: markerTypes[i % markerTypes.length] as MarkerType,
    })),
    onClick: e => {
      setHistory(_ => [..._, e.index])
    }
  }), [])

  TractTileLayer.assertType(colorParams, 'sdssTrueColor')

  const domPosition = useMemo<V3>(() => [1, 0, 0], [])

  return (
    <div>
      <div style={{ width: '100vw', height: '100vh' }}>
        <Globe$ {...globeOptions}>
          <TractTileLayer$
            baseUrl='//hscmap.mtk.nao.ac.jp/hscMap4/data/pdr3_wide'
            outline={area}
            colorParams={colorParams}
            visible={baseType === 'tile'}
          />
          <TractTileLayer$
            baseUrl='//hscmap.mtk.nao.ac.jp/hscMap4/data/pdr3_dud'
            outline={area}
            colorParams={colorParams}
            visible={dud && baseType === 'tile'}
          />
          <HipsSimpleLayer$
            baseUrl='//alasky.cds.unistra.fr/Pan-STARRS/DR1/color-i-r-g'
            visible={baseType === 'hips'}
          />
          <GridLayer$ />
          <ConstellationLayer$ showNames={constellationNames} visible={constellation} />
          <HipparcosCatalogLayer$ visible={catalog} />
          <EsoMilkyWayLayer$ fadeInDuration={400} visible={milkyway} />
          <TextLayer$ defaultColor='white' defaultFont='24pt sans-serif' texts={texts} />
          <ClickableMarkerLayer$ {...clickableMarkerLayerProps} />
          <DomLayer$ position={domPosition}>
            <button onClick={() => alert('ok')}>DomLayer</button>
          </DomLayer$>
        </Globe$>
      </div>
      <div className='controlpanel'>
        <label>
          <input type='checkbox' checked={constellation} onChange={e => {
            setVisibility({ ...visibility, constellation: e.currentTarget.checked })
          }} />
          Constellation
        </label>
        <label>
          <input type='checkbox' checked={constellationNames} onChange={e => {
            setVisibility({ ...visibility, constellationNames: e.currentTarget.checked })
          }} />
          Constellation Names
        </label>
        <label>
          <input type='checkbox' checked={catalog} onChange={e => {
            setVisibility({ ...visibility, catalog: e.currentTarget.checked })
          }} />
          Hipparcos Catalog
        </label>
        <label>
          <input type='checkbox' checked={area} onChange={e => {
            setVisibility({ ...visibility, area: e.currentTarget.checked })
          }} />
          Area
        </label>
        <label>
          <input type='checkbox' checked={milkyway} onChange={e => {
            setVisibility({ ...visibility, milkyway: e.currentTarget.checked })
          }} />
          Eso Milkyway
        </label>
        <label>
          <input type='checkbox' checked={dud} onChange={e => {
            setVisibility({ ...visibility, dud: e.currentTarget.checked })
          }} />
          DUD
        </label>
        <dl>
          <dt>
            Type:
          </dt>
          <dd>
            <select value={baseType} onChange={e => setBaseType(e.currentTarget.value as 'hips' | 'tile')}>
              <option value='tile'>Tile</option>
              <option value='hips'>HiPS</option>
            </select>
          </dd>
          <dt> &beta; </dt>
          <dd>
            <LogScaleRange value={colorParams.sdssTrueColor.beta} min={0} max={2.e+8} onInput={beta => {
              setColorParams(produce(colorParams, _ => { _.sdssTrueColor.beta = beta }))
            }} />
          </dd>
          <dt>b<sub>0</sub></dt>
          <dd>
            <LogScaleRange value={colorParams.sdssTrueColor.b0} min={0} max={5.e-5} onInput={b0 => {
              setColorParams(produce(colorParams, _ => { _.sdssTrueColor.b0 = b0 }))
            }} />
          </dd>
          <dt> A </dt>
          <dd>
            <LogScaleRange value={colorParams.sdssTrueColor.a} min={0} max={1.e4} onInput={a => {
              setColorParams(produce(colorParams, _ => { _.sdssTrueColor.a = a }))
            }} />
          </dd>
          <dt>bias</dt>
          <dd>
            <LogScaleRange value={colorParams.sdssTrueColor.bias} min={-0.5} max={0.5} a={1.e-8} onInput={bias => {
              setColorParams(produce(colorParams, _ => { _.sdssTrueColor.bias = bias }))
            }} />
          </dd>
        </dl>
        <div>
          {history.join(', ')}
        </div>
      </div>
    </div>
  )
}



function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  let r: number, g: number, b: number

  const i = Math.floor(h * 6)
  const f = h * 6 - i
  const p = v * (1 - s)
  const q = v * (1 - f * s)
  const t = v * (1 - (1 - f) * s)

  switch (i % 6) {
    case 0: r = v, g = t, b = p; break
    case 1: r = q, g = v, b = p; break
    case 2: r = p, g = v, b = t; break
    case 3: r = p, g = q, b = v; break
    case 4: r = t, g = p, b = v; break
    case 5: r = v, g = p, b = q; break
  }

  // @ts-ignore
  return [r, g, b]
}

function randomInRange(min: number, max: number) {
  return (max - min) * Math.random() + min
}
