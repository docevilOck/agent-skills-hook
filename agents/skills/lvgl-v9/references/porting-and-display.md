# Porting and display reference (LVGL v9.6)

Contents: 1 Init order · 2 Tick · 3 Timer handler and sleeping · 4 Threads and RTOS ·
5 Display setup (buffers, render modes, flush) · 6 Color format and byte swapping ·
7 Input devices · 8 Configuration · 9 Building and packaging · 10 ESP32 / ESP-IDF ·
11 Pipeline picture

---

## 1. Init order

1. Initialize hardware (clocks, SPI/RGB/MIPI peripheral, panel, touch).
2. `lv_init()`.
3. Tick: `lv_tick_set_cb()` (or `lv_tick_inc()` from a timer).
4. `lv_display_create()` → color format → buffers → flush callback.
5. `lv_indev_create()` for each input device.
6. Build UI (inside the LVGL task, or under `lv_lock()`).
7. Start the `lv_timer_handler()` loop/task.

Verify the panel works **without LVGL** first (fill it red, then draw a gradient). If the panel is
wrong, no amount of LVGL tuning helps.

## 2. Tick

LVGL needs a millisecond clock. Either:

- `lv_tick_set_cb(cb)` where `cb` returns ms since boot (preferred), or
- `lv_tick_inc(x)` from a periodic timer/ISR every `x` ms.

Platform one-liners: SDL `SDL_GetTicks`; STM32 `HAL_GetTick`; Arduino wrapper around `millis()`;
ESP32 wrapper returning `esp_timer_get_time() / 1000`; FreeRTOS `xTaskGetTickCount` **only if the
tick rate is 1000 Hz** (otherwise convert with `pdTICKS_TO_MS`).

`lv_tick_inc()` may be called from any thread/ISR if a 32-bit write is atomic on your platform.

## 3. Timer handler and sleeping

Everything LVGL does (rendering, input reads, animations, widget timers, your `lv_timer`s) runs as
a timer inside `lv_timer_handler()`. Call it periodically from `main()` or one OS task.

```c
for(;;) {
    uint32_t wait = lv_timer_handler();               /* ms until next timer is due */
    if(wait == LV_NO_TIMER_READY) wait = LV_DEF_REFR_PERIOD;  /* nothing scheduled: check again soon */
    lv_sleep_ms(wait);
}
```

- `LV_NO_TIMER_READY` (`UINT32_MAX`) is returned when there is nothing to redraw, no enabled indevs,
  no running animations, and no user timers. Do not sleep forever: either sleep briefly, wait on an
  event you post when LVGL has work, or sleep the CPU.
- With `LV_USE_OS` set, `lv_sleep_ms` is the OS sleep; otherwise it is a blocking delay.
- Low-power pattern: skip `lv_timer_handler()` and sleep the MCU when
  `lv_display_get_inactive_time(lv_display_get_default()) > N` and `lv_anim_count_running() == 0`.
- 9.6 adds `uint32_t lv_timer_get_time_to_next(void)` if you need finer scheduling (distinct from the older `lv_timer_get_time_until_next()` / `lv_timer_get_next()`), and two loop shortcuts: `lv_timer_periodic_handler()` runs the super-loop for you (call it as often as you like; it decides when to actually run the handler), and `lv_timer_handler_run_in_period(period_ms)` forces a handler run every `period_ms`.
- `lv_timer_get_idle()` reports how much idle time was left in the last handler run — useful for spotting a UI that is busy but not visible.

## 4. Threads and RTOS

**LVGL is not thread-safe.** Do not call any LVGL function while another LVGL call (including
`lv_timer_handler`) is executing in another thread.

Set `LV_USE_OS` to your OS (`LV_OS_NONE`, `LV_OS_PTHREAD`, `LV_OS_FREERTOS`, `LV_OS_CMSIS_RTOS2`, `LV_OS_RTTHREAD`, `LV_OS_WINDOWS`, ...) then:

```c
void lvgl_task(void * arg) {
    for(;;) {
        uint32_t wait = lv_timer_handler();   /* takes/releases the lock internally */
        if(wait == LV_NO_TIMER_READY || wait > 10) wait = 10;   /* other threads may make timers ready */
        vTaskDelay(pdMS_TO_TICKS(wait));
    }
}

void sensor_task(void * arg) {
    for(;;) {
        int t = read_temperature();
        lv_lock();
        lv_subject_set_int(temperature_subject, t);   /* any LVGL call goes inside the lock */
        lv_unlock();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

- No lock needed inside event/timer/animation callbacks (already inside `lv_timer_handler`).
- Allowed from any thread without a lock: `lv_tick_inc()`, `lv_display_flush_ready()`.
- Do **not** call LVGL from an ISR, **except** `lv_tick_inc()` (if a 32-bit write is atomic) and `lv_display_flush_ready()`. Post everything else to a queue or set a flag; let the LVGL task apply it.
- Hold the lock for a *group* of related calls, not one lock per call, and never block on I/O while
  holding it (the UI freezes).
- If you run `lv_timer_handler()` in an RTOS task, increase its stack size when you see random
  crashes (this is in LVGL's own FAQ).
- Alternative design that avoids shared locking: producer tasks write into a queue/atomic and a single
  LVGL-thread `lv_timer` drains it into subjects. `lv_async_call(cb, data)` schedules work for the next
  handler run — from another thread, still under the lock, and `data` must stay valid until it runs.
- Multiple independent LVGL instances are possible by supplying your own `lv_global.h` (through
  `LV_GLOBAL_USE_CUSTOM_INCLUDE` + `LV_GLOBAL_CUSTOM_INCLUDE`, resolved through the `LV_GLOBAL_DEFAULT()`
  macro) plus thread-local storage. Rare; read the Integration overview page first.

## 5. Display setup

```c
lv_display_t * disp = lv_display_create(hor_res, ver_res);
lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);
lv_display_set_buffers(disp, buf1, buf2_or_NULL, size_in_BYTES, render_mode);
lv_display_set_flush_cb(disp, flush_cb);
```

The first display created becomes the default display; `lv_display_set_default()` moves that role to
another display. v9.6 deprecates passing `NULL` as the display to ~50 `lv_display_*` plus 8
`lv_sysmon_*` functions: use `lv_display_get_default()` explicitly. Note this one is a **runtime** log
message (`LV_LOG_DEPRECATED`), not a build warning — you only see it with `LV_USE_LOG` on, and the
docs only promise it "will be considered an error in future versions".

### Render modes

| Mode | Buffer | Behavior | Use when |
|---|---|---|---|
| `PARTIAL` | Smaller than screen (≥ 1/10, 1/5 recommended) | Renders only invalidated areas in chunks; `flush_cb` is called per chunk and must copy the chunk to the panel window | Default for MCUs; lowest RAM |
| `DIRECT` | Whole screen (1 or 2 buffers) | Renders into the right place of a full frame buffer, only invalidated areas; with 2 buffers LVGL syncs the other buffer after flush; `flush_cb` typically just switches the frame-buffer address | RGB/MIPI panels with frame buffers, enough RAM |
| `FULL` | Whole screen (1 or 2 buffers) | Redraws the entire screen every refresh | Simplest traditional double-buffering; wastes CPU on unchanged screens |

Buffers:
- **One buffer**: LVGL renders, calls flush, then *waits* for `lv_display_flush_ready()` before it
  renders again. Serial, simple.
- **Two buffers**: render into one while DMA sends the other. Needs DMA (or a peripheral doing the
  transfer) to be worth it.
- **Three buffers** (`lv_display_set_3rd_draw_buffer`): removes idle time waiting for DMA completion
  in direct/full modes.
- Custom stride for a controller: `lv_display_set_buffers_with_stride()`.
- Draw buffers should be aligned to `LV_DRAW_BUF_ALIGN` (default 4; some accelerators need more,
  e.g. 64 for ESP32-P4 PPA).

Sizing example (RGB565 = 2 B/px, 320×240): full frame = 153,600 B; 1/10 = 15,360 B; 1/5 = 30,720 B.

### The flush callback contract

```c
void flush_cb(lv_display_t * disp, const lv_area_t * area, uint8_t * px_map);
```

- `area` coordinates are **inclusive** (`x2`/`y2` are the last pixel). Width = `x2 - x1 + 1`.
- LVGL may call flush multiple times per frame; `lv_display_flush_is_last(disp)` tells you when it
  is the final chunk (useful to trigger a VSYNC swap or backlight enable on the first frame).
- You **must** eventually call `lv_display_flush_ready(disp)` once per call. This is the single most
  common porting bug. It may be called from the DMA-complete callback or another thread.
- Optionally set `lv_display_set_flush_wait_cb()` to block on a semaphore instead of LVGL spinning
  while it waits for the previous flush. The wait callback just blocks until the previous transfer is done; it does not call `flush_ready` itself.
- Keep the flush callback fast and non-blocking; prefer async DMA.

Direct mode with two frame buffers (RGB/MIPI panels): in `flush_cb`, only act when `lv_display_flush_is_last()`
tells you it is the final chunk, then tell the panel to display `px_map`; call `lv_display_flush_ready()` from the VSYNC-done interrupt so
LVGL does not block while waiting for the buffer swap. See also `lv_display_set_sync_cb()` for pre-render sync in 9.6.

### The sync callbacks (new in 9.6)

With two frame buffers in DIRECT/FULL mode LVGL has to keep the buffers in step: it copies newly
rendered areas into the other buffer after the flush, but first it may need to wait for the panel to
finish scanning that area out. `lv_display_set_sync_cb(disp, cb)` is called before rendering an area
and `lv_display_set_sync_wait_cb(disp, cb)` when LVGL has to block until the previous sync finished —
the pair mirrors flush/flush-wait. The matching display-side helpers are
`lv_display_sync_ready()` and `lv_display_sync_is_last()`, and the events are `LV_EVENT_SYNC_START` /
`SYNC_FINISH` / `SYNC_WAIT_START` / `SYNC_WAIT_FINISH`. If you do not set the callbacks, LVGL assumes
your flush callback handles the swap itself, which is the usual case.

VSYNC plumbing, if your controller exposes it: `lv_display_send_vsync_event()`,
`lv_display_register_vsync_event()` / `lv_display_unregister_vsync_event()`, plus `LV_EVENT_VSYNC`
and `LV_EVENT_VSYNC_REQUEST`.

### Monochrome (I1) panels

- Use `LV_COLOR_FORMAT_I1`; LVGL reserves 8 bytes at the start of the buffer for a palette, so make
  the buffer 8 bytes larger and **skip the palette** in `flush_cb` (`px_map += 8`).
- Redrawn areas are rounded to byte boundaries; for controllers needing N×8 rows/columns add a
  rounder callback on `LV_EVENT_INVALIDATE_AREA`.
- Round the horizontal resolution up to a multiple of 8.
- Use `lv_draw_i1_convert_to_vtiled()` (9.6 name; `lv_draw_sw_i1_convert_to_vtiled` in ≤ 9.5) for
  page-addressed controllers.

### Rotation and resolution

- `lv_display_set_rotation(disp, LV_DISPLAY_ROTATION_90)` does **not** rotate anything: it swaps the
  horizontal/vertical resolutions internally and emits `LV_EVENT_RESOLUTION_CHANGED` so your driver
  can reconfigure. Rotating pixels is your job — either in the controller (preferred) or with
  `lv_draw_rotate(src, dst, w, h, src_stride, dst_stride, rotation, cf)` plus
  `lv_display_rotate_area(disp, &area)` in the flush callback.
- Constraint worth knowing: in DIRECT mode the small changed areas are rendered straight into the frame
  buffer and cannot be rotated afterwards, so only a whole-frame-buffer rotation works there. PARTIAL
  mode can rotate each chunk. FULL mode works if the buffer you render into differs from the one you
  rotate into and the render buffer has no stride requirement.
- Resolution changes at runtime: `lv_display_set_resolution()` (also `lv_display_set_physical_resolution()`
  and `lv_display_set_dpi()`), each sending `LV_EVENT_RESOLUTION_CHANGED`. Changing the color format at
  runtime sends `LV_EVENT_COLOR_FORMAT_CHANGED`.
- Display events (`lv_display_add_event_cb(disp, cb, event, user_data)` returns an `lv_event_dsc_t *`;
  remove with `lv_display_remove_event(disp, index)` or
  `lv_display_remove_event_cb_with_user_data(disp, cb, user_data)`): `LV_EVENT_FLUSH_START/FINISH`,
  `FLUSH_WAIT_START/FINISH`, `RENDER_START/READY`, `REFR_START/READY`, `INVALIDATE_AREA`,
  `SCREEN_LOAD_START/LOADED`, `VSYNC`: useful for FPS counters and logic analyzer pins.
  `LV_EVENT_INVALIDATE_AREA` is the one that can *modify* the area (`lv_event_get_param(e)`), which is
  how you round areas for monochrome panels.

## 6. Color format and byte swapping

| Panel interface | Typical setting |
|---|---|
| RGB565 over SPI / 8-bit parallel (big-endian wire order) | `LV_COLOR_FORMAT_RGB565_SWAPPED` (no manual swap needed) |
| RGB565 over native 16-bit RGB/MIPI bus | `LV_COLOR_FORMAT_RGB565` |
| 24-bit | `LV_COLOR_FORMAT_RGB888` (3 B/px) or `XRGB8888` (4 B/px, usually faster) |
| Transparent screen / compositor | `LV_COLOR_FORMAT_ARGB8888` (or `ARGB8888_PREMULTIPLIED` for Wayland) |
| Monochrome | `LV_COLOR_FORMAT_I1` |

- **Swap in exactly one place.** Options, in order of preference: (1) `RGB565_SWAPPED` format,
  (2) let the SPI host/DMA swap, (3) `lv_draw_rgb565_swap(px_map, px_count)` in `flush_cb`
  (`lv_draw_sw_rgb565_swap` in ≤ 9.5). Combining them undoes the swap and gives wrong colors.
- A display's format can be changed at runtime with `lv_display_set_color_format()`, but then
  buffers must be large enough and `flush_cb` must handle the layout.
- `lv_color_t` is always RGB888 internally in v9 regardless of display format. Do not assume it
  is 16-bit.
- Some panels need RGB/BGR order set in the controller (MADCTL) instead of in LVGL.
- Images should be converted to the display's native format to avoid per-frame conversion.

## 7. Input devices

```c
lv_indev_t * indev = lv_indev_create();
lv_indev_set_type(indev, LV_INDEV_TYPE_POINTER);   /* KEYPAD, ENCODER, BUTTON also exist */
lv_indev_set_read_cb(indev, read_cb);
```

- Read callback: set `data->state` (`LV_INDEV_STATE_PRESSED/RELEASED`) and `data->point` for pointers,
  `data->key` for keypads, `data->enc_diff` for encoders. It runs inside `lv_timer_handler()`.
- Keep reads short; do not block on I2C with long timeouts. Debounce/interrupt-gate if the touch
  controller is slow.
- Keypad/encoder navigation needs **groups**: `lv_group_create()`, `lv_group_add_obj()`,
  `lv_indev_set_group()`. Pointer devices do not need groups.
- Indevs can be bound to a specific display with `lv_indev_set_display()`.
- Gesture and click timing thresholds are configurable in 9.6 (`lv_indev_set_gesture_min_velocity/min_distance`, dedicated `lv_indev_set_double_click_time`, `lv_indev_set_scroll_limit`). The compile-time defaults behind them are now `LV_INDEV_DEF_*` options (`LV_INDEV_DEF_DOUBLE_CLICK_TIME`, `LV_INDEV_DEF_LONG_PRESS_TIME`, `LV_INDEV_DEF_GESTURE_MIN_VELOCITY`, `LV_INDEV_DEF_SCROLL_THROW`, ...), which is the right place to change them if you want one value for the whole app.
- Physical button indevs report a key id; map it to screen coordinates once with `lv_indev_set_button_points(indev, points)`.
- Curved / concave panels: `lv_indev_set_ccw()` / `lv_indev_get_ccw()` / `lv_indev_clear_ccw()` describe the panel's curvature so hit testing stays accurate.

## 8. Configuration

- Start from `lv_conf_template.h` → copy to `lv_conf.h` next to the `lvgl` folder, change the first
  `#if 0` to `#if 1`. In 9.6 this template is generated from Kconfig, so every default matches
  Kconfig; hand-written `lv_conf.h` is still fully supported.
- Set `LV_COLOR_FORMAT_DEFAULT` to match the panel (9.6) / `LV_COLOR_DEPTH` (≤ 9.5).
- `LV_MEM_SIZE` is in bytes (the internal TLSF pool). Too small → random failures when creating
  widgets or loading images.
- `LV_USE_OS` must match your OS to get `lv_lock/lv_unlock` and the OS-aware sleep.
- Disable widgets, fonts, libraries you do not use (flash and RAM).
- Enable `LV_USE_LOG` during bring-up (route to `printf`/ESP_LOG).
- v9.6 `LV_USE_CHECK_ARG` is **on by default** (~2,900 checks); it logs a warning and returns early
  instead of dereferencing bad arguments. It only *prints* if `LV_USE_LOG` is on **and**
  `LV_CHECK_ARG_LOG_MODE` is not `NONE` — and `NONE` is the `lv_conf.h` default, so a stock build
  fails silently. Set `LV_CHECK_ARG_LOG_MODE LV_CHECK_ARG_LOG_MODE_VERBOSE` while bringing a board up.
  For use-after-delete and wrong-widget-type bugs also enable `LV_USE_CHECK_OBJ_VALIDITY` and
  `LV_USE_CHECK_OBJ_CLASSTYPE` (both default off) — and turn them back off for release, since they walk
  the widget tree on every call. `LV_USE_ASSERT_*` are off by default too.
- Using Kconfig? Function-like macros (`LV_ASSERT_HANDLER`, `LV_ATTRIBUTE_*`, `LV_FONT_CUSTOM_DECLARE`)
  cannot be Kconfig values; use the per-module `*_USE_CUSTOM_INCLUDE` + `*_CUSTOM_INCLUDE` header
  (`FONT`, `ASSERT`, `ATTRIBUTE`, `SYSMON`, `NEMA`, and the global custom include).
- Old v9.0 note: keep `lv_conf.h` free of unrelated includes (the migration guide warned that
  `<stdint.h>` there broke assembly-optimized code).
- Build with warnings visible after upgrading: renames are `#warning`s. Add
  `-DLV_DISABLE_API_MAPPING` for a verification build that turns every compatibility alias into a
  compile error.

## 9. Building and packaging (new in 9.6)

9.6 made LVGL behave like an ordinary system library. Worth knowing before you hand-roll a build:

- **Dependencies resolve themselves.** Every dependency (SDL2, FreeType, GStreamer, libdrm, ...) goes
  through `find_package`, then pkg-config, and anything still missing is fetched and built from source.
  You no longer install them by hand before configuring.
- **Installed LVGL is a real library.** `lvgl.pc` and `lvglConfig.cmake` ship with the install and name
  every library LVGL was compiled against, so `find_package(lvgl)` works from another project.
- **Presets.** `configs/defconfigs/` has ready-made starting points: `sdl2`, `wayland`, `drm` and
  `empty` (the minimal one that replaced `LV_CONF_MINIMAL`).
- **Ubuntu packages.** LVGL is published through a Launchpad PPA, so `apt install` works for host-side
  development.
- **Kconfig integration.** `cmake -B build -DLV_BUILD_USE_KCONFIG=ON [-DLV_BUILD_DEFCONFIG_PATH=...]`
  makes LVGL's CMake read your `.config` / `defconfig`. `LV_BUILD_DEFCONFIG_PATH` also accepts a
  `;`-separated list, merged left to right, so you can layer `my_overrides.defconfig` on top of a
  shipped preset.
- **`lv_conf.defaults`** is the low-friction alternative to a hand-merged `lv_conf.h`: keep one option
  per line, then run `scripts/generate_lv_conf.py` after each upgrade to regenerate `lv_conf.h` from the
  current template.
- Test coverage rose from 78.7% to 82.2% in the 9.6 cycle — a reasonable signal of how well-used a given
  path is, and worth weighting when you rely on an obscure feature.

## 10. ESP32 / ESP-IDF

### Recommended integration

Use Espressif's `esp_lvgl_port` component (LVGL docs call it the recommended way to connect an ESP32
chip's displays and inputs). It supports LVGL v8 and v9 and wraps esp_lcd / touch drivers, adds
touch/encoder/button/USB-HID input, rotation, and runs `lv_timer_handler()` in its own task, so you
do not call it yourself:

```
idf.py add-dependency "espressif/esp_lvgl_port^2.9.0"   # registry version as of Oct 2026; check for newer
idf.py add-dependency "espressif/esp_lcd_<panel>"    # e.g. a controller driver from esp-bsp
idf.py add-dependency "lvgl/lvgl^9.*"                # e.g. "lvgl/lvgl^9.6.0" to pin
```

Pin the LVGL version in `idf_component.yml` if you do not want automatic upgrades
(`lvgl/lvgl` with a version range such as `^9.*`).

Usage pattern (names per the docs' BSP/port examples; confirm config struct fields against the
installed version's README):

```c
const lvgl_port_cfg_t lvgl_cfg = ESP_LVGL_PORT_INIT_CONFIG();
ESP_ERROR_CHECK(lvgl_port_init(&lvgl_cfg));
/* ...lvgl_port_add_disp(...) / lvgl_port_add_touch(...) with your esp_lcd handles... */

lvgl_port_lock(0);            /* with a BSP this is bsp_display_lock(0) */
build_ui();                   /* every LVGL call outside the LVGL task must be locked */
lvgl_port_unlock();
```

`lvgl_port_lock(timeout_ms)` is the ESP32 equivalent of `lv_lock()`: use it from `app_main`, sensor
tasks, Wi-Fi/MQTT callbacks. A separate, newer Espressif component, `esp_lvgl_adapter` (0.7.x as of
Oct 2026; it pulls in `esp_lcd_touch`, `esp_lv_decoder`, `esp_lv_fs`, FreeType, …), is the other
option — unified display management, tearing control, thread safety and PPA acceleration. Evaluate
both READMEs against your board before choosing; they are not drop-in replacements for each other.

If you hand-roll the port with esp_lcd: the esp_lcd "color transfer done" callback is the place to
call `lv_display_flush_ready()` (it runs in ISR context, so do nothing else with LVGL there and keep
the callback in IRAM); use `LV_COLOR_FORMAT_RGB565_SWAPPED` for SPI panels.

### `sdkconfig.defaults` tuning (from LVGL's Espressif "tips and tricks")

IDF defaults optimize for size; LVGL benefits from speed:

```ini
CONFIG_COMPILER_OPTIMIZATION_PERF=y        # up to ~30% faster overall, uses SIMD where possible
CONFIG_LV_ATTRIBUTE_FAST_MEM_USE_IRAM=y    # put LVGL's hot code in IRAM
CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240=y      # or _360 on P4 (some options need CONFIG_IDF_EXPERIMENTAL_FEATURES=y)
```

PSRAM boards (lets you copy read-only data to PSRAM, and use direct mode + dual buffers):

```ini
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_HEX=y
CONFIG_SPIRAM_USE=y
CONFIG_SPIRAM_ALLOW_BSS_SEG_EXTERNAL_MEMORY=y
CONFIG_SPIRAM_RODATA=y
```

Still keep PARTIAL-mode draw buffers in **internal** RAM when you can; PSRAM is slower and LVGL
touches the buffers constantly.

ESP32-P4 specifics:
- Enabling the PPA needs **both** `CONFIG_LV_USE_PPA=y` and `CONFIG_LV_DRAW_BUF_ALIGN=64` (PPA only
  accepts L1-cache-line-aligned data). The usual symptom of forgetting the alignment is an
  `esp_msync` error on the console. The draw unit then runs alongside the software renderer with no
  application code.
- Expected gain: ~30% of rendering time on average for image and rectangle-fill tasks, up to 9× for
  pure fills on integer multiples of the display size. Image *blending* shows little gain — DMA2D
  memory bandwidth is the limit — and in PARTIAL mode there is no gain at all, so use it with the
  port's double-buffer support.
- Buffer underrun / FPS drops with PSRAM + PPA → `CONFIG_SPIRAM_SPEED_200M=y`.
  `CONFIG_LV_PPA_BURST_LENGTH` accepts 8/16/32/64/128 and **already defaults to 128** (the maximum);
  anything else is a build error. Lowering it is what you would try if another DMA2D consumer needs
  the shared channel.

Logging and files:

```ini
CONFIG_LV_USE_LOG=y
CONFIG_LV_LOG_LEVEL_INFO=y
CONFIG_LV_LOG_PRINTF=y
```

Argument checking needs no `CONFIG_` line — it is on by default — but to actually *see* the warnings
also add `CONFIG_LV_CHECK_ARG_LOG_MODE=y` (Kconfig picks VERBOSE when logging is on) or set
`CONFIG_LV_CHECK_ARG_LOG_MODE_...` explicitly.

Filesystem images (SPIFFS/LittleFS/SD) work via `LV_USE_FS_STDIO` with a drive letter
(`CONFIG_LV_FS_STDIO_LETTER=65` for `A:`), then `lv_image_set_src(img, "A:/spiffs/logo.bin")`.
Setting `CONFIG_LV_FS_DEFAULT_DRIVER_LETTER=65` too lets you drop the prefix in paths.
Put `CONFIG_` settings in `sdkconfig.defaults` (not just menuconfig) so they are tracked in git;
`sdkconfig.<chip>` files apply per chip.

## 11. Pipeline picture

```
 your tasks / ISRs
   |  (lv_lock + LVGL calls, or queue -> LVGL thread)
   v
 +----------------------- lv_timer_handler() (one thread) ----------------------+
 |  indev read timers -> events -> your callbacks                                |
 |  animation timers  -> exec callbacks                                          |
 |  refresh timer     -> render invalidated areas into draw buffer(s)            |
 |                       -> flush_cb(area, px_map) -> start DMA                  |
 +-------------------------------------------------------------------------------+
                                          |
              DMA-complete callback / VSYNC ISR -> lv_display_flush_ready(disp)
```