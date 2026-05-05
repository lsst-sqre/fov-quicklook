export class Dummy {
  constructor() {
    const handler: ProxyHandler<this> = {
      get: (target, propKey, receiver) => {
        if (typeof target[propKey as keyof this] === 'undefined') {
          return (..._args: any[]) => {
            // console.log(`Called method "${String(propKey)}" with arguments:`, args)
            return receiver
          }
        }
        return Reflect.get(target, propKey, receiver)
      }
    }
    return new Proxy(this, handler)
  }
}
