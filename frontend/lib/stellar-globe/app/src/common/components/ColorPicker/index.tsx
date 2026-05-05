import { flip, useClick, useDismiss, useFloating, useInteractions } from '@floating-ui/react'
import { V3, V4 } from "@stellar-globe/stellar-globe"
import classNames from 'classnames'
import { Fragment, ReactNode, memo, useRef, useState } from "react"
import { RgbColor, RgbColorPicker, RgbaColor, RgbaColorPicker } from 'react-colorful'
import { CSSTransition } from 'react-transition-group'
import styles from './styles.module.scss'


type Props<Color extends V3 | V4> = {
  color: Color
  onChange: (newColor: Color) => void
}


function Pallete({
  renderPalette,
  renderTrigger,
}: {
  renderTrigger: ReactNode,
  renderPalette: ReactNode,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { refs, floatingStyles, context } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    middleware: [flip()],
    placement: 'bottom-start',
  })
  const click = useClick(context)
  const dismiss = useDismiss(context)
  const { getReferenceProps, getFloatingProps } = useInteractions([click, dismiss])
  const nodeRef = useRef(null)

  return (
    <Fragment>
      <div style={{ display: 'inline-block' }} {...getReferenceProps()} ref={refs.setReference}>
        {renderTrigger}
      </div>
      <CSSTransition
        in={isOpen}
        timeout={400}
        mountOnEnter
        unmountOnExit
        nodeRef={nodeRef}
        classNames={{
          enter: styles.fadeEnter,
          enterActive: styles.fadeEnterActive,
          exit: styles.fadeExit,
          exitActive: styles.fadeExitActive,
        }}
      >
        <div ref={refs.setFloating} style={floatingStyles} {...getFloatingProps()}>
          <div ref={nodeRef} className={styles.wrapper}>
            {renderPalette}
          </div>
        </div>
      </CSSTransition>
    </Fragment >
  )
}


export const ColorPickerRgb = memo(({ color, onChange }: Props<V3>) => {
  const rgb = v3ToRgb(color)
  const { r, g, b } = rgb
  return (
    <Pallete
      renderTrigger={
        <CheckeredPatternBackground className={styles.toggleButton} >
          <div
            style={{
              height: '100%',
              flexGrow: 1,
              backgroundColor: `rgb(${r}, ${g}, ${b})`
            }}
          />
        </CheckeredPatternBackground>
      }
      renderPalette={
        <RgbColorPicker color={v3ToRgb(color)} onChange={newRgb => {
          onChange(rgbaToV3(newRgb))
        }} />
      }
    />
  )
})


export const ColorPickerRgba = memo(({ color, onChange }: Props<V4>) => {
  const rgba = v4ToRgba(color)
  const { r, g, b, a } = rgba
  return (
    <Pallete
      renderTrigger={
        <CheckeredPatternBackground
          className={styles.toggleButton}
        >
          <div
            style={{
              height: '100%',
              flexGrow: 1,
              backgroundColor: `rgba(${r}, ${g}, ${b}, ${a})`
            }}
          />
        </CheckeredPatternBackground>
      }
      renderPalette={
        <RgbaColorPicker color={v4ToRgba(color)} onChange={newRgba => {
          onChange(rgbaToV4(newRgba))
        }} />
      }
    />
  )
})


function CheckeredPatternBackground({ children, className }: { children: ReactNode, className?: string }) {
  return (
    <button className={classNames(styles.checkeredPattern, className)}>
      {children}
    </button>
  )
}


function v3ToRgb(v3: V3): RgbColor {
  const [r, g, b] = v3
  return {
    r: 255 * r,
    g: 255 * g,
    b: 255 * b,
  }
}

function rgbaToV3(rgb: RgbColor): V3 {
  const { r, g, b } = rgb
  return [
    r / 255,
    g / 255,
    b / 255,
  ]
}

function v4ToRgba(v4: V4): RgbaColor {
  const [r, g, b, a] = v4
  return {
    r: 255 * r,
    g: 255 * g,
    b: 255 * b,
    a,
  }
}

function rgbaToV4(rgba: RgbaColor): V4 {
  const { r, g, b, a } = rgba
  return [
    r / 255,
    g / 255,
    b / 255,
    a,
  ]
}
