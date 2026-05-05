import { ToApp } from '@stellar-globe/app/commTools'
import Koa from 'koa'
import bodyParser from 'koa-bodyparser'
import Router from 'koa-router'
import { BadRequestError, Comm } from './comm'


const app = new Koa()
const router = new Router()


const comms = new Map<string, Comm>()


// GET /healthz
// curl http://localhost:3000/healthz
router.get('/healthz', async (ctx) => {
  ctx.body = {
    status: 'ok',
  }
})


// POST /comms
// curl -X POST -H "Content-Type: application/json" -d '{"id":"123}", "queryId":"456"}' http://localhost:3000/comms
router.post('/comms', async (ctx) => {
  const openMessage: ToApp['Open'] = ctx.request.body as any
  const comm = new Comm(openMessage)
  comms.set(comm.id, comm)
  ctx.body = ''
})


// POST /comms/:id
// curl -X POST -H "Content-Type: application/json" -d '{"type":"Close"}' http://localhost:3000/comms/123
router.post('/comms/:id', async (ctx) => {
  const id = ctx.params.id
  const comm = comms.get(id)
  if (comm === undefined) {
    throw new BadRequestError(`No comm with id: ${id}`, 404)
  }
  comm.onReceiveMessage(ctx.request.body)
  ctx.body = ''
})


// GET /comms/:id/queryResponse/:queryId
// curl http://localhost:3000/comms/123/queryResponse/456
router.get('/comms/:id/queryResponse/:queryId', async (ctx) => {
  const id = ctx.params.id
  const queryId = ctx.params.queryId
  const comm = comms.get(id)
  const response = comm?.getQueryResponse(queryId)
  if (response === undefined) {
    throw new BadRequestError(`No response for queryId: ${queryId}, commId: ${id}`, 404)
  }
  ctx.body = response
})


// GET /comms/:id/messages/first
// curl http://localhost:3000/comms/123/messages/first
router.get('/comms/:id/messages/first', async (ctx) => {
  const id = ctx.params.id
  const comm = comms.get(id)
  if (comm === undefined) {
    throw new BadRequestError(`No comm with id: ${id}`, 404)
  }
  const message = comm.getFirstMessage()
  if (message === undefined) {
    throw new BadRequestError(`No messages for commId: ${id}`, 404)
  }
  ctx.body = message
})

// GET /comms
// curl http://localhost:3000/comms
router.get('/comms', async (ctx) => {
  ctx.body = Array.from(comms.keys())
})


app
  .use(async (ctx, next) => {
    await next()
    console.log(`${ctx.method} ${ctx.url} - ${ctx.status}`)
  })
  .use(undefinedToNullMiddleware)
  .use(bodyParser())
  .use(async (ctx, next) => {
    try {
      await next()
    }
    catch (err) {
      if (err instanceof BadRequestError) {
        ctx.status = 400
        ctx.body = err.message
        console.warn(err.message)
      }
      else {
        throw err
      }
    }
  })
  .use(router.routes())
  .use(router.allowedMethods())


// @ts-ignore
if (import.meta.env.PROD) {
  const port = process.env.MOCKCOMPANY_PORT || 3000
  app.listen(port)
  console.log(`Server running on http://localhost:${port}`)
}


async function undefinedToNullMiddleware(ctx: Koa.ParameterizedContext, next: Koa.Next) {
  await next()
  if (ctx.body && (typeof ctx.body === 'object' || Array.isArray(ctx.body))) {
    ctx.body = JSON.parse(JSON.stringify(ctx.body, (key, value) => {
      if (value === undefined) {
        return null
      }
      return value
    }))
  }
}


export const viteNodeApp = app
