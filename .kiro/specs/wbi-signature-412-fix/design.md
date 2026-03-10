# WBI Signature 412 Error Bugfix Design

## Overview

This bugfix addresses a critical issue where the Python implementation incorrectly applies WBI signature to the `/x/player/wbi/v2` endpoint, causing HTTP 412 Precondition Failed errors. The endpoint only requires Cookie authentication and does not expect WBI signature parameters (wts, w_rid). When the 412 error occurs, the system falls back to the v2 API which returns subtitles from completely different videos, resulting in users receiving incorrect content.

The fix removes the incorrect WBI signature generation for the player API endpoint while preserving WBI signature functionality for other endpoints that require it.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the system calls `/x/player/wbi/v2` with WBI signature parameters
- **Property (P)**: The desired behavior - `/x/player/wbi/v2` should be called with only aid and cid parameters, using Cookie authentication only
- **Preservation**: WBI signature functionality for other endpoints (like `/x/space/wbi/arc/search`) must remain unchanged
- **get_player_info()**: The method in `src/bilibili_extractor/modules/bilibili_api.py` (line 399) that fetches player information including subtitle lists
- **WbiSigner**: The class in `src/bilibili_extractor/modules/wbi_sign.py` that generates WBI signatures for API requests
- **wts**: Timestamp parameter added by WBI signature (current Unix timestamp)
- **w_rid**: MD5 hash parameter added by WBI signature (signature of sorted params + mixin_key)

## Bug Details

### Fault Condition

The bug manifests when the system attempts to fetch player information (subtitles) from Bilibili's API. The `get_player_info()` method incorrectly applies WBI signature to the `/x/player/wbi/v2` endpoint, which does not expect or support these signature parameters.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type APIRequest with properties {endpoint, params}
  OUTPUT: boolean
  
  RETURN input.endpoint == "/x/player/wbi/v2"
         AND ("wts" IN input.params OR "w_rid" IN input.params)
         AND validCookieExists()
END FUNCTION
```

### Examples

- **Example 1 (BV1SpqhBbE7F - 国补政策视频)**:
  - Current: Call `/x/player/wbi/v2?aid=X&cid=Y&wts=1234567890&w_rid=abc123...` → 412 error → fallback to v2 API → returns subtitles about "济南烧烤" (wrong video)
  - Expected: Call `/x/player/wbi/v2?aid=X&cid=Y` → 200 success → returns subtitles about "国补政策" (correct video)

- **Example 2 (BV1M8c7zSEBQ - 固态电池视频)**:
  - Current: Call `/x/player/wbi/v2?aid=X&cid=Y&wts=1234567890&w_rid=abc123...` → 412 error → fallback to v2 API → returns subtitles about "电竞比赛" (wrong video)
  - Expected: Call `/x/player/wbi/v2?aid=X&cid=Y` → 200 success → returns subtitles about "固态电池" (correct video)

- **Example 3 (Any video with valid Cookie)**:
  - Current: WBI signature added → 412 error → wrong subtitles returned
  - Expected: No WBI signature → 200 success → correct subtitles returned

- **Edge Case (No Cookie authentication)**:
  - Expected: Call `/x/player/wbi/v2?aid=X&cid=Y` → returns code -101 → raises AuthenticationError (correct behavior)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- WBI signature generation for other endpoints (like `/x/space/wbi/arc/search`) must continue to work with signature parameters
- WBI key fetching from the nav API endpoint must continue to function
- WBI key caching with 1-hour expiration must remain unchanged
- Authentication error handling (code -101) must continue to raise AuthenticationError
- Subtitle data parsing and formatting must remain unchanged
- Rate limiting for API calls must continue to apply
- Player info caching mechanism must continue to use the same cache keys

**Scope:**
All API endpoints that are NOT `/x/player/wbi/v2` should be completely unaffected by this fix. This includes:
- Other WBI endpoints that require signature (e.g., `/x/space/wbi/arc/search`)
- WBI key management and caching
- WbiSigner class functionality
- All other API methods in BilibiliAPI class

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Incorrect API Endpoint Understanding**: The developer assumed that all endpoints under `/x/player/wbi/` require WBI signature, but `/x/player/wbi/v2` is an exception that only requires Cookie authentication.

2. **Misinterpretation of SubBatch Reference**: The SubBatch reference implementation correctly calls `/x/player/wbi/v2?aid={aid}&cid={cid}` without signature, but the Python implementation added signature logic.

3. **Overgeneralization of WBI Requirements**: The presence of "wbi" in the endpoint path led to the assumption that WBI signature is required, when in fact this endpoint uses a different authentication mechanism.

4. **Fallback Mechanism Masking the Issue**: The v2 API fallback mechanism prevented immediate failure, but returned incorrect data, making the bug harder to detect during initial testing.

## Correctness Properties

Property 1: Fault Condition - Player API Without Signature

_For any_ API request to `/x/player/wbi/v2` with valid aid and cid parameters and valid Cookie authentication, the fixed function SHALL call the endpoint without WBI signature parameters (no wts, no w_rid), and the API SHALL return HTTP 200 with code 0 containing the correct subtitles for the requested video.

**Validates: Requirements 2.1, 2.4, 2.5**

Property 2: Preservation - WBI Signature for Other Endpoints

_For any_ API request to endpoints other than `/x/player/wbi/v2` that require WBI signature (such as `/x/space/wbi/arc/search`), the fixed code SHALL continue to generate and apply WBI signature parameters (wts, w_rid) exactly as before, preserving all existing WBI signature functionality.

**Validates: Requirements 2.7, 3.2, 3.3**

## Fix Implementation

### Changes Required

The code has already been fixed. The implementation correctly removes WBI signature from the player API endpoint.

**File**: `src/bilibili_extractor/modules/bilibili_api.py`

**Function**: `get_player_info()` (line 399)

**Specific Changes**:
1. **Remove WBI Signature Generation**: The method now constructs the URL as `https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}` without calling WbiSigner methods.

2. **Direct URL Construction**: Instead of using `_get_wbi_keys()` and `sign_params()`, the method directly builds the URL with only aid and cid parameters.

3. **Cookie-Only Authentication**: The endpoint relies solely on the Cookie in the session headers for authentication.

4. **Preserve Fallback Logic**: The v2 API fallback mechanism remains in place for cases where the WBI API legitimately fails (e.g., authentication issues).

5. **Preserve Other WBI Endpoints**: All other methods that use WBI signature (if any) remain unchanged.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that call `get_player_info()` with real video IDs (BV1SpqhBbE7F, BV1M8c7zSEBQ) and verify that the correct subtitles are returned. Run these tests on the UNFIXED code to observe 412 errors and wrong subtitle content.

**Test Cases**:
1. **BV1SpqhBbE7F Test**: Call `get_player_info()` for 国补政策 video (will fail on unfixed code, returning 济南烧烤 subtitles)
2. **BV1M8c7zSEBQ Test**: Call `get_player_info()` for 固态电池 video (will fail on unfixed code, returning 电竞比赛 subtitles)
3. **URL Inspection Test**: Capture the actual URL being called and verify it contains wts and w_rid parameters (will show signature on unfixed code)
4. **HTTP Status Test**: Verify that 412 errors occur when signature is present (will fail on unfixed code)

**Expected Counterexamples**:
- API returns HTTP 412 when WBI signature parameters are present
- Possible causes: endpoint does not support signature, signature parameters cause validation failure, Cookie authentication conflicts with signature

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := get_player_info_fixed(input.aid, input.cid)
  ASSERT result.http_status == 200
  ASSERT result.code == 0
  ASSERT result.subtitles match expected video content
  ASSERT request_url does NOT contain "wts" parameter
  ASSERT request_url does NOT contain "w_rid" parameter
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT get_player_info_original(input) = get_player_info_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for authentication errors, caching, and rate limiting, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Authentication Error Preservation**: Verify that code -101 still raises AuthenticationError after fix
2. **Caching Preservation**: Verify that cached results are still returned on subsequent calls
3. **Rate Limiting Preservation**: Verify that rate limiting still applies to API calls
4. **Subtitle Parsing Preservation**: Verify that subtitle data structure remains unchanged

### Unit Tests

- Test `get_player_info()` with valid aid/cid returns correct subtitles
- Test that URL does not contain wts or w_rid parameters
- Test that HTTP 200 with code 0 is returned
- Test that authentication errors (code -101) still raise AuthenticationError
- Test that caching works correctly
- Test that subtitle content matches expected video topic

### Property-Based Tests

- Generate random aid/cid combinations and verify no WBI signature parameters in URL
- Generate random video IDs and verify correct subtitles are returned (not from other videos)
- Test that all non-player-API endpoints continue to use WBI signature if they did before

### Integration Tests

- Test full subtitle extraction flow with real video IDs
- Test that correct subtitles are extracted for BV1SpqhBbE7F (国补政策)
- Test that correct subtitles are extracted for BV1M8c7zSEBQ (固态电池)
- Test that no 412 errors occur during normal operation
- Test that v2 API fallback is not triggered when WBI API succeeds
