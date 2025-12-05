import { sortAddresses } from './addresses';

export interface CanonicalPair {
  token0: string;
  token1: string;
  isSellTokenToken0: boolean;
}

export function toCanonicalPair(sellToken: string, buyToken: string): CanonicalPair {
  const [token0, token1] = sortAddresses(sellToken, buyToken);
  return {
    token0,
    token1,
    isSellTokenToken0: token0.toLowerCase() === sellToken.toLowerCase(),
  };
}

