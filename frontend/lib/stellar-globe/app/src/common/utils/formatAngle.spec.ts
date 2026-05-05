// angleFormatter.ts から formatAngleInSexagesimal 関数をインポート
import { formatAngleInSexagesimal } from './formatAngle'

// 角度をラジアンに変換する関数
function deg2rad(degrees: number): number {
  return degrees * Math.PI / 180
}

// Vitestのテストスイートを定義
describe('formatAngleInSexagesimal', () => {
  it('should correctly format angles in degrees', () => {
    const radians = deg2rad(1.146)
    expect(formatAngleInSexagesimal(radians)).toBe('1.146°')
  })

  it('should correctly format angles in minutes and seconds', () => {
    const radians = deg2rad(1 / 60 + 1.08 / 3600)
    expect(formatAngleInSexagesimal(radians)).toBe("1' 1.1''")
  })

  it('should correctly format angles in seconds', () => {
    const radians = deg2rad(0.1944 / 3600)
    expect(formatAngleInSexagesimal(radians)).toBe("0.194''")
  })

  it('should correctly format angles in seconds with three significant figures when less than or equal to 1 second', () => {
    expect(formatAngleInSexagesimal(deg2rad(0.648 / 3600))).toBe("0.648''")
    expect(formatAngleInSexagesimal(deg2rad(0.123 / 3600))).toBe("0.123''")
    expect(formatAngleInSexagesimal(deg2rad(0.0123 / 3600))).toBe("0.0123''")
    expect(formatAngleInSexagesimal(deg2rad(0.00123 / 3600))).toBe("0.00123''")
  })
})