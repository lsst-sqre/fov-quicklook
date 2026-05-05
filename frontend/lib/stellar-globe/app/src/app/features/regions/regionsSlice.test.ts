import { SkyCoord } from '@stellar-globe/stellar-globe'
import { test } from 'vitest'
import { PathRegion, regionCenterAndFov } from './regionsSlice'


test("returns center and fov for an empty region", () => {
  const region: PathRegion = {
    id: '1',
    name: 'test',
    showLabel: true,
    type: 'Path',
    visible: true,
    color: [0, 0, 0, 0],
    paths: [],

  }
  const result = regionCenterAndFov(region)
  expect(result.center).toEqual(SkyCoord.fromRad(0, 0))
  expect(result.fov).toBe(1)
})


test("returns center and fov for a region with paths", () => {
  const region: PathRegion = {
    paths: [
      {
        close: false,
        joint: 'MITER',
        points: [
          { position: [1, 0, 0], color: [0, 0, 0, 0], size: 0 },
          { position: [0, 0, 1], color: [0, 0, 0, 0], size: 0 },
        ]
      },
    ],
    color: [0, 0, 0, 0],
    id: '1',
    name: 'test',
    showLabel: true,
    type: 'Path',
    visible: true,
  }
  const result = regionCenterAndFov(region)
  expect(result.center).toEqual(SkyCoord.fromRad(0, Math.PI / 4))
  expect(result.fov).toBe(0.7071067811865476)
})
