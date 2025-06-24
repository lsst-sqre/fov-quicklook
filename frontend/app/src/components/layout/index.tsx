
export function FlexiblePadding() {
  return <div style={{ flexGrow: 1 }}></div>
}

export function WindowCenter({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div style={{ display: 'flex', flexGrow: 1, justifyContent: 'center', alignItems: 'center' }}>
        {children}
      </div>
    </div>
  )
}
