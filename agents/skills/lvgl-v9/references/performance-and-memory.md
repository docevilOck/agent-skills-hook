# Performance and memory reference (LVGL v9.6)

Contents: 1 Measure first · 2 Speed checklist · 3 Expensive drawing features · 4 RAM · 5 Flash ·
6 Images · 7 Fonts · 8 Hardware acceleration · 9 Dev vs production config

Legend: **[docs]** = stated in official LVGL docs/FAQ/release notes. **[practice]** = widely used engineering
rule of thumb; verify on your hardware.

---

## 1. Measure first

Do not optimize blind. Enable the system monitor (needs `LV_USE_LABEL`, `LV_USE_OBSERVER`, `LV_USE_SYSMON`):

```c
#define LV_USE_SYSMON        1
#define LV_USE_PERF_MONITOR  1    /* FPS, CPU %, render ms, flush ms */
#define LV_USE_MEM_MONITOR   1    /* used / peak / fragmentation of the LV_MEM_SIZE pool */
/* optional: LV_USE_PERF_MONITOR_LOG_MODE 1 to print to console instead of drawing on screen */
```
```c
lv_sysmon_show_performance(lv_display_get_default());   /* 9.6: pass the display explicitly */
lv_sysmon_show_memory(lv_display_get_default());
```

Reading the numbers:
- **render ms high, flush ms low** → CPU/draw-bound: styles, blend modes, buffer in slow RAM, compiler
  flags, missing SIMD/GPU.
- **flush ms high** → transfer-bound: slow SPI clock, single buffer, no DMA, flush blocking.
- **CPU % high but FPS fine** → you are redrawing more than needed (see section 2, last bullets).
- **Memory: peak near pool size, or high fragmentation** → raise `LV_MEM_SIZE` or reduce churn
  (create/delete patterns, big temporary allocations).
- Display events (`LV_EVENT_RENDER_START/READY`, `FLUSH_START/FINISH`) can toggle a GPIO for logic-analyzer timing.
- For call-level detail use LVGL's profiler hooks (`LV_USE_PROFILER`, output to Perfetto) and, in 9.6,
  the GDB helpers shipped with LVGL (dump of timers, animations, styles, draw tasks, memory).
- When benchmarking, turn off arg-checking and assertions (they add overhead; the benchmark demo warns
  if `LV_USE_CHECK_ARG` is enabled), and test on the real board with the real build flags.

## 2. Speed checklist

From LVGL's own "How do I speed up my UI?" **[docs]**:

1. Compiler optimization on (not `-Os`); enable instruction/data caches if the MCU has them.
2. Faster display bus: raise SPI/parallel clock; a parallel or RGB interface beats SPI by a lot.
3. PARTIAL mode: buffers **≥ 1/10 screen, 1/5 recommended**; use **two buffers + DMA** so render and
   transfer overlap.
4. With enough RAM: DIRECT mode, two screen-sized buffers; gate the swap on `lv_display_flush_is_last()` and
   signal `lv_display_flush_ready()` from the VSYNC interrupt (see `flush_wait_cb` / sync callbacks).
5. Keep draw buffers in **internal RAM**, not slow external RAM.
6. Update widgets **only when the value changes** and **only just before the display refresh**; coalesce
   multiple updates per frame.

Additional **[docs]** items:
- v9.6's software renderer measured 20-25% faster on reference boards with no config change (25% on a Renesas RA8D2, 22% on an NXP i.MX RT700, 20% on an FRDM-MCXN947; individual scenes much more — alpha-blended images dropped 76% on the RA8D2, and the ESP32-P4 rotated-ARGB scene went from 27 to a capped 60 FPS). Re-measure on your board. SIMD options:
  `LV_USE_DRAW_SW_ASM` = NEON / Helium / RISC-V V / Arm SVE2 as applicable.
- ESP-IDF: `CONFIG_COMPILER_OPTIMIZATION_PERF=y` (LVGL tips report up to ~30% on reference setups — re-measure), `CONFIG_LV_ATTRIBUTE_FAST_MEM_USE_IRAM=y`, max CPU frequency.
- The object style cache (`LV_OBJ_STYLE_CACHE`) is on by default in 9.6: it costs 2 × 32-bit per `lv_obj_t` and buys faster style lookups.

**[practice]**
- Invalidate small areas: update the smallest widget that changed, not a big container.
- Avoid animating/transforming large regions; animate position/opacity of small opaque widgets.
- Avoid unnecessary full-screen translucent overlays (every pixel underneath must be blended).
- Cap chart point counts and tick counts on `lv_chart` / `lv_scale`; decimate high-rate data before
  pushing it in.
- Don't run per-frame logic in `LV_EVENT_DRAW_*` callbacks; keep draw hooks tiny.
- Keep `lv_timer_handler()` period tight enough for input responsiveness (the returned wait value
  handles this); long event callbacks are the usual cause of "laggy touch".

## 3. Expensive drawing features **[practice, direction confirmed by renderer docs]**

Roughly in order of how often they hurt on MCUs, with the config knob that actually mitigates each
(all defaults are the "off/cheap" side, so raising them trades RAM for speed):

| Feature | Why it costs | Cheaper alternative / knob |
|---|---|---|
| Shadows, blur (blur/drop-shadow became native in 9.5), outlines with large spread | Extra render passes and offscreen buffers; shadow buffers are `shadow_width + radius` squared | Pre-rendered image, or a flat border/darker bg; keep radius/size small. Cache: `LV_DRAW_SW_SHADOW_CACHE_SIZE` (bytes; 0 = off, costs `size²`) |
| Widget `style_opa < 255` and non-NORMAL blend modes on containers | The subtree is rendered into a "layer" buffer, then blended | Use per-property opacities (`bg_opa`, `text_opa`) on leaf parts. Sizing: `LV_DRAW_LAYER_SIMPLE_BUF_SIZE` (default 24576); `LV_DRAW_LAYER_MAX_MEMORY` (default 0 = no limit) caps the total layer RAM |
| Rotation/zoom (`transform_*`, image rotate/scale) | Per-pixel transform | Pre-rotated assets; limit to small images. `LV_USE_MATRIX` enables 3×3 matrix transforms (needs `LV_USE_FLOAT`) |
| Large corner `radius` + `clip_corner` | Mask generation per redraw | Smaller radius, avoid clip on big/scrolling containers. Arc cache: `LV_DRAW_SW_CIRCLE_CACHE_SIZE` (default 4, costs `radius × 4` B/circle; 0 = off) |
| Gradients, dither | More per-pixel math | Solid colors; gradients as pre-rendered images. `LV_GRADIENT_MAX_STOPS` (default 2; each extra stop costs `sizeof(lv_color_t) + 1` B); `LV_USE_DRAW_SW_COMPLEX_GRADIENTS` (default off) adds angled, radial and conical |
| Anti-aliased arcs/lines/very large circles | Mask + blend | Smaller arcs; disable AA only if quality is acceptable |
| Many nested `LV_SIZE_CONTENT` flex containers | Repeated layout passes | Fixed sizes on hot screens |
| Compressed images drawn every frame | Decode cost | Raw/RLE converted to display format, with image cache. `LV_BIN_DECODER_RAM_LOAD` loads a `.bin` fully into RAM instead of reading from flash |
| Repeated large-area redraw from tiling | Renders each tile separately | `LV_DRAW_DISABLE_TILED_RENDERING` (default on) forces one contiguous pass |

Two flags worth knowing before you start measuring: `LV_DRAW_SW_COMPLEX` (default on) adds rounded
corners, shadows, skewed lines and arcs — turning it off leaves only rectangles with gradients, images,
texts and straight lines. And 9.6 expanded blur invalidation to once per frame instead of per draw, so
blurred content is cheaper than it was in 9.5 even though it costs more than a plain rect.

## 4. RAM

**[docs]** FAQ "How to reduce RAM usage":
- In PARTIAL mode, shrink the draw buffers; or switch from DIRECT/FULL to PARTIAL.
- Reduce `LV_MEM_SIZE` (bytes; the pool used for widgets, styles, etc.) once measured. To live with a
  smaller pool, create widgets only when needed and delete them afterwards.

If LVGL "randomly crashes or draws nothing", the same FAQ says first try **increasing `LV_MEM_SIZE`**.

**[practice]**
- Budget: draw buffers (bytes) + `LV_MEM_SIZE` + image cache (`LV_CACHE_DEF_SIZE`) + task stacks + your app.
  Example (320×240 RGB565, double 1/10 buffers): 2 × 15,360 B = 30,720 B just for draw buffers.
- Use `lv_label_set_text_static()` for constant strings; `const` styles; shared styles instead of
  local styles; avoid per-row widgets for very long lists (reuse a small pool of row widgets and
  update their content on scroll, or use `lv_table`).
- Prefer subjects with static string buffers over `lv_label_set_text_fmt` in hot paths (temporary allocation).
- Watch **fragmentation** in the mem monitor: heavy create/delete cycles of differently sized objects
  fragment the TLSF pool. Reuse widgets (hide/show) on hot screens.
- On ESP32 with PSRAM: put big assets/caches in PSRAM, keep render buffers in internal RAM. Consider
  using the C library allocator (`LV_STDLIB_CLIB` / IDF heap) instead of a fixed `LV_MEM_SIZE` pool
  so the heap can use both memories; verify the option names in your menuconfig/`lv_conf.h`.
- Allocator choice is `LV_USE_STDLIB_MALLOC`: `LV_STDLIB_BUILTIN` (the TLSF pool sized by
  `LV_MEM_SIZE`, default 64 KB) or `LV_STDLIB_CLIB` / `LV_STDLIB_MICROPYTHON` / `LV_STDLIB_RTTHREAD` /
  `LV_STDLIB_CUSTOM`. Two pool-only options follow from it: `LV_MEM_ADR` pins the pool at a fixed
  address, and `LV_USE_TLSF` is new in 9.6. Note `LV_USE_MEM_MONITOR` (sysmon) requires the builtin
  allocator. If you move to `LV_STDLIB_CLIB`, `LV_USE_ASSERT_MALLOC` and the pool-based memory
  monitors stop being meaningful — lean on `lv_test_get_allocation_count()` in host tests instead.
- Keep `LV_USE_LOG` on in dev so allocation-failure paths and internal errors are visible.

## 5. Flash/ROM

**[docs]**
- Disable unused widgets, themes, file systems, GPU backends, libraries in `lv_conf.h`/Kconfig.
- GCC/Clang: `-fdata-sections -ffunction-sections` + linker `--gc-sections`; add `-flto` with `-Os`
  (GCC) or `-Oz` (Clang) when you are optimizing for size.
- 9.6 `LV_CONF_MINIMAL` was removed; start from `configs/defconfigs/empty.defconfig` (Kconfig builds)
  and enable only what you need.

**[practice]** Fonts and images are usually the biggest flash consumers; see below.

## 6. Images

**[docs]**
- Convert with `scripts/LVGLImage.py` (offline) or the online converter (limited formats: RGB565,
  RGB565A8, RGB888, XRGB8888, ARGB8888). BMP/WEBP are supported only as files on a filesystem.
- Use the display's native format when possible (RGB565 for a 16-bit panel) so no per-frame conversion is needed.
  Use alpha formats (RGB565A8, ARGB8888) only for images that need transparency: they cost more RAM/CPU.
- `.bin` files with RLE or LZ4 compression keep RAM low (pixels are read straight from the file);
  enable `LV_USE_RLE` / `LV_USE_LZ4` (+ `_INTERNAL` bundled or external). `LV_BIN_DECODER_RAM_LOAD`
  instead loads the whole file into RAM — faster, and only worth it for assets that are redrawn often.
- Decoded/compressed image **cache** is `LV_CACHE_DEF_SIZE` bytes, **default 0 = off**. LRU eviction.
  It is "resource intensive": you must have RAM for the largest simultaneous set.
  **Caveat in 9.6**: the cache module headers (`lv_cache.h`, `lv_image_cache.h`) moved under `src/`
  and are now private API, so the runtime resizing calls are only reachable through
  `lvgl_private.h` / `LV_USE_PRIVATE_API`. They are
  `lv_image_cache_resize(new_size, evict_now)`, `lv_image_cache_drop(&dsc)` (or `NULL` for all) and
  `lv_image_cache_is_enabled()`; the generic `lv_cache_set_max_size(cache, max_size, user_data)`
  takes a `lv_cache_t *`, not a bare size. Check your installed headers before calling any of these.
- Runtime-generated images: build an `lv_image_dsc_t` (magic, cf, w, h, stride, data_size, data) or use
  the Canvas widget. Free draw buffers with `lv_draw_buf_destroy()` (9.6; `lv_image_buf_free` is deprecated).
- 9.6 adds `LV_IMAGE_ALIGN_CONTAIN_DOWNSCALE` (fit without ever scaling up) and a fast path for I1/I2/I4
  decoding. The indexed formats are decoded through ARGB8888, so those paths assume
  `LV_DRAW_SW_SUPPORT_ARGB8888` (on by default) — disabling that format support removes the fast path.

**[practice]** Prefer a small number of pre-sized assets over scaling at runtime; avoid decoding PNG/JPEG
on weak MCUs at runtime unless cached; keep rarely used images on external flash/SD via the file system
driver.

## 7. Fonts

- Enable only the built-in Montserrat sizes you use; each adds flash. Set `LV_FONT_DEFAULT` deliberately.
- Custom glyph sets: generate with `lv_font_conv` choosing exact ranges (digits, a few symbols) and bpp (1/2/4);
  fewer glyphs and lower bpp = less flash and faster draw. Use `--no-compress` only if you need speed over size.
- FreeType/Tiny TTF give flexible sizes but cost RAM/CPU and rely on caches; use for few styles and
  consider PSRAM. 9.6: variable font weights (FreeType) and dynamic glyph loading for binary fonts (see 9.6 changelog for exact APIs).
- Text-heavy UIs: avoid `LV_SIZE_CONTENT` labels that re-layout on every value change; give numeric labels
  a fixed width.

## 8. Hardware acceleration (draw units)

LVGL v9 renders through *draw units*; the software renderer is always available and multiple units can
coexist. Backends exist for
NXP PXP/VG-Lite/G2D, STM32 DMA2D (Chrom-ART), Renesas Dave2D, Espressif PPA (ESP32-P4) and DMA2D, Arm-2D,
NemaGFX, OpenGL-ES/NanoVG, SiFli EPIC, EVE, etc. Enable what your silicon needs (flash saving, not exclusivity).

- Keep each unit's alignment requirements (defaults `LV_DRAW_BUF_ALIGN 4` / `LV_DRAW_BUF_STRIDE_ALIGN 1`; e.g. `CONFIG_LV_DRAW_BUF_ALIGN=64`
  for ESP32-P4 PPA L1 cache lines) and follow the vendor page in the LVGL docs.
- Cache coherency matters: buffers written by DMA/GPU must be invalidated/cleaned; 9.6 reworked DMA2D
  and PPA cache handling onto `lv_draw_buf`, which now exposes `lv_draw_buf_invalidate_cache()` /
  `lv_draw_buf_flush_cache()` plus per-backend handlers.
- Measure with sysmon before/after: accelerators help fills/blits/blends, not necessarily text or masks.
- Multiple software draw threads are possible with `LV_DRAW_SW_DRAW_UNIT_CNT` and an OS (rule: only on
  multi-core with enough RAM; test for gains).

## 9. Dev vs production config

| Setting | Development | Production |
|---|---|---|
| `LV_USE_LOG` | on, INFO/WARN | WARN/ERROR or off |
| `LV_USE_ASSERT_*` / `LV_USE_ASSERT` | on | off (disabled by default in 9.6) |
| `LV_USE_CHECK_ARG` | on (already the default in 9.6), `LV_CHECK_ARG_LOG_MODE_VERBOSE`, `LV_CHECK_ARG_ASSERT_ON_FAIL 1` while debugging | on, `LV_CHECK_ARG_LOG_MODE_MINIMAL`; set 0 only for the last % of flash, and only if every call site is known good |
| `LV_USE_CHECK_OBJ_CLASSTYPE`, `LV_USE_CHECK_OBJ_VALIDITY` | on (catch wrong type / use-after-delete) | off (default; they walk the class hierarchy and widget tree on every call) |
| `LV_USE_SYSMON` perf/mem monitors | on (on-screen) | off, or `lv_sysmon_performance_dump()` in a service build |
| Optimization | `-O2`/perf with symbols | perf or size per your target; LTO |
| Watchdog | long enough not to fire in long renders | tuned; feed it from a non-LVGL context or after `lv_timer_handler` |

Also: keep one LVGL-tuned `sdkconfig.defaults` / `lv_conf.h` per target in version control, and re-run
the benchmark demo (`lv_demo_benchmark`) after any config change to catch regressions. Full details of
the logging / assertion / argument-check layers, plus Monkey and `lv_test_*` UI testing, are in
`references/debugging-and-testing.md`.