// Recovered from Walaber::ZipArchiveReader. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__ZIPARCHIVEREADER_H
#define WMW_WALABER__ZIPARCHIVEREADER_H

#include <stdint.h>

namespace Walaber {
struct ZipArchiveReader {
    // size 96, align 8, confidence high
    uint64_t f_0x0;
    uint64_t filenames;  // named from getFilenames
    uint64_t f_0x10;
    uint8_t _pad88[64];
    int32_t currentFileSize;  // named from getCurrentFileSize
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
