export {}

declare global {
  interface EthereumProvider {
    request<T = unknown>(args: { method: string; params?: unknown[] }): Promise<T>
    on?(event: string, handler: (...args: unknown[]) => void): void
    removeListener?(event: string, handler: (...args: unknown[]) => void): void
  }

  interface Window {
    ethereum?: EthereumProvider
  }
}
