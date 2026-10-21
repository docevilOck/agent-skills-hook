---
name: "lvgl-v9"
description: Expert guidance for writing, reviewing, debugging, porting, and optimizing LVGL v9 embedded UI code in C/C++, current through v9.6.0 (16 Sept 2026, the final v9 release). Use this skill whenever the user mentions LVGL, lv_conf.h, lv_display, lv_indev, lv_obj, lv_timer_handler, flush_cb, draw buffers, esp_lvgl_port, LVGL on ESP32/ESP-IDF/STM32/Zephyr/Linux, TFT/LCD/touchscreen UIs on microcontrollers, LVGL styles/events/subjects/observers, LVGL performance or RAM problems, wrong colors or tearing on an LVGL display, or migrating LVGL v8 to v9 or v9.5 to v9.6 / v10. Use it any time LVGL code is being generated so the output uses current v9 APIs instead of removed v8 or deprecated calls, even if the user never says "v9" or "best practices".
---

# LVGL v9 best practices

LVGL is a single-threaded, timer-driven C graphics library. Almost every real-world bug falls into
one of five buckets: **threading, flush handling, color format, memory, or stale (v8/deprecated) API**.
This skill is organized around avoiding those.

## 0. Know which version you are targeting

As of October 2026 the latest release is **v9.6.0 (16 Sept 2026) and it is the last v9 release**.
Everything marked `LV_DEPRECATED` in 9.6 is **removed in v10**; deprecated names still compile and
emit a `#warning`. So v9.6 is the version to write and clean up against.

Before writing code:

1. Find the project's actual version (`LVGL_VERSION_MAJOR/MINOR` in `lv_version.h`, ESP-IDF
   `idf_component.yml`, `lv_conf.h` header comment). esp_lvgl_port pulls the latest stable LVGL by
   default, but many projects are pinned to 9.2-9.5.
2. If unknown, write 9.6-clean code and say so. If the project is ≤ 9.5, use the "≤ 9.5 equivalent"
   column below. Never emit v8 API (`lv_disp_*`, `lv_scr_act`, `lv_btn_create`...).

| Topic | v9.6 (preferred) | ≤ 9.5 equivalent |
|---|---|---|
| Include | `#include <lvgl/lvgl.h>` (public API lives in `include/lvgl/`) | `#include "lvgl.h"` |
| Color config | `LV_COLOR_FORMAT_DEFAULT` (e.g. `LV_COLOR_FORMAT_RGB565`) | `LV_COLOR_DEPTH 16` |
| Widget flags | `lv_obj_set_hidden(o, true)`, `lv_obj_is_hidden(o)`, `lv_obj_set_clickable`, `lv_obj_set_scrollable` | `lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN)` etc. |
| Checked/pressed/disabled | `lv_obj_set_checked` / `lv_obj_is_checked`, `lv_obj_set_pressed` / `lv_obj_is_pressed`, `lv_obj_set_disabled` / `lv_obj_is_disabled`, `lv_obj_set_state(o, st, bool)` | `lv_obj_add_state` / `lv_obj_has_state` (preferred helpers in 9.6, not deprecated) |
| Subjects | `lv_subject_create(TYPE)` / `lv_subject_delete` (pointer) | `lv_subject_init_int(&s, v)` / `lv_subject_deinit` |
| Flag/state binding | `lv_obj_bind_bool(o, subj, lv_obj_set_hidden)` | `lv_obj_bind_flag_if_*` |
| RGB565 byte swap helper | `lv_draw_rgb565_swap` | `lv_draw_sw_rgb565_swap` |
| Find widget by name | `lv_obj_find_by_name` (needs `LV_USE_OBJ_NAME`) | `lv_obj_find_by_id` |
| Memory size option | `LV_MEM_SIZE` in **bytes** (e.g. `64 * 1024`) | `LV_MEM_SIZE_KILOBYTES`, `LV_MEM_POOL_EXPAND_SIZE[_KILOBYTES]` |

Details and the full deprecation list: `references/migration.md`.

Two more version facts that change what you generate:

- **XML UI engine**: removed from the open-source LVGL repo in v9.5 (development continues in
  LVGL Pro). Do not generate `lv_xml_*` code for open-source LVGL 9.5+.
- **`lv_list`, `lv_menu`, `lv_win`, `lv_file_explorer`** are deprecated in 9.6. Build them from
  `lv_obj` + flex layouts (see `references/ui-patterns.md`).

## 1. Workflow

When asked to write, review, or fix LVGL code:

1. **Identify the target**: LVGL version, MCU/OS (bare metal, FreeRTOS, Zephyr, Linux), display
   interface (SPI, parallel, RGB, MIPI, SDL), color format, RAM available (internal vs PSRAM).
   Ask only for what you cannot infer; otherwise state assumptions in one line and proceed.
2. **Check the five bug buckets** against the code (section 3 triage table helps).
3. **Write code** following the rules in section 2 and the skeleton in section 4.
4. **Point out** anything that is deprecated in 9.6 or will break in v10.
5. For performance or memory questions, **measure first** (sysmon, see
   `references/performance-and-memory.md`) instead of guessing.

For deeper material, read the matching reference file:

- Porting a display/touch driver, tick, threading, buffers, ESP32/ESP-IDF setup →
  `references/porting-and-display.md`
- Styles, events, screens, layouts, data binding, animations, widget lifecycle →
  `references/ui-patterns.md`
- FPS, RAM/flash, images, fonts, profiling, dev-vs-production config →
  `references/performance-and-memory.md`
- Logging, assertions, argument checks, sysmon, profiler, GDB introspection, fuzzing, UI tests →
  `references/debugging-and-testing.md`
- Upgrading v8→v9 or v9.5→v9.6 (rename tables, deprecations, v10 prep) →
  `references/migration.md`

## 2. The rules (and why)

1. **One thread touches LVGL at a time.** LVGL is not thread-safe: any LVGL call from another task
   must be wrapped in `lv_lock()` / `lv_unlock()` (requires `LV_USE_OS` set to your OS), or, with
   esp_lvgl_port, `lvgl_port_lock(0)` / `lvgl_port_unlock()`. Only `lv_tick_inc()` and
   `lv_display_flush_ready()` may be called from any thread. Event, timer, and animation callbacks
   already run inside `lv_timer_handler()`, so they need no lock. *Why:* LVGL's data structures are
   briefly inconsistent during every call; races corrupt the widget tree and show up as random crashes.
2. **Never call LVGL from an ISR.** From an interrupt, set a flag or post to a queue and let the LVGL
   task act on it. (`lv_tick_inc` and `lv_display_flush_ready` are the documented exceptions.)
3. **Call `lv_display_flush_ready(disp)` exactly once per `flush_cb` invocation**, when the pixels
   have actually been sent (from the DMA-complete callback if the transfer is async). Missing it →
   only the top strip updates / the UI freezes. Calling it early → tearing and corrupted frames
   because LVGL overwrites the buffer that is still being sent.
4. **Match the color format to the panel, and swap bytes in exactly one place.** For 16-bit SPI/8-bit
   parallel panels that need big-endian RGB565, set
   `lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565_SWAPPED)` and do **not** also swap in the
   flush callback. Nonsense colors almost always mean a mismatch or a double swap.
5. **Buffer sizes are in bytes in v9.** `lv_display_set_buffers(disp, buf1, buf2, sizeof(buf1), mode)`.
   For `DIRECT`/`FULL` the buffer must hold `hor_res * ver_res * bytes_per_pixel`.
6. **Prefer PARTIAL rendering with DMA double-buffering unless you have RAM for full frames.** Use
   ≥ 1/10 of the screen (1/5 recommended), keep draw buffers in **internal** RAM (LVGL hammers them),
   and flush with DMA so rendering and transfer overlap. With enough RAM, use two screen-sized buffers
   in `DIRECT` mode: gate the swap on `lv_display_flush_is_last()` (flush is called per area) and use the
   `flush_wait_cb` / sync / VSYNC callbacks so `flush_ready` is only signalled when the swap is safe.
7. **Drive the loop from `lv_timer_handler()`'s return value** and sleep that long. If it returns
   `LV_NO_TIMER_READY`, sleep a short fixed time (e.g. `LV_DEF_REFR_PERIOD`) because another thread
   may make a timer ready. If the handler runs in an RTOS task, give that task a generous stack
   (stack overflow looks like random crashes).
8. **Styles are `static` (or heap-allocated), initialized once, shared across widgets.** Never put an
   `lv_style_t` on the stack. `const` applies to prop arrays (e.g. transition `props[]`), not to `lv_style_t` itself.
   Per-widget local styles (`lv_obj_set_style_*`) cost RAM per widget; use them for one-offs only.
9. **Do not create/delete widgets or change styles inside draw events** (`LV_EVENT_DRAW_*`); rendering
   is in progress. LVGL asserts on this, but asserts are **off by default in 9.6** — without
   `LV_USE_ASSERT` it is silent corruption instead of a clean abort. Do that work in a normal event
   or timer.
10. **Delete safely.** Deleting a widget from inside its own event callback → use
    `lv_obj_delete_async()`. Remove or stop anything that outlives the widget and still points at it
    (user-created `lv_timer`s, animations with a custom `var`, raw pointers). Observers added with
    `lv_subject_add_observer_obj()` and widget bindings clean up automatically. To null out a
    pointer-to-pointer automatically on delete, register it with `lv_obj_null_on_delete(&my_ptr)`.
11. **Push data to the UI with Subjects/Observers** (`lv_subject_t`, `lv_label_bind_text`, ...) rather
    than polling timers that call `lv_label_set_text` on every tick. Update the UI only when the
    value changed and only when the user would see it.
12. **Write 9.6-clean code**: dedicated flag/state setters (`lv_obj_set_hidden`, `lv_obj_set_checked`, ...),
    `lv_subject_create(LV_SUBJECT_TYPE_*)` + `lv_subject_delete`,
    `LV_COLOR_FORMAT_DEFAULT`, no `NULL` display argument to `lv_display_*` / `lv_sysmon_*` calls, no private headers
    from `src/`. Generic `lv_obj_add_state` / `has_state` still work — the dedicated setters are just preferred. It costs nothing now and avoids a v10 rewrite.
    To prove it: build once with `-DLV_DISABLE_API_MAPPING` and every v8/v9 compatibility name becomes a compile error.
13. **Develop with safety nets, ship without them.** `LV_USE_CHECK_ARG` is **on by default** — keep it on in production; only `LV_USE_CHECK_OBJ_CLASSTYPE` /
    `LV_USE_CHECK_OBJ_VALIDITY` (which walk the class hierarchy and widget tree on every call) get turned off for release.
    Dev adds `LV_USE_LOG` + `LV_USE_ASSERT_*` + sysmon. Production reduces logging, keeps `LV_CHECK_ARG_LOG_MODE` at `MINIMAL`.
14. **Prototype UI in the PC simulator** (SDL via `lv_port_pc_vscode`), then move to hardware.
    Iteration is minutes instead of flash cycles, and layout/style bugs are separated from driver bugs.

## 3. Symptom triage

| Symptom | Most likely cause | Fix |
|---|---|---|
| Nothing drawn, driver never called | Tick or `lv_timer_handler()` not running | Set `lv_tick_set_cb()` or call `lv_tick_inc()`; make sure the handler loop/task runs |
| Only the top strip refreshes / UI freezes | `lv_display_flush_ready()` missing or never reached | Call it at end of flush (or in the DMA-done callback) |
| Garbage / diagonal shear | Wrong buffer stride, area width handling, or panel window setup | Test panel without LVGL; honor `area` (x1..x2, y1..y2 inclusive) |
| Wrong/swapped colors | Format mismatch, RGB/BGR order, or double byte-swap | `LV_COLOR_FORMAT_RGB565_SWAPPED` *or* manual swap, never both; check panel's RGB/BGR bit |
| Tearing | Single buffer, or `flush_ready` called before DMA finished | Double buffer + DMA, flush_ready in completion callback; direct mode + VSYNC if RAM allows |
| Random crash / hard fault | Threading without lock, ISR calling LVGL, stack too small, `LV_MEM_SIZE` too small, stack-allocated style | Rules 1, 2, 7, 8; raise `LV_MEM_SIZE`; enable asserts + logs |
| Works then crashes after screen changes | Dangling pointer to deleted widget, leaked timers/anims | Rule 10; `LV_EVENT_DELETE` cleanup; `lv_screen_load_anim(..., auto_del=true)` |
| Low FPS | Small/single partial buffer, slow SPI, heavy styles, `-Os` build | See performance reference; measure with sysmon first |
| Out of memory | `LV_MEM_SIZE` pool exhausted, image cache, many widgets | Create on demand, static label text, const styles, see memory section |
| "Check failed:" warnings you never see | `LV_USE_LOG` off, or `LV_CHECK_ARG_LOG_MODE` left at `NONE` (the `lv_conf.h` default) | Enable `LV_USE_LOG`; set `LV_CHECK_ARG_LOG_MODE LV_CHECK_ARG_LOG_MODE_VERBOSE` |
| Widget calls do nothing, no error | A failed `LV_CHECK_ARG` logs a warning and returns early — it does not fix the call | Read the log line; it names the function and the failing condition |
| PPA/DMA2D crash on ESP32-P4 | Draw buffer not cache-line aligned | `CONFIG_LV_DRAW_BUF_ALIGN=64` (verify against the installed component; defaults are 4 / stride 1) |
| Build warnings after upgrading to 9.6 | Deprecated APIs/options | `references/migration.md` |

## 4. Skeleton (generic port, v9.6 style)

```c
#include <lvgl/lvgl.h>

#define HOR_RES 320
#define VER_RES 240
#define BYTES_PER_PX (LV_COLOR_FORMAT_GET_SIZE(LV_COLOR_FORMAT_RGB565))

/* 1/10 screen, internal RAM, aligned. Prefer 1/5 + a second buffer if RAM allows. */
static uint8_t buf1[HOR_RES * VER_RES / 10 * BYTES_PER_PX] __attribute__((aligned(LV_DRAW_BUF_ALIGN)));
static uint8_t buf2[HOR_RES * VER_RES / 10 * BYTES_PER_PX] __attribute__((aligned(LV_DRAW_BUF_ALIGN)));

static uint32_t my_tick_ms(void) { return /* platform ms since boot, e.g. esp_timer_get_time()/1000 */ 0; }

static void flush_cb(lv_display_t * disp, const lv_area_t * area, uint8_t * px_map)
{
    /* Start an async (DMA) transfer of px_map to the panel window `area`.
     * area->x2/y2 are INCLUSIVE. Do NOT call flush_ready here if the transfer is async;
     * call lv_display_flush_ready(disp) from the transfer-complete callback instead. */
    panel_draw_bitmap_async(area->x1, area->y1, area->x2 + 1, area->y2 + 1, px_map);
}

static void touch_read_cb(lv_indev_t * indev, lv_indev_data_t * data)
{
    uint16_t x, y;
    if(touch_get_point(&x, &y)) {           /* your driver */
        data->state = LV_INDEV_STATE_PRESSED;
        data->point.x = x;
        data->point.y = y;
    } else {
        data->state = LV_INDEV_STATE_RELEASED;
    }
}

void ui_port_init(void)
{
    lv_init();
    lv_tick_set_cb(my_tick_ms);

    lv_display_t * disp = lv_display_create(HOR_RES, VER_RES);
    lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);  /* or ..._RGB565_SWAPPED for big-endian SPI panels */
    lv_display_set_buffers(disp, buf1, buf2, sizeof(buf1), LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(disp, flush_cb);

    lv_indev_t * indev = lv_indev_create();
    lv_indev_set_type(indev, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(indev, touch_read_cb);
}

/* Bare-metal / single task loop */
void ui_loop(void)
{
    for(;;) {
        uint32_t wait = lv_timer_handler();
        if(wait == LV_NO_TIMER_READY) wait = LV_DEF_REFR_PERIOD;
        lv_sleep_ms(wait);   /* or vTaskDelay(pdMS_TO_TICKS(wait)) under FreeRTOS */
    }
}
```

Notes on the skeleton:

- If other threads call LVGL, also cap the sleep (e.g. ≤ 10 ms) so work they trigger is not delayed.
- `lv_tick_set_cb(xTaskGetTickCount)` is only correct when the RTOS tick is 1 kHz; otherwise
  convert with `pdTICKS_TO_MS`.
- For ESP32 prefer the managed route (`esp_lvgl_port` / BSP) over hand-rolled init; see
  `references/porting-and-display.md`.

## 5. Confidence notes

Guidance in this skill comes from the official LVGL docs (v9.6 and dev docs, FAQ, migration guides,
Espressif integration pages) read in Oct 2026, plus well-established v9 usage. Two kinds of claims
deserve a quick check against the user's actual headers/docs before being stated as fact:

- Exact names of the *new* per-flag setters other than hidden/clickable/scrollable/checkable (confirm in
  `include/lvgl/core/lv_obj.h` or run `scripts/migration/migrate_obj_flags.py` from the LVGL repo).
- Component-specific APIs (esp_lvgl_port config structs, vendor draw units): they change between
  component versions; read the component's README for the installed version.
- Runtime log deprecations (the `NULL`-display warnings) are only visible with `LV_USE_LOG` on — their
  absence is not evidence the code is clean. Build with `-DLV_DISABLE_API_MAPPING` to check the names instead.

When unsure, say so and point to the header or doc page rather than guessing a signature.
