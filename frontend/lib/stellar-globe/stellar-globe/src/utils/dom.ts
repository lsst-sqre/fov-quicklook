let divMemo: HTMLElement | undefined


export function elementSize(cb: (el: HTMLElement) => void) {
  const div = (divMemo ??= createHiddenDiv())
  cb(div)
  document.body.appendChild(div)
  const { clientWidth, clientHeight } = div
  document.body.removeChild(div)
  return { width: clientWidth, height: clientHeight }
}


function createHiddenDiv() {
  const div = document.createElement('div')
  div.style.position = 'fixed'
  div.style.visibility = 'hidden'
  return div
}
