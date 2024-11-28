import { DarkDialog, DialogContext, DialogContextHandle } from '@stellar-globe/react-draggable-dialog'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CSSSize } from '../../../../../lib/stellar-globe/react-draggable-dialog/types/types'


export function Example() {
  const [count, setCount] = useState(10)
  const dialogContext = useRef<DialogContextHandle>(null)

  const defaultPositionHint = useMemo(() => ({
    right: 8,
    bottom: 8,
  }), [])

  return (
    <DialogContext ref={dialogContext} defaultPositionHint={defaultPositionHint} >
      <RightBottom />
      <button onClick={() => setCount(_ => _ + 1)}>+</button>
      <button onClick={() => setCount(_ => 0)}>Clear</button>
      <button onClick={() => dialogContext.current?.rearrange()}>Rearrange</button>
      {Array.from({ length: count }).map((_, i) => (
        <MyDialog key={i} />
      ))}
    </DialogContext>
  )
}


function MyDialog() {
  const [visible, setVisible] = useState(true)
  const [resizable,] = useState(() => ({
    x: true,
    y: true,

    // x: Math.random() < 0.5,
    // y: Math.random() < 0.5,
  }))

  const autoResize = useMemo(() => resizable.x || resizable.y, [resizable])

  useEffect(() => {
    if (!visible) {
      setTimeout(() => {
        setVisible(true)
      }, 2000)
    }
  }, [visible])

  const onClick = useCallback(() => {
    setVisible(false)
  }, [])

  const text = useMemo(() => generateRandomSentence(1, 8, 20), [])
  const sizeHint = useMemo<CSSSize>(() => ({
    width: 100 + Math.floor(200 * Math.random()),
  }), [])

  return (
    <DarkDialog
      title={'hello'}
      visible={visible}
      sizeHint={sizeHint}
      onCloseButtonClick={onClick}
      resizable={resizable}
      minmaxSize={{
        minWidth: '80px',
        minHeight: '80px',
        maxWidth: '300px',
        maxHeight: '50vh',
      }}
      resizeButton
    >
      {text}
      <code><pre>{JSON.stringify(resizable)}</pre></code>
    </DarkDialog >
  )
}


function RightBottom() {
  const [text, setText] = useState('')

  useEffect(() => {
    const interval = setInterval(() => {
      setText(generateRandomSentence(1, 8, 10))
    }, 1000)
    return () => {
      clearInterval(interval)
    }
  }, [])

  return (
    <DarkDialog
      title="RightBottom"
      positionHint={{ right: '10px', bottom: '10px' }}
      sizeHint={{ width: '200px' }}
    >
      {text}
    </DarkDialog>
  )
}


function generateRandomString(length: number): string {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
  let result = ''
  const charactersLength = characters.length
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength))
  }
  return result
}

function generateRandomSentence(minWordLength: number, maxWordLength: number, numberOfWords: number): string {
  const sentence: string[] = []
  for (let i = 0; i < numberOfWords; i++) {
    const wordLength = Math.floor(Math.random() * (maxWordLength - minWordLength + 1)) + minWordLength
    sentence.push(generateRandomString(wordLength))
  }
  return sentence.join(' ')
}
