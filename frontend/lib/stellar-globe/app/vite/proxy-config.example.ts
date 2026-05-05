import { ProxyOptions } from 'vite'

const auth = 'user:password'

export const proxyOptions: Record<string, ProxyOptions> = {
  '/data/s23b_wide/': {
    target: 'https://storage.mtk.nao.ac.jp',
    secure: false,
    changeOrigin: true,
    rewrite: path => path.replace(/^\/path\//, '/super-secret-path/'),
      auth,
  },
}
