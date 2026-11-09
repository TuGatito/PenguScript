"""GDB pretty printers for PenguScript runtime values.

Load inside GDB with:
    source tools/pengu_printers.py

The compiler erases container element types in the generated C (all lists are
PenguList, all maps PenguMap, Rc/Arc store a void* payload), so these printers
show the runtime shape, not a guessed element type.  PenguString and omens are
fully printable because their layout is present in DWARF.
"""
import gdb


def _field(value, name, default=None):
    try:
        return value[name]
    except Exception:
        return default


def _enum_name(value):
    try:
        return str(value)
    except Exception:
        return "?"


class PenguStringPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            data = int(_field(self.val, "data") or 0)
            length = int(_field(self.val, "len") or 0)
            if data == 0 or length <= 0:
                return '""'
            raw = gdb.selected_inferior().read_memory(data, length).tobytes()
            text = raw.decode("utf-8", "backslashreplace")
            text = text.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            return text
        except Exception as exc:
            return "<PenguString: %s>" % exc

    def display_hint(self):
        return "string"


class PenguListPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            length = int(_field(self.val, "len") or 0)
            elem = int(_field(self.val, "elem_size") or 0)
            return "PenguList(len=%d, elem_size=%d)" % (length, elem)
        except Exception:
            return "PenguList(?)"


class PenguMapPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            length = int(_field(self.val, "len") or 0)
            ks = int(_field(self.val, "key_size") or 0)
            vs = int(_field(self.val, "val_size") or 0)
            return "PenguMap(len=%d, key_size=%d, val_size=%d)" % (length, ks, vs)
        except Exception:
            return "PenguMap(?)"


class PenguMaybePrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            present = bool(_field(self.val, "is_present"))
            if not present:
                return "none"
            return "some(%s)" % (_field(self.val, "value"),)
        except Exception:
            return "maybe(?)"


class PenguResultPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            if bool(_field(self.val, "is_ok")):
                return "ok(%s)" % (_field(self.val, "ok_val"),)
            return "err(%s)" % (_field(self.val, "err_val"),)
        except Exception:
            return "result(?)"


class PenguRcPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            ptr = int(_field(self.val, "ptr") or 0)
            if ptr == 0:
                return "Rc(null)"
            # Header immediately precedes the payload.
            hdr_type = gdb.lookup_type("PenguRcHdr").pointer()
            hdr = gdb.Value(ptr).cast(hdr_type)
            strong = int(_field(hdr.dereference(), "strong") or 0)
            weak = int(_field(hdr.dereference(), "weak") or 0)
            return "Rc(payload=0x%x, strong=%d, weak=%d)" % (ptr, strong, weak)
        except Exception:
            return "Rc(%s)" % (_field(self.val, "ptr"),)


class PenguArcPrinter(PenguRcPrinter):
    def to_string(self):
        text = super().to_string()
        return text.replace("Rc(", "Arc(", 1) if text.startswith("Rc(") else text


class PenguOmenPrinter:
    """Print `Type { Variant { payload... } }` for omen values.

    The compiler emits `struct T { T_Tag tag; union { ... } data; }`, so the
    variant name and payload are both available in DWARF.
    """

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            typ = self.val.type.strip_typedefs()
            name = str(typ)
            if name.startswith("struct "):
                name = name[len("struct "):]
            tag = _field(self.val, "tag")
            if tag is None:
                return "<omen>"
            variant = _enum_name(tag)
            prefix = name + "_"
            if variant.startswith(prefix):
                variant = variant[len(prefix):]
            data = _field(self.val, "data")
            if data is None:
                return "%s.%s" % (name, variant)
            payload = _field(data, variant)
            if payload is None:
                return "%s.%s" % (name, variant)
            fields = []
            try:
                for f in payload.type.fields():
                    if f.name:
                        fields.append("%s: %s" % (f.name, payload[f.name]))
            except Exception:
                pass
            if fields:
                return "%s.%s { %s }" % (name, variant, ", ".join(fields))
            return "%s.%s" % (name, variant)
        except Exception as exc:
            return "<omen: %s>" % exc


def _is_omen(typ):
    try:
        fields = {f.name for f in typ.fields() if f.name}
        return "tag" in fields and "data" in fields
    except Exception:
        return False


def lookup(val):
    try:
        typ = val.type
        name = str(typ)
        fnames = {f.name for f in typ.fields() if f.name}
        if name == "PenguString" or name.endswith("PenguString") or (
            fnames == {"data", "len", "is_owned"}
        ):
            return PenguStringPrinter(val)
        if fnames == {"data", "len", "cap", "elem_size"}:
            return PenguListPrinter(val)
        if fnames == {"state", "len", "cap", "key_size", "val_size"}:
            return PenguMapPrinter(val)
        if fnames == {"is_present", "value"}:
            return PenguMaybePrinter(val)
        if fnames == {"is_ok", "ok_val", "err_val"}:
            return PenguResultPrinter(val)
        if name in ("Rc", "WeakRc", "Arc", "WeakArc"):
            return PenguArcPrinter(val) if name.startswith(("Arc", "WeakArc")) else PenguRcPrinter(val)
        if _is_omen(typ):
            return PenguOmenPrinter(val)
    except Exception:
        return None
    return None


gdb.pretty_printers.append(lookup)
