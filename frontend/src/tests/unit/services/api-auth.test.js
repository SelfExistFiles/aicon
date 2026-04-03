/**
 * @vitest-environment jsdom
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      patch: vi.fn()
    }))
  }
}))

vi.mock('@/router', () => ({
  default: {
    push: vi.fn(),
    currentRoute: {
      value: {
        fullPath: '/projects'
      }
    }
  }
}))

describe('api auth handling helpers', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('forces logout for session-check endpoints returning 401', async () => {
    const { shouldForceLogoutOnUnauthorized } = await import('@/services/api')

    expect(
      shouldForceLogoutOnUnauthorized({
        response: { status: 401 },
        config: { url: '/users/me' }
      })
    ).toBe(true)

    expect(
      shouldForceLogoutOnUnauthorized({
        response: { status: 401 },
        config: { url: '/auth/verify-token' }
      })
    ).toBe(true)
  })

  it('does not force logout for login failures or unrelated 401s', async () => {
    const { shouldForceLogoutOnUnauthorized } = await import('@/services/api')

    expect(
      shouldForceLogoutOnUnauthorized({
        response: { status: 401 },
        config: { url: '/auth/login' }
      })
    ).toBe(false)

    expect(
      shouldForceLogoutOnUnauthorized({
        response: { status: 401 },
        config: { url: '/projects' }
      })
    ).toBe(false)
  })

  it('does not force logout for non-401 responses', async () => {
    const { shouldForceLogoutOnUnauthorized } = await import('@/services/api')

    expect(
      shouldForceLogoutOnUnauthorized({
        response: { status: 500 },
        config: { url: '/users/me' }
      })
    ).toBe(false)
  })
})
