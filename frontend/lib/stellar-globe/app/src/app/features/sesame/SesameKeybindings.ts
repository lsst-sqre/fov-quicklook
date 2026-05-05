import { SkyCoord, angle, easing } from "@stellar-globe/stellar-globe"
import { useMemo } from "react"
import { useBlockUI } from "../../../common/components/Modal"
import { useAsyncPrompt } from "../../../common/components/Modal/useAsyncPrompt"
import { Keybind } from "../../../common/components/keybindings"
import { useAppContext } from "../../context"


export function useSesameKeybindings() {
  const blockUI = useBlockUI()
  const { globeHandle } = useAppContext()
  const prompt = useAsyncPrompt()

  return useMemo(() => {
    const inputSesameQuery: Keybind = {
      action: async () => {
        try {
          await blockUI(async () => {
            const query = await prompt('Object Name ?')
            if (query) {
              const coord = await resolveObjectNameBySesame(query)
              globeHandle.current!().camera.jumpTo({ fovy: angle.amin2rad(10) }, { coord, duration: 2000, easingFunction: easing.slowStartStop4 })
            }
          })
        }
        catch (e) {
          alert(e)
        }
      },
      shortcut: 'Shift+Ctrl+S',
    }
    return {
      inputSesameQuery,
    }
  }, [blockUI, globeHandle, prompt])
}


async function resolveObjectNameBySesame(query: string) {
  const url = `//cds.unistra.fr/cgi-bin/nph-sesame/A?${encodeURIComponent(query)}`
  const result = await (await fetch(url)).text()
  // %J 10.68470833 +41.26875000 = 00 42 44.330  +41 16 07.50 
  const match = result.match(/^%J\s+(\d.*?)=/m)
  if (match) {
    return SkyCoord.parse(match[1])
  }
  else {
    throw new Error(`Object not found: ${query}`)
  }
}
