import { V4 } from "@stellar-globe/stellar-globe"

type CustomErrorClass = new (message?: string) => Error


export function hexToRgba(hexColor: string, ErrorClass: CustomErrorClass = Error): V4 {
  if (!hexColor.startsWith('#')) {
    throw new ErrorClass("Invalid format: Hex color should start with '#'")
  }

  const hex = hexColor.substring(1)
  let r: number, g: number, b: number, a: number = 1

  try {
    switch (hex.length) {
      case 3: // RGB format
        r = parseInt(hex.charAt(0) + hex.charAt(0), 16) / 255
        g = parseInt(hex.charAt(1) + hex.charAt(1), 16) / 255
        b = parseInt(hex.charAt(2) + hex.charAt(2), 16) / 255
        break
      case 4: // RGBA format
        r = parseInt(hex.charAt(0) + hex.charAt(0), 16) / 255
        g = parseInt(hex.charAt(1) + hex.charAt(1), 16) / 255
        b = parseInt(hex.charAt(2) + hex.charAt(2), 16) / 255
        a = parseInt(hex.charAt(3) + hex.charAt(3), 16) / 255
        break
      case 6: // RRGGBB format
        r = parseInt(hex.substring(0, 2), 16) / 255
        g = parseInt(hex.substring(2, 4), 16) / 255
        b = parseInt(hex.substring(4, 6), 16) / 255
        break
      case 8: // RRGGBBAA format
        r = parseInt(hex.substring(0, 2), 16) / 255
        g = parseInt(hex.substring(2, 4), 16) / 255
        b = parseInt(hex.substring(4, 6), 16) / 255
        a = parseInt(hex.substring(6, 8), 16) / 255
        break
      default:
        throw new ErrorClass("Invalid format: Hex color should be #RGB, #RGBA, #RRGGBB, or #RRGGBBAA")
    }
  } catch (error) {
    throw new ErrorClass("Invalid hex color value")
  }

  if (isNaN(r) || isNaN(g) || isNaN(b) || isNaN(a)) {
    throw new ErrorClass("Invalid hex color value")
  }

  return [r, g, b, a]
}
