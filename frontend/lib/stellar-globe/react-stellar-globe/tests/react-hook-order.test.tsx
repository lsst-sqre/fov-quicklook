import "@testing-library/jest-dom/vitest"
import { render } from '@testing-library/react'
import React, { useEffect } from 'react'
import { expect, test } from 'vitest'


const calls: string[] = []


function Parent() {
    calls.push('Parent.render')

    useEffect(() => {
        calls.push('Parent.useEffect')
        return () => {
            calls.push('Parent.useEffect.cleanup')
        }
    }, [])

    return <Child />
}

function Child() {
    calls.push('Child.render')

    useEffect(() => {
        calls.push('Child.useEffect')
        return () => {
            calls.push('Child.useEffect.cleanup')
        }
    }, [])

    return <div>Child</div>
}


test('hook order', () => {
    calls.splice(0)
    const { unmount } = render(<Parent />)
    expect(calls).toEqual(['Parent.render', 'Child.render', 'Child.useEffect', 'Parent.useEffect'])
    calls.splice(0)
    unmount()
    expect(calls).toEqual(['Parent.useEffect.cleanup', 'Child.useEffect.cleanup'])
})
