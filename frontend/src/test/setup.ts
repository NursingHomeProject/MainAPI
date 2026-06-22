import "@testing-library/jest-dom"

// Polyfill window.matchMedia — ausente no jsdom, usado por Radix UI
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Polyfill ResizeObserver — ausente no jsdom
class ResizeObserverPolyfill {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverPolyfill
