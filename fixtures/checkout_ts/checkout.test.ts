import { expect, test } from 'vitest';
import { canSubmit } from './checkout';
test('R06 prevents duplicate submissions',()=>expect(canSubmit(true,1)).toBe(false));
test('R01 enables valid checkout',()=>expect(canSubmit(false,1)).toBe(true));
test('R05 rejects zero quantity',()=>expect(canSubmit(false,0)).toBe(false));
