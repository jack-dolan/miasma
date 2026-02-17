import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { lookupApi } from '../services/api'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('lookupApi', () => {
  describe('search', () => {
    it('should be a function', () => {
      expect(typeof lookupApi.search).toBe('function')
    })
  })

  describe('getSources', () => {
    it('should be a function', () => {
      expect(typeof lookupApi.getSources).toBe('function')
    })
  })

  describe('getResults', () => {
    it('should be a function', () => {
      expect(typeof lookupApi.getResults).toBe('function')
    })
  })

  describe('getResult', () => {
    it('should be a function', () => {
      expect(typeof lookupApi.getResult).toBe('function')
    })
  })

  describe('deleteResult', () => {
    it('should be a function', () => {
      expect(typeof lookupApi.deleteResult).toBe('function')
    })
  })
})
