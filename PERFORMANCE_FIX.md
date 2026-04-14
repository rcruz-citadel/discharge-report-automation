# Performance Fix: UI Lag on Filter/Action (~3 Second Pause)

## Problem

Every user interaction (sidebar filter change, status button click, row selection, tab switch) causes a ~3 second pause before the UI updates. This makes the app feel sluggish and frustrating for staff doing bulk outreach work.

## Root Cause Analysis

Streamlit reruns the **entire script** top-to-bottom on every interaction. In our app, that means:

### 1. `_merge_outreach()` is slow — row-level `.apply()` on every rerun
```python
def _merge_outreach(df, outreach):
    def _lookup(row):
        key = (str(row["Event Id"]), row["Discharge Date"])
        entry = outreach.get(key)
        ...
    df["Status"] = df.apply(_lookup, axis=1)  # <-- O(n) Python loop, called EVERY rerun
```
- `.apply()` with a Python function iterates row-by-row — no vectorization
- On 17,000+ discharge rows, this is the single biggest bottleneck
- This runs on EVERY rerun, even when the user is just clicking a status button

### 2. Full page rerun on detail panel interactions
- Clicking a status button ("No Outreach" / "Outreach Made" / "Outreach Complete") triggers `st.rerun()`
- This reruns the entire page: reloads data, re-merges outreach, re-renders all tabs, re-renders sidebar
- The detail panel is a small isolated component — it doesn't need the full page to rerun

### 3. Outreach status legend + detail panel HTML re-rendered on every rerun
- All the HTML markdown blocks (legend, detail panel, stat chips) are re-rendered even when unchanged
- Not the biggest cost, but adds up

### 4. Multiple `load_practice_assignments()` calls per rerun
- Called in both `render_sidebar_filters()` and `apply_filters()` — two calls per rerun
- Cached, so the DB isn't hit twice, but the cache lookup + dict construction happens twice

## Fix Plan

### Fix 1: Vectorized outreach merge (HIGH IMPACT)
Replace the `.apply()` with a pandas merge/map operation:
```python
def _merge_outreach(df, outreach):
    df = df.copy()
    # Build a Series keyed on (Event Id, Discharge Date) -> status label
    keys = df.set_index(["Event Id", "Discharge Date"]).index
    df["Status"] = pd.Series(keys).map(
        lambda k: STATUS_DISPLAY.get(outreach.get(k, {}).get("status", "no_outreach"), "No Outreach")
    ).values
    return df
```
Or even better — convert outreach dict to a DataFrame and do a proper left merge.

### Fix 2: Use `st.fragment` for the detail panel (HIGH IMPACT)
Wrap `render_detail_panel()` in `@st.fragment` so status button clicks only rerun the detail panel, not the entire page:
```python
@st.fragment
def render_detail_panel(row, outreach, tab_key):
    ...
```
This requires Streamlit 1.33+. The status buttons, notes textarea, and save/cancel would all operate within the fragment without triggering a full page rerun.

### Fix 3: Cache the merged DataFrame (MEDIUM IMPACT)
Instead of merging outreach into the discharge data on every rerun, cache the merged result:
```python
@st.cache_data(ttl=60)
def load_discharge_data_with_status():
    df = load_discharge_data()
    outreach = load_outreach_statuses()
    return _merge_outreach(df, outreach)
```
This way the merge only runs when the cache expires (60s) or is explicitly cleared after a status update.

### Fix 4: Single practice_assignments load (LOW IMPACT)
Load once in `main()` and pass as argument to both `render_sidebar_filters()` and `apply_filters()`.

## Expected Outcome
- Filter changes: near-instant (cached data, no merge)
- Status button clicks: near-instant (fragment rerun, not full page)
- Status save: ~1s (DB write + cache clear + fragment rerun)
- Tab switches: near-instant (cached data already merged)
