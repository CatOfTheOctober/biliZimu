# Implementation Plan

- [x] 1. Write expected behavior validation test
  - **Property 1: Expected Behavior** - Player API Returns Correct Subtitles Without WBI Signature
  - **NOTE**: The fix has already been implemented in the code - this test validates the fix works correctly
  - **GOAL**: Verify that player API now works correctly without WBI signature parameters
  - **Scoped PBT Approach**: Test with concrete cases that previously failed (BV1SpqhBbE7F, BV1M8c7zSEBQ)
  - Test that calling `/x/player/wbi/v2` with only aid and cid parameters (no wts, w_rid) returns HTTP 200 with code 0
  - Test with known problematic videos: BV1SpqhBbE7F (国补政策) and BV1M8c7zSEBQ (固态电池)
  - Verify that BV1SpqhBbE7F returns subtitles about "国补政策" (not "济南烧烤")
  - Verify that BV1M8c7zSEBQ returns subtitles about "固态电池" (not "电竞比赛")
  - Verify that current implementation does NOT add wts and w_rid parameters to the URL
  - **EXPECTED OUTCOME**: Test PASSES (confirms the fix works correctly)
  - Create test file: `tests/property/test_wbi_player_api_fix.py`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 2. Write preservation property tests
  - **Property 2: Preservation** - Non-Player-API Behavior Unchanged After Fix
  - **GOAL**: Verify that the fix did not introduce regressions in other functionality
  - Test that other WBI endpoints (like `/x/space/wbi/arc/search`) continue to use WBI signature correctly
  - Test that authentication errors (code -101) still raise AuthenticationError
  - Test that WBI key fetching and caching behavior remains unchanged
  - Test that subtitle parsing and formatting remains unchanged
  - Test that rate limiting behavior remains unchanged
  - Test that caching mechanism for player info remains unchanged
  - Test that v2 API fallback still works when WBI API legitimately fails
  - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
  - Add tests to: `tests/property/test_wbi_player_api_fix.py`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 2.7_

- [x] 3. Run property-based tests to validate the fix

  - [x] 3.1 Run expected behavior validation test
    - **Property 1: Expected Behavior** - Player API Returns Correct Subtitles
    - Run the test from task 1: `pytest tests/property/test_wbi_player_api_fix.py::test_player_api_expected_behavior -v`
    - Verify that BV1SpqhBbE7F returns subtitles about "国补政策" (not "济南烧烤")
    - Verify that BV1M8c7zSEBQ returns subtitles about "固态电池" (not "电竞比赛")
    - Verify that API returns HTTP 200 with code 0
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.2 Run preservation tests
    - **Property 2: Preservation** - Non-Player-API Behavior Unchanged
    - Run preservation tests from task 2: `pytest tests/property/test_wbi_player_api_fix.py::test_preservation -v`
    - Confirm other WBI endpoints still use signature correctly
    - Confirm authentication error handling unchanged
    - Confirm WBI key management unchanged
    - Confirm subtitle parsing unchanged
    - Confirm rate limiting unchanged
    - Confirm caching unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 2.7_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run all tests: `pytest tests/ -v`
  - Verify bug condition test passes (player API works correctly)
  - Verify preservation tests pass (no regressions in other functionality)
  - Test with real videos: BV1SpqhBbE7F and BV1M8c7zSEBQ
  - Ensure all tests pass, ask the user if questions arise
