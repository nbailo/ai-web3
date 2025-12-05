import { getAddress } from 'ethers';

export function normalizeAddress(value: string): string {
  return getAddress(value);
}

export function isSameAddress(a: string, b: string): boolean {
  return normalizeAddress(a) === normalizeAddress(b);
}

export function sortAddresses(a: string, b: string): [string, string] {
  const na = normalizeAddress(a);
  const nb = normalizeAddress(b);
  return na.toLowerCase() < nb.toLowerCase() ? [na, nb] : [nb, na];
}

