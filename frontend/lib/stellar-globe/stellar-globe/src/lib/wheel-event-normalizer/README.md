# Wheel Event Normalizer

```JavaScript
import './style.css'
import { realEventDetector } from '../src'
import { HistoryCanvas } from './HistoryCanvas'
import { WheelEventNormalizer } from '../src/WheelEventNormalizer'
import { Inertia } from '@stellar-globe/inertia'


window.addEventListener('load', () => {
  setupRealEventDetector()
  setupNormalizer()
})


function setupRealEventDetector() {
  const trackpad: HTMLElement = document.querySelector('.trackpad')!
  const isRealEvent = realEventDetector()
  const history = new HistoryCanvas(document.querySelector('#real-event-history')!)
  const dtHistory = new HistoryCanvas(document.querySelector('#dt-history')!)

  let lastTimestamp: number | undefined
  trackpad.addEventListener('wheel', (e: WheelEvent) => {
    const dt = e.timeStamp - (lastTimestamp ?? e.timeStamp)
    lastTimestamp = e.timeStamp
    dtHistory.push([dt, false])

    e.preventDefault()
    history.push([e.deltaY, isRealEvent(e)])
  })
}


function setupNormalizer() {
  const trackpad: HTMLElement = document.querySelector('.trackpad')!
  const history = new HistoryCanvas(document.querySelector('#wheel-event-normalizer-history')!)

  const wheelEventNormalizer = new WheelEventNormalizer((e) => {
    history.push([e.deltaY, false])
  }, {
    on: {
      start() {
        console.log('start')
      },
      end() {
        console.log('end')
      },
    },
    inertia: new Inertia({
      gamma0: 1.e-2,
    })
  })

  trackpad.addEventListener('wheel', (e: WheelEvent) => {
    e.preventDefault()
    wheelEventNormalizer.feedRawEvent(e)
  })
}
```