# UI patterns reference (LVGL v9.6)

Contents: 1 Widgets, names, parents · 2 Screens and layers · 3 Layouts (and replacing lv_list/menu/win) ·
4 Styles · 5 Events · 6 Data binding (Subjects/Observers) · 7 Flags and states · 8 Text and fonts ·
9 Animations and timers · 10 Lifecycle and cleanup · 11 Worked example

Naming reminder: v9 uses `lv_button_create`, `lv_image_create`, `lv_buttonmatrix`, `lv_scale` (replaces
`lv_meter`), `lv_screen_active()`, `lv_obj_delete()`. See `migration.md` for the full rename list.

---

## 1. Widgets, names, parents

- Every widget is created with a parent: `lv_label_create(parent)`. Screens are `lv_obj_create(NULL)`.
- Passing 20 `lv_obj_t *` through globals does not scale. Enable `LV_USE_OBJ_NAME` and use names:
  `lv_obj_set_name(obj, "title")` (copies) or `lv_obj_set_name_static(obj, "title")` (pointer only; string
  must outlive the widget). A trailing `#` becomes a sibling index (`"item_#"` → `item_0`, `item_1`...).
  Find with `lv_obj_find_by_name(parent, "ok_button")` (any depth) or
  `lv_obj_get_child_by_name(parent, "list/item_5/ok_button")` (path). Indices are resolved at lookup time,
  so they shift when siblings are deleted. This replaces the deprecated `lv_obj_find_by_id`.
- Put widget construction for one screen/component in a `xxx_create(parent)` function that returns the
  root; keep the child pointers you need in a small struct, not in globals.

## 2. Screens and layers

```c
lv_obj_t * scr = lv_obj_create(NULL);              /* a screen is a parentless widget */
lv_screen_load(scr);                               /* make it active, or: */
lv_screen_load_anim(scr, LV_SCREEN_LOAD_ANIM_FADE_IN, 300, 0, true /* auto_del previous */);
```

- `lv_screen_active()` returns the active one. **Never delete the active screen.**
- `auto_del = true` deletes the previous screen after the transition: the simplest way to avoid screen
  leaks when screens are cheap to rebuild. Keep screens alive (`false`) only when rebuilding is expensive
  or they hold state; then budget RAM for all of them.
- Input is disabled during the transition animation.
- Screen events: `LV_EVENT_SCREEN_LOAD_START`, `LV_EVENT_SCREEN_LOADED`, `LV_EVENT_SCREEN_UNLOAD_START`,
  `LV_EVENT_SCREEN_UNLOADED`: use them to start/stop timers and subscriptions that belong to a screen.
- Each display has `lv_layer_top()` and `lv_layer_sys()` (plus `lv_layer_bottom()`) that sit above/below all screens: use them for toasts,
  status bars, popups that must persist across screen changes.
- Screen size always equals the display; `lv_obj_set_size/pos` do not apply to screens.

## 3. Layouts

Prefer flex/grid layouts over hard-coded x/y: they survive resolution changes and text-length changes.

```c
lv_obj_set_flex_flow(cont, LV_FLEX_FLOW_COLUMN);                       /* or ROW, ROW_WRAP... */
lv_obj_set_flex_align(cont, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
lv_obj_set_flex_grow(child, 1);                                        /* share remaining space */
lv_obj_set_size(cont, lv_pct(100), LV_SIZE_CONTENT);                   /* percent and content sizing */
```

- `LV_SIZE_CONTENT` chains can cause multiple layout passes; avoid deep nests of content-sized flex
  containers on hot screens.
- Use `pad_row` / `pad_column` styles for gaps.

**Replacements for widgets deprecated in 9.6** (they still compile via `LV_DEPRECATED`, removed in v10):

```c
/* lv_list  ->  flex column of buttons */
lv_obj_t * list = lv_obj_create(parent);
lv_obj_set_size(list, lv_pct(100), lv_pct(100));
lv_obj_set_flex_flow(list, LV_FLEX_FLOW_COLUMN);
lv_obj_t * item = lv_button_create(list);
lv_obj_set_width(item, lv_pct(100));
lv_label_set_text(lv_label_create(item), "Item 1");
```

- `lv_win` → a flex-column `lv_obj` with a header bar and a content area.
- `lv_menu` → pages built from `lv_obj` plus a back button that swaps which page is visible.
- File-browser UI (the `lv_file_explorer` widget is deprecated in 9.6, as is the `lv_file_explorer` demo pattern) → path header + `lv_table` of entries read via the `lv_fs` API.
- `lv_spangroup_set_mode()` **and** `lv_spangroup_set_align()` are deprecated → set the width to `LV_SIZE_CONTENT` / fixed to control wrapping, and use the `text_align` style property for alignment.
- `lv_textarea_set_align()` is deprecated → same `text_align` style property.
The LVGL docs ship matching examples (`lv_example_flex_list`, `lv_example_flex_win`,
`lv_example_menu_navigation`, `lv_example_table_file_browser`).

## 4. Styles

Style objects are shared, CSS-like property bags.

```c
static lv_style_t style_card;           /* static/global/heap, NEVER a stack variable */
static lv_style_t style_card_pressed;

void ui_styles_init(void)               /* call once at startup */
{
    lv_style_init(&style_card);
    lv_style_set_radius(&style_card, 12);
    lv_style_set_bg_color(&style_card, lv_color_hex(0x1E2430));
    lv_style_set_bg_opa(&style_card, LV_OPA_COVER);
    lv_style_set_pad_all(&style_card, 12);
    lv_style_set_border_width(&style_card, 0);

    lv_style_init(&style_card_pressed);
    lv_style_set_bg_color(&style_card_pressed, lv_color_hex(0x2A3242));
}

lv_obj_add_style(card, &style_card, 0);                      /* selector 0 = MAIN part, DEFAULT state */
lv_obj_add_style(card, &style_card_pressed, LV_STATE_PRESSED);
```

Rules:
- **Selector** = part | state, OR-ed: `LV_PART_INDICATOR | LV_STATE_CHECKED`, `LV_PART_SCROLLBAR`, ...
- **Cascade**: styles added later win over earlier ones; local styles (`lv_obj_set_style_*`) beat all
  shared styles; text properties inherit from the parent when no style sets them. Add base styles first,
  state/override styles after.
- Prefer **shared styles** for anything used by more than one widget. Local styles allocate per widget.
- **Const styles** save RAM when nothing changes at runtime — as `static const` prop arrays:
  ```c
  static const lv_style_prop_t props[] = { LV_STYLE_BG_COLOR, 0 };
  ```
  (not `const lv_style_t`; a style itself is mutated by `lv_style_init` / `set_*`).
- Changing a style that is already applied: tell LVGL.
  - simple redraw properties (color, opacity): `lv_obj_invalidate(obj)`
  - size/layout-affecting: `lv_obj_refresh_style(obj, LV_PART_ANY, LV_STYLE_PROP_ANY)`
  - style used all over: `lv_obj_report_style_change(&style)` (NULL = everything)
- `lv_obj_remove_style_all(obj)` strips the theme: good for fully custom widgets and cheaper to draw
  than overriding many theme properties.
- **Transitions** animate property changes between states:
  ```c
  static const lv_style_prop_t trans_props[] = { LV_STYLE_BG_COLOR, 0 };
  static lv_style_transition_dsc_t trans;
  lv_style_transition_dsc_init(&trans, trans_props, lv_anim_path_linear, 120, 0, NULL);
  lv_style_set_transition(&style_card_pressed, &trans);
  ```
  Each transition is an animation; keep them to cheap properties on small widgets.
- **Light/dark theme**: add light styles normally and `lv_obj_bind_style(obj, &style_dark, selector, dark_subject, 1)`
  for the few properties that differ when a `dark_theme` subject equals 1. (With 9.6 pointer-style
  subjects pass the pointer; the official Style Sheets page still shows the ≤ 9.5 `&subject` form.)
- **Themes**: the default theme is set on the display; extend it with your own styles rather than
  forking it. The theme costs draw time, so strip it (`remove_style_all`) on very hot widgets.
- 9.6: the object style cache is on by default (faster style lookups); `text_leading_trim` trims the
  font's phantom leading so `LV_SIZE_CONTENT` labels/buttons hug the glyphs.

## 5. Events

```c
static void slider_cb(lv_event_t * e)
{
    lv_obj_t * slider = lv_event_get_target_obj(e);      /* originating widget (use _target_obj for widgets) */
    int32_t v = lv_slider_get_value(slider);
    void * ctx = lv_event_get_user_data(e);
    /* ... */
}
lv_obj_add_event_cb(slider, slider_cb, LV_EVENT_VALUE_CHANGED, ctx);
```

- Register for the **specific** code you need; `LV_EVENT_ALL` runs your callback for every event
  including draw events.
- Callbacks run inside `lv_timer_handler()`: **do not block** (no sleeps, no slow I/O, no long
  computations): the UI cannot render while your callback runs. Hand slow work to another task and post
  the result back under `lv_lock()` (or via a subject).
- `LV_EVENT_CLICKED` fires on release if the press did not scroll; `LV_EVENT_PRESSED`/`RELEASED`,
  `LONG_PRESSED`, `GESTURE`, `VALUE_CHANGED` (slider/switch/dropdown...), `KEY`, `FOCUSED`/`DEFOCUSED` are the
  commonly used ones. 9.6 adds `LV_EVENT_CHECKED/UNCHECKED` and `GESTURE_UP/DOWN/LEFT/RIGHT`.
- **Bubbling**: with the event-bubble flag on a child, events also go to the parent; the callback's
  current target is the parent, the original target is `lv_event_get_target_obj(e)`. Handy for lists:
  one callback on the container instead of one per row. (The flag API is deprecated in 9.6 via `LV_DEPRECATED`; use the
  dedicated `lv_obj_set_event_bubble()`, or `lv_obj_add_flag(..., LV_OBJ_FLAG_EVENT_BUBBLE)` which still
  compiles with a warning.)
- **Draw events** (`LV_EVENT_DRAW_MAIN/POST/...`): rendering is in progress. Creating/deleting widgets
  or changing attributes/styles here triggers an assertion. Only issue draw tasks.
- **Custom events**: `uint32_t MY_EVT = lv_event_register_id();` then `lv_obj_send_event(obj, MY_EVT, &data)`.
- Displays and indevs have events too (`lv_display_add_event_cb`, `lv_indev_add_event_cb`).
- Do not call `lv_event_get_target_obj()` when the target is a display/indev (undefined behavior).

## 6. Data binding (Subjects and Observers)

A **Subject** holds a value (int, float, string, pointer, color, or a group of subjects). An **Observer**
runs a callback when it changes, **and once immediately on subscribe**. Widgets can bind directly.

```c
static lv_subject_t * temperature;                 /* 9.6 style: pointer + create/delete */

void data_init(void)
{
    temperature = lv_subject_create(LV_SUBJECT_TYPE_INT);
    lv_subject_set_min_value_int(temperature, -40);   /* limits BEFORE the first value: set_int clamps */
    lv_subject_set_max_value_int(temperature, 125);
    lv_subject_set_int(temperature, 25);              /* no init value in create(); starts at 0 */
}
```

Binding helpers (each is just an Observer and is removed automatically when the widget is deleted):

| Need | Call |
|---|---|
| Label text with printf format | `lv_label_bind_text(label, subject, "%d °C")` |
| Slider / arc / dropdown / roller value (two-way) | `lv_slider_bind_value`, `lv_arc_bind_value`, `lv_dropdown_bind_value`, `lv_roller_bind_value` |
| Show/hide or any bool flag from 0/non-zero | `lv_obj_bind_bool(obj, subject, lv_obj_set_hidden)` |
| Checked state (two-way, needs `lv_obj_set_checkable(obj, true)`) | `lv_obj_bind_checked(obj, subject)` |
| Style active when subject == value | `lv_obj_bind_style(obj, &style, selector, subject, value)` |
| Any style property from a subject (color, text, number, pointer, string) | `lv_obj_bind_color`, `lv_obj_bind_int`, `lv_obj_bind_float`, `lv_obj_bind_string`, `lv_obj_bind_pointer` |
| Scale needles from a subject | `lv_scale_bind_line_needle_value`, `lv_scale_bind_image_needle_value` |
| Anything else (states, comparisons) | `lv_subject_add_observer_obj(subject, cb, widget, NULL)` + `lv_observer_get_target_obj(observer)` |
| Let a widget *write* a subject (no event handler) | `lv_obj_add_subject_toggle_event(obj, subject, LV_EVENT_CLICKED)`, `lv_obj_add_subject_increment_event(obj, subject, trigger, step)` |

Custom observer:

```c
static void disabled_cb(lv_observer_t * obs, lv_subject_t * subj)
{
    lv_obj_t * obj = lv_observer_get_target_obj(obs);
    lv_obj_set_state(obj, LV_STATE_DISABLED, lv_subject_get_int(subj) > 80);
}
lv_subject_add_observer_obj(temperature, disabled_cb, widget, NULL);
```

Notes:
- `lv_subject_add_observer_obj` observers die with the widget. Plain `lv_subject_add_observer()` ones
  must be removed with `lv_observer_delete()`. `lv_obj_remove_from_subject(widget, subject)` detaches a
  widget from one subject (or from all of them, with `NULL`).
- For a non-widget target use `lv_subject_add_observer_with_target()` and read it back with
  `lv_observer_get_target()`.
- `lv_subject_delete(subject)` disconnects observers and frees the subject (accepts NULL; pointer is
  invalid afterwards). Subjects alive at `lv_deinit()` are cleaned automatically in 9.6.
- String subjects: `lv_subject_set_string_buffer_static(s, buf, prev_buf, size)` then `lv_subject_set_string(s, "..")`
  (buffers must outlive the subject). Group subjects: `lv_subject_set_group_list_static(...)`; a group
  subject must outlive its member subjects.
- Subject writes are LVGL calls: from other threads take the lock (`lv_lock(); lv_subject_set_int(...); lv_unlock();`).
- ≤ 9.5 uses `lv_subject_init_int(&subj, v)` / `lv_subject_deinit(&subj)` with `lv_subject_t` values and
  `&subj` addresses. Do not mix the two styles in one project.
- Float values: a float subject type exists; for display on a label, a common safe pattern is an int in
  tenths (`235` → "23.5") with a small observer that formats text.

## 7. Flags and states (9.6)

| Intent | 9.6 | ≤ 9.5 |
|---|---|---|
| hide / show | `lv_obj_set_hidden(o, true/false)`; `lv_obj_is_hidden(o)` | `lv_obj_add_flag/remove_flag(o, LV_OBJ_FLAG_HIDDEN)` |
| clickable | `lv_obj_set_clickable(o, en)` | `LV_OBJ_FLAG_CLICKABLE` |
| scrollable | `lv_obj_set_scrollable(o, en)` | `LV_OBJ_FLAG_SCROLLABLE` |
| checkable / checked | `lv_obj_set_checkable(o, en)`, `lv_obj_set_checked(o, en)` | flag / `LV_STATE_CHECKED` |
| disabled / pressed | `lv_obj_set_disabled(o, en)`, `lv_obj_is_pressed(o)` | `LV_STATE_DISABLED` / `LV_STATE_PRESSED` |
| arbitrary state | `lv_obj_set_state(o, LV_STATE_x, bool)` | `lv_obj_add_state/remove_state` |
| user flags 1-4 | `lv_obj_set_user_flag(o, bit0to3, en)` | `LV_OBJ_FLAG_USER_1..4` |

The generic `lv_obj_add_flag/remove_flag/set_flag/has_flag/has_flag_any` still compile in 9.6 with a
`#warning` and are removed in v10. LVGL ships `scripts/migration/migrate_obj_flags.py` which rewrites
raw flag constants automatically (expressions using variables are skipped). For flags not listed here,
look up the setter name in the 9.6 headers before using it.

## 8. Text and fonts

- `lv_label_set_text()` **copies** the string. `lv_label_set_text_static()` stores the pointer: no
  allocation, but the string must outlive the label (ideal for long-lived writable buffers).
  `lv_label_set_text_fmt()` formats printf-style (uses a temporary allocation). `set_text_static` combined
  with `LONG_MODE_DOTS` edits the buffer in place, so never pass ROM/`const` there.
- For values refreshed at high rate, only call the setter when the value changed.
- 9.6: `lv_label_set_max_lines(label, n)` caps line count.
- Built-in fonts: enable only the Montserrat sizes you use (`LV_FONT_MONTSERRAT_xx`); each enabled font
  costs flash. Set `LV_FONT_DEFAULT`. For other glyph sets/scripts generate a bitmap font with
  `lv_font_conv` (choose only needed ranges, optionally compressed), or use Tiny TTF/FreeType (heavier
  on RAM/CPU; consider caching and PSRAM). 9.6 adds dynamic glyph loading for binary fonts and variable-weight
  FreeType (see the 9.6 changelog/fonts docs for exact APIs).
- Symbols (`LV_SYMBOL_*`) are font glyphs; make sure the font in use contains them.

### Translations (new in 9.6)

UI strings can live in a translation pack instead of in the code, so a language switch does not mean a
rebuild. `lv_translation.h` provides `lv_translation_init()`, `lv_translation_add_static()` /
`lv_translation_add_dynamic()` per language, `lv_translation_set_language()`,
`lv_translation_get()` to resolve a tag, and `lv_translation_add_tag()` / `lv_translation_set_tag_translation()`
for the tag indirection. Changing the language fires `LV_EVENT_TRANSLATION_LANGUAGE_CHANGED`; the
dropdown and roller widgets have direct entry points
(`lv_dropdown_set_text_translation_tag()`, `lv_dropdown_set_options_translation_tag()`,
`lv_roller_set_options_translation_tag()`). Because this is a new module, confirm the exact function
set against `include/lvgl/core/lv_translation.h` in the version you build against.

## 9. Animations and timers

```c
static void set_arc(void * var, int32_t v) { lv_arc_set_value((lv_obj_t *)var, v); }

lv_anim_t a;
lv_anim_init(&a);
lv_anim_set_var(&a, arc);
lv_anim_set_exec_cb(&a, set_arc);
lv_anim_set_values(&a, 0, 100);
lv_anim_set_duration(&a, 500);                 /* lv_anim_set_time in early 9.0 */
lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
lv_anim_start(&a);
/* later: */ lv_anim_delete(arc, set_arc);     /* NULL exec_cb = delete all anims of this var */
```

- Animations and `lv_timer`s run inside `lv_timer_handler()`; no locking inside their callbacks.
- If the animation `var` is a widget, LVGL deletes its animations automatically with the widget; `lv_anim_delete()` is only needed when `var` is **not** a widget (or for a custom callback holding outside pointers).
- `lv_anim_count_running()` tells you whether it is safe to let the device sleep.
- Timelines (`lv_anim_timeline_*`) sequence multiple animations.
- User timers: `lv_timer_t * t = lv_timer_create(cb, period_ms, user_data); lv_timer_set_repeat_count(t, n); lv_timer_delete(t);`
  Prefer subjects over polling timers for data → UI. `lv_async_call(cb, data)` schedules work on the
  next handler run (from another thread still hold the lock, and the `data` pointer must stay valid until the call runs).
- Budget animations: every animated frame costs a redraw of the affected area; moving/scaling large,
  alpha-blended content is the expensive case.

## 10. Lifecycle and cleanup

- `lv_obj_delete(obj)` deletes the subtree. `lv_obj_clean(parent)` deletes only the children.
- Deleting from inside the widget's own event → `lv_obj_delete_async(obj)`.
- Free per-widget heap data in an `LV_EVENT_DELETE` callback:
  ```c
  static void card_delete_cb(lv_event_t * e) { lv_free(lv_event_get_user_data(e)); }
  lv_obj_add_event_cb(card, card_delete_cb, LV_EVENT_DELETE, ctx);
  ```
- Never keep a raw `lv_obj_t *` across a screen change without a way to know it is gone. The three
  options, in order of preference:
  1. `lv_obj_null_on_delete(&my_ptr)` — new in 9.6. Register the *address of your pointer* and LVGL
     sets it to `NULL` when the widget dies, so a stale read is `NULL`, not a dangling pointer:
     ```c
     static lv_obj_t * card;
     card = card_create(parent);
     lv_obj_null_on_delete(&card);
     ```
  2. Clear it yourself in an `LV_EVENT_DELETE` callback.
  3. Look it up again by name (needs `LV_USE_OBJ_NAME`).
  During development `lv_obj_is_in_widget_tree()` / `LV_USE_CHECK_OBJ_VALIDITY` will tell you a
  pointer is already dead.
- Free anything else the widget owns with `lv_obj_add_delete_cb(obj, cb, user_data)` (removed again
  with `lv_obj_remove_delete_cb(dsc)`) when a one-shot `LV_EVENT_DELETE` callback is not enough.
- Create-on-demand + delete saves RAM but fragments the pool and costs rebuild time; hiding
  (`lv_obj_set_hidden`) costs RAM but is instant. Choose per screen based on measurements.
- Enable `LV_USE_CHECK_OBJ_CLASSTYPE` / `LV_USE_CHECK_OBJ_VALIDITY` in dev builds to catch
  use-after-delete (they log a warning and return instead of corrupting memory); disable in production.

## 11. Worked example: live sensor dashboard

```c
/* data.c */
static lv_subject_t * temperature;
void data_init(void) { /* see section 6 */ }
void data_set_temperature(int c)   /* callable from any task */
{
    lv_lock();
    lv_subject_set_int(temperature, c);
    lv_unlock();
}

/* ui.c */
lv_obj_t * dashboard_create(void)
{
    lv_obj_t * scr = lv_obj_create(NULL);
    lv_obj_set_flex_flow(scr, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_flex_align(scr, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);

    lv_obj_t * label = lv_label_create(scr);
    lv_label_bind_text(label, temperature, "%d °C");

    lv_obj_t * arc = lv_arc_create(scr);
    lv_arc_set_range(arc, -40, 125);
    lv_arc_bind_value(arc, temperature);
    lv_obj_set_clickable(arc, false);                 /* read-only gauge (≤9.5: remove CLICKABLE flag) */
    lv_obj_remove_style(arc, NULL, LV_PART_KNOB);     /* hide the knob */
    return scr;
}

void ui_start(void)
{
    ui_styles_init();
    lv_screen_load_anim(dashboard_create(), LV_SCREEN_LOAD_ANIM_FADE_IN, 250, 0, true);
}
```

Why this is the recommended shape: no polling timer, no cross-thread widget pointers, one lock held for
one subject write, UI updates only when the value changes, and cleanup is automatic when the screen is
deleted.