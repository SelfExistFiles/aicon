/**
 * @vitest-environment jsdom
 */

import { describe, expect, it } from 'vitest'
import { shouldLogoutOnCurrentUserError } from '@/stores/auth'

describe('auth session error handling', () => {
  it('logs out only for 401 responses', () => {
    expect(
      shouldLogoutOnCurrentUserError({
        response: { status: 401 }
      })
    ).toBe(true)

    expect(
      shouldLogoutOnCurrentUserError({
        response: { status: 500 }
      })
    ).toBe(false)

    expect(shouldLogoutOnCurrentUserError(new Error('network'))).toBe(false)
  })
})
