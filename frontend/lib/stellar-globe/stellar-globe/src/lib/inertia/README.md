# Inertia

Inertia simulator for a 1D mass point.

```JavaScript
import { Inertia2D } from './src'
import interact from 'interactjs'
import './style.css'


function main() {
  const el = addNewElement()
  const inertia = new Inertia2D()

  interact(el)
    .on('down', () => {
      inertia.stop()
    }).on('dragend', () => {
      inertia.release()
    }).draggable({
      listeners: {
        move(event) {
          inertia.drag(event.dx, event.dy)
        },
      }
    })

  const refresh = (t: number) => {
    requestAnimationFrame(refresh)
    const { position, moving } = inertia.evolve(t).state
    const { x, y } = position
    el.style.transform = `translate(${x}px, ${y}px)`
    moving ?
      el.classList.add('moving') :
      el.classList.remove('moving')
  }

  requestAnimationFrame(refresh)
}


function addNewElement() {
  const el = document.createElement('div')
  el.className = 'draggable'
  el.style.left = '200px'
  el.style.top = '200px'
  el.addEventListener('selectstart', e => {
    e.preventDefault()
  })
  document.body.appendChild(el)
  return el
}


window.addEventListener('load', main)
```