import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react"
import { makeStateHistory } from "./stateHistory"


type StateHistory = ReturnType<typeof makeStateHistory>


type Props = {
  stateHistory: ReturnType<typeof makeStateHistory>
  children: ReactNode
}


const Context = createContext<StateHistory | undefined>(undefined)


export function StateHistoryProvider({ children, stateHistory }: Props) {
  return (
    <Context.Provider value={stateHistory}>
      {children}
    </Context.Provider>
  )
}


export function useStateHistory() {
  const stateHistory = useContext(Context)
  if (stateHistory === undefined) {
    throw new Error(`use of useStateHistory outside its provider`)
  }

  const makeState = useCallback(() => ({
    records: stateHistory.records,
    currentIndex: stateHistory.currentIndex(),
  }), [stateHistory])

  const [history, setHistory] = useState(makeState)

  useEffect(() => {
    const off = stateHistory.onChange(() => {
      setHistory(makeState())
    })
    return off
  }, [makeState, stateHistory])

  return history
}
