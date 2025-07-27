# Test Script Log

## Purpose
Track test scripts created during development to avoid technical debt and relearning old findings.

## Format
- **Date**: When test was created
- **Script**: Filename and purpose
- **Hypothesis**: What we wanted to test/find out
- **Findings**: Results and conclusions
- **Status**: Active/Completed/Deleted

---

## Test Scripts

### 2025-07-27 - test_auth.py
**Purpose**: Debug AMBOSS authentication and article access issues
**Hypothesis**: 
- Authentication is failing and causing privacy/cookie pages instead of medical articles
- Need to verify if cookies are working and what content we're actually getting

**Findings**:
- ✅ Authentication is working correctly (cookies loaded successfully)
- ✅ Can access actual medical articles (Molluscum contagiosum with 240K characters)
- ❌ First URL tested (CL0q-g) redirects to features page "Schlüsselfunktionen in AMBOSS"
- ✅ Second URL (-40DNT) loads actual medical content
- ❌ Article body selector `[data-testid="article-body"]` not found, but content exists
- ✅ Main processor successfully captured 8 screenshots per article (features page content)
- ⚠️ Some URLs redirect to AMBOSS features/overview pages instead of medical articles

**Status**: Completed - Authentication issues resolved, main processor now working

**Action**: Delete test script as purpose served

---

### 2025-07-27 - extract_amboss_urls.py
**Purpose**: Extract article URLs from AMBOSS search page
**Hypothesis**: Can crawl search page to discover all article URLs automatically

**Findings**:
- ❌ Superseded by user providing existing URL list (amboss_all_articles_links.txt)
- ✅ Search extraction logic works but not needed

**Status**: Completed - Not needed due to existing URL list

**Action**: Delete test script as superseded by existing data

---

## Key Learnings
1. **Authentication**: Your provided cookies work perfectly for accessing medical articles
2. **URL Validation**: Some URLs in the list may redirect to features pages, but most work
3. **Content Detection**: Article body selector may vary, but content is accessible
4. **Test Scripts**: Should be deleted after serving their purpose to avoid clutter 