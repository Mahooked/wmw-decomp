// Recovered from Walaber::BitmapFont::GlyphInfo. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__BITMAPFONT__GLYPHINFO_H
#define WMW_WALABER__BITMAPFONT__GLYPHINFO_H

#include <stdint.h>

namespace Walaber {
namespace BitmapFont {
struct GlyphInfo {
    // size 40, align 4, confidence med
    uint8_t _pad4[4];
    float f_0x4;
    int32_t f_0x8;
    float f_0xc;
    int32_t f_0x10;
    float f_0x14;
    uint8_t _pad28[4];
    float f_0x1c;
    float f_0x20;
    float f_0x24;
};

}  // namespace Walaber::BitmapFont
#endif
