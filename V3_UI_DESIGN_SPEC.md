# V3 UI Design Specification — Discharge Report Dashboard
## React Migration from Streamlit

**Version:** 1.0  
**Date:** 2026-04-13  
**Author:** UI Designer  
**For:** React / FastAPI migration (V3)  
**Reference implementation:** `streamlit_app.py` (V2 feature branch)

---

## Table of Contents

1. Layout Architecture
2. Component Specifications
3. Design Tokens (Tailwind config)
4. Interaction Patterns
5. Status Visual System
6. Accessibility
7. Empty States and Loading States

---

## 1. Layout Architecture

### 1.1 Overall Page Structure

The app has three distinct layout modes: **Login**, **Authenticated (Staff)**, and **Authenticated (Manager)**. All share the same base shell.

```
┌──────────────────────────────────────────────────────────┐
│  [Native browser bar — not controlled]                   │
├──────────────────────────────────────────────────────────┤
│  AppShell                                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Sidebar (240px fixed)  │  Main Area (flex: 1)      │ │
│  │                         │  ┌───────────────────────┐ │ │
│  │  Logo                   │  │ Header bar            │ │ │
│  │  ─────────────          │  ├───────────────────────┤ │ │
│  │  Filters section        │  │ Tab strip             │ │ │
│  │                         │  ├───────────────────────┤ │ │
│  │  Date range             │  │ Stat chips row        │ │ │
│  │  ─────────────          │  ├───────────────────────┤ │ │
│  │  Clear Filters btn      │  │ Table | Detail Panel  │ │ │
│  │  ─────────────          │  │ (split pane)          │ │ │
│  │  User info + Sign out   │  └───────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 1.2 Sidebar

- **Width:** 240px, fixed. Does not collapse on desktop.
- **Behavior on tablet (768px–1024px):** Sidebar overlays as a drawer. Hamburger icon appears in the header. Drawer slides in from the left, sits above the main content with a semi-transparent overlay behind it.
- **Background:** `#132e45` (navy). Light text throughout. No dark mode toggle needed — the sidebar IS the dark panel.

### 1.3 Main Area

- **Padding:** 24px top, 24px right, 24px bottom, 24px left (relative to sidebar edge).
- **Max width:** None. Fills remaining space. Internal tool; full-width is expected.
- On tablet, main area takes full width when sidebar is closed.

### 1.4 Split-Pane Layout (Table + Detail Panel)

When a row is selected, the main content area transitions to a split pane. The table shrinks and the detail panel slides in from the right.

```
No selection:
┌────────────────────────────────────────────────────────┐
│  Table (full width, 100%)                              │
└────────────────────────────────────────────────────────┘

Row selected:
┌────────────────────────────┬───────────────────────────┐
│  Table (55% width)         │  Detail Panel (45% width) │
│  Selected row highlighted  │  Slides in from right     │
└────────────────────────────┴───────────────────────────┘
```

- Split uses CSS `display: flex; gap: 16px` on the container.
- Table column: `flex: 0 0 55%`
- Detail panel column: `flex: 0 0 calc(45% - 16px)`
- Panel entrance: CSS transition `transform: translateX(100%)` → `translateX(0)`, duration 220ms, easing `cubic-bezier(0.25, 0.46, 0.45, 0.94)` (ease-out).
- On tablet (768px–1024px): split pane collapses to full-width stacked layout. Detail panel renders below the table.

### 1.5 Staff View vs Manager View

**Staff view tabs:** Recent Discharges | Last 6 Months | All Discharges

**Manager view tabs:** Recent Discharges | Last 6 Months | All Discharges | Manager Dashboard

The Manager Dashboard tab replaces the standard table+detail layout with a metrics-only layout (no split pane). Tab strip rendering is identical for both roles.

---

## 2. Component Specifications

### 2.1 Sidebar

#### Structure (top to bottom)
1. Logo image (Citadel Health)
2. Section heading: "Filters"
3. Assigned To — single-select dropdown
4. Practice — multi-select dropdown (options depend on Assigned To selection)
5. Payer Name — multi-select dropdown
6. Line of Business — multi-select dropdown
7. Stay Type — multi-select dropdown
8. Divider line
9. Section heading: "Date Range"
10. From — date picker
11. Through — date picker
12. Divider line
13. Clear All Filters — ghost/outline button, full width
14. Divider line
15. User info block (name + email)
16. Sign Out — button, full width

#### Sidebar Token Overrides (all elements within sidebar)

| Element | Style |
|---|---|
| Background | `#132e45` |
| Section heading text (h3) | `#ffffff`, 14px, font-weight 700, `border-bottom: 1px solid #1b4459`, padding-bottom 6px, margin-top 16px |
| Label text | `#a8c4d8`, 11px, font-weight 600, uppercase, letter-spacing 0.06em |
| Divider | `border-color: #1b4459` |
| Dropdown/select background | White (input interior), dark navy ring focus |
| Dropdown/select text | `#1a1a2e` (dark) — this is the V2 lesson: inputs must render dark text |
| Multi-select tag/chip | Background `#e07b2a`, text `#ffffff` |
| Buttons (Clear, Sign Out) | See button spec below |
| User name | `#ffffff`, 13px, font-weight 700 |
| User email | `#7ea8c0`, 11px |
| "Signed in as" label | `#a8c4d8`, 12px |

#### Sidebar Buttons

**Clear All Filters:**
- `border: 1.5px solid #1b4459`, background transparent, text `#d6e6f0`, border-radius 8px, padding 8px 12px, font-size 13px, font-weight 600, width 100%
- Hover: background `#1b4459`, text `#ffffff`

**Sign Out:**
- Same as Clear All Filters styling
- Positioned at the bottom with user info above it

#### Filter Interaction Logic
- When "Assigned To" changes → Practice options are re-scoped to only that person's assigned practices. Previously selected practices that are no longer in scope are removed from the selection.
- All other filters are independent multi-selects.
- Filter changes fire immediately (no "Apply" button). Table re-filters on each change.
- When filters change and the currently selected row is no longer in the filtered result set → detail panel closes automatically.

---

### 2.2 Header

Rendered at the top of the main area, below the page background but above the tabs.

#### Structure
```
┌──────────────────────────────────────────────────────────────┐
│  Logo (300px wide, centered or left-aligned)                 │
│  Welcome, [Name]  (centered, muted)                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Discharge Report Dashboard               [orange bar] │  │
│  │  Live discharge activity — filter, explore, and export │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### Header Bar Styles
- Background: `linear-gradient(135deg, #132e45 0%, #1b4459 100%)`
- Border-radius: 14px
- Padding: 18px 28px
- Box-shadow: `0 4px 18px rgba(19,46,69,0.18)`
- Right edge accent: `position: absolute; right: 0; top: 0; bottom: 0; width: 5px; background: linear-gradient(180deg, #e07b2a 0%, #c96920 100%); border-radius: 0 14px 14px 0`
- Title text: `#ffffff`, 26px (1.65rem), font-weight 800, letter-spacing -0.5px
- Subtitle text: `#a8c4d8`, 13px (0.82rem), margin-top 3px

#### Logo
- Width: 300px, height auto
- Centered above header bar
- Margin-bottom: 6px between logo and welcome line
- Alt text: "Citadel Health"

#### Welcome Line
- `"Welcome, [Name]"` — [Name] portion: `#132e45`, font-weight 700
- Base text: `#556e81`, font-size 21px (1.3rem)
- Text-align center
- Margin-bottom: 6px

---

### 2.3 Tab Strip

Tabs sit immediately below the header bar, above stat chips.

#### Visual Style
- Tab container: background `#e4eaf0`, border-radius 10px, padding 4px, display inline-flex (wraps to fit)
- Each tab: border-radius 7px, color `#1b4459`, font-weight 600, font-size 13.5px (0.85rem), padding 6px 18px, no border
- Active tab: background `#132e45`, color `#ffffff`
- Hover (inactive): background `rgba(19,46,69,0.08)`
- No underline or bottom indicator — pill/capsule style

#### Tab Labels
- Staff: `Recent Discharges` | `Last 6 Months` | `All Discharges`
- Manager adds: `Manager Dashboard`
- Switching tabs clears the selected row (detail panel closes) but preserves all filter state.

---

### 2.4 Stat Chips

Rendered as a horizontal flex row below the tab strip and above the table.

#### Layout
- Container: `display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap`
- Each chip: `flex: 1; min-width: 130px`

#### Chip Structure
```
┌─[4px left border]─────────────────┐
│  LABEL (uppercase, muted)          │
│  VALUE (large, bold)               │
└────────────────────────────────────┘
```

#### Chip Styles

| Variant | Left border | Value color | Background |
|---|---|---|---|
| Default (navy) | `#132e45` | `#132e45` | `#ffffff` |
| Orange | `#e07b2a` | `#e07b2a` | `#ffffff` |
| Green | `#38a169` | `#22753a` | `#ffffff` |
| Gray | `#a0aec0` | `#718096` | `#ffffff` |

#### Chip Common Styles
- Background: `#ffffff`
- Border: `1px solid #d0dae3` (plus 4px left override)
- Border-radius: 10px
- Padding: 10px 18px
- Box-shadow: `0 2px 6px rgba(19,46,69,0.06)`
- Label: `#556e81`, 11.5px (0.72rem), font-weight 700, uppercase, letter-spacing 0.06em, margin-bottom 3px
- Value: 24.8px (1.55rem), font-weight 800, line-height 1

#### Staff Tab Chips (render_stats)
- Total Records (navy)
- Unique Patients (navy)
- Practices (orange)
- Hospitals (navy)

#### Manager Dashboard Chips
- Total Discharges (navy)
- No Outreach (gray)
- Outreach Made (orange)
- Complete (green)
- % Complete (green)

#### Responsive: Below 1024px
- Chips wrap to 2 per row (flex-wrap already handles this via min-width)
- On mobile (< 640px): stack to 1 per row if needed

---

### 2.5 Discharge Table

The table is the primary interaction surface. Uses TanStack Table (React Table v8) with virtual scrolling for the 17k row dataset.

#### Column Set (display order)

| Column | Width | Notes |
|---|---|---|
| Patient Name | 180px | Sortable, left-aligned |
| Discharge Date | 120px | Sortable DESC by default, formatted MM/DD/YYYY |
| Practice | 160px | Sortable |
| Payer Name | 150px | Sortable |
| Discharge Hospital | 180px | Sortable |
| LOS (days) | 80px | Right-aligned, numeric sort |
| Disposition | 130px | Sortable |
| Status | 160px | Pill badge, sortable |

- Event Id is loaded in the data model but not rendered as a visible column. Used internally for row selection and detail lookup.

#### Table Container
- Background: `#ffffff`
- Border-radius: 10px
- Box-shadow: `0 2px 8px rgba(19,46,69,0.07)`
- Overflow: hidden

#### Table Header
- Background: `#132e45`
- Text: `#ffffff`, 11px, font-weight 600, uppercase, letter-spacing 0.04em
- Padding: 10px 12px
- Sort indicator: `↑` / `↓` in `#a8c4d8`, displayed inline after column name

#### Table Rows
- Default row: background `#ffffff`, text `#2a3f50`
- Font-size: 13px (0.82rem)
- Cell padding: 9px 12px
- Row border-bottom: `1px solid #e8ecf0`
- Row hover: background `#f7f9fb`
- Selected row: background `#e8f0f7`, left border `3px solid #132e45` on the first cell, text `#132e45`
- Status-tinted rows (subtle): see Section 5 for row tinting rules
- Last row: no border-bottom

#### Sorting Behavior
- Default sort: Discharge Date descending
- Click column header to sort ascending; click again for descending; click again to remove sort
- Only one column sorted at a time (no multi-sort)
- Visual: sort arrow in header cell; unsorted columns show a faint `↕` on header hover

#### Row Selection
- Single row selection only
- Click anywhere on a row to select it
- Clicking a second row deselects the first and selects the new one
- Clicking the already-selected row deselects it (toggles detail panel closed)
- No checkbox column — click-to-select only

#### Pagination vs Virtual Scroll
Use **virtual scrolling** (TanStack Virtual). Do not paginate.
- Viewport height: `calc(100vh - 380px)` with a minimum of 300px. This ensures the table fills available space below chips and header without requiring page scroll.
- Row height: 40px (fixed for virtual scroll calculation)
- Scroll container: `overflow-y: auto` on the table body wrapper

#### Record Count Badge
Rendered above the table, left-aligned:
- Label text: section name (e.g., "Recent Discharges"), font-size 16px, font-weight 700, color `#132e45`
- Count badge: `display: inline-block; background: #132e45; color: #ffffff; font-size: 12px; font-weight: 700; border-radius: 20px; padding: 2px 10px; margin-left: 8px; vertical-align: middle`

#### Outreach Status Legend
Displayed between the record count badge and the table header row:
```
● No Outreach   ● Outreach Made   ● Outreach Complete
```
- Font-size: 12.5px (0.78rem), color `#556e81`
- Dots: 8px diameter circles, no border
- Dot colors: `#cbd5e0` (gray), `#e07b2a` (orange), `#38a169` (green)
- Gap between items: 24px

#### Export Button
Positioned below the table, right-aligned.
- Label: "Export to CSV"
- Style: see Primary Button spec in section 3

---

### 2.6 Detail Panel (Split-Pane Right)

Opens as the right panel in the split-pane layout when a table row is selected.

#### Overall Structure
```
┌────────────────────────────────────────────────┐
│  HEADER BAR (gradient navy)                    │
│  [Patient Name] — Discharge [MM/DD/YYYY]       │
├────────────────────────────────────────────────┤
│  PATIENT INFO GRID (3 columns, 2 rows)         │
│  Practice | Payer | Hospital                   │
│  Diagnosis | Length of Stay | Disposition      │
├────────────────────────────────────────────────┤
│  UPDATE OUTREACH STATUS heading                │
│  [No Outreach] [Outreach Made] [Complete]      │
│  (button group / segmented control)            │
│                                                │
│  Notes textarea                                │
│                                                │
│  Last updated by [Name] on [Date]              │
│                                                │
│  [Save Status]  [Cancel]                       │
└────────────────────────────────────────────────┘
```

#### Panel Container
- Background: `#ffffff`
- Border-radius: 12px
- Box-shadow: `0 4px 18px rgba(19,46,69,0.10)`
- Border: `1.5px solid #132e45`
- Overflow: hidden

#### Panel Header Bar
- Background: `linear-gradient(135deg, #132e45 0%, #1b4459 100%)`
- Padding: 16px 20px
- Title: `#ffffff`, 16px, font-weight 700, margin 0
- No close button in header — close is via Cancel button or clicking selected row again

#### Patient Info Grid
- Layout: CSS grid, `grid-template-columns: 1fr 1fr 1fr`, gap 16px
- Container padding: 20px
- Border-bottom: `1px solid #e8ecf0`, padding-bottom 20px, margin-bottom 20px
- Field label: `#7e96a6`, 11px (0.7rem), font-weight 700, uppercase, letter-spacing 0.05em, display block, margin-bottom 3px
- Field value: `#132e45`, 14.4px (0.9rem), font-weight 600
- "—" (em dash) rendered when value is null/empty

Fields (row 1): Practice | Payer | Hospital  
Fields (row 2): Diagnosis | Length of Stay | Disposition

- **Diagnosis:** render as `{dx_code} — {description}` when both present; just description if no code
- **Length of Stay:** render as `{n} day` / `{n} days` (singular/plural)

#### Outreach Status Controls

Section heading:
- Text: "Update Outreach Status"
- Font-size: 13.5px (0.85rem), font-weight 700, color `#132e45`, margin-bottom 12px

**Status selection — use a Segmented Button Group (not radio inputs)**

Three buttons in a row, full-width of the panel content area:
```
[ No Outreach ] [ Outreach Made ] [ Outreach Complete ]
```

Button group container: `display: flex; gap: 8px`

Each button:
- Unselected: background `#f7f9fb`, border `1.5px solid #d0dae3`, color `#2a3f50`, border-radius 8px, padding 8px 16px, font-size 13px (0.82rem), font-weight 600, cursor pointer
- Unselected hover: border-color `#132e45`
- Selected — No Outreach: background `#edf2f7`, border-color `#a0aec0`, color `#718096`, font-weight 700
- Selected — Outreach Made: background `#fff3e0`, border-color `#e07b2a`, color `#c05621`, font-weight 700
- Selected — Outreach Complete: background `#e6ffed`, border-color `#38a169`, color `#22753a`, font-weight 700
- Transition: `all 0.15s ease`
- Status dot (8px circle) rendered left of label text inside each button, color matching status dot colors

Status selection is purely visual until Save is clicked. Changing status does not trigger any API call.

#### Notes Textarea
- Label: "Notes" (standard field label style)
- Placeholder: "Add details about the outreach attempt..."
- Background: `#f7f9fb`
- Border: `1.5px solid #d0dae3`, border-radius 8px
- Focus border: `#132e45`, box-shadow `0 0 0 2px rgba(19,46,69,0.15)`
- Text color: `#2a3f50`
- Font-size: 13px
- Height: 80px (non-resizable, or resize: vertical only)
- Padding: 8px 12px
- Margin-bottom: 8px

#### Last Updated Line
- Font-size: 12px (0.75rem), color `#7e96a6`
- Text: "Last updated by **[Name]** on [MM/DD/YYYY at HH:MM AM/PM]"
- **[Name]** portion: font-weight 700
- Margin-bottom: 12px
- Only rendered when an entry exists in outreach_status (i.e., has been saved before)

#### Action Buttons
Container: `display: flex; gap: 8px; margin-top: 4px`

**Save Status (Primary):**
- Background: `#e07b2a`, color `#ffffff`, border none, border-radius 8px, padding 8px 20px, font-size 13.5px (0.85rem), font-weight 700
- Hover: background `#c96920`
- Active: scale `0.98`
- Loading state: spinner icon replaces text, disabled, opacity 0.8
- Transition: `background 0.2s ease`

**Cancel (Secondary):**
- Background transparent, border `1.5px solid #d0dae3`, color `#556e81`, border-radius 8px, padding 8px 16px, font-size 13.5px, font-weight 600
- Hover: border-color `#132e45`, color `#132e45`
- Clicking Cancel: closes detail panel, deselects row, no API call

#### Panel Padding
- All content inside the panel (below header): 20px on all sides

#### Detail Panel — Slide-In Animation
```css
/* Initial state (panel not yet mounted) */
transform: translateX(100%);
opacity: 0;

/* Entered state */
transform: translateX(0);
opacity: 1;
transition: transform 220ms cubic-bezier(0.25, 0.46, 0.45, 0.94),
            opacity 180ms ease;

/* Exit state (row deselected) */
transform: translateX(100%);
opacity: 0;
transition: transform 180ms ease-in,
            opacity 120ms ease;
```

Use a CSS transition group (e.g., `react-transition-group` CSSTransition or a Framer Motion `AnimatePresence`). The panel is unmounted from the DOM when not visible (not just hidden with display:none) to keep the DOM clean.

---

### 2.7 Manager Dashboard

Rendered inside the "Manager Dashboard" tab. No table, no split-pane. Full-width layout.

#### Section 1: Summary Stat Chips
Five chips in a row (see stat chip spec): Total Discharges | No Outreach | Outreach Made | Complete | % Complete

#### Section 2: Staff Outreach Breakdown Table

Section heading: "Staff Outreach Breakdown"
- Font-size: 14.4px (0.9rem), font-weight 700, color `#132e45`, margin-bottom 12px

Table columns (in order):
1. Name — 160px, bold value
2. Practices — 80px (count), center-aligned
3. Total — 80px, right-aligned
4. No Outreach — 100px, right-aligned
5. Made — 80px, right-aligned
6. Complete — 80px, right-aligned
7. % Done — 80px, right-aligned, bold value
8. Last Login — 100px
9. Last Activity — 100px

Table styles use manager-table spec (see below).

#### Section 3: Practice Roll-Up Table

Section heading: "Practice Roll-Up"
- Same heading style as above, margin-top 24px

Table columns:
1. Practice — 200px
2. Total — 80px, right-aligned
3. No Outreach — 100px, right-aligned
4. Made — 80px, right-aligned
5. Complete — 80px, right-aligned
6. % Done — 80px, right-aligned, bold value

Sorted by Total descending by default. Sortable by clicking headers.

#### Manager Table Common Styles
- Width: 100%
- Background: `#ffffff`
- Border-radius: 10px
- Overflow: hidden
- Box-shadow: `0 2px 8px rgba(19,46,69,0.07)`
- Font-size: 13px (0.82rem)
- Margin-bottom: 24px
- **Header row:** background `#132e45`, text `#ffffff`, padding 10px 12px, font-size 12px (0.75rem), font-weight 600, uppercase, letter-spacing 0.04em
- **Data cells:** padding 9px 12px, border-bottom `1px solid #e8ecf0`, color `#2a3f50`
- **Last row:** no border-bottom
- **Row hover:** background `#f7f9fb`

---

### 2.8 Login Page

Full-page layout, no sidebar.

#### Page Background
- `#f0f2f5` (same as main app background)

#### Center Column
- Max-width: 420px
- Margin: auto
- Padding-top: 80px

#### Logo
- Above the card, centered
- Width: 160px, height auto
- Margin-bottom: 16px

#### Login Card
```
┌─────────────────────────────────────────┐
│  Discharge Report Dashboard             │
│  (subtitle text)                        │
│                                         │
│  [Sign in with Microsoft]  (btn)        │
│                                         │
│  Access restricted to: @domain.com      │
└──────────────────────────────────────[▌]│
```

- Background: `linear-gradient(135deg, #132e45 0%, #1b4459 100%)`
- Border-radius: 16px
- Padding: 32px 32px 28px
- Box-shadow: `0 6px 28px rgba(19,46,69,0.22)`
- Right edge orange accent bar: `position: absolute; right: 0; top: 0; bottom: 0; width: 5px; background: linear-gradient(180deg, #e07b2a 0%, #c96920 100%); border-radius: 0 16px 16px 0`
- Title: `#ffffff`, 21.6px (1.35rem), font-weight 800, text-align center, margin-bottom 6px
- Subtitle: `#a8c4d8`, 14px (0.88rem), text-align center, margin-bottom 28px

#### Sign In Button
- Display: block, full width
- Background: `#e07b2a`, color `#ffffff`, no border
- Font-size: 15.2px (0.95rem), font-weight 700
- Padding: 12px 24px
- Border-radius: 9px
- Box-shadow: `0 2px 8px rgba(224,123,42,0.35)`
- Hover: background `#c96920`
- Text: "Sign in with Microsoft"

#### Domain Restriction Note
- Color `#7e96a6`, 12px (0.75rem), text-align center, margin-top 16px
- Text: "Access restricted to: @citadelhealth.com, @aylohealth.com"

---

## 3. Design Tokens (Tailwind Config)

### 3.1 Color Palette

```js
// tailwind.config.js — theme.extend.colors
colors: {
  navy: {
    DEFAULT: '#132e45',  // primary brand navy
    light:   '#1b4459',  // secondary navy, gradients
    dark:    '#0d1f30',  // hover states, deep shadows
  },
  accent: {
    DEFAULT: '#e07b2a',  // orange CTA
    hover:   '#c96920',  // orange hover
    light:   '#fff3e0',  // orange pill background
    text:    '#c05621',  // orange pill text
  },
  success: {
    DEFAULT: '#38a169',  // green
    dark:    '#22753a',  // green text / value
    light:   '#e6ffed',  // green pill background
  },
  muted: {
    100: '#f7f9fb',  // input backgrounds, hover fills
    200: '#f0f2f5',  // page background
    300: '#e8ecf0',  // dividers, row borders
    400: '#d0dae3',  // borders
    500: '#a8c4d8',  // sidebar muted text, subtitle
    600: '#7e96a6',  // label text, footer
    700: '#556e81',  // legend text, stat chip labels
    800: '#2a3f50',  // table cell text
  },
  status: {
    none:     '#cbd5e0',  // gray dot
    none_bg:  '#edf2f7',  // gray pill background
    none_text:'#718096',  // gray pill text
    made_dot: '#e07b2a',  // orange dot (reuses accent.DEFAULT)
    done_dot: '#38a169',  // green dot (reuses success.DEFAULT)
  },
},
```

### 3.2 Typography

```js
// tailwind.config.js — theme.extend.fontFamily
fontFamily: {
  sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
}
```

Font: **Inter** (Google Fonts, self-hosted for internal server). Fallback chain above.

#### Type Scale

| Role | Size | Weight | Color | Class example |
|---|---|---|---|---|
| Page title (header bar) | 26px / 1.625rem | 800 | `#ffffff` | `text-[1.625rem] font-extrabold` |
| Header subtitle | 13px / 0.8125rem | 400 | `#a8c4d8` | `text-[0.8125rem]` |
| Welcome greeting | 21px / 1.3125rem | 400 | `#556e81` | `text-[1.3125rem]` |
| Section heading | 16px / 1rem | 700 | `#132e45` | `text-base font-bold` |
| Manager section heading | 14.5px / 0.905rem | 700 | `#132e45` | `text-[0.905rem] font-bold` |
| Tab label | 13.5px / 0.844rem | 600 | `#1b4459` (inactive) | `text-[0.844rem] font-semibold` |
| Stat chip label | 11.5px / 0.72rem | 700 | `#556e81` | `text-[0.72rem] font-bold uppercase tracking-wider` |
| Stat chip value | 24.8px / 1.55rem | 800 | varies | `text-[1.55rem] font-extrabold leading-none` |
| Table header cell | 11px / 0.6875rem | 600 | `#ffffff` | `text-[0.6875rem] font-semibold uppercase tracking-wide` |
| Table body cell | 13px / 0.8125rem | 400 | `#2a3f50` | `text-[0.8125rem]` |
| Detail field label | 11px / 0.7rem | 700 | `#7e96a6` | `text-[0.7rem] font-bold uppercase tracking-[0.05em]` |
| Detail field value | 14.4px / 0.9rem | 600 | `#132e45` | `text-[0.9rem] font-semibold` |
| Status button text | 13px / 0.82rem | 600 | varies | `text-[0.82rem] font-semibold` |
| Notes textarea text | 13px / 0.8125rem | 400 | `#2a3f50` | `text-[0.8125rem]` |
| Last updated line | 12px / 0.75rem | 400 | `#7e96a6` | `text-xs` |
| Sidebar label | 11px / 0.7rem | 600 | `#a8c4d8` | `text-[0.7rem] font-semibold uppercase tracking-[0.06em]` |
| Sidebar section heading | 15.2px / 0.95rem | 700 | `#ffffff` | `text-[0.95rem] font-bold` |
| Footer | 12.5px / 0.78rem | 400 | `#7e96a6` | `text-[0.78rem]` |
| Status pill text | 11.8px / 0.74rem | 600 | varies | `text-[0.74rem] font-semibold` |
| Login card title | 21.6px / 1.35rem | 800 | `#ffffff` | `text-[1.35rem] font-extrabold` |
| Login card subtitle | 14px / 0.875rem | 400 | `#a8c4d8` | `text-[0.875rem]` |
| Sign in button text | 15.2px / 0.95rem | 700 | `#ffffff` | `text-[0.95rem] font-bold` |

### 3.3 Spacing Scale

Standard Tailwind spacing applies. Key values in use:

| Token | Value | Usage |
|---|---|---|
| `p-3` | 12px | Button padding (small) |
| `p-4` | 16px | Sidebar padding, small card padding |
| `p-5` | 20px | Detail panel body padding |
| `p-6` | 24px | Main area padding, login card padding |
| `p-7` | 28px | Header bar padding |
| `gap-2` | 8px | Button group gap, action buttons |
| `gap-4` | 16px | Stat chips gap, detail grid gap |
| `gap-6` | 24px | Section spacing |
| `mb-3` | 12px | Section heading bottom margin |
| `mb-5` | 20px | Stat chips bottom margin |
| `mb-6` | 24px | Manager table bottom margin |
| `mt-4` | 16px | Sidebar section heading top margin |

### 3.4 Border Radii

```js
borderRadius: {
  'sm':   '6px',    // minor elements
  'md':   '8px',    // buttons, inputs, notes textarea, status buttons
  'lg':   '10px',   // stat chips, table container, manager tables, expanders
  'xl':   '12px',   // detail panel
  '2xl':  '14px',   // header bar, main header
  '3xl':  '16px',   // login card
  'full': '9999px', // pill badges, status dots, record count badge, tag chips
}
```

### 3.5 Shadows

```js
boxShadow: {
  'chip':    '0 2px 6px rgba(19,46,69,0.06)',
  'card':    '0 2px 8px rgba(19,46,69,0.07)',
  'panel':   '0 4px 18px rgba(19,46,69,0.10)',
  'header':  '0 4px 18px rgba(19,46,69,0.18)',
  'login':   '0 6px 28px rgba(19,46,69,0.22)',
  'btn-cta': '0 2px 8px rgba(224,123,42,0.35)',
  'input-focus': '0 0 0 2px rgba(19,46,69,0.15)',
}
```

### 3.6 Transitions and Animations

```js
transitionDuration: {
  'fast':   '120ms',
  'base':   '180ms',
  'slow':   '220ms',
}
transitionTimingFunction: {
  'panel-in':  'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
  'panel-out': 'ease-in',
  'button':    'ease',
}
```

Key animation values:
- Button hover: 200ms ease
- Status button selection: 150ms ease
- Detail panel enter: 220ms `panel-in`
- Detail panel exit: 180ms `panel-out`
- Row highlight on select: 100ms ease
- Tab switch: no animation (instant)
- Toast/success notification: 200ms fade-in, auto-dismiss at 3s, 200ms fade-out

---

## 4. Interaction Patterns

### 4.1 Row Click → Detail Panel Opens

1. User clicks a row in the discharge table.
2. The selected row receives highlighted styling (background `#e8f0f7`, left accent border `3px solid #132e45`).
3. The main content area transitions to split-pane: table shrinks to 55%, detail panel enters from right (220ms slide + fade).
4. Detail panel renders with patient data from the clicked row and the current outreach status for that row.
5. The detail panel is populated synchronously from already-loaded client-side data. No API call is needed to open the panel.

If the user clicks the same row again: detail panel closes (exit animation 180ms), table returns to full width.

If a different row is clicked while a panel is open: panel content swaps instantly (no exit/enter animation for the panel itself — just content swap). The table highlight moves to the new row.

### 4.2 Status Selection → Visual Feedback

1. User clicks one of the three status buttons in the detail panel.
2. The clicked button immediately updates to its "selected" visual state (color change, 150ms transition).
3. The previously selected button returns to unselected state.
4. No API call is made. The selection is local state only until Save is clicked.
5. If the user clicks Cancel, the button group reverts to the last saved status.

### 4.3 Save → Optimistic Update

1. User clicks "Save Status."
2. The Save button immediately enters a loading state (spinner, disabled, opacity 0.8).
3. The row in the table immediately updates its Status pill to the new value (optimistic update, before the API responds).
4. API call fires: `PUT /api/outreach/{event_id}` with `{ discharge_date, status, notes }`.
5. On success (HTTP 200):
   - Loading state clears.
   - A success toast appears (top-right, green, "Status updated for [Patient Name]", 3s auto-dismiss).
   - The detail panel closes (treated as task complete).
   - Table row highlight clears.
   - TanStack Query cache is invalidated for the discharge list so the next fetch reflects the real DB value.
6. On error (non-200 or network failure):
   - The optimistic table update is reverted (row pill goes back to previous status).
   - Save button returns to normal state.
   - An error toast appears: "Failed to save. Please try again." (red, manual dismiss).
   - Detail panel stays open so the user can retry.

### 4.4 Filter Change → Table Updates

1. User changes any filter in the sidebar.
2. The table re-filters instantly (client-side computation from the cached full dataset).
3. If the currently selected row is no longer in the filtered result set:
   - Detail panel closes immediately (no animation, instant).
   - Row selection is cleared.
4. If the currently selected row is still in the filtered result set: detail panel stays open, no change.
5. Stat chips update to reflect the new filtered count.
6. The record count badge updates.

### 4.5 Tab Switching

1. User clicks a different tab.
2. The new tab's data view renders (using the same filtered dataset, scoped to the tab's date range).
3. Row selection is cleared — detail panel closes if open. (Each tab maintains independent selection state; switching back to a previous tab does not restore the prior selection.)
4. All filter state is preserved across tab switches.
5. Stat chips update to reflect the new tab's record count.

### 4.6 Keyboard Navigation

| Key | Action |
|---|---|
| `Tab` | Move focus through sidebar filters, tab strip, table rows (when table is focused) |
| `Arrow Down` / `Arrow Up` | Navigate table rows when table is focused |
| `Enter` or `Space` | Select focused row (opens detail panel) |
| `Escape` | Close detail panel / deselect row |
| `Enter` (when Save button focused) | Submit save |
| `Tab` within detail panel | Move through status buttons → notes → Save → Cancel |

Row focus management: when the detail panel opens, focus moves to the first interactive element in the panel (the first status button). When the panel closes, focus returns to the selected row in the table.

---

## 5. Status Visual System

### 5.1 Status Values and Display Labels

| DB value | Display label | Meaning |
|---|---|---|
| `no_outreach` | No Outreach | Default; no attempt has been made |
| `outreach_made` | Outreach Made | An attempt was made (call, message, etc.) |
| `outreach_complete` | Outreach Complete | Outreach was successful |

### 5.2 Status Color Mapping

| Status | Dot color | Pill background | Pill text | Row tint | Button selected bg | Button selected border | Button selected text |
|---|---|---|---|---|---|---|---|
| No Outreach | `#cbd5e0` | `#edf2f7` | `#718096` | none | `#edf2f7` | `#a0aec0` | `#718096` |
| Outreach Made | `#e07b2a` | `#fef3e2` | `#c05621` | `rgba(224,123,42,0.04)` | `#fff3e0` | `#e07b2a` | `#c05621` |
| Outreach Complete | `#38a169` | `#e6ffed` | `#22753a` | `rgba(56,161,105,0.04)` | `#e6ffed` | `#38a169` | `#22753a` |

### 5.3 Pill Badge Design

Used in the Status column of the discharge table.

```
[ ● No Outreach ]       gray pill
[ ● Outreach Made ]     orange pill
[ ● Outreach Complete ] green pill
```

Structure:
- `display: inline-flex; align-items: center; gap: 5px`
- `padding: 3px 10px` (0.2rem 0.6rem)
- `border-radius: 9999px` (fully rounded)
- `font-size: 11.8px` (0.74rem)
- `font-weight: 600`
- Dot: 7px diameter circle, `border-radius: 50%`, `display: inline-block`

Do not use border on pills — the background color differentiates them sufficiently.

### 5.4 Row Tinting

Rows with status Outreach Made or Outreach Complete receive a very subtle background tint (see table in 5.2). Row tint is applied via an inline or dynamic CSS class on the `<tr>` element.

- "No Outreach" rows: no tint (default white `#ffffff`)
- Tint should be barely perceptible — it adds visual scanning aid without creating heavy visual noise
- The selected row highlight (`#e8f0f7`) overrides the tint when active

### 5.5 Status in the Detail Panel

Use a **segmented button group** (three side-by-side buttons), not radio inputs. This is more scannable and touch-friendly.

Each button shows:
1. A colored dot (7px circle matching status colors)
2. The display label

The active button reflects both the current saved status (on initial render) and the user's pending selection. The button group state is local component state, initialized from the saved status when the panel opens.

The visual pattern of the active button strongly communicates the current selection:
- No Outreach selected: gray tones
- Outreach Made selected: orange tones
- Outreach Complete selected: green tones

---

## 6. Accessibility

### 6.1 Color Contrast Ratios

All text combinations meet WCAG 2.1 AA minimum (4.5:1 for normal text, 3:1 for large text / UI components).

| Text color | Background | Ratio | Pass level |
|---|---|---|---|
| `#ffffff` on `#132e45` | — | 9.7:1 | AAA |
| `#ffffff` on `#1b4459` | — | 7.8:1 | AAA |
| `#ffffff` on `#e07b2a` | — | 3.1:1 | AA (large/UI) |
| `#2a3f50` on `#ffffff` | — | 10.4:1 | AAA |
| `#132e45` on `#e8f0f7` | — | 8.7:1 | AAA |
| `#556e81` on `#f0f2f5` | — | 4.6:1 | AA |
| `#718096` on `#edf2f7` | — | 4.5:1 | AA (borderline — verify in production) |
| `#c05621` on `#fef3e2` | — | 4.7:1 | AA |
| `#22753a` on `#e6ffed` | — | 5.1:1 | AA |
| `#a8c4d8` on `#132e45` | — | 4.5:1 | AA |
| `#7e96a6` on `#ffffff` | — | 4.8:1 | AA |

Note: `#7ea8c0` (sidebar email text) on `#132e45` should be verified. If it falls below 4.5:1, use `#a8c4d8` instead.

### 6.2 Focus Indicators

All interactive elements must have a visible focus indicator. Do not rely solely on browser defaults.

Focus ring spec:
- Outline: `2px solid #e07b2a` (orange, high contrast on both light and dark backgrounds)
- Outline offset: `2px`
- Applied via `:focus-visible` (not `:focus`, to avoid showing on mouse click)

Tailwind utility (add to global CSS):
```css
.focus-ring:focus-visible {
  outline: 2px solid #e07b2a;
  outline-offset: 2px;
}
```

Apply to: all buttons, links, table rows (when using keyboard nav), dropdown triggers, date inputs, textarea.

### 6.3 ARIA Labels and Roles

| Element | ARIA attribute | Value |
|---|---|---|
| Sidebar nav | `role="navigation"` | `aria-label="Filters"` |
| Tab strip container | `role="tablist"` | — |
| Each tab | `role="tab"` | `aria-selected="true/false"`, `aria-controls="tab-panel-{id}"` |
| Tab panel | `role="tabpanel"` | `id="tab-panel-{id}"`, `aria-labelledby="tab-{id}"` |
| Discharge table | `role="grid"` | `aria-label="Discharge records"` |
| Table body row | `role="row"` | `aria-selected="true/false"` |
| Status button group | `role="group"` | `aria-label="Outreach status"` |
| Status buttons | `role="radio"` inside group | `aria-checked="true/false"` |
| Detail panel | `role="complementary"` | `aria-label="Patient detail"` |
| Save button | `aria-busy="true"` when loading | — |
| Error toast | `role="alert"` | `aria-live="assertive"` |
| Success toast | `role="status"` | `aria-live="polite"` |
| Logo image | `alt="Citadel Health"` | — |
| Sort button in column header | `aria-sort="ascending"/"descending"/"none"` | — |
| Loading skeleton | `aria-busy="true"` | `aria-label="Loading discharge records"` |

### 6.4 Screen Reader Considerations

- Status pills in the table: wrap in a `<span>` with the full display text (e.g., "No Outreach") rather than relying on color dots. The dot is `aria-hidden="true"`.
- Record count badge in section heading: structure as `<h2>Recent Discharges <span aria-label=", 247 records">247</span></h2>` so screen readers read the count in context.
- "Last updated by" line: keep as plain text, no special treatment needed.
- Virtual scroll: ensure `aria-rowcount` is set to the full dataset size, and `aria-rowindex` is set on each rendered row.
- When detail panel opens, announce to screen readers: `aria-live="polite"` region with text "Detail panel opened for [Patient Name]."

---

## 7. Empty States and Loading States

### 7.1 Initial Data Load (Table Loading State)

Shown when the app first loads and is fetching from the API.

Use **skeleton rows** instead of a spinner. Skeleton provides more accurate visual feedback for a table.

Skeleton layout:
- Render 10 fake rows with gray animated shimmer bars in place of cell content
- Row height: 40px (matches real row height)
- Cell content placeholder: `background: linear-gradient(90deg, #e8ecf0 25%, #f0f3f5 50%, #e8ecf0 75%)`, `background-size: 200% 100%`, animated left-to-right (1.5s infinite)
- Table header is rendered normally (columns are known)
- Stat chips show skeleton bars in place of values

Tailwind-compatible animation:
```css
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}
.skeleton {
  background: linear-gradient(90deg, #e8ecf0 25%, #f0f3f5 50%, #e8ecf0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}
```

### 7.2 No Records After Filtering

Shown when filters produce zero results.

```
┌──────────────────────────────────────────┐
│                                          │
│   [search icon, 48px, muted]             │
│                                          │
│   No records match the current filters   │
│                                          │
│   Try adjusting the date range or        │
│   removing one of the active filters.    │
│                                          │
│   [ Clear All Filters ]                  │
│                                          │
└──────────────────────────────────────────┘
```

- Icon: magnifying glass with an X, SVG, 48px, color `#a8c4d8`
- Heading: "No records match the current filters", 16px, font-weight 600, color `#556e81`
- Subtext: 13px, color `#7e96a6`
- "Clear All Filters" button: same as secondary button style, centered
- Container: centered in the table area, padding 48px 24px

### 7.3 Empty Tab (No Records for Date Range)

When a tab (e.g., "Recent Discharges") has zero records because the date range contains no discharges:

- Same no-results UI as 7.2 but message changes:
  - Heading: "No discharges in this time range"
  - Subtext: "There are no records in the last 14 days for the selected filters."
- No "Clear All Filters" button — just informational.

### 7.4 API / Database Error State

Shown when the initial data fetch fails.

```
┌──────────────────────────────────────────┐
│                                          │
│   [warning triangle icon, 48px, orange]  │
│                                          │
│   Could not load discharge data          │
│                                          │
│   There was a problem connecting to the  │
│   database. Please try refreshing the    │
│   page. If the issue persists, contact   │
│   your administrator.                    │
│                                          │
│   [ Retry ]                              │
│                                          │
└──────────────────────────────────────────┘
```

- Icon: warning triangle, `#e07b2a`, 48px
- Container: centered in the full main area
- "Retry" button: primary orange button, triggers re-fetch
- Error detail (optional, collapsed by default): small expandable section showing the raw error string for debugging

### 7.5 Save Error (Inline)

When the save API call fails, do not show the above full-page error. Instead:

- Revert the optimistic status pill update in the table row
- Show a dismissible error toast (top-right, red background `#fee2e2`, text `#991b1b`, icon `!`, border `1px solid #fca5a5`)
- Toast text: "Failed to save status. Please try again."
- Toast dismiss: X button, or auto-dismiss after 6s (longer than success toast due to urgency)
- Detail panel remains open for retry

### 7.6 Success Toast (Save Confirmed)

- Position: top-right of the viewport, `position: fixed; top: 16px; right: 16px`
- Background: `#f0fff4`, border `1px solid #9ae6b4`, text `#22543d`
- Icon: checkmark circle, `#38a169`, 16px
- Text: "Status updated for [Patient Name]"
- Border-radius: 8px
- Padding: 12px 16px
- Box-shadow: `0 4px 12px rgba(0,0,0,0.12)`
- Auto-dismiss: 3 seconds
- Animation: slide down from top + fade in (150ms), fade out (200ms)
- Stack multiple toasts vertically if needed (16px gap)

### 7.7 First-Time User Experience

A user who has authenticated but has no outreach records saved yet:

- The table loads normally with all rows showing "No Outreach" status pills (gray)
- Stat chips show all counts with "0" for Outreach Made and Outreach Complete
- No special onboarding UI needed — the workflow is self-evident (click a row, update status)
- The outreach legend above the table serves as the only necessary explanation

### 7.8 Loading State During Save

While the Save API call is in-flight:

- Save button: disabled, text replaced with a 16px animated spinner (white, border-based CSS spinner), opacity 0.8
- Status buttons in the panel: disabled (pointer-events none, opacity 0.6)
- Notes textarea: disabled (pointer-events none, opacity 0.6)
- Cancel button: disabled
- Table row's Status pill: immediately updated to the new value (optimistic)

Spinner CSS:
```css
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## Appendix A: Component Tree Reference

```
App
├── AuthProvider (MSAL.js context)
├── LoginPage (unauthenticated)
└── AppShell (authenticated)
    ├── Sidebar
    │   ├── SidebarLogo
    │   ├── FilterSection
    │   │   ├── AssignedToSelect
    │   │   ├── PracticeMultiSelect
    │   │   ├── PayerMultiSelect
    │   │   ├── LobMultiSelect
    │   │   ├── StayTypeMultiSelect
    │   │   └── DateRangePicker
    │   ├── ClearFiltersButton
    │   └── UserInfo (name, email, sign-out)
    └── MainArea
        ├── AppHeader (logo, welcome, header bar)
        ├── TabStrip
        └── TabPanels
            ├── DischargeTab ("recent" | "six_months" | "all")
            │   ├── TabHeading (with record count badge)
            │   ├── StatChipsRow
            │   ├── OutreachLegend
            │   ├── SplitPane
            │   │   ├── DischargeTable (TanStack Table + TanStack Virtual)
            │   │   └── DetailPanel (conditional, slide-in)
            │   │       ├── DetailPanelHeader
            │   │       ├── PatientInfoGrid
            │   │       ├── StatusButtonGroup
            │   │       ├── NotesTextarea
            │   │       ├── LastUpdatedLine
            │   │       └── ActionButtons (Save, Cancel)
            │   └── ExportButton
            └── ManagerDashboard (manager role only)
                ├── StatChipsRow (5 chips)
                ├── StaffBreakdownTable
                └── PracticeRollupTable
```

---

## Appendix B: Quick Reference — Key Measurements

| Element | Value |
|---|---|
| Sidebar width | 240px |
| Main area padding | 24px all sides |
| Table split (no selection) | 100% |
| Table split (row selected) | 55% |
| Detail panel split | 45% |
| Split pane gap | 16px |
| Table row height | 40px (fixed for virtual scroll) |
| Table viewport height | `calc(100vh - 380px)`, min 300px |
| Stat chip min-width | 130px |
| Detail panel enter animation | 220ms ease-out |
| Detail panel exit animation | 180ms ease-in |
| Header bar border-radius | 14px |
| Login card border-radius | 16px |
| Detail panel border-radius | 12px |
| Stat chip border-radius | 10px |
| Table border-radius | 10px |
| Button border-radius | 8px |
| Input border-radius | 8px |
| Status pill border-radius | 9999px (full) |
| Orange accent bar width | 5px |
| Status dot diameter | 7–8px |
| Primary CTA color | `#e07b2a` |
| Primary CTA hover | `#c96920` |
| Navy primary | `#132e45` |
| Navy secondary | `#1b4459` |
| Page background | `#f0f2f5` |
| Card background | `#ffffff` |
