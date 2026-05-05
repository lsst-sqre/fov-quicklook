import { DndContext, KeyboardSensor, useDraggable, useSensor, useSensors } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'

import { DragEndEvent } from "@dnd-kit/core/dist/types"
import { restrictToWindowEdges } from '@dnd-kit/modifiers'
import classNames from 'classnames'
import { CSSProperties, ReactNode, RefObject, forwardRef, useCallback, useEffect, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import CSSTransition, { CSSTransitionClassNames } from 'react-transition-group/CSSTransition'
import { useDialogContext } from './Context'
import { Resizable } from './Resizable'
import { PointerSensor } from './dnd'
import { useSeqId } from './hooks'
import styles from './styles.module.scss'
import { CSSPosition, CSSSize, CSSSizeLimit, Origin, PartialSize, Position } from './types'
import { pickXY, position2origin, position2topleft } from './utils'


export type DialogProps = {
  title: ReactNode
  children: ReactNode
  resizable?: boolean | { y?: boolean, x?: boolean }
  positionHint?: CSSPosition
  classNames: ClassNames
  visible?: boolean
  fadeDuration?: number
  fadeClassNames?: CSSTransitionClassNames
  rememberPosition?: boolean
  sizeHint?: CSSSize
  minmaxSize?: CSSSizeLimit
}


type ClassNames = {
  dialog?: string
  titlebar?: string
  content?: string
  active?: string
}


export type DialogHandle = {
  autoResize: () => void
}


export const Dialog = forwardRef<DialogHandle, DialogProps>(function Dialog(props, ref) {
  const [autoResizeTrigger, setAutoSizeTrigger] = useState({})

  useImperativeHandle(ref, () => ({
    autoResize: () => setAutoSizeTrigger({})
  }), [])

  const { portal } = useDialogContext()
  const props2 = { ...props, autoResizeTrigger }

  if (portal) {
    return createPortal(<DialogDraggable {...props2} />, portal)
  }
  else {
    return <DialogDraggable {...props2} />
  }
})


function DialogDraggable(props: DialogProps & { autoResizeTrigger: unknown }) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor),
  )
  const [position, setPosition] = useState<Position | undefined>(undefined)
  const positionAtDragStart = useRef<Position | undefined>()
  const onDragStart = useCallback(({ active: { data } }: DragEndEvent) => {
    const sizeRef: React.RefObject<HTMLDivElement> = data.current?.sizeRef
    const { left, top } = sizeRef.current!.getBoundingClientRect()
    positionAtDragStart.current = { left, top }
  }, [])
  const onDragEnd = useCallback(({ delta }: DragEndEvent) => {
    setPosition(() => {
      if (positionAtDragStart.current) {
        return pickXY(positionAtDragStart.current, ([[xkey, xvalue], [ykey, yvalue]]) => ({
          [xkey]: xvalue + delta.x,
          [ykey]: yvalue + delta.y,
        })) as Position
      }
    })
  }, [])
  return (
    <DndContext
      sensors={sensors}
      onDragStart={(onDragStart)}
      onDragEnd={onDragEnd}
      modifiers={[restrictToWindowEdges]}
    >
      <DnDContent {...{ ...props, }} position={position} setPosition={setPosition} />
    </DndContext>
  )
}


function DnDContent({
  children,
  title,
  classNames: $classNames,
  position,
  positionHint: intrinsicPositionHint,
  sizeHint,
  setPosition,
  visible = true,
  fadeClassNames,
  fadeDuration = 0,
  rememberPosition = false,
  resizable: resizableProp = false,
  minmaxSize,
  autoResizeTrigger,
}: DialogProps & {
  autoResizeTrigger: unknown,
  position: Position | undefined
  setPosition: React.Dispatch<React.SetStateAction<Position | undefined>>
}) {
  const id = useSeqId()
  const zIndex = useZIndex(id)
  const sizeRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState<PartialSize | undefined>(undefined)
  const { raiseDialog, defaultPositionHint, portal } = useDialogContext()
  const positionHint = intrinsicPositionHint ?? defaultPositionHint

  const resizable = useMemo(() => {
    if (typeof resizableProp === 'boolean') {
      return {
        x: resizableProp,
        y: resizableProp,
      }
    }
    return {
      x: !!resizableProp.x,
      y: !!resizableProp.y,
    }
  }, [resizableProp])

  const _origin = useMemo((): Origin => {
    const p = position ?? positionHint
    return p ? position2origin(p) : { x: 'left', y: 'top' }
  }, [position, positionHint])

  const origin = useMemo((): Origin => ({
    x: _origin.x,
    y: _origin.y,
  }), [_origin.x, _origin.y])

  usePositionRegistry({
    id,
    position,
    setPosition,
    positionHint,
    sizeRef,
    visible,
    origin,
  })

  const { setNodeRef, listeners, transform, attributes, setActivatorNodeRef, active } = useDraggable({
    id: 'dialog',
    data: { sizeRef },
  })

  const maxHeight = useMemo(() => {
    const { height } = (portal ?? document.body).getBoundingClientRect()
    return height
  }, [portal])

  const positionStyle = useMemo<CSSProperties>(
    () => ({
      ...(
        position
          ? pickXY(position, ([[xkey, xvalue], [ykey, yvalue]]) => ({
            [xkey]: `${xvalue}px`,
            [ykey]: `${yvalue}px`,
          }))
          : positionHint
      ),
      transform: CSS.Translate.toString(transform),
      position: 'fixed',
      zIndex,
    }),
    [position, positionHint, transform, zIndex],
  )

  const sizeStyle: CSSProperties = useMemo(() => {
    const overwrite: {
      width?: string
      height?: string
    } = {}
    if (size?.width !== undefined) {
      overwrite.width = `${size.width}px`
    }
    if (size?.height !== undefined) {
      overwrite.height = `${size.height}px`
    }
    return {
      ...sizeHint,
      ...overwrite,
      maxHeight: maxHeight - 16,
      ...minmaxSize,
    }
  }, [maxHeight, minmaxSize, size, sizeHint])

  const onExited = useCallback(() => {
    if (!rememberPosition) {
      setPosition(undefined)
    }
  }, [rememberPosition, setPosition])

  const transitionRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    setSize(undefined)
  }, [autoResizeTrigger])

  return (
    <CSSTransition
      timeout={fadeDuration}
      classNames={fadeClassNames}
      mountOnEnter
      onExited={onExited}
      in={visible}
      nodeRef={transitionRef}
      appear
    >{state => (
      <div
        className={styles.position}
        ref={sizeRef}
        style={{
          ...positionStyle,
          display: (state === 'exited' && !visible) ? 'none' : 'block',
        }}
      >
        <Resizable
          enabled={resizable}
          container={sizeRef}
          position={position}
          setPosition={setPosition}
          size={size}
          setSize={setSize}
          origin={origin}
        >
          <div ref={transitionRef} className={styles.transitionWrapper}>
            <div
              className={classNames(styles.dialog, $classNames.dialog, active && $classNames.active)}
              ref={setNodeRef}
              style={sizeStyle}
              onMouseDown={() => raiseDialog(id)}
            >
              <div
                className={classNames(styles.titlebar, $classNames.titlebar)}
                ref={setActivatorNodeRef}
                {...listeners}
                {...attributes}
              >
                {title}
              </div>
              <div className={classNames(styles.content, $classNames.content)} >
                {children}
              </div>
            </div >
          </div>
        </Resizable>
      </div >
    )}
    </CSSTransition>
  )
}



type PositionRegistryProps = {
  id: number
  sizeRef: RefObject<HTMLDivElement>
  visible: boolean
  position: Position | undefined
  setPosition: React.Dispatch<React.SetStateAction<Position | undefined>>
  positionHint: CSSPosition | undefined
  origin: Origin
}

function usePositionRegistry({
  id,
  position,
  setPosition,
  positionHint,
  sizeRef,
  visible,
  origin,
}: PositionRegistryProps) {
  const { dialogs, nextPosition, rearrangeTrigger } = useDialogContext()

  const positionBeforeRearrange = useRef<Position>()

  useLayoutEffect(
    () => {
      const el = sizeRef.current
      if (visible && el && position) {
        positionBeforeRearrange.current = el.getBoundingClientRect()
        setPosition(undefined)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rearrangeTrigger, setPosition, sizeRef],
  )

  useLayoutEffect(() => {
    const el = sizeRef.current
    if (el && visible) {
      // 初回commit時などpositionが未指定の状態ではpositionHintによって配置されている
      const { width, height, left, top } = sizeRef.current!.getBoundingClientRect()
      if (position) {
        dialogs.set(id, { rect: { left, top, width, height } })
      }
      else {
        const newPosition = nextPosition(
          { width, height },
          {
            positionHint: positionHint && { left, top },
            origin,
          },
        )
        const newTopLeft = position2topleft(newPosition, { width, height })
        dialogs.set(id, { rect: { ...newTopLeft, width, height } })
        setPosition(newPosition)
        if (positionBeforeRearrange.current) {
          const p0 = position2topleft(positionBeforeRearrange.current, { width, height })
          const p1 = newTopLeft
          const dx = p0.left - p1.left
          const dy = p0.top - p1.top
          sizeRef.current.animate?.([
            { transform: `translate(${dx}px, ${dy}px)` },
            { transform: `translate(0, 0)`, },
          ], {
            duration: 200,
            easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
          })
          positionBeforeRearrange.current = undefined
        }
      }
      return () => {
        dialogs.delete(id)
      }
    }
    else {
      dialogs.delete(id)
    }
  }, [dialogs, id, nextPosition, origin, position, positionHint, setPosition, sizeRef, visible])

  useEffect(() => {
    const el = sizeRef.current
    if (el && visible) {
      const resizeObserver = new ResizeObserver(() => {
        const { width, height, left, top } = el.getBoundingClientRect()
        dialogs.set(id, { rect: { left, top, width, height } })
      })
      resizeObserver.observe(el)
      return () => {
        resizeObserver.unobserve(el)
      }
    } else {
      dialogs.delete(id)
    }
  }, [dialogs, id, sizeRef, visible])
}


function useZIndex(id: number) {
  const { zIndex } = useDialogContext()
  if (!zIndex.has(id)) {
    zIndex.set(id, zIndex.size)
  }
  useEffect(() => {
    return () => {
      zIndex.delete(id)
    }
  }, [id, zIndex])
  return zIndex.get(id)!
}
