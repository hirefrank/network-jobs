import { describe, expect, it } from 'bun:test'

import worker from './index'

describe('jobs-api sunset worker', () => {
  it('returns 410 JSON for advisor skill paths', async () => {
    const response = await worker.fetch(
      new Request('https://jobs.hirefrank.com/hirefrank/advisor.json', {
        headers: { Accept: '*/*' },
      }),
    )
    expect(response.status).toBe(410)
    const body = await response.json()
    expect(body.retired).toBe(true)
    expect(body.install).toContain('network-jobs')
  })

  it('returns HTML for browser Accept', async () => {
    const response = await worker.fetch(
      new Request('https://jobs.hirefrank.com/', {
        headers: { Accept: 'text/html' },
      }),
    )
    expect(response.status).toBe(200)
    const text = await response.text()
    expect(text).toContain('Network Jobs has moved')
  })
})
