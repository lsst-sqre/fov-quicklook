import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { CSSTransition } from "react-transition-group"
import { useAppDispatch, useAppSelector } from "../../../store/hooks"
import { indicatorSlice } from "../indicatorSlice"
import styles from './styles.module.scss'
import { commonSlice } from "../../common/commonSlice"

export const Indicator = memo(() => {
  const dispatch = useAppDispatch()
  const [show, setShow] = useState(false)
  const coord = useAppSelector(indicatorSlice.selectors.coord)
  const angleUnit = useAppSelector(state => state.common.angleUnit)
  const coordString = useMemo(() => {
    if (Number.isNaN(coord.a.rad)) {
      return '-'
    }

    switch (angleUnit) {
      case 'degree': {
        return `&alpha;=${coord.a.deg.toFixed(4)}&deg; &delta;=${coord.d.deg.toFixed(4)}&deg;`
      }
      case 'radian':
        return `&alpha;=${coord.a.rad.toFixed(4)} rad &delta;=${coord.d.rad.toFixed(4)} rad`
      case 'sexadecimal': {
        const { a, d } = coord.toString()
        return `&alpha;=${a} &delta;=${d}`
      }
    }
  }, [coord, angleUnit])

  const fovy = useAppSelector(state => state.camera.params.fovy)

  const fovyString = useMemo(() => {
    switch (angleUnit) {
      case 'degree': {
        return `FoV=${fovy.toFixed(4)}&deg;`
      }
      case 'radian':
        return `FoV=${fovy} rad`
      case 'sexadecimal': {
        return `FoV=${fovy} &deg;`
      }
    }
  }, [fovy, angleUnit])

  const setTimeout = useMakeSetTimeout()

  useEffect(() => {
    if (!Number.isNaN(coord.a.rad)) {
      setShow(true)
      setTimeout(() => {
        setShow(false)
      }, 2000)
    }
  }, [coord, setTimeout])

  const ndoeRef = useRef<HTMLDivElement>(null)
  const toggleUnit = useCallback(() => {
    dispatch(commonSlice.actions.unitToggled())
  }, [dispatch])

  return (
    <CSSTransition
      in={show} nodeRef={ndoeRef} timeout={500} unmountOnExit
      classNames={{
        enter: styles.fadeEnter,
        enterActive: styles.fadeEnterActive,
        exit: styles.fadeExit,
        exitActive: styles.fadeExitActive,
      }}
    >
      <div className={styles.indicator} ref={ndoeRef} onClick={toggleUnit} >
        <span dangerouslySetInnerHTML={{ __html: coordString }} />
        {/* <span dangerouslySetInnerHTML={{ __html: fovyString }} /> */}
      </div>
    </CSSTransition>
  )
})


// setTimeoutのような関数を返す。
// しかしただのsetTimeoutとは違い、unmountされた後は何もしない。
function useMakeSetTimeout() {
  type TimeoutId = ReturnType<typeof setTimeout>
  const ids = useRef<TimeoutId[]>([])

  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      for (const id of ids.current) {
        clearTimeout(id)
      }
    }
  })

  return useCallback((callback: () => void, ms: number) => {
    const id = setTimeout(callback, ms)
    ids.current.push(id)
    return id
  }, [])
}
