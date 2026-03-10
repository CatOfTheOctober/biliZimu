# Bugfix Requirements Document

## Introduction

This document specifies the requirements for fixing the WBI (Web Bilibili Interface) API bug that causes 412 Precondition Failed errors. The root cause is that the Python implementation incorrectly applies WBI signature to the `/x/player/wbi/v2` endpoint, while this endpoint only requires Cookie authentication without signature parameters.

When the WBI API fails with 412 error, the system falls back to the v2 API which returns subtitles from completely different videos, resulting in users receiving incorrect content.

The bug affects all subtitle extraction operations and has a HIGH impact on system reliability. The fix removes the incorrect WBI signature generation for the player API endpoint.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the system calls the WBI API endpoint `/x/player/wbi/v2` with WBI signature parameters (wts, w_rid) THEN the API returns HTTP 412 Precondition Failed error

1.2 WHEN the WBI API returns 412 error THEN the system falls back to v2 API endpoint `/x/player/v2` without WBI signature

1.3 WHEN the system uses v2 API fallback for video BV1SpqhBbE7F (国补政策) THEN the API returns subtitles from a different video about "济南烧烤" instead of the requested video

1.4 WHEN the system uses v2 API fallback for video BV1M8c7zSEBQ (固态电池) THEN the API returns subtitles from a different video about "电竞比赛" instead of the requested video

1.5 WHEN the system generates WBI signature for `/x/player/wbi/v2` endpoint THEN it incorrectly adds wts and w_rid parameters that the endpoint does not expect

1.6 WHEN the `/x/player/wbi/v2` endpoint receives unexpected signature parameters THEN Bilibili's server rejects the request with 412 Precondition Failed

### Expected Behavior (Correct)

2.1 WHEN the system calls the WBI API endpoint `/x/player/wbi/v2` with only aid and cid parameters (no signature) THEN the API SHALL return HTTP 200 with code 0 in the response body

2.2 WHEN the WBI API succeeds for video BV1SpqhBbE7F THEN the system SHALL return subtitles containing content about "国补政策" (the correct video topic)

2.3 WHEN the WBI API succeeds for video BV1M8c7zSEBQ THEN the system SHALL return subtitles containing content about "固态电池" (the correct video topic)

2.4 WHEN calling `/x/player/wbi/v2` endpoint THEN the system SHALL construct URL as `https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}` without WBI signature parameters

2.5 WHEN calling `/x/player/wbi/v2` endpoint THEN the system SHALL rely on Cookie authentication only, not WBI signature

2.6 WHEN the WBI API succeeds THEN the system SHALL NOT fall back to v2 API

2.7 WHEN other WBI endpoints (like `/x/space/wbi/arc/search`) are called THEN the system SHALL CONTINUE TO use WBI signature as required by those endpoints

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the WBI API legitimately requires authentication (returns code -101) THEN the system SHALL CONTINUE TO raise AuthenticationError

3.2 WHEN WBI keys are needed for other endpoints THEN the system SHALL CONTINUE TO fetch keys from the nav API endpoint

3.3 WHEN WBI keys are successfully fetched THEN the system SHALL CONTINUE TO cache them with 1-hour expiration

3.4 WHEN the system processes subtitle data after successful API call THEN it SHALL CONTINUE TO parse and return subtitles in the same format

3.5 WHEN the system uses rate limiting for API calls THEN it SHALL CONTINUE TO apply the same rate limiting behavior

3.6 WHEN the system caches player info results THEN it SHALL CONTINUE TO use the same caching mechanism with the same cache keys
