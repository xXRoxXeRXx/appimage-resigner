# Signature Verification Bug - Analysis

## Problem

Embedded signatures sometimes fail verification with "BAD signature" error, even when they were created with the correct key.

## Root Cause

The problem is **inconsistent newline handling** when embedding signatures:

### Bad Signatures (Failed Verification)
- Created with **2 newlines** (`\n\n`) between data and signature:
  ```
  [AppImage Data]\n\n-----BEGIN PGP SIGNATURE-----
  ```
- But the signature was created by signing data **without** these newlines
- When verifying, GPG sees: `data + \n\n + signature`
- But the signature expects: `data` (without newlines)
- **Result: BAD signature**

### Good Signatures (Pass Verification)
- Created with **1 newline** (`\n`) between data and signature:
  ```
  [AppImage Data]\n-----BEGIN PGP SIGNATURE-----
  ```
- The signature was created by signing clean data
- When verifying, we trim the `\n` and verify: `data` vs `signature`
- **Result: GOOD signature**

## Analysis

```bash
# Bad signature example:
Last bytes: 00 00 00 00 00 00 00 00 00 0a 0a
Position: 193640954
Result: BAD signature ❌

# Good signature example:
Last bytes: 00 00 00 00 00 00 00 00 00 00 0a
Position: 193640953  
Result: GOOD signature ✅
```

## Fix Applied

### src/verify.py
1. **Normalize line endings** in signature (`\r\n` → `\n`)
2. **Trim all whitespace** before signature marker
3. **Write temp file with Unix line endings** for GPG

### src/resigner.py
1. **Normalize signature text** before embedding
2. **Use exactly 1 newline** as separator
3. **Trim whitespace** when removing old embedded signatures

## Conclusion

- ✅ **New signatures** created with our fix will verify correctly
- ❌ **Old signatures** with 2 newlines cannot be fixed (they're fundamentally broken)
- 📝 **Recommendation**: Re-sign any AppImages that show "BAD signature"

## Testing

Run: `python test_signature_fix.py`

Expected results:
- New signatures: ✅ VALID
- Old signatures (2 newlines): ❌ INVALID (expected, cannot fix)
