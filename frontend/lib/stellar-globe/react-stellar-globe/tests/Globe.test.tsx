import { Globe, Layer } from '@stellar-globe/stellar-globe'
import '@testing-library/jest-dom/vitest'
import { render, renderHook } from '@testing-library/react'
import React, { useRef } from 'react'
import { describe, expect, test } from 'vitest'
import { makePureLayerComponent } from '../src/GlobeContext'
import { Globe$, GlobeHandle } from '../src/Globe'



test('<Globe$ /> does not throw any error', () => {
  render(<Globe$ jsdomTest />)
})


class LogLayer extends Layer {
  constructor(globe: Globe, log: string[], postfix = '') {
    super(globe)
    log.push(`DummyLayer.constructor${postfix}`)
    this.onRelease(() => {
      log.push(`DummyLayer.release${postfix}`)
    })
  }
}


type LogLayerProps = {
  log: string[]
  postfix?: string
  visible?: boolean
}


const LogLayer$ = makePureLayerComponent<LogLayerProps>(
  (globe, { log, postfix }) => new LogLayer(globe, log, postfix),
  'visible',
)


describe('Mount & Unmount', () => {
  test('Globe & Layer', () => {
    const log: string[] = []

    const onInit = () => {
      log.push('Globe.onInit')
    }

    const onRelease = () => {
      log.push('Globe.onRelease')
    }

    const { rerender } = render(
      <Globe$ jsdomTest onInit={onInit} onRelease={onRelease}>
        <LogLayer$ log={log} />
      </Globe$>
    )
    expect(log).toEqual(["Globe.onInit", "DummyLayer.constructor"])

    log.splice(0)
    rerender(
      <Globe$ jsdomTest onInit={onInit} onRelease={onRelease}>
        <LogLayer$ log={log} />
      </Globe$>
    )
    expect(log).toEqual([])

    log.splice(0)
    rerender(<></>)
    expect(log).toEqual(['DummyLayer.release', 'Globe.onRelease'])

    log.splice(0)
    rerender(
      <Globe$ jsdomTest onInit={onInit} onRelease={onRelease}>
      </Globe$>
    )
    rerender(
      <Globe$ jsdomTest onInit={onInit} onRelease={onRelease}>
        <LogLayer$ log={log} />
      </Globe$>
    )
    expect(log).toEqual(['Globe.onInit', 'DummyLayer.constructor'])

    log.splice(0)
    rerender(
      <Globe$ jsdomTest onInit={onInit} onRelease={onRelease}>
      </Globe$>
    )
    expect(log).toEqual(['DummyLayer.release'])

    log.splice(0)
    rerender(<></>)
    expect(log).toEqual(['Globe.onRelease'])
  })
})



describe('makePureLayerComponent', () => {
  test('同じpropsでのrenderではLayerは保持される', () => {
    const log: string[] = []
    const { rerender } = render(
      <Globe$ jsdomTest>
        <LogLayer$ log={log} postfix='_1' />
      </Globe$>
    )
    expect(log).toEqual(["DummyLayer.constructor_1"])
    rerender(
      <Globe$ jsdomTest>
        <LogLayer$ log={log} postfix='_1' />
      </Globe$>
    )
    expect(log).toEqual(["DummyLayer.constructor_1"])
  })

  test('propsの変化でLayerが作り直される', () => {
    const log: string[] = []
    const { rerender } = render(
      <Globe$ jsdomTest>
        <LogLayer$ log={log} postfix='_1' />
      </Globe$>
    )
    expect(log).toEqual(["DummyLayer.constructor_1"])
    log.splice(0)
    rerender(
      <Globe$ jsdomTest>
        <LogLayer$ log={log} postfix='_2' />
      </Globe$>
    )
    expect(log).toEqual(["DummyLayer.release_1", "DummyLayer.constructor_2"])
  })
})


class NumberedLayer extends Layer {
  constructor(globe: Globe, readonly n: number) {
    super(globe)
  }
}


const NumberedLayer$ = makePureLayerComponent<
  { n: number, visible?: boolean }
>((globe, { n }) => new NumberedLayer(globe, n), 'visible')


test('ref', () => {
  const { result: { current: ref } } = renderHook(() => useRef<GlobeHandle>(null))

  render(
    <Globe$ jsdomTest ref={ref}></Globe$>
  )

  expect(ref.current).toBeTruthy()
  expect(ref.current!()).toBeInstanceOf(Globe)
})


describe('Layer order', () => {
  const { result: { current: globeRef } } = renderHook(() => useRef<GlobeHandle>(null))

  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  const allLayers: () => Layer[] = () => globeRef.current!().layers
  const layers = () => allLayers().filter(l => l instanceof NumberedLayer) as NumberedLayer[]

  const { rerender } = render(
    <Globe$ ref={globeRef} jsdomTest>
      <NumberedLayer$ key={1} n={1} />
      <NumberedLayer$ key={2} n={2} />
      <NumberedLayer$ key={3} n={3} />
    </Globe$>
  )

  test('properly sorted', () => {
    expect(globeRef.current).toBeTruthy()
    expect(layers().map(l => l.n)).toEqual([1, 2, 3])
  })

  test('増減なし、key付き、順番入れ替え', () => {
    rerender(
      <Globe$ ref={globeRef} jsdomTest>
        <NumberedLayer$ key={3} n={3} />
        <NumberedLayer$ key={2} n={2} />
        <NumberedLayer$ key={1} n={1} />
      </Globe$>
    )
    expect(layers().map(l => l.n)).toEqual([3, 2, 1])
  })

  test('追加', () => {
    rerender(
      <Globe$ ref={globeRef} jsdomTest>
        <NumberedLayer$ key={4} n={4} />
        <NumberedLayer$ key={3} n={3} />
        <NumberedLayer$ key={2} n={2} />
        <NumberedLayer$ key={1} n={1} />
      </Globe$>
    )
    expect(layers().map(l => l.n)).toEqual([4, 3, 2, 1])
  })
})
