/**
 * Browser polyfills for Node.js dependencies
 * Required for @polkadot/api and other packages
 */

import { Buffer } from 'buffer';

// Make Buffer available globally for @polkadot/api
if (typeof window !== 'undefined') {
  (window as any).Buffer = Buffer;
  (window as any).global = window;
}

export {};
