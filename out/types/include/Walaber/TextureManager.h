// Recovered from Walaber::TextureManager. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__TEXTUREMANAGER_H
#define WMW_WALABER__TEXTUREMANAGER_H

#include <stdint.h>

namespace Walaber {
struct TextureManager {
    // size 8, align 8, confidence high
    uint64_t textureFileName;  // named from getTextureFileName
};

}  // namespace Walaber
#endif
