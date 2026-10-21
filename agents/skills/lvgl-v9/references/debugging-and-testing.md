# Debugging and testing reference (LVGL v9.6)

Contents: 1 Debug configuration · 2 Logging · 3 Argument checking · 4 Assertions ·
5 Sysmon · 6 Profiler · 7 GDB plug-in · 8 Monkey (fuzzing) · 9 UI testing · 10 A debug loop that works

---

## 1. Debug configuration

Three independent layers. All of them are cheap to switch, so use names instead of magic numbers:

```c
/* lv_conf.h */

/* 1. Logging */
#define LV_USE_LOG 1
#define LV_LOG_LEVEL LV_LOG_LEVEL_INFO
#define LV_LOG_PRINTF 1              /* or register your own sink */

/* 2. Argument validation — ON BY DEFAULT in 9.6, ~2900 checks */
#define LV_USE_CHECK_ARG 1
#define LV_CHECK_ARG_LOG_MODE LV_CHECK_ARG_LOG_MODE_VERBOSE
#define LV_CHECK_ARG_ASSERT_ON_FAIL 0   /* 1 = also run LV_ASSERT_HANDLER */

/* 3. Assertions — off by default */
#define LV_USE_ASSERT 1
#define LV_USE_ASSERT_MALLOC 1
#define LV_USE_ASSERT_NULL 1
#define LV_USE_ASSERT_STYLE 1
#define LV_USE_ASSERT_MEM_INTEGRITY 1
#define LV_USE_ASSERT_OBJ 1
```

What each layer is for:

| Layer | Catches | Typical setting |
|---|---|---|
| `LV_CHECK_ARG` | Wrong arguments to any public function (`NULL` widget, negative size, out-of-range value) | on, always |
| `LV_CHECK_ARG_LOG_MODE` | How much a failed check prints | `VERBOSE` in dev, `MINIMAL` in release |
| `LV_USE_ASSERT_*` | Internal invariants — the ones that mean "LVGL itself is inconsistent" | on in dev, off in release |
| `LV_USE_CHECK_OBJ_CLASSTYPE` | Passing a button where a label was expected | on in dev, off in release |
| `LV_USE_CHECK_OBJ_VALIDITY` | Use-after-delete (pointer not in the widget tree) | on in dev, off in release |

The last two default to `0` and are the ones you turn off for a release build — `lv_obj_has_class()`
walks the class hierarchy and `lv_obj_is_in_widget_tree()` walks the widget tree on **every call
site**, which is real overhead in render-heavy code. `LV_USE_ASSERT` and `LV_CHECK_ARG` stay on.

Two more worth knowing:

- `LV_ASSERT_HANDLER` is your hook for "what happens when an assert fires" — restart the MCU, halt,
  raise a fault. With `lv_conf.h` define it inline; with Kconfig use
  `LV_ASSERT_USE_CUSTOM_INCLUDE` + `LV_ASSERT_CUSTOM_INCLUDE` pointing at a header that defines it.
- `LV_DISABLE_ASSERT_HANDLER_INCLUDE_WARNING` silences the deprecation warning for the old
  `LV_ASSERT_HANDLER_INCLUDE` name if you cannot migrate it yet. The macro still works.

## 2. Logging

`LV_USE_LOG` + `LV_LOG_LEVEL` + an output path. Levels, most to least verbose:
`TRACE`, `INFO`, `WARN`, `ERROR`, `USER`, `NONE`. Setting a level also prints everything less verbose
than it, so `WARN` gives you `WARN` + `ERROR` + `USER`.

Output: `LV_LOG_PRINTF` uses `printf`. Otherwise register your own sink, which is what you want when
`printf` is unavailable or you want to prefix messages with a task name:

```c
static void my_log_cb(lv_log_level_t level, const char * buf)
{
    printf("[%d] %s", (int)level, buf);
}

void ui_log_init(void) { lv_log_register_print_cb(my_log_cb); }
```

Use `LV_LOG_USER(...)` for your own messages — unlike the other macros it adds no file/line/func
context, so it reads cleanly in production logs.

Route by platform: ESP-IDF → `LV_LOG_PRINTF` (LVGL logs through `printf`), Zephyr → its own printk
hook, bare metal → a UART ring buffer or RTT.

## 3. Argument checking

`LV_CHECK_ARG` (roughly 2,900 call sites across 168 source files) validates arguments before the
function does any work. On failure it logs and **returns early**:

```
[Warn]  (5.123, +12)  lv_label_set_text: Check failed: obj != NULL  lv_label.c:134
```

What this changes for you:

- **A failed check has no effect.** Getters return `NULL`/`0`, setters do nothing. It converts a
  crash into one log line; it does not make the invalid call work.
- **The default logs nothing.** `LV_CHECK_ARG_LOG_MODE` is `NONE` in `lv_conf_template.h`
  (VERBOSE under Kconfig when logging is on), and logging itself is off by default. A stock build
  rejects bad calls silently. If you are debugging a "my setter does nothing" report, check these
  two options before anything else.
- **Two widget layers are opt-in**: `LV_USE_CHECK_OBJ_CLASSTYPE` (wrong widget type) and
  `LV_USE_CHECK_OBJ_VALIDITY` (use-after-delete). `LV_USE_CHECK_OBJ_PARENT_LINK` additionally
  verifies parent/child links and requires VALIDITY plus `LV_USE_ASSERT`.

Public API macros:

```c
LV_CHECK_ARG(cond, action);                 /* action runs instead of the body */
LV_CHECK_OBJ(obj, &lv_label_class, return); /* NULL + class (+ validity) checks */
LV_CHECK_ARG_MSG(cond, action, "message");
```

The NULL check happens regardless of whether the class/validity layers are enabled — the layers are
cumulative, not alternatives.

## 4. Assertions

Different from argument checking: assertions guard LVGL's own internal invariants, and they abort
(or run `LV_ASSERT_HANDLER`) rather than return.

```c
#define LV_USE_ASSERT 1
#define LV_USE_ASSERT_NULL 1         /* internal NULL derefs */
#define LV_USE_ASSERT_MALLOC 1       /* allocation failures */
#define LV_USE_ASSERT_STYLE 1        /* style cache consistency */
#define LV_USE_ASSERT_MEM_INTEGRITY 1/* pool corruption — slow */
#define LV_USE_ASSERT_OBJ 1          /* LV_ASSERT_OBJ(), itself deprecated → LV_CHECK_OBJ */
```

`LV_ASSERT_OBJ` and `LV_ASSERT_STYLE` are deprecated in 9.6 and both map to `LV_CHECK_ARG`
alternatives: use `LV_CHECK_OBJ(obj, &lv_label_class, return)` and
`LV_CHECK_ARG(style != NULL, return)`.

Assertions are off by default and LVGL's own advice is to leave them off in production: they are a
development tool, not a runtime safety net.

## 5. Sysmon

Needs `LV_USE_SYSMON` **and** `LV_USE_LABEL` **and** `LV_USE_OBSERVER`.

```c
#define LV_USE_SYSMON 1
#define LV_USE_PERF_MONITOR 1
#define LV_USE_MEM_MONITOR 1
#define LV_USE_PERF_MONITOR_POS LV_ALIGN_BOTTOM_RIGHT   /* default */
#define LV_USE_MEM_MONITOR_POS LV_ALIGN_BOTTOM_LEFT     /* default */
#define LV_USE_PERF_MONITOR_LOG_MODE 0                  /* 1 = print to console instead of drawing */
```

`LV_USE_MEM_MONITOR` requires `LV_USE_STDLIB_MALLOC == LV_STDLIB_BUILTIN` — with a C-library heap
there is no pool to report, and the build errors out.

```c
lv_display_t * disp = lv_display_get_default();
lv_sysmon_show_performance(disp);   /* pass the display: NULL is deprecated in 9.6 */
lv_sysmon_show_memory(disp);
```

Reads as `32 FPS, 45% CPU` / `8 ms` (render | flush) and `24.8 kB (76%)` / `32.4 kB max, 18% frag.`.
Pause/resume with `lv_sysmon_performance_pause()` / `lv_sysmon_performance_resume()` — useful when
you want a clean measurement window. `lv_sysmon_create()` builds a generic monitor if you want your
own layout. `lv_sysmon_performance_dump()` prints the FPS data recorded since the last dump without
drawing anything, so it is the one to use in log mode or in a service build.

It works by timing display events, so `LV_EVENT_REFR_START`/`READY`, `RENDER_START`/`READY` and
`FLUSH_*` are also yours to use directly — toggle a GPIO from a callback and look at a logic
analyzer when you need exact numbers rather than averages.

## 6. Profiler

`LV_USE_PROFILER` records timestamped trace events (render phases, input events) into a ring buffer
and emits them in Android `systrace` format, which [Perfetto](https://ui.perfetto.dev) opens.

```c
#define LV_USE_PROFILER 1
#define LV_USE_PROFILER_BUILTIN 1
#define LV_USE_PROFILER_BUILTIN_POSIX 1     /* POSIX: write straight to the trace file */
#define LV_PROFILER_BUILTIN_BUF_SIZE 8192    /* bigger = less interference, more RAM */
```

Runtime setup:

```c
lv_profiler_builtin_config_t cfg;
lv_profiler_builtin_config_init(&cfg);
cfg.buf_size = 8192;
cfg.tick_per_sec = 1000000;              /* default is 1000 */
cfg.tick_get_cb = my_us_tick_cb;         /* sub-ms resolution */
lv_profiler_builtin_init(&cfg);
lv_profiler_builtin_set_enable(true);
lv_profiler_builtin_flush();             /* write the buffer out */
```

`lv_profiler_builtin_config_t` is only forward-declared in `lv_types.h`; the field list lives in the
private `src/debugging/profiler/lv_profiler_builtin_private.h` and is
`buf_size`, `tick_per_sec`, `tick_get_cb`, `flush_cb`, `tid_get_cb`, `cpu_get_cb`. It has been stable
across v9, but check that header if your build ever rejects a field. `lv_profiler_builtin_posix_init()`
is a one-liner shortcut when you are on a POSIX host.

Default timestamps come from `lv_tick_get()` at 1 ms, which cannot resolve intervals below a
millisecond — supply a microsecond callback (`micros()` on Arduino, `esp_timer_get_time()` on ESP32,
a DWT cycle counter on Cortex-M) before concluding that something is "free".

## 7. GDB plug-in

`lvgl/scripts/gdb` ships a Python plug-in. Load it in any GDB session (J-Link, OpenOCD, or a core
dump):

```
(gdb) source lvgl/scripts/gdb/gdbinit.py
(gdb) dump obj -L 3
Display @0x519000005a80
  Screen @0x507000003eb0 (sys_layer)
    lv_obj @0x507000003eb0  (0,0) 800x480
      lv_label @0x50e000000820  "0 FPS, 0% CPU"  (0,0) 104x32
  Screen @0x507000025da0 (act_scr)
    lv_obj @0x507000025da0  name=main_screen  (0,0) 800x480
      lv_button @0x507000025e80  name=ball_1  (10,60) 40x22  state=FOCUSED
```

Commands worth knowing:

| Command | Shows |
|---|---|
| `dump obj [-L n]` / `info widget [...]` | The widget tree, or everything known about one widget |
| `dump display [-f bmp\|png]` | The draw buffers as image files — look at what was actually rendered |
| `dump draw_task <lv_layer_t *>` | Draw tasks queued on a layer |
| `info draw_unit` | Draw-unit internals (which backend, buffer sizes) |
| `info obj_class [--all] [<class>]` | The widget class hierarchy |
| `info style <lv_style_t>` / `info style --obj <lv_obj_t *>` | One style, or every style on a widget |
| `dump anim` / `dump timer` / `dump indev` / `dump group` | What is currently scheduled |
| `dump cache image\|image_header`, `check cache image` | Image cache contents and sanity |
| `info subject <lv_subject_t *>` | A subject and its observers |
| `dump dashboard [--json\|--viewer]` | HTML/JSON dump of all runtime state |
| `info lvgl_version` | Target and plug-in versions — check these match |

Widgets can be named (`info widget ball_1`, resolved the same way as `lv_obj_get_name_resolved()`:
a trailing `#` becomes the sibling index, unnamed widgets answer to `<class>_<n>`), addressed
(`my_label`, `obj->parent`, `0x50e000000820`), or reached by path from a screen
(`main_screen_0/lv_button_0/label3`).

This is the fastest way to answer "is the widget even there, and what state is it in?" — including
the use-after-delete case, where the pointer is simply not in any tree.

## 8. Monkey (fuzzing)

`LV_USE_MONKEY` feeds random input at random intervals. It is the cheapest way to find crashes that
only happen on the tenth interaction.

```c
lv_monkey_config_t cfg;
lv_monkey_config_init(&cfg);
cfg.type = LV_INDEV_TYPE_POINTER;          /* POINTER / ENCODER / BUTTON / KEYPAD */
cfg.period_range.min = 50;
cfg.period_range.max = 300;
cfg.input_range.min = 0;
cfg.input_range.max = 100;
lv_monkey_t * monkey = lv_monkey_create(&cfg);
lv_monkey_set_enable(monkey, true);
```

For `LV_INDEV_TYPE_BUTTON`, `lv_monkey_get_indev(monkey)` returns the indev so you can map key IDs to
coordinates with `lv_indev_set_button_points()`. Run it with assertions and argument checking on,
under a watchdog, and treat any assert as a bug report.

## 9. UI testing

`LV_USE_TEST` (assumes a host/desktop target with no memory constraints) emulates displays, input
and time, and compares screenshots against reference PNGs. It is designed to drop into Unity,
GoogleTest or any other framework.

```c
#define LV_USE_TEST 1
#define LV_USE_TEST_SCREENSHOT_COMPARE 1
/* LV_USE_LODEPNG is required by screenshot compare; Kconfig selects it for you,
   with lv_conf.h you must enable it yourself. */
#define LV_USE_LODEPNG 1
#define LV_TEST_SCREENSHOT_CREATE_REFERENCE_IMAGE 0   /* 0 = never auto-create references */
```

```c
lv_display_t * disp = lv_test_display_create(800, 480);   /* in-memory framebuffer, XRGB8888 */
lv_test_indev_create_all();                               /* pointer + keypad + encoder */

lv_test_mouse_move_to(20, 30);
lv_test_mouse_press();
lv_test_wait(20);                 /* runs lv_timer_handler() every ms */
lv_test_mouse_move_by(0, 100);
lv_test_mouse_release();

int32_t y_end = lv_obj_get_y(child);
assert(y_start + 100 == y_end);
```

- `lv_test_wait(ms)` steps `lv_timer_handler()` each millisecond, so timed behaviour (long press,
  long-press repeat, debounce) is exercised realistically. `lv_test_fast_forward(ms)` jumps ahead and
  runs the handler once — cheap, but it skips intermediate timer fires.
- Both call `lv_refr_now(NULL)` so coordinates and animations settle.
- Memory-leak assertions: `size_t before = lv_test_get_free_mem();` … create/delete … `after`. Use a
  tolerance of about 32 bytes for fragmentation, or loop the cycle to average it out.
  `lv_test_get_free_mem()` only works with `LV_STDLIB_BUILTIN` — with another allocator LVGL
  substitutes a constant, so use `lv_test_get_allocation_count()` (live block count) instead.
- `lv_test_screenshot_compare("ref/main.png")` returns a result and, on mismatch, writes
  `<name>_err.png` next to the reference and prints the first divergent pixel plus both colors. If the
  reference is missing it is created from the render — handy for seeding, dangerous in CI
  (`LV_TEST_SCREENSHOT_CREATE_REFERENCE_IMAGE 0` to forbid it). References must be 32-bit PNGs
  matching the display size; the test display converts to XRGB8888 for comparison.
- `lv_test_get_allocation_count()` counts allocations, which catches leaks that a free-memory delta
  can hide behind fragmentation.

## 10. A debug loop that works

1. Reproduce with logging on and `LV_CHECK_ARG_LOG_MODE_VERBOSE`. Read the log line: it names the
   function and the exact condition.
2. Turn on `LV_USE_CHECK_OBJ_VALIDITY` + `LV_USE_CHECK_OBJ_CLASSTYPE` and the `LV_USE_ASSERT_*`
   family. Fix everything they report; a failing widget check almost always points at the real bug.
3. If it is a data problem, drop into GDB: `dump obj` to confirm the tree, `info widget <name>` for
   the widget's state and fields, `dump anim` / `dump timer` for what is scheduled.
4. If it is a stress or interaction problem, run Monkey under a watchdog.
5. If it is a rendering difference, `dump display -f png` and look at the frame.
6. If it is a regression, profile with the built-in profiler and compare traces in Perfetto.