type Env = {
  target: 'public' | 'u2k' | 'legacy-archive' | 'internal'
  data: {
    u2k: boolean
    la2016: boolean
    la2020: boolean
    pdr3: boolean
    idr: boolean
  }
}

export function env(): Env {
  const target = String(import.meta.env.VITE_target) as Env['target']
  
  // @ts-ignore
  if (target === 'undefined') {
    throw new Error('env.target is not set')
  }

  return {
    target,
    data: {
      u2k: target === 'u2k',
      la2016: target === 'legacy-archive',
      la2020: target === 'legacy-archive',
      pdr3: target === 'public',
      idr: target === 'internal',
    },
  }
}
