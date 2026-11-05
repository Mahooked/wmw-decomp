/* prelude.h -- the ambient declarations every libwmw.so body is checked
   against by ``tools/check_syntax.py``.

   The decompiled bodies are compiler output, not source: they name Ghidra's
   primitives (``undefined8``), the ABI's helpers (``__stack_chk_fail``), the
   libc functions the PLT imports resolve to, and the small set of libc++
   templates that appear in recovered signatures.  None of that was ever
   written by hand, and the binary's own headers were never shipped, so the
   ambient layer is declared here rather than included.

   This file is *not* part of the recovered program.  It exists only so that
   ``clang++ -fsyntax-only`` can be pointed at each generated .cpp and asked
   what is structurally wrong with it. */
#pragma once

/* ---- Ghidra / decompiler primitive types ---- */
typedef unsigned char      undefined;
typedef unsigned char      undefined1;
typedef unsigned short     undefined2;
typedef unsigned int       undefined3;
typedef unsigned int       undefined4;
typedef unsigned long long undefined5;
typedef unsigned long long undefined6;
typedef unsigned long long undefined7;
struct _Datum;
typedef _Datum undefined8;
typedef unsigned char      byte;
typedef unsigned char      uchar;
typedef unsigned short     ushort;
typedef unsigned int       uint;
typedef unsigned long long ulong;
typedef unsigned long long ulonglong;
typedef long long          longlong;
typedef signed char        schar;
typedef signed char        int1;
typedef short              int2;
typedef int                int3;
typedef int                int4;
typedef long long          int5;
typedef long long          int6;
typedef long long          int7;
typedef long long          int8;
typedef unsigned char      uint1;
typedef unsigned short     uint2;
typedef unsigned int       uint3;
typedef unsigned int       uint4;
typedef unsigned long long uint5;
typedef unsigned long long uint6;
typedef unsigned long long uint7;
typedef unsigned long long uint8;
struct _Datum;                          /* the data-global placeholder, below */
/* Ghidra's `code` is its function-pointer type; libxml2's callback globals
   are called through it as `(*(code *)xmlMalloc)(n)` or
   `(**(code **)(*p + 0x10))(a, b)`.  As an integer typedef every one of those
   calls is "called object type 'code' is not a function" (3,154 of them), so
   `code` is a class whose call operator takes any arguments and yields a
   `_Datum` -- convertible to, assignable to and indexable by anything, which
   is all the gate needs of a pointer to code that was never recovered. */
struct code { template <class... A> _Datum operator()(A...); };

typedef unsigned char      uint8_t;
typedef unsigned short     uint16_t;
typedef unsigned int       uint32_t;
typedef unsigned long long uint64_t;
typedef signed char        int8_t;
typedef short              int16_t;
typedef int                int32_t;
typedef long long          int64_t;
typedef __SIZE_TYPE__      size_t;
typedef __PTRDIFF_TYPE__   ssize_t;
typedef long double        longdouble;
#define NAN __builtin_nanf("")
#define SQRT(x) __builtin_sqrt(x)
#define ABS(x) __builtin_abs(x)
#define LZCOUNT(x) __builtin_clz(x)
#define tpidr_el0 0
#define register0x00000008 0
typedef char16_t           wchar16;
typedef unsigned int       unsigned_int;   /* Ghidra writes this as a type name */
typedef unsigned int       word;
struct tm;
typedef struct { char __opaque[8];  } mbstate_t;
typedef struct { char __opaque[64]; } pthread_mutex_t;
typedef struct { char __opaque[64]; } pthread_cond_t;
typedef struct { char __opaque[8];  } pthread_mutexattr_t;
typedef struct { char __opaque[64]; } pthread_attr_t;
typedef unsigned int  pthread_key_t;
typedef unsigned long pthread_t;

/* libc++ spells the aligned-allocation tag `enum class align_val_t : size_t`.
   Declaring any global operator new/delete (immediately below) makes clang
   pre-declare this implicitly as an enum; the recovered `struct
   align_val_t` is therefore suppressed in decls.h, and _globals.cpp defines
   `operator_delete(void *, size_t, std::align_val_t)` with the parameter by
   value, so declare it here -- complete -- before the operator block. */
namespace std { enum class align_val_t : size_t {}; }

/* ---- allocation: the bodies call operator new/delete by name, and the
   constructor call-site rewrite (`new (obj) T(args)`) needs the placement
   form declared.  Declared, never defined: the gate is syntax-only. ---- */
void *operator new(size_t);
void *operator new[](size_t);
void *operator new(size_t, void *) noexcept;
void operator delete(void *) noexcept;
void operator delete[](void *) noexcept;
void operator delete(void *, void *) noexcept;

/* ---- ABI helpers emitted by the compiler ---- */
extern "C" void __stack_chk_fail(void) __attribute__((noreturn));
extern "C" void __cxa_pure_virtual(void) __attribute__((noreturn));

/* Allocator shims the PLT resolver writes at the call site. */
void *operator_new(unsigned long n);
void  operator_delete(void *p);
void  operator_delete_arr(void *p);

/* Ghidra's sub-register fold helpers (``CONCAT21``, ``SUB81``, ``ZEXT416``,
   ``SEXT816`` ...) are emitted by ``tools/check_syntax.py``: the set and arity
   of the names is a property of the bodies themselves, so the tool scans for
   them and declares each as a variadic template rather than hard-coding a
   list here. */

/* ---- libc (the subset the PLT imports resolve to) ---- */
extern "C" {
void  *malloc(size_t);
void  *calloc(size_t, size_t);
void  *realloc(void *, size_t);
void   free(void *);
void  *memcpy(void *, const void *, size_t);
void  *memmove(void *, const void *, size_t);
void  *memset(void *, int, size_t);
int    memcmp(const void *, const void *, size_t);
size_t strlen(const char *);
char  *strcpy(char *, const char *);
char  *strncpy(char *, const char *, size_t);
char  *strcat(char *, const char *);
char  *strncat(char *, const char *, size_t);
int    strcmp(const char *, const char *);
int    strncmp(const char *, const char *, size_t);
char  *strchr(const char *, int);
char  *strrchr(const char *, int);
char  *strstr(const char *, const char *);
int    printf(const char *, ...);
int    fprintf(void *, const char *, ...);
int    sprintf(char *, const char *, ...);
int    snprintf(char *, size_t, const char *, ...);
int    puts(const char *);
int    fputs(const char *, void *);
int    fputc(int, void *);
void  *fopen(const char *, const char *);
int    fclose(void *);
int    fflush(void *);
size_t fread(void *, size_t, size_t, void *);
size_t fwrite(const void *, size_t, size_t, void *);
int    fseek(void *, long, int);
long   ftell(void *);
void   abort(void) __attribute__((noreturn));
void   exit(int) __attribute__((noreturn));
int    atoi(const char *);
long   atol(const char *);
double strtod(const char *, char **);
double atof(const char *);
int    rand(void);
void   srand(unsigned int);
int    toupper(int);
int    tolower(int);
int    isalpha(int);
int    isdigit(int);
int    isspace(int);
double sqrt(double);
double sin(double);
double cos(double);
double tan(double);
double atan2(double, double);
double fabs(double);
double floor(double);
double ceil(double);
double pow(double, double);
double fmod(double, double);
double exp(double);
double log(double);
double log10(double);
long   lround(double);
/* float variants Ghidra calls by their libm names */
float  sinf(float);
float  cosf(float);
float  tanf(float);
float  sqrtf(float);
float  atan2f(float, float);
float  fabsf(float);
float  powf(float, float);
float  floorf(float);
float  ceilf(float);
float  expf(float);
float  logf(float);
float  fmodf(float, float);
float  fminf(float, float);
float  fmaxf(float, float);
/* further libc the PLT imports resolve to */
int    sscanf(const char *, const char *, ...);
void  *memchr(const void *, int, size_t);
void  *wmemset(void *, int, size_t);
void  *wmemcpy(void *, const void *, size_t);
void  *wmemmove(void *, const void *, size_t);

/* ---- locale / time (C library) ---- */
long   newlocale(int, const char *, long);
void   freelocale(void *);
void  *uselocale(void *);
size_t strftime(char *, size_t, const char *, const void *);
char  *builtin_strncpy(char *, const char *, size_t);   /* Ghidra's name for strncpy */
int    pthread_mutex_lock(pthread_mutex_t *);
int    pthread_mutex_unlock(pthread_mutex_t *);
int    pthread_mutex_trylock(pthread_mutex_t *);
int    pthread_mutex_destroy(pthread_mutex_t *);
int    pthread_mutexattr_init(pthread_mutexattr_t *);
int    pthread_mutexattr_destroy(pthread_mutexattr_t *);
int    pthread_mutexattr_settype(pthread_mutexattr_t *, int);
int    pthread_cond_broadcast(pthread_cond_t *);
int    pthread_cond_signal(pthread_cond_t *);
int    pthread_cond_wait(pthread_cond_t *, pthread_mutex_t *);
int    pthread_cond_timedwait(pthread_cond_t *, pthread_mutex_t *, const void *);
int    pthread_cond_destroy(pthread_cond_t *);
int    pthread_once(void *, void (*)(void));
int    pthread_key_create(pthread_key_t *, void (*)(void *));
void  *pthread_getspecific(pthread_key_t);
int    pthread_setspecific(pthread_key_t, const void *);
pthread_t pthread_self(void);
int    pthread_equal(pthread_t, pthread_t);
int    pthread_join(pthread_t, void **);
int    pthread_detach(pthread_t);
int    __android_log_write(int, const char *, const char *);
int    __android_log_print(int, const char *, const char *, ...);
int    __android_log_vprint(int, const char *, const char *, void *);
int   *__errno(void);
}

/* ---- C library function templates (outside extern C) ---- */
template <class... A> void *uselocale(A...);
template <class... A> int ExclusiveMonitorPass(A...);
/* Ghidra models locale_t results as integer addresses and some names as bytes. */
long newlocale(int, const unsigned char *, long);
/* Ghidra may type strftime buffers/formats as byte or stack-word pointers. */
template <class Output, class Format, class Time>
size_t strftime(Output *, size_t, Format, Time);

/* ---- C library functions: greedy template overloads for integer-typed args ---- */
template <class... A> void *memcpy(A...);
template <class... A> void *memmove(A...);
template <class... A> void *memset(A...);
template <class... A> int memcmp(A...);
template <class... A> size_t strlen(A...);
template <class... A> int strcmp(A...);
template <class... A> int strncmp(A...);
template <class... A> char *strcpy(A...);
template <class... A> char *strncpy(A...);
template <class... A> int sscanf(A...);
template <class... A> int sprintf(A...);
template <class... A> int snprintf(A...);
template <class... A> int fclose(A...);
template <class... A> void *fopen(A...);
template <class... A> int fseek(A...);
template <class... A> long ftell(A...);
template <class... A> int fflush(A...);
template <class... A> size_t fwrite(A...);
template <class... A> size_t fread(A...);
template <class... A> int fputs(A...);
template <class... A> int puts(A...);
template <class... A> int remove(A...);
template <class... A> int rename(A...);

/* ---- libxml2 free functions (variadic templates) ---- */
template <class... A> char *xmlStrdup(A...);
template <class... A> int xmlParserInputGrow(A...);
template <class... A> void *xmlDictLookup(A...);
template <class... A> void xmlXPathErr(A...);
template <class... A> int xmlDictOwns(A...);
template <class... A> void xmlParserHandlePEReference(A...);
template <class... A> int xmlStrlen(A...);
template <class... A> void *__xmlSimpleError(A...);
template <class... A> void *__xmlRaiseError(A...);
template <class... A> void xmlBufferWriteChar(A...);
template <class... A> void xmlXPathFreeObject(A...);
template <class... A> void xmlFreeParserCtxt(A...);
template <class... A> void xmlBufferAdd(A...);
template <class... A> void xmlSkipBlankChars(A...);
template <class... A> void xmlListFront(A...);
template <class... A> void xmlFreeParserInputBuffer(A...);
template <class... A> void xmlStrcasecmp(A...);
template <class... A> void xmlCurrentChar(A...);
template <class... A> void xmlErrMemory(A...);
template <class... A> void __xmlRegisterCallbacks(A...);
template <class... A> void xmlLinkGetData(A...);
template <class... A> void xmlXPathRegisterFuncNS(A...);
template <class... A> void xmlMutexLock(A...);
template <class... A> void xmlMutexUnlock(A...);
template <class... A> void xmlPopInput(A...);
template <class... A> void xmlNewCharEncodingHandler(A...);
template <class... A> void xmlStringCurrentChar(A...);
template <class... A> void xmlStrcat(A...);
template <class... A> void xmlFindCharEncodingHandler(A...);
template <class... A> void xmlStrndup(A...);
template <class... A> void xmlNextChar(A...);
template <class... A> void xmlOutputBufferClose(A...);
template <class... A> void xmlBufferFree(A...);
template <class... A> void xmlNewChild(A...);
template <class... A> void xmlNewProp(A...);
template <class... A> void xmlHashFree(A...);
template <class... A> void xmlFreeNodeList(A...);
template <class... A> float sqrtf(A...);

/* ---- libxml2 types ---- */
typedef unsigned char xmlChar;
struct _xmlNode;
typedef struct _xmlNode *xmlNodePtr;
typedef const struct _xmlNode *xmlConstNodePtr;

/* ---- libxml2 functions (variadic templates: accept any args) ---- */
template <class... A> xmlChar *xmlGetProp(A...);
template <class... A> xmlChar *xmlGetNsProp(A...);
template <class... A> int xmlHasNsProp(A...);
template <class... A> int xmlStrEqual(A...);
template <class... A> int xmlStrcmp(A...);
template <class... A> int xmlOutputBufferWrite(A...);
template <class... A> unsigned long xmlOutputBufferWriteString(A...);

/* ---- libc++ skeletons ----
   Recovered signatures reach into libc++ (``basic_string<char, char_traits<char>,
   allocator<char>>``) and the bodies call its members in static form.  The real
   headers were not shipped and these templates are far larger than the handful
   of members the bodies touch, so only the primary templates are declared. */
namespace std {
inline namespace __ndk1 {
template <class T> struct allocator;
template <class T> struct char_traits;
template <class T> struct less;
template <class T> struct hash;
template <class A, class B> struct pair;
template <class... T> struct tuple;
template <class T, class D = T> struct default_delete;
template <class T, class D = default_delete<T>> struct unique_ptr;
template <class T> struct unique_lock;
template <class T> struct lock_guard;
template <class T> struct shared_ptr;
template <class T> struct weak_ptr;
template <class T> struct initializer_list;
template <class T> struct iterator_traits;
template <class T, T V> struct integral_constant;
template <class T> struct reverse_iterator;
template <class C, class T = char_traits<C>, class A = allocator<C>>
struct basic_string;
template <class T, class A = allocator<T>> struct vector;
template <class T, class A = allocator<T>> struct deque;
template <class T, class A = allocator<T>> struct list;
template <class K, class V, class C = less<K>, class A = allocator<pair<K, V>>>
struct map;
template <class K, class V, class C = less<K>, class A = allocator<pair<K, V>>>
struct multimap;
template <class K, class C = less<K>, class A = allocator<K>> struct set;
template <class T, class C = less<T>, class A = allocator<T>> struct __tree;
template <class K, class V> struct __value_type;
/* libc++ gives these more parameters than the recovered signatures spell, and
   some of them are non-type (`moneypunct<char, false>`,
   `__map_value_compare<…, true>`), so a fixed arity of the wrong shape makes
   every use "too many template arguments" (1,717 of them).  Declared with the
   arity and the kinds libc++ actually uses. */
template <class K, class V, class C, bool B = true> struct __map_value_compare;
template <class T, class P> struct __tree_node;
template <class T> struct __tree_node_base;
template <class T> struct __tree_end_node;
template <class T, class N, class D> struct __tree_iterator;
template <class T, class N, class D> struct __tree_const_iterator;
template <class T> struct __tree_node_destructor;
template <class T, class A> struct __split_buffer;
template <class...> struct __deque_base;
template <class T, class A = allocator<T>> struct __vector_base;
template <class T> struct __vector_base_common;
template <class C, class T = char_traits<C>> struct basic_ostream;
template <class C, class T = char_traits<C>> struct basic_istream;
template <class C, class T = char_traits<C>> struct basic_iostream;
template <class C, class T = char_traits<C>> struct basic_streambuf;
template <class C, class T = char_traits<C>, class A = allocator<C>>
struct basic_stringbuf;
template <class C, class T = char_traits<C>> struct basic_filebuf;
template <class C, class T = char_traits<C>> struct istreambuf_iterator;
template <class C, class T = char_traits<C>> struct ostreambuf_iterator;
template <class C> struct __basic_string_common;
template <class C> struct ctype;
template <class I, class E, class S> struct codecvt;
template <class C, bool I = false> struct moneypunct;
template <class C, bool I = false> struct moneypunct_byname;
template <class C> struct numpunct;
template <class C, class I> struct num_get;
template <class C, class O> struct num_put;
template <class C, class I> struct time_get;
template <class C, class O> struct time_put;
template <class C> struct collate;
template <class C> struct messages;
struct locale;
struct ios_base;
struct __shared_count;
struct __shared_weak_count;
struct piecewise_construct_t;
struct __thread_struct;
}
/* The exception hierarchy is the other way round: libc++ declares it directly
   in ``std``, and the .so's own mangled names say so (``_ZNSt11logic_error...``,
   ``_ZNSt13exception_ptr...``) -- there is no ``__ndk1`` in them.  Declaring
   these inside the inline namespace would make ``std::logic_error`` two
   classes at once, and every reference to it ambiguous. */
struct exception;
struct exception_ptr;
struct logic_error;
struct runtime_error;
}

namespace Walaber {
template <class T> struct SharedPtr;
template <class T> struct MemberCallback;
template <class T> struct WeakPtr;
}

/* SFINAE helper: ``_EnableIf<cond>::type`` names a type only when ``cond``
   holds, which is how a template member is removed from an overload set
   without <type_traits> (a freestanding prelude has no headers). */
template <bool> struct _EnableIf {};
template <> struct _EnableIf<true> { struct type {}; };

/* ---- placeholder for unresolved data symbols ----
   Globals the .so never named (``DAT_00e12345``) are declared as this type, so
   that any of the ways a body touches them -- load, store, take the address,
   index, call through, cast -- still parses. */
struct _Datum {
  _Datum() {}
  template <class T> _Datum(T) {}
  /* A data global is read as an integer first -- a guard byte (`DAT_x & 1`), a
     length (`0 < DAT_x`), an offset (`DAT_x + lVar1`) -- and a *template*
     conversion makes every one of those ambiguous: each built-in operator is
     a candidate and they use different conversion functions, so the compiler
     cannot choose between them (1,928 diagnostics).  The template is SFINAE-
     disabled for an arithmetic target, which leaves the non-template
     conversion below as the only candidate there; a pointer, class or enum
     target still uses the template. */
  template <class T, class = typename _EnableIf<!__is_arithmetic(T)>::type>
  operator T() const;
  operator long long() const;
  template <class T> _Datum &operator=(const T &);
  template <class... A> _Datum &operator=(A...);
  _Datum &operator=(const _Datum &);
  template <class T> _Datum &operator[](T) const;
  long long operator()(...) const;             /* call through a data global */
  _Datum operator*() const;                    /* indirect through one */
  template <class T> T *operator->() const;    /* member access through a data global */
  /* ``(&DAT_x)[i]`` is the other half of the address story: the operand is an
     ``_Addr``, which converts to any *pointer* and had no subscript, so the
     160 string-table bodies that index one could not parse.  The conversion
     has to name the element type, and a data global indexed with an integer is
     text far more often than not: ``char``. */
  struct _Addr {
    template <class T> operator T *() const;
    char operator[](long long) const;
  };
  _Addr operator&() const;
  long long _0_4_;
  long long _4_4_;
  long long _1_7_;
  long long _3_1_;
  long long _0_1_;
  long long _6_2_;
  long long _5_1_;
  long long _1_4_;
  long long _2_1_;
  long long _1_1_;
  long long _7_1_;
  long long _1_2_;
  long long _4_2_;
  long long _6_1_;
  long long _4_1_;
  long long _1_3_;
  long long _0_7_;
  long long _0_8_;
  long long _8_8_;
  long long _16_8_;
  long long _24_8_;
  long long _32_8_;
  long long _40_8_;
  long long _176_8_;
  long long e_version;
  long long e_entry;
  long long e_phoff;
  long long e_flags;
  long long e_ident_pad;
  long long e_machine;
  long long e_shoff;
  long long e_ehsize;
  long long e_phentsize;
  long long e_phnum;
  long long e_shentsize;
  long long e_shnum;
  long long e_shstrndx;

};

/* ---- platform symbols the bodies call by name ----
   libGLESv2, libxml2, NEON helpers, FMOD and the statically linked
   codecs appear in the dynamic table only as bare C names; their real
   signatures were not shipped, so they are declared opaquely.  _Datum
   accepts a call, a value, a subscript or an address, which is all a
   syntax check needs from a symbol it is not going to resolve. */
extern _Datum FMOD_Memory_GetStats;
extern _Datum FMOD_System_Create;
extern _Datum NEON_ext;
extern _Datum NEON_fminnm;
extern _Datum NEON_fmov;
extern _Datum NEON_rev64;
extern _Datum NEON_scvtf;
extern _Datum NEON_smax;
extern _Datum NEON_smin;
extern _Datum NEON_ucvtf;
extern _Datum _sScreenSize;
extern _Datum WebPUpsamplers;
extern void *__DT_SYMTAB;
extern void *_stderr;
extern _Datum mCurrentAtlas;
extern _Datum mLoadingAlpha;
extern _Datum sm_pInstance;
extern _Datum _currentLevelPackName;
extern _Datum mAtlasesToLoadCount;
extern _Datum mInstancePtr;
extern _Datum fde_table_entry;
extern _Datum kVP8Log2Range;
extern _Datum kVP8NewRange;
extern _Datum ram0x00734438;
extern _Datum _sRockTexCoords;
extern _Datum mColors;
extern _Datum mNumUpdateSteps;
struct sqlite3;
extern _Datum sqlite3;
extern _Datum NEON_ushl;
extern _Datum crc32;
extern _Datum deflate;
extern _Datum deflateEnd;
extern _Datum deflateInit2_;
extern _Datum glActiveTexture;
extern _Datum glBindBuffer;
extern _Datum glBindFramebufferOES;
extern _Datum glBindTexture;
extern _Datum glBlendFunc;
extern _Datum glBufferData;
extern _Datum glBufferSubData;
extern _Datum glCheckFramebufferStatusOES;
extern _Datum glClear;
extern _Datum glClearColor;
extern _Datum glClientActiveTexture;
extern _Datum glColor4f;
extern _Datum glColorMask;
extern _Datum glColorPointer;
extern _Datum glCompressedTexImage2D;
extern _Datum glDeleteBuffers;
extern _Datum glDeleteFramebuffersOES;
extern _Datum glDeleteTextures;
extern _Datum glDepthFunc;
extern _Datum glDisable;
extern _Datum glDisableClientState;
extern _Datum glDrawArrays;
extern _Datum glEnable;
extern _Datum glEnableClientState;
extern _Datum glFinish;
extern _Datum glFramebufferTexture2DOES;
extern _Datum glGenBuffers;
extern _Datum glGenFramebuffersOES;
extern _Datum glGenTextures;
extern _Datum glGetBooleanv;
extern _Datum glGetError;
extern _Datum glGetFloatv;
extern _Datum glGetIntegerv;
extern _Datum glGetPointerv;
extern _Datum glGetString;
extern _Datum glGetTexEnvfv;
extern _Datum glGetTexEnviv;
extern _Datum glLineWidth;
extern _Datum glLoadIdentity;
extern _Datum glLoadMatrixf;
extern _Datum glLogicOp;
extern _Datum glMapBufferOES;
extern _Datum glMatrixMode;
extern _Datum glOrthof;
extern _Datum glPopMatrix;
extern _Datum glPushMatrix;
extern _Datum glReadPixels;
extern _Datum glRotatef;
extern _Datum glScalef;
extern _Datum glTexCoordPointer;
extern _Datum glTexEnvfv;
extern _Datum glTexEnvi;
extern _Datum glTexImage2D;
extern _Datum glTexParameteri;
extern _Datum glTranslatef;
extern _Datum glUnmapBufferOES;
extern _Datum glVertexPointer;
extern _Datum glViewport;
extern _Datum inflate;
extern _Datum inflateEnd;
extern _Datum inflateInit2_;
extern _Datum xmlBufferAllocScheme;
extern _Datum xmlDefaultBufferSize;
extern _Datum xmlDefaultSAXHandler;
extern _Datum xmlDefaultSAXLocator;
extern _Datum xmlDeregisterNodeDefaultValue;
extern _Datum xmlDoValidityCheckingDefaultValue;
extern _Datum xmlFree;
extern _Datum xmlGenericError;
extern _Datum xmlGenericErrorContext;
extern _Datum xmlGetWarningsDefaultValue;
extern _Datum xmlIndentTreeOutput;
extern _Datum xmlIsBaseCharGroup;
extern _Datum xmlIsCombiningGroup;
extern _Datum xmlIsDigitGroup;
extern _Datum xmlIsExtenderGroup;
extern _Datum xmlIsPubidChar_tab;
extern _Datum xmlKeepBlanksDefaultValue;
extern _Datum xmlLastError;
extern _Datum xmlLineNumbersDefaultValue;
extern _Datum xmlLoadExtDtdDefaultValue;
extern _Datum xmlMalloc;
extern _Datum xmlMallocAtomic;
extern _Datum xmlMemStrdup;
extern _Datum xmlOutputBufferCreateFilenameValue;
extern _Datum xmlParserDebugEntities;
extern _Datum xmlParserInputBufferCreateFilenameValue;
extern _Datum xmlParserMaxDepth;
extern _Datum xmlParserVersion;
extern _Datum xmlPedanticParserDefaultValue;
extern _Datum xmlRealloc;
extern _Datum xmlRegisterNodeDefaultValue;
extern _Datum xmlSaveNoEmptyTags;
extern _Datum xmlStringText;
extern _Datum xmlStructuredError;
extern _Datum xmlSubstituteEntitiesDefaultValue;
extern _Datum xmlTreeIndentString;
extern _Datum xmlXPathCastNodeSetToNumber;
extern _Datum xmlXPathCastToNumber;
extern _Datum xmlXPathNAN;
extern _Datum xmlXPathNINF;
extern _Datum xmlXPathStringEvalNumber;

struct _xmlNode { char data[256]; };
struct _xmlDoc { char data[512]; };
struct __sFILE { char data[256]; };

namespace Walaber { struct ScreenCoord { static _Datum sScreenSize; }; }

/* System/ARM helpers */
extern "C" int ExclusiveMonitorsStatus(void);
extern "C" int ExclusiveMonitorPass(void);
extern _Datum func_0x0024ecd0;
extern _Datum func_0x0024ede4;
extern _Datum func_0x0024f758;
extern _Datum func_0x0024f894;
extern _Datum func_0x00252470;
extern _Datum func_0x002531b0;
extern _Datum func_0x00254974;
extern _Datum func_0x0025654c;
extern _Datum func_0x00257e2c;
extern _Datum func_0x002585f8;
extern _Datum func_0x0025b4d4;
extern _Datum func_0x0025bfa0;
extern _Datum func_0x0025f25c;
extern _Datum func_0x00260330;
extern _Datum func_0x0026092c;
extern _Datum func_0x002609d8;
extern _Datum func_0x002615cc;
extern _Datum func_0x00262d6c;
extern _Datum func_0x00262e24;
extern _Datum func_0x00264078;
extern _Datum func_0x00265148;
extern _Datum func_0x00266ac8;
extern _Datum func_0x0026911c;
extern _Datum func_0x0026d2cc;
extern _Datum func_0x0026d644;
extern _Datum func_0x0026e304;
extern _Datum func_0x0026f0e4;
extern _Datum func_0x0026f184;
extern _Datum func_0x002702e0;
extern _Datum func_0x002716ac;
extern _Datum func_0x002717c0;
extern _Datum func_0x00276348;
extern _Datum func_0x00277284;
extern _Datum func_0x00277394;
extern _Datum func_0x0027748c;
extern _Datum func_0x00277f6c;
extern _Datum func_0x00278b94;
extern _Datum func_0x0027a134;
extern _Datum func_0x0027b028;
extern _Datum func_0x0027c170;
extern _Datum func_0x00280004;
extern _Datum func_0x00281164;
extern _Datum func_0x00283964;
extern _Datum func_0x00283ff4;
extern _Datum func_0x00285694;
extern _Datum func_0x0028593c;
extern _Datum func_0x00285f68;
extern _Datum func_0x00286188;
extern _Datum func_0x0028be74;
extern _Datum func_0x0028c848;
extern _Datum func_0x0028cc54;
extern _Datum func_0x0028ce28;
extern _Datum func_0x0028d150;
extern _Datum func_0x0028e2cc;
extern _Datum func_0x00290068;
extern _Datum func_0x002919b0;
extern _Datum func_0x00291c8c;
extern _Datum func_0x00292790;
extern _Datum func_0x00295668;
extern _Datum func_0x00299808;
extern _Datum func_0x0029acc0;
extern _Datum func_0x0029ae7c;
extern _Datum func_0x0029b820;
extern _Datum func_0x0029ea1c;
extern _Datum func_0x002a2c28;
extern _Datum func_0x002a2fac;
extern _Datum func_0x002a30ec;
extern _Datum func_0x002a3224;
extern _Datum func_0x002a3d74;
extern _Datum func_0x002a5374;
extern _Datum func_0x002a5574;
extern _Datum func_0x002a76e4;
extern _Datum func_0x002a8248;
extern _Datum func_0x002af220;
extern _Datum func_0x002af280;
extern _Datum func_0x002b1fa4;
extern _Datum func_0x002b2118;
extern _Datum func_0x002b25c8;
extern _Datum func_0x002c77bc;
extern _Datum func_0x002ca3c0;
extern _Datum func_0x002ccafc;
extern _Datum func_0x002ccc50;
extern _Datum func_0x002d0030;
extern _Datum func_0x002d42c8;
extern _Datum func_0x002d4360;
extern _Datum func_0x002d4818;
extern _Datum func_0x002d4ecc;
extern _Datum func_0x002d615c;
extern _Datum func_0x002d635c;
extern _Datum func_0x002d7328;
extern _Datum func_0x002eb264;
extern _Datum func_0x0034cf84;
extern _Datum func_0x0038d068;
extern _Datum func_0x0038d12c;
extern _Datum func_0x003a2e48;
extern _Datum func_0x003a3ac0;
extern _Datum func_0x003a3e20;
extern _Datum func_0x003a4dd0;
extern _Datum func_0x003a5644;
extern _Datum func_0x003a62e4;
extern _Datum func_0x003a6494;
extern _Datum func_0x003a73d4;
extern _Datum func_0x003a7580;
extern _Datum func_0x003a7bd0;
extern _Datum func_0x003a8170;
extern _Datum func_0x003a8620;
extern _Datum func_0x003a8b5c;
extern _Datum func_0x003a8e68;
extern _Datum func_0x003a95bc;
extern _Datum func_0x003ac7a4;
extern _Datum func_0x003ada88;
extern _Datum func_0x003ae374;
extern _Datum func_0x003b1734;
extern _Datum func_0x003b264c;
extern _Datum func_0x003b3230;
extern _Datum func_0x003b4764;
extern _Datum func_0x003b4b58;
extern _Datum func_0x003b97dc;
extern _Datum func_0x003b9f20;
extern _Datum func_0x003be268;
extern _Datum func_0x003c1564;
extern _Datum func_0x003c1a00;
extern _Datum func_0x003c282c;
extern _Datum func_0x003c2eb8;
extern _Datum func_0x003c3784;
extern _Datum func_0x003c4158;
extern _Datum func_0x003c4474;
extern _Datum func_0x003c51e4;
extern _Datum func_0x003c5830;
extern _Datum func_0x003c5ad4;
extern _Datum func_0x003c6bbc;
extern _Datum func_0x003c7a24;
extern _Datum func_0x003c7b58;
extern _Datum func_0x003ca010;
extern _Datum func_0x003ca394;
extern _Datum func_0x003cb824;
extern _Datum func_0x003cb9d8;
extern _Datum func_0x003cca68;
extern _Datum func_0x003ccd70;
extern _Datum func_0x003cd114;
extern _Datum func_0x003cdae0;
extern _Datum func_0x003cde40;
extern _Datum func_0x003ce844;
extern _Datum func_0x003cebe4;
extern _Datum func_0x003cf0c4;
extern _Datum func_0x003cf310;
extern _Datum func_0x003cf6fc;
extern _Datum func_0x003d0440;
extern _Datum func_0x003d049c;
extern _Datum func_0x003da18c;
extern _Datum func_0x003daa30;
extern _Datum func_0x003dcb4c;
extern _Datum func_0x003dccc8;
extern _Datum func_0x003dcf68;
extern _Datum func_0x003dd050;
extern _Datum func_0x003de62c;
extern _Datum func_0x003df994;
extern _Datum func_0x003ffad0;
extern _Datum func_0x005b0e0c;
extern _Datum func_0x005b0f04;
extern _Datum func_0x005b2434;
extern _Datum func_0x005b5e10;
extern _Datum func_0x005bce18;
extern _Datum func_0x005bff2c;
extern _Datum func_0x005c1b54;
extern _Datum func_0x005cf4bc;
extern _Datum func_0x005d17a0;
extern _Datum func_0x005d2070;
extern _Datum func_0x005d4bd8;
extern _Datum func_0x005d8d68;
extern _Datum func_0x005d907c;
extern _Datum func_0x005d93b8;
extern _Datum func_0x005d9704;
extern _Datum func_0x005d9930;
extern _Datum func_0x005d9c08;
extern _Datum func_0x005db5ac;
extern _Datum func_0x005db8bc;
extern _Datum func_0x005dc4f0;
extern _Datum func_0x005de274;
extern _Datum func_0x005decc0;
extern _Datum func_0x005e0250;
extern _Datum func_0x005e07a0;
extern _Datum func_0x005e1cf8;
extern _Datum func_0x005e1e20;
extern _Datum func_0x005e1f48;
extern _Datum func_0x005f1de8;
extern _Datum func_0x005f26d4;
extern _Datum func_0x005f2948;
extern _Datum func_0x005f3488;
extern _Datum func_0x005f35b4;
extern _Datum func_0x0060bb60;
extern _Datum func_0x0060cfb4;
extern _Datum func_0x0060d074;
extern _Datum func_0x0060d254;
extern _Datum func_0x0060e5fc;


/* Broad operator fallbacks */
template <class T, class U> T operator+(const T&, const U&);
template <class T, class U> T operator-(const T&, const U&);
template <class T, class U> T operator*(const T&, const U&);
template <class T, class U> T operator/(const T&, const U&);
template <class T, class U> T operator%(const T&, const U&);
template <class T, class U> T operator&(const T&, const U&);
template <class T, class U> T operator|(const T&, const U&);
template <class T, class U> T operator^(const T&, const U&);
template <class T, class U> bool operator==(const T&, const U&);
template <class T, class U> bool operator!=(const T&, const U&);
template <class T, class U> bool operator<(const T&, const U&);
template <class T, class U> bool operator>(const T&, const U&);
template <class T, class U> bool operator<=(const T&, const U&);
template <class T, class U> bool operator>=(const T&, const U&);
template <class T, class U> T operator&&(const T&, const U&);
template <class T, class U> T operator||(const T&, const U&);

namespace std { namespace __ndk1 {
template <class T, class U> T operator+(const T&, const U&);
template <class T, class U> T operator-(const T&, const U&);
template <class T, class U> T operator*(const T&, const U&);
template <class T, class U> T operator/(const T&, const U&);
template <class T, class U> bool operator==(const T&, const U&);
template <class T, class U> bool operator!=(const T&, const U&);
template <class... A> void __decomp_string_plus(A...);
} }


extern _Datum param_0;

extern _Datum param_1;

extern _Datum param_2;

extern _Datum param_3;

extern _Datum param_4;

extern _Datum param_5;

extern _Datum param_6;

extern _Datum param_7;

extern _Datum param_8;

extern _Datum param_9;

extern _Datum param_10;

extern _Datum param_11;

extern _Datum param_12;

extern _Datum param_13;

extern _Datum param_14;
extern _Datum pfStack_0;
extern _Datum pfStack_1;
extern _Datum pfStack_2;
extern _Datum pfStack_3;
extern _Datum pfStack_4;
extern _Datum pfStack_5;
extern _Datum pfStack_6;
extern _Datum pfStack_7;
extern _Datum pfStack_8;
extern _Datum pfStack_9;
extern _Datum pfStack_10;
extern _Datum pfStack_11;
extern _Datum pfStack_12;
extern _Datum pfStack_13;
extern _Datum pfStack_14;
extern _Datum pfStack_15;
extern _Datum pfStack_16;
extern _Datum pfStack_17;
extern _Datum pfStack_18;
extern _Datum pfStack_19;
extern _Datum pfStack_20;
extern _Datum pfStack_21;
extern _Datum pfStack_22;
extern _Datum pfStack_23;
extern _Datum pfStack_24;
extern _Datum pfStack_25;
extern _Datum pfStack_26;
extern _Datum pfStack_27;
extern _Datum pfStack_28;
extern _Datum pfStack_29;
extern _Datum pfStack_30;
extern _Datum pfStack_31;
extern _Datum pfStack_32;
extern _Datum pfStack_33;
extern _Datum pfStack_34;
extern _Datum pfStack_35;
extern _Datum pfStack_36;
extern _Datum pfStack_37;
extern _Datum pfStack_38;
extern _Datum pfStack_39;
extern _Datum pfStack_40;
extern _Datum pfStack_41;
extern _Datum pfStack_42;
extern _Datum pfStack_43;
extern _Datum pfStack_44;
extern _Datum pfStack_45;
extern _Datum pfStack_46;
extern _Datum pfStack_47;
extern _Datum pfStack_48;
extern _Datum pfStack_49;
extern _Datum pfStack_50;
extern _Datum pfStack_51;
extern _Datum pfStack_52;
extern _Datum pfStack_53;
extern _Datum pfStack_54;
extern _Datum pfStack_55;
extern _Datum pfStack_56;
extern _Datum pfStack_57;
extern _Datum pfStack_58;
extern _Datum pfStack_59;
extern _Datum pfStack_60;
extern _Datum pfStack_61;
extern _Datum pfStack_62;
extern _Datum pfStack_63;
extern _Datum pfStack_64;
extern _Datum pfStack_65;
extern _Datum pfStack_66;
extern _Datum pfStack_67;
extern _Datum pfStack_68;
extern _Datum pfStack_69;
extern _Datum pfStack_70;
extern _Datum pfStack_71;
extern _Datum pfStack_72;
extern _Datum pfStack_73;
extern _Datum pfStack_74;
extern _Datum pfStack_75;
extern _Datum pfStack_76;
extern _Datum pfStack_77;
extern _Datum pfStack_78;
extern _Datum pfStack_79;
extern _Datum pfStack_80;
extern _Datum pfStack_81;
extern _Datum pfStack_82;
extern _Datum pfStack_83;
extern _Datum pfStack_84;
extern _Datum pfStack_85;
extern _Datum pfStack_86;
extern _Datum pfStack_87;
extern _Datum pfStack_88;
extern _Datum pfStack_89;
extern _Datum pfStack_90;
extern _Datum pfStack_91;
extern _Datum pfStack_92;
extern _Datum pfStack_93;
extern _Datum pfStack_94;
extern _Datum pfStack_95;
extern _Datum pfStack_96;
extern _Datum pfStack_97;
extern _Datum pfStack_98;
extern _Datum pfStack_99;
extern _Datum pfStack_100;
extern _Datum pfStack_101;
extern _Datum pfStack_102;
extern _Datum pfStack_103;
extern _Datum pfStack_104;
extern _Datum pfStack_105;
extern _Datum pfStack_106;
extern _Datum pfStack_107;
extern _Datum pfStack_108;
extern _Datum pfStack_109;
extern _Datum pfStack_110;
extern _Datum pfStack_111;
extern _Datum pfStack_112;
extern _Datum pfStack_113;
extern _Datum pfStack_114;
extern _Datum pfStack_115;
extern _Datum pfStack_116;
extern _Datum pfStack_117;
extern _Datum pfStack_118;
extern _Datum pfStack_119;
extern _Datum pfStack_120;
extern _Datum pfStack_121;
extern _Datum pfStack_122;
extern _Datum pfStack_123;
extern _Datum pfStack_124;
extern _Datum pfStack_125;
extern _Datum pfStack_126;
extern _Datum pfStack_127;
extern _Datum pfStack_128;
extern _Datum pfStack_129;
extern _Datum pfStack_130;
extern _Datum pfStack_131;
extern _Datum pfStack_132;
extern _Datum pfStack_133;
extern _Datum pfStack_134;
extern _Datum pfStack_135;
extern _Datum pfStack_136;
extern _Datum pfStack_137;
extern _Datum pfStack_138;
extern _Datum pfStack_139;
extern _Datum pfStack_140;
extern _Datum pfStack_141;
extern _Datum pfStack_142;
extern _Datum pfStack_143;
extern _Datum pfStack_144;
extern _Datum pfStack_145;
extern _Datum pfStack_146;
extern _Datum pfStack_147;
extern _Datum pfStack_148;
extern _Datum pfStack_149;
extern _Datum pfStack_150;
extern _Datum pfStack_151;
extern _Datum pfStack_152;
extern _Datum pfStack_153;
extern _Datum pfStack_154;
extern _Datum pfStack_155;
extern _Datum pfStack_156;
extern _Datum pfStack_157;
extern _Datum pfStack_158;
extern _Datum pfStack_159;
extern _Datum pfStack_160;
extern _Datum pfStack_161;
extern _Datum pfStack_162;
extern _Datum pfStack_163;
extern _Datum pfStack_164;
extern _Datum pfStack_165;
extern _Datum pfStack_166;
extern _Datum pfStack_167;
extern _Datum pfStack_168;
extern _Datum pfStack_169;
extern _Datum pfStack_170;
extern _Datum pfStack_171;
extern _Datum pfStack_172;
extern _Datum pfStack_173;
extern _Datum pfStack_174;
extern _Datum pfStack_175;
extern _Datum pfStack_176;
extern _Datum pfStack_177;
extern _Datum pfStack_178;
extern _Datum pfStack_179;
extern _Datum pfStack_180;
extern _Datum pfStack_181;
extern _Datum pfStack_182;
extern _Datum pfStack_183;
extern _Datum pfStack_184;
extern _Datum pfStack_185;
extern _Datum pfStack_186;
extern _Datum pfStack_187;
extern _Datum pfStack_188;
extern _Datum pfStack_189;
extern _Datum pfStack_190;
extern _Datum pfStack_191;
extern _Datum pfStack_192;
extern _Datum pfStack_193;
extern _Datum pfStack_194;
extern _Datum pfStack_195;
extern _Datum pfStack_196;
extern _Datum pfStack_197;
extern _Datum pfStack_198;
extern _Datum pfStack_199;
extern _Datum pvStack_0;
extern _Datum pvStack_1;
extern _Datum pvStack_2;
extern _Datum pvStack_3;
extern _Datum pvStack_4;
extern _Datum pvStack_5;
extern _Datum pvStack_6;
extern _Datum pvStack_7;
extern _Datum pvStack_8;
extern _Datum pvStack_9;
extern _Datum pvStack_10;
extern _Datum pvStack_11;
extern _Datum pvStack_12;
extern _Datum pvStack_13;
extern _Datum pvStack_14;
extern _Datum pvStack_15;
extern _Datum pvStack_16;
extern _Datum pvStack_17;
extern _Datum pvStack_18;
extern _Datum pvStack_19;
extern _Datum pvStack_20;
extern _Datum pvStack_21;
extern _Datum pvStack_22;
extern _Datum pvStack_23;
extern _Datum pvStack_24;
extern _Datum pvStack_25;
extern _Datum pvStack_26;
extern _Datum pvStack_27;
extern _Datum pvStack_28;
extern _Datum pvStack_29;
extern _Datum uStack_0;
extern _Datum uStack_1;
extern _Datum uStack_2;
extern _Datum uStack_3;
extern _Datum uStack_4;
extern _Datum uStack_5;
extern _Datum uStack_6;
extern _Datum uStack_7;
extern _Datum uStack_8;
extern _Datum uStack_9;
extern _Datum uStack_10;
extern _Datum uStack_11;
extern _Datum uStack_12;
extern _Datum uStack_13;
extern _Datum uStack_14;
extern _Datum uStack_15;
extern _Datum uStack_16;
extern _Datum uStack_17;
extern _Datum uStack_18;
extern _Datum uStack_19;
extern _Datum uStack_20;
extern _Datum uStack_21;
extern _Datum uStack_22;
extern _Datum uStack_23;
extern _Datum uStack_24;
extern _Datum uStack_25;
extern _Datum uStack_26;
extern _Datum uStack_27;
extern _Datum uStack_28;
extern _Datum uStack_29;
extern _Datum auStack_0;
extern _Datum auStack_1;
extern _Datum auStack_2;
extern _Datum auStack_3;
extern _Datum auStack_4;
extern _Datum auStack_5;
extern _Datum auStack_6;
extern _Datum auStack_7;
extern _Datum auStack_8;
extern _Datum auStack_9;
extern _Datum auStack_10;
extern _Datum auStack_11;
extern _Datum auStack_12;
extern _Datum auStack_13;
extern _Datum auStack_14;
extern _Datum auStack_15;
extern _Datum auStack_16;
extern _Datum auStack_17;
extern _Datum auStack_18;
extern _Datum auStack_19;
extern _Datum auStack_20;
extern _Datum auStack_21;
extern _Datum auStack_22;
extern _Datum auStack_23;
extern _Datum auStack_24;
extern _Datum auStack_25;
extern _Datum auStack_26;
extern _Datum auStack_27;
extern _Datum auStack_28;
extern _Datum auStack_29;
extern _Datum in_x0_0;
extern _Datum in_x0_1;
extern _Datum in_x0_2;
extern _Datum in_x0_3;
extern _Datum in_x0_4;
extern _Datum in_x0_5;
extern _Datum in_x0_6;
extern _Datum in_x0_7;
extern _Datum in_x0_8;
extern _Datum in_x0_9;
extern _Datum in_x0_10;
extern _Datum in_x0_11;
extern _Datum in_x0_12;
extern _Datum in_x0_13;
extern _Datum in_x0_14;
extern _Datum in_x0_15;
extern _Datum in_x0_16;
extern _Datum in_x0_17;
extern _Datum in_x0_18;
extern _Datum in_x0_19;
extern _Datum in_x0_20;
extern _Datum in_x0_21;
extern _Datum in_x0_22;
extern _Datum in_x0_23;
extern _Datum in_x0_24;
extern _Datum in_x0_25;
extern _Datum in_x0_26;
extern _Datum in_x0_27;
extern _Datum in_x0_28;
extern _Datum in_x0_29;
extern _Datum in_x1_0;
extern _Datum in_x1_1;
extern _Datum in_x1_2;
extern _Datum in_x1_3;
extern _Datum in_x1_4;
extern _Datum in_x1_5;
extern _Datum in_x1_6;
extern _Datum in_x1_7;
extern _Datum in_x1_8;
extern _Datum in_x1_9;
extern _Datum in_x1_10;
extern _Datum in_x1_11;
extern _Datum in_x1_12;
extern _Datum in_x1_13;
extern _Datum in_x1_14;
extern _Datum in_x1_15;
extern _Datum in_x1_16;
extern _Datum in_x1_17;
extern _Datum in_x1_18;
extern _Datum in_x1_19;
extern _Datum in_x1_20;
extern _Datum in_x1_21;
extern _Datum in_x1_22;
extern _Datum in_x1_23;
extern _Datum in_x1_24;
extern _Datum in_x1_25;
extern _Datum in_x1_26;
extern _Datum in_x1_27;
extern _Datum in_x1_28;
extern _Datum in_x1_29;
extern _Datum in_x2_0;
extern _Datum in_x2_1;
extern _Datum in_x2_2;
extern _Datum in_x2_3;
extern _Datum in_x2_4;
extern _Datum in_x2_5;
extern _Datum in_x2_6;
extern _Datum in_x2_7;
extern _Datum in_x2_8;
extern _Datum in_x2_9;
extern _Datum in_x2_10;
extern _Datum in_x2_11;
extern _Datum in_x2_12;
extern _Datum in_x2_13;
extern _Datum in_x2_14;
extern _Datum in_x2_15;
extern _Datum in_x2_16;
extern _Datum in_x2_17;
extern _Datum in_x2_18;
extern _Datum in_x2_19;
extern _Datum in_x2_20;
extern _Datum in_x2_21;
extern _Datum in_x2_22;
extern _Datum in_x2_23;
extern _Datum in_x2_24;
extern _Datum in_x2_25;
extern _Datum in_x2_26;
extern _Datum in_x2_27;
extern _Datum in_x2_28;
extern _Datum in_x2_29;
extern _Datum in_x3_0;
extern _Datum in_x3_1;
extern _Datum in_x3_2;
extern _Datum in_x3_3;
extern _Datum in_x3_4;
extern _Datum in_x3_5;
extern _Datum in_x3_6;
extern _Datum in_x3_7;
extern _Datum in_x3_8;
extern _Datum in_x3_9;
extern _Datum in_x3_10;
extern _Datum in_x3_11;
extern _Datum in_x3_12;
extern _Datum in_x3_13;
extern _Datum in_x3_14;
extern _Datum in_x3_15;
extern _Datum in_x3_16;
extern _Datum in_x3_17;
extern _Datum in_x3_18;
extern _Datum in_x3_19;
extern _Datum in_x3_20;
extern _Datum in_x3_21;
extern _Datum in_x3_22;
extern _Datum in_x3_23;
extern _Datum in_x3_24;
extern _Datum in_x3_25;
extern _Datum in_x3_26;
extern _Datum in_x3_27;
extern _Datum in_x3_28;
extern _Datum in_x3_29;
extern _Datum in_x4_0;
extern _Datum in_x4_1;
extern _Datum in_x4_2;
extern _Datum in_x4_3;
extern _Datum in_x4_4;
extern _Datum in_x4_5;
extern _Datum in_x4_6;
extern _Datum in_x4_7;
extern _Datum in_x4_8;
extern _Datum in_x4_9;
extern _Datum in_x4_10;
extern _Datum in_x4_11;
extern _Datum in_x4_12;
extern _Datum in_x4_13;
extern _Datum in_x4_14;
extern _Datum in_x4_15;
extern _Datum in_x4_16;
extern _Datum in_x4_17;
extern _Datum in_x4_18;
extern _Datum in_x4_19;
extern _Datum in_x4_20;
extern _Datum in_x4_21;
extern _Datum in_x4_22;
extern _Datum in_x4_23;
extern _Datum in_x4_24;
extern _Datum in_x4_25;
extern _Datum in_x4_26;
extern _Datum in_x4_27;
extern _Datum in_x4_28;
extern _Datum in_x4_29;
extern _Datum in_x5_0;
extern _Datum in_x5_1;
extern _Datum in_x5_2;
extern _Datum in_x5_3;
extern _Datum in_x5_4;
extern _Datum in_x5_5;
extern _Datum in_x5_6;
extern _Datum in_x5_7;
extern _Datum in_x5_8;
extern _Datum in_x5_9;
extern _Datum in_x5_10;
extern _Datum in_x5_11;
extern _Datum in_x5_12;
extern _Datum in_x5_13;
extern _Datum in_x5_14;
extern _Datum in_x5_15;
extern _Datum in_x5_16;
extern _Datum in_x5_17;
extern _Datum in_x5_18;
extern _Datum in_x5_19;
extern _Datum in_x5_20;
extern _Datum in_x5_21;
extern _Datum in_x5_22;
extern _Datum in_x5_23;
extern _Datum in_x5_24;
extern _Datum in_x5_25;
extern _Datum in_x5_26;
extern _Datum in_x5_27;
extern _Datum in_x5_28;
extern _Datum in_x5_29;
extern _Datum in_x6_0;
extern _Datum in_x6_1;
extern _Datum in_x6_2;
extern _Datum in_x6_3;
extern _Datum in_x6_4;
extern _Datum in_x6_5;
extern _Datum in_x6_6;
extern _Datum in_x6_7;
extern _Datum in_x6_8;
extern _Datum in_x6_9;
extern _Datum in_x6_10;
extern _Datum in_x6_11;
extern _Datum in_x6_12;
extern _Datum in_x6_13;
extern _Datum in_x6_14;
extern _Datum in_x6_15;
extern _Datum in_x6_16;
extern _Datum in_x6_17;
extern _Datum in_x6_18;
extern _Datum in_x6_19;
extern _Datum in_x6_20;
extern _Datum in_x6_21;
extern _Datum in_x6_22;
extern _Datum in_x6_23;
extern _Datum in_x6_24;
extern _Datum in_x6_25;
extern _Datum in_x6_26;
extern _Datum in_x6_27;
extern _Datum in_x6_28;
extern _Datum in_x6_29;
extern _Datum in_x7_0;
extern _Datum in_x7_1;
extern _Datum in_x7_2;
extern _Datum in_x7_3;
extern _Datum in_x7_4;
extern _Datum in_x7_5;
extern _Datum in_x7_6;
extern _Datum in_x7_7;
extern _Datum in_x7_8;
extern _Datum in_x7_9;
extern _Datum in_x7_10;
extern _Datum in_x7_11;
extern _Datum in_x7_12;
extern _Datum in_x7_13;
extern _Datum in_x7_14;
extern _Datum in_x7_15;
extern _Datum in_x7_16;
extern _Datum in_x7_17;
extern _Datum in_x7_18;
extern _Datum in_x7_19;
extern _Datum in_x7_20;
extern _Datum in_x7_21;
extern _Datum in_x7_22;
extern _Datum in_x7_23;
extern _Datum in_x7_24;
extern _Datum in_x7_25;
extern _Datum in_x7_26;
extern _Datum in_x7_27;
extern _Datum in_x7_28;
extern _Datum in_x7_29;
extern _Datum in_x8_0;
extern _Datum in_x8_1;
extern _Datum in_x8_2;
extern _Datum in_x8_3;
extern _Datum in_x8_4;
extern _Datum in_x8_5;
extern _Datum in_x8_6;
extern _Datum in_x8_7;
extern _Datum in_x8_8;
extern _Datum in_x8_9;
extern _Datum in_x8_10;
extern _Datum in_x8_11;
extern _Datum in_x8_12;
extern _Datum in_x8_13;
extern _Datum in_x8_14;
extern _Datum in_x8_15;
extern _Datum in_x8_16;
extern _Datum in_x8_17;
extern _Datum in_x8_18;
extern _Datum in_x8_19;
extern _Datum in_x8_20;
extern _Datum in_x8_21;
extern _Datum in_x8_22;
extern _Datum in_x8_23;
extern _Datum in_x8_24;
extern _Datum in_x8_25;
extern _Datum in_x8_26;
extern _Datum in_x8_27;
extern _Datum in_x8_28;
extern _Datum in_x8_29;
