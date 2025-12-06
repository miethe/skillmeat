# Cross-Browser Testing Quick Start

**DIS-5.9**: Test LocalStorage persistence and UI rendering across Chrome, Firefox, and Safari

---

## One Command to Rule Them All

```bash
cd /Users/miethe/dev/homelab/development/skillmeat/skillmeat/web
./tests/e2e/run-cross-browser-tests.sh
```

**Expected Output**:
```
✓ Chromium (Chrome): PASSED
✓ Firefox: PASSED
✓ WebKit (Safari): PASSED

All browsers passed! (3/3)
```

---

## Quick Commands

### Run All Browsers
```bash
./tests/e2e/run-cross-browser-tests.sh
```

### Run with Browser Windows Visible
```bash
./tests/e2e/run-cross-browser-tests.sh --headed
```

### Run in Interactive UI Mode
```bash
./tests/e2e/run-cross-browser-tests.sh --ui
```

### Run Single Browser
```bash
pnpm test:e2e:chromium tests/e2e/cross-browser-skip-prefs.spec.ts  # Chrome
pnpm test:e2e:firefox tests/e2e/cross-browser-skip-prefs.spec.ts   # Firefox
pnpm test:e2e:webkit tests/e2e/cross-browser-skip-prefs.spec.ts    # Safari
```

---

## Files Created

| File | Purpose |
|------|---------|
| `tests/e2e/cross-browser-skip-prefs.spec.ts` | 22 test cases |
| `tests/e2e/run-cross-browser-tests.sh` | Automated runner |
| `tests/e2e/CROSS_BROWSER_TESTING.md` | Full documentation |
| `tests/e2e/CROSS_BROWSER_TEST_SUMMARY.md` | Detailed summary |
| `tests/e2e/QUICK_START.md` | This file |

---

## What Gets Tested

- ✓ LocalStorage write/read (3 tests)
- ✓ Page reload persistence (3 tests)
- ✓ UI rendering (4 tests)
- ✓ Toast notifications (3 tests)
- ✓ Tab switcher (3 tests)
- ✓ Checkbox states (3 tests)
- ✓ Error handling (3 tests)

**Total**: 22 comprehensive tests

---

## Browser Coverage

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Chromium 141.0 | Ready |
| Firefox | Latest Gecko | Ready |
| Safari | Latest WebKit | Ready |

---

## Installation (One-Time Setup)

```bash
# Install Playwright browsers
npx playwright install chromium firefox webkit

# Or with system dependencies (if needed)
npx playwright install --with-deps chromium firefox webkit
```

---

## Troubleshooting

### Permission Denied
```bash
chmod +x tests/e2e/run-cross-browser-tests.sh
```

### Browsers Not Installed
```bash
npx playwright install chromium firefox webkit
```

### View Test Report
```bash
pnpm test:report
# Open playwright-report/index.html
```

---

## Acceptance Criteria

- [ ] All tests pass on Chrome
- [ ] All tests pass on Firefox
- [ ] All tests pass on Safari
- [ ] LocalStorage working consistently
- [ ] UI renders identically
- [ ] Toast notifications display
- [ ] Tabs functional
- [ ] No console errors

---

**Ready to Execute**: Yes
**Estimated Time**: 6-9 minutes
