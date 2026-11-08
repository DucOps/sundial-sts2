"""Build Sundial knowledge (cards, relics, potions) from YOUR OWN Slay the Spire 2 install.

Reads the English text from SlayTheSpire2.pck and the numbers (damage, block, costs, upgrades, rarity,
character) from sts2.dll, then writes ~/.sundial-sts2/knowledge/game.json. Nothing is downloaded and
no game data is shipped with Sundial: re-run this after a game patch.

    uv run --with dnfile python tools/import_game_data.py ["C:\\...\\steamapps\\common\\Slay the Spire 2"]

Numbers come from reading the game's code, not running it, so text that depends on the fight
(e.g. "Hits X times") shows X. Unread values are left as X rather than guessed.

The output is derived from the game's files on your machine and is for your own use; don't redistribute it.
This reads internal formats that Mega Crit can change in any update, so it may break or give wrong text after
a patch, and future support isn't guaranteed. Unofficial; not affiliated with Mega Crit.
Uses dnfile (https://github.com/malwarefrank/dnfile, MIT) to read sts2.dll.
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from decimal import Decimal
from pathlib import Path

try:
    import dnfile
except ImportError:
    sys.exit("Needs dnfile:  uv run --with dnfile python tools/import_game_data.py")

DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2")
NS = "MegaCrit.Sts2.Core.Models"
CARD_TYPE = ["", "Attack", "Skill", "Power", "Status", "Curse", "Quest"]
CARD_RARITY = ["", "Basic", "Common", "Uncommon", "Rare", "Ancient", "Event", "Token", "Status", "Curse", "Quest"]
KEYWORD = ["", "Exhaust", "Ethereal", "Innate", "Unplayable", "Retain", "Sly", "Eternal"]
RELIC_RARITY = ["", "Starter", "Common", "Uncommon", "Rare", "Shop", "Event", "Ancient"]
POTION_RARITY = ["", "Common", "Uncommon", "Rare", "Event", "Token"]
TARGET = ["", "Self", "AnyEnemy", "AllEnemies", "RandomEnemy", "AnyPlayer", "AnyAlly", "AllAllies", "TargetedNoCreature", "Osty"]


# ---------------------------------------------------------------- the .pck (Godot 4 pack)
def read_pck(path: Path, prefix: str) -> dict[str, bytes]:
    out = {}
    with open(path, "rb") as f:
        magic, fmt, _ma, _mi, _pa, flags, base, dir_off = struct.unpack("<4sIIIIIQQ", f.read(40))
        if magic != b"GDPC" or fmt < 3:
            sys.exit(f"Unexpected pack format in {path} ({magic!r} v{fmt}); the importer needs updating.")
        f.seek(dir_off)
        n, = struct.unpack("<I", f.read(4))
        entries = []
        for _ in range(n):
            ln, = struct.unpack("<I", f.read(4))
            name = f.read(ln).rstrip(b"\0").decode("utf-8")
            off, size = struct.unpack("<QQ", f.read(16))
            f.read(16)
            fl, = struct.unpack("<I", f.read(4))
            if name.startswith(prefix):
                if fl & 1:
                    sys.exit("The game's pack is encrypted; can't read it.")
                entries.append((name, off, size))
        for name, off, size in entries:
            f.seek(base + off)
            out[name] = f.read(size)
    return out


# ---------------------------------------------------------------- sts2.dll (IL reading)
OP1: dict[int, tuple[str, str | None]] = {}
for _i, _n in enumerate("nop break ldarg.0 ldarg.1 ldarg.2 ldarg.3 ldloc.0 ldloc.1 ldloc.2 ldloc.3 stloc.0 stloc.1 stloc.2 stloc.3".split()):
    OP1[_i] = (_n, None)
OP1.update({0x0E: ("ldarg.s", "u1"), 0x0F: ("ldarga.s", "u1"), 0x10: ("starg.s", "u1"), 0x11: ("ldloc.s", "u1"),
            0x12: ("ldloca.s", "u1"), 0x13: ("stloc.s", "u1"), 0x14: ("ldnull", None), 0x15: ("ldc.i4.m1", None)})
for _i in range(9):
    OP1[0x16 + _i] = (f"ldc.i4.{_i}", None)
OP1.update({0x1F: ("ldc.i4.s", "i1"), 0x20: ("ldc.i4", "i4"), 0x21: ("ldc.i8", "i8"), 0x22: ("ldc.r4", "r4"),
            0x23: ("ldc.r8", "r8"), 0x25: ("dup", None), 0x26: ("pop", None), 0x27: ("jmp", "tok"), 0x28: ("call", "tok"),
            0x29: ("calli", "tok"), 0x2A: ("ret", None), 0x45: ("switch", "switch")})
for _i in range(0x2B, 0x38):
    OP1[_i] = ("br.s" if _i == 0x2B else ("brcond1.s" if _i in (0x2C, 0x2D) else "brcond2.s"), "i1")
for _i in range(0x38, 0x45):
    OP1[_i] = ("br" if _i == 0x38 else ("brcond1" if _i in (0x39, 0x3A) else "brcond2"), "i4")
OP1.update({0x6F: ("callvirt", "tok"), 0x70: ("cpobj", "tok"), 0x71: ("ldobj", "tok"), 0x72: ("ldstr", "str"),
            0x73: ("newobj", "tok"), 0x74: ("castclass", "tok"), 0x75: ("isinst", "tok"), 0x79: ("unbox", "tok"),
            0x7B: ("ldfld", "tok"), 0x7C: ("ldflda", "tok"), 0x7D: ("stfld", "tok"), 0x7E: ("ldsfld", "tok"),
            0x7F: ("ldsflda", "tok"), 0x80: ("stsfld", "tok"), 0x81: ("stobj", "tok"), 0x8C: ("box", "tok"),
            0x8D: ("newarr", "tok"), 0x8F: ("ldelema", "tok"), 0xA3: ("ldelem", "tok"), 0xA4: ("stelem", "tok"),
            0xA5: ("unbox.any", "tok"), 0xC2: ("refanyval", "tok"), 0xC6: ("mkrefany", "tok"), 0xD0: ("ldtoken", "tok"),
            0xDD: ("leave", "i4"), 0xDE: ("leave.s", "i1")})
for _i in range(0x9B, 0xA3):
    OP1[_i] = ("stelem", None)
OP2 = {0x06: ("ldftn", "tok"), 0x07: ("ldvirtftn", "tok"), 0x09: ("ldarg", "u2"), 0x0A: ("ldarga", "u2"),
       0x0B: ("starg", "u2"), 0x0C: ("ldloc", "u2"), 0x0D: ("ldloca", "u2"), 0x0E: ("stloc", "u2"),
       0x12: ("unaligned.", "u1"), 0x15: ("initobj", "tok"), 0x16: ("constrained.", "tok"), 0x19: ("no.", "u1"),
       0x1C: ("sizeof", "tok")}
SIZE = {"u1": 1, "i1": 1, "u2": 2, "i4": 4, "tok": 4, "str": 4, "r4": 4, "i8": 8, "r8": 8}


def _cuint(b: bytes, i: int) -> tuple[int, int]:
    if b[i] & 0x80 == 0:
        return b[i], i + 1
    if b[i] & 0xC0 == 0x80:
        return ((b[i] & 0x3F) << 8) | b[i + 1], i + 2
    return ((b[i] & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4


def _blob(x) -> bytes:
    v = getattr(x, "value", x)
    return bytes(v) if not isinstance(v, bytes) else v


class Dll:
    def __init__(self, path: Path):
        self.pe = dnfile.dnPE(str(path))
        self.md = self.pe.net.mdtables
        self.data = self.pe.__data__
        self.types: dict[tuple[str, str], object] = {}
        self.owner: dict[int, str] = {}
        for t in self.md.TypeDef:
            self.types[(str(t.TypeNamespace), str(t.TypeName))] = t
            for m in t.MethodList:
                self.owner[m.row_index] = str(t.TypeName)
        self.var_names = self._var_names()

    # names
    def _coded(self, v: int) -> str:
        tag, row = v & 3, v >> 2
        if tag == 0:
            return str(self.md.TypeDef[row - 1].TypeName)
        if tag == 1:
            return str(self.md.TypeRef[row - 1].TypeName)
        return self._typespec(row)

    def _sigtype(self, b: bytes, i: int) -> tuple[str, int]:
        e = b[i]; i += 1
        if e in (0x11, 0x12):
            v, i = _cuint(b, i)
            return self._coded(v), i
        if e == 0x15:
            gen, i = self._sigtype(b, i)
            n, i = _cuint(b, i)
            args = []
            for _ in range(n):
                a, i = self._sigtype(b, i)
                args.append(a)
            return f"{gen.split('`')[0]}<{','.join(args)}>", i
        if e == 0x1D:
            t, i = self._sigtype(b, i)
            return t + "[]", i
        return f"prim{e:x}", i

    def _typespec(self, row: int) -> str:
        try:
            return self._sigtype(_blob(self.md.TypeSpec[row - 1].Signature), 0)[0]
        except Exception:
            return "?"

    def _parent_name(self, coded) -> str:
        tbl = coded.table.name if hasattr(coded, "table") and coded.table is not None else ""
        idx = coded.row_index
        if tbl == "TypeDef":
            return str(self.md.TypeDef[idx - 1].TypeName)
        if tbl == "TypeRef":
            return str(self.md.TypeRef[idx - 1].TypeName)
        if tbl == "TypeSpec":
            return self._typespec(idx)
        return "?"

    def method(self, tok: int) -> tuple[str, str, int, bool, bool, list[str]]:
        """(owner type, name, param count, has this, returns void, generic args) for a call token."""
        tbl, row = tok >> 24, tok & 0xFFFFFF
        gargs: list[str] = []
        if tbl == 0x2B:
            ms = self.md.MethodSpec[row - 1]
            b = _blob(ms.Instantiation); n, i = _cuint(b, 1)
            for _ in range(n):
                a, i = self._sigtype(b, i)
                gargs.append(a)
            m = ms.Method
            tbl = 0x06 if m.table.name == "MethodDef" else 0x0A
            row = m.row_index
        if tbl == 0x06:
            r = self.md.MethodDef[row - 1]; owner = self.owner.get(row, "?"); sig = _blob(r.Signature)
        elif tbl == 0x0A:
            r = self.md.MemberRef[row - 1]; owner = self._parent_name(r.Class); sig = _blob(r.Signature)
        else:
            return "?", "?", 0, False, True, gargs
        i = 1
        if sig[0] & 0x10:
            _, i = _cuint(sig, i)
        n, i = _cuint(sig, i)
        return owner, str(r.Name), n, bool(sig[0] & 0x20), sig[i] == 0x01, gargs

    def field(self, tok: int) -> str:
        tbl, row = tok >> 24, tok & 0xFFFFFF
        if tbl == 0x0A:
            r = self.md.MemberRef[row - 1]
            return f"{self._parent_name(r.Class)}::{r.Name}"
        if tbl == 0x04:
            return f"::{self.md.Field[row - 1].Name}"
        return "?"

    # IL
    def ops(self, rva: int) -> list[tuple[str, object]]:
        off = self.pe.get_offset_from_rva(rva); d = self.data; h = d[off]
        if h & 3 == 2:
            size, start = h >> 2, off + 1
        else:
            size = struct.unpack_from("<I", d, off + 4)[0]
            start = off + (struct.unpack_from("<H", d, off)[0] >> 12) * 4
        code = bytes(d[start:start + size]); i = 0; out = []
        while i < len(code):
            op = code[i]; i += 1
            if op == 0xFE:
                name, kind = OP2.get(code[i], ("fe", None)); i += 1
            else:
                name, kind = OP1.get(op, ("op", None))
            arg: object = None
            if kind == "switch":
                n = struct.unpack_from("<I", code, i)[0]; i += 4 + 4 * n
            elif kind:
                raw = code[i:i + SIZE[kind]]; i += SIZE[kind]
                if kind in ("tok", "str"):
                    arg = struct.unpack("<I", raw)[0]
                elif kind == "i1":
                    arg = struct.unpack("<b", raw)[0]
                elif kind in ("u1",):
                    arg = raw[0]
                elif kind == "u2":
                    arg = struct.unpack("<H", raw)[0]
                elif kind == "i4":
                    arg = struct.unpack("<i", raw)[0]
                elif kind == "i8":
                    arg = struct.unpack("<q", raw)[0]
                else:
                    arg = struct.unpack("<f" if kind == "r4" else "<d", raw)[0]
            out.append((name, arg))
        return out

    def static_ints(self, field_tok: int, count: int) -> list[int]:
        """Values of an int32 array initialised from a static data blob (FieldRVA)."""
        row = field_tok & 0xFFFFFF
        for fr in getattr(self.md, "FieldRva", None) or []:
            if fr.Field.row_index == row:
                off = self.pe.get_offset_from_rva(fr.Rva)
                return list(struct.unpack_from(f"<{count}i", self.data, off))
        return []

    def string(self, tok: int) -> str:
        return self.pe.net.user_strings.get(tok & 0xFFFFFF).value

    def methods_of(self, t) -> dict[str, object]:
        return {str(m.row.Name): m.row for m in t.MethodList}

    def run(self, rva: int, fields: dict | None = None) -> tuple[object, list]:
        """Symbolically evaluate a simple method body. Returns (return value, events).
        `fields` maps this object's field names (normalised) to values set in its constructor."""
        fields = fields or {}
        stack: list = []; locs: dict = {}; events: list = []; ret = None; counts: dict = {}
        pop = lambda: stack.pop() if stack else None
        for name, arg in self.ops(rva):
            if name.startswith("ldc.i4"):
                v = arg if arg is not None else (-1 if name.endswith("m1") else int(name.rsplit(".", 1)[1]))
                stack.append(Decimal(v))
            elif name in ("ldc.r4", "ldc.r8", "ldc.i8"):
                stack.append(Decimal(str(arg)))
            elif name == "ldstr":
                stack.append(self.string(arg))
            elif name == "ldnull":
                stack.append(None)
            elif name == "ldarg.0":
                stack.append(("this",))
            elif name.startswith("ldarg"):
                stack.append(("arg",))
            elif name == "dup":
                stack.append(stack[-1] if stack else None)
            elif name == "pop" or name.startswith("brcond1") or name == "stsfld":
                pop()
            elif name == "stfld":
                v = pop(); o = pop()
                if o == ("this",):
                    events.append(("field", self.field(arg).rsplit("::", 1)[-1], v))
            elif name.startswith("brcond2"):
                pop(); pop()
            elif name in ("ldftn", "ldtoken"):
                stack.append(("tok", arg))
            elif name.startswith("stloc"):
                locs[arg if arg is not None else name] = pop()
            elif name.startswith("ldloc"):
                key = arg if arg is not None else name.replace("ld", "st")
                stack.append(locs.get(key))
            elif name == "ldsfld":
                f = self.field(arg)
                stack.append({"Decimal::One": Decimal(1), "Decimal::Zero": Decimal(0),
                              "Decimal::MinusOne": Decimal(-1)}.get(f, ("fld", f)))
            elif name in ("ldfld", "ldflda"):
                pop(); stack.append(("fld", self.field(arg)))
            elif name == "newarr":
                n = pop(); stack.append(["arr"]); counts[id(stack[-1])] = int(n) if isinstance(n, Decimal) else 0
            elif name == "stelem":
                v = pop(); pop(); a = pop()
                if isinstance(a, list):
                    a.append(v)
            elif name in ("newobj", "call", "callvirt"):
                owner, mname, n, this, void, gargs = self.method(arg)
                args = [pop() for _ in range(n)][::-1]
                if name == "newobj":
                    if owner == "Decimal":
                        nums = [a for a in args if isinstance(a, Decimal)]
                        if len(args) == 5 and len(nums) == 5:
                            lo, mid, hi, neg, scale = (int(x) for x in nums)
                            v = Decimal((hi << 64) | (mid << 32) | (lo & 0xFFFFFFFF)) / (Decimal(10) ** scale)
                            stack.append(-v if neg else v)
                        else:
                            stack.append(nums[0] if nums else None)
                    else:
                        stack.append(("obj", owner, args))
                    continue
                obj = pop() if this else None
                res: object = ("ret", mname)
                if owner == "RuntimeHelpers" and mname == "InitializeArray" and len(args) == 2:
                    arr, tk = args
                    if isinstance(arr, list) and isinstance(tk, tuple):
                        arr.extend(Decimal(x) for x in self.static_ints(tk[1], counts.get(id(arr), 0)))
                    continue
                if isinstance(obj, tuple) and obj[:1] == ("obj",) and not void and mname != "get_Item":
                    res = obj          # fluent builders like .FromOsty() / .WithMultiplier() return the var itself
                if mname == "op_Implicit" and len(args) == 1 and isinstance(args[0], Decimal):
                    res = args[0]      # int -> decimal conversion
                if owner == "ModelDb" and args and isinstance(args[0], str):
                    res = ("modelname", mname, args[0])
                if isinstance(obj, tuple) and obj[:1] == ("modelname",):
                    res = obj
                if obj == ("this",) and mname.startswith("get_") and norm(mname[4:]) in fields:
                    res = fields[norm(mname[4:])]      # property backed by a field set in the constructor
                elif mname == "get_DynamicVars":
                    res = ("dv",)
                elif isinstance(obj, tuple) and obj[:1] == ("dv",):
                    res = ("var", args[0] if mname == "get_Item" and args else mname.removeprefix("get_"))
                elif mname == "UpgradeValueBy" and isinstance(obj, tuple) and obj[:1] == ("var",):
                    events.append(("up", obj[1], args[0] if args else None))
                elif "Cost" in mname and any(isinstance(a, Decimal) for a in args):
                    events.append(("cost", mname, next(a for a in args if isinstance(a, Decimal))))
                elif mname in ("AddKeyword", "RemoveKeyword") and args:
                    events.append((mname, args[0]))
                elif mname == ".ctor" and obj == ("this",):
                    events.append(("base", owner, args))
                elif mname in ("Card", "Relic", "Potion") and gargs:
                    res = ("model", gargs[0])
                if not void:
                    stack.append(res)
            elif name == "ret":
                ret = pop()
                break
        return ret, events

    def _var_names(self) -> dict[str, str]:
        """DynamicVar subclasses -> the name their constructor passes to the base class."""
        names = {}
        for (ns, n), t in self.types.items():
            if not n.endswith("Var"):
                continue
            for m in t.MethodList:
                if str(m.row.Name) == ".ctor" and m.row.Rva:
                    s = next((self.string(a) for op, a in self.ops(m.row.Rva) if op == "ldstr"), None)
                    if s:
                        names[n] = s
                        break
        return names


def flatten_vars(dll: Dll, v, out: dict) -> None:
    if isinstance(v, list):
        for x in v[1:]:
            flatten_vars(dll, x, out)
    elif isinstance(v, tuple) and v[:1] == ("obj",):
        _, owner, args = v
        base = owner.split("<")[0]
        if base.startswith("Calculated"):
            return      # computed in combat; its constructor args are flags, not values (text falls back to CalculationBase)
        if base.endswith("Var"):
            name = next((a for a in args if isinstance(a, str)), None)
            if not name:
                if "<" in owner:
                    name = owner.split("<", 1)[1].rstrip(">").split(",")[0]
                else:
                    name = dll.var_names.get(owner, owner.removesuffix("Var"))
            val = next((a for a in args if isinstance(a, Decimal)), None)
            if val is None:
                val = next((a for a in args if isinstance(a, tuple) and a[:1] == ("modelname",)), None)
            out[name] = val
        else:
            for a in args:
                flatten_vars(dll, a, out)


# ---------------------------------------------------------------- SmartFormat text rendering
def fmt_num(v) -> str:
    if v is None:
        return "X"
    if isinstance(v, str):
        return v
    v = Decimal(v)
    return str(int(v)) if v == v.to_integral_value() else str(v.normalize())


def split_top(s: str, sep: str = "|") -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    return parts + [cur]


ICONS = {"singleStarIcon": "Star", "singleEnergyIcon": "Energy", "energyIcon": "Energy", "starIcon": "Star"}
FORMATTERS = {"diff", "inverseDiff", "percentMore", "percentLess", "energyIcons", "starIcons", "plural", "show", "cond", "choose"}


def render(s: str, vars: dict, upgraded: bool) -> str:
    out, i = "", 0
    while i < len(s):
        if s[i] != "{":
            out += s[i]; i += 1
            continue
        depth, j = 0, i
        while j < len(s):
            depth += {"{": 1, "}": -1}.get(s[j], 0)
            if depth == 0:
                break
            j += 1
        out += render_field(s[i + 1:j], vars, upgraded)
        i = j + 1
    return out


def render_field(inner: str, vars: dict, upgraded: bool) -> str:
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)(?::(.*))?$", inner, re.S)
    if not m:
        return inner
    name, rest = m.group(1), m.group(2)
    known = name in vars
    v = vars.get(name)
    if not known and name.startswith("Calculated") and "CalculationBase" in vars:
        known, v = True, vars["CalculationBase"]      # out of combat the game shows the base value
    if name in ICONS:
        return ICONS[name]
    if name == "IfUpgraded":
        known, v = True, Decimal(1 if upgraded else 0)
    if rest is None:
        return fmt_num(v)
    fm = re.match(r"^([a-zA-Z]+)(?:\(([^)]*)\))?(?::(.*))?$", rest, re.S)
    if fm and fm.group(1) in FORMATTERS:
        f, parg, opts = fm.group(1), fm.group(2), fm.group(3)
        if f in ("diff", "inverseDiff", "percentMore", "percentLess"):
            return fmt_num(v)
        if f == "energyIcons":
            return f"{fmt_num(v)} Energy" if known else (" Energy" if parg else "X Energy")
        if f == "starIcons":
            return f"{fmt_num(v)} Star{'s' if v != 1 else ''}" if known else "X Stars"
        # inside options, "{}" means "this value" (e.g. {Cards:plural:card|{} cards})
        o = [render(x.replace("{}", fmt_num(v)), vars, upgraded) for x in split_top(opts or "")]
        if f == "plural":
            return o[0] if (known and v == 1 and o) else o[-1]
        if f == "show":
            return o[0] if (known and v) else (o[1] if len(o) > 1 else "")
        if f == "cond":
            cm = re.match(r"^([<>=!]+)(-?\d+)\?(.*)$", opts or "", re.S)
            if cm:
                a, b = split_top(cm.group(3))[:2] if "|" in cm.group(3) else (cm.group(3), "")
                ok = known and eval(f"{v}{cm.group(1)}{cm.group(2)}") if cm.group(1) in (">", "<", ">=", "<=", "==", "!=") else False
                return render(a if ok else b, vars, upgraded)
            return o[-1]
        if f == "choose":
            # value set during the run (e.g. Mad Science's type from Tinker Time): list the known choices
            labels = (parg or "").split("|")
            if known and isinstance(v, str):
                return o[labels.index(v)] if v in labels else o[-1]
            if not known and len(labels) == 1:
                return o[-1]       # a one-choice switch, e.g. {TargetType:choose(AllEnemies): to ALL enemies|}
            if known and v is not None and 0 <= int(v) < len(o):
                return o[int(v)]
            parts = [f"{labels[i]}: {x.strip()}" if i < len(labels) and labels[i] else x.strip()
                     for i, x in enumerate(o) if x.strip() and "???" not in x]
            return " / ".join(parts)
    # boolean conditional "{Flag:text if true|text if false}"; unknown flags read as false
    o = [render(x, vars, upgraded) for x in split_top(rest)]
    return o[0] if (known and v) else (o[1] if len(o) > 1 else "")


def clean(s: str) -> str:
    s = re.sub(r"\[/?[a-z]+\]", "", s)
    s = re.sub(r"\s*\?\?\?\s*", " ", s)     # the game's placeholder for choices made during a run
    s = re.sub(r"\s*\n\s*", " ", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


# ---------------------------------------------------------------- build
def build(game: Path) -> list[dict]:
    version = json.loads((game / "release_info.json").read_text(encoding="utf-8")).get("version", "?")
    loc_files = read_pck(game / "SlayTheSpire2.pck", "localization/eng/")
    loc = {k.rsplit("/", 1)[1]: json.loads(v.decode("utf-8")) for k, v in loc_files.items() if k.endswith(".json")}
    dll = Dll(game / "data_sts2_windows_x86_64" / "sts2.dll")
    src = f"game files ({version}, your install)"

    def pools(ns: str, method: str, suffix: str) -> dict[str, str]:
        owner = {}
        for (tns, n), t in dll.types.items():
            if tns != f"{NS}.{ns}" or not n.endswith(suffix):
                continue
            m = dll.methods_of(t).get(method)
            if not m or not m.Rva:
                continue
            ret, _ = dll.run(m.Rva)
            who = n.removesuffix(suffix)
            if who in ("Deprecated", "Mock"):
                continue
            def models(v):
                if isinstance(v, list):
                    for x in v[1:]:
                        yield from models(x)
                elif isinstance(v, tuple) and v[:1] == ("model",):
                    yield v[1]
                elif isinstance(v, tuple) and v[:1] == ("obj",):
                    for a in v[2]:
                        yield from models(a)
            for x in models(ret):
                owner.setdefault(x, who)
        return owner

    card_pool = pools("CardPools", "GenerateAllCards", "CardPool")
    relic_pool = pools("RelicPools", "GenerateAllRelics", "RelicPool")
    potion_pool = pools("PotionPools", "GenerateAllPotions", "PotionPool")

    def keys_by_norm(table: dict) -> dict[str, str]:
        return {norm(k.rsplit(".", 1)[0]): k.rsplit(".", 1)[0] for k in table if k.endswith(".title")}

    out: list[dict] = []
    for kind, ns, table_name, pool in (("card", "Cards", "cards.json", card_pool),
                                       ("relic", "Relics", "relics.json", relic_pool),
                                       ("potion", "Potions", "potions.json", potion_pool)):
        table = loc.get(table_name, {})
        keys = keys_by_norm(table)
        for (tns, n), t in dll.types.items():
            if tns != f"{NS}.{ns}" or n.startswith(("Mock", "Deprecated")) or "<" in n:
                continue
            key = keys.get(norm(n))
            if not key:
                continue
            meths = dll.methods_of(t)
            vars: dict = {}
            if meths.get("get_CanonicalVars") is not None and meths["get_CanonicalVars"].Rva:
                fields = {}
                if meths.get(".ctor") is not None and meths[".ctor"].Rva:
                    _, ev = dll.run(meths[".ctor"].Rva)
                    fields = {norm(f): v for e0, f, v in (x for x in ev if x[0] == "field") if isinstance(v, Decimal)}
                ret, _ = dll.run(meths["get_CanonicalVars"].Rva)
                flatten_vars(dll, ret, vars)
                if fields and any(v is None for v in vars.values()):
                    # only fill values that are otherwise unknown (e.g. Ember Tea's combat count)
                    ret, _ = dll.run(meths["get_CanonicalVars"].Rva, fields)
                    filled: dict = {}
                    flatten_vars(dll, ret, filled)
                    for k, v in vars.items():
                        if v is None and filled.get(k) is not None:
                            vars[k] = filled[k]
            for k, v in list(vars.items()):
                if isinstance(v, tuple) and v[:1] == ("modelname",):
                    tbl = loc.get({"Enchantment": "enchantments.json", "Power": "powers.json", "Card": "cards.json",
                                   "Relic": "relics.json", "Potion": "potions.json"}.get(v[1], ""), {})
                    ek = keys_by_norm(tbl).get(norm(v[2]))
                    vars[k] = tbl.get(f"{ek}.title", v[2]) if ek else v[2].replace("_", " ").title()
            e = {"id": key, "kind": kind, "name": table.get(f"{key}.title", n), "source": src, "as_of": version}
            desc = table.get(f"{key}.description", "")
            base_text = clean(render(desc, vars, False))
            if kind == "card":
                cost = typ = rar = None
                kw: list[str] = []
                if meths.get(".ctor") is not None and meths[".ctor"].Rva:
                    _, ev = dll.run(meths[".ctor"].Rva)
                    b = next((x for x in ev if x[0] == "base"), None)
                    if b and len(b[2]) >= 3 and all(isinstance(a, Decimal) for a in b[2][:3]):
                        cost, typ, rar = (int(a) for a in b[2][:3])
                        tgt = int(b[2][3]) if len(b[2]) > 3 and isinstance(b[2][3], Decimal) else None
                        # text can switch on the card's own type/target; skip cards that change them during a run
                        if tgt is not None and tgt < len(TARGET) and "get_TargetType" not in meths:
                            vars.setdefault("TargetType", TARGET[tgt])
                        if typ < len(CARD_TYPE) and "get_Type" not in meths:
                            vars.setdefault("CardType", CARD_TYPE[typ])
                        base_text = clean(render(desc, vars, False))
                xcost = False
                if meths.get("get_HasEnergyCostX") is not None:
                    r, _ = dll.run(meths["get_HasEnergyCostX"].Rva)
                    xcost = r == 1
                if meths.get("get_CanonicalKeywords") is not None:
                    r, _ = dll.run(meths["get_CanonicalKeywords"].Rva)
                    def kws(v):
                        if isinstance(v, list):
                            return [x for x in v[1:] if isinstance(x, Decimal)]
                        if isinstance(v, tuple) and v[:1] == ("obj",):
                            return [a for a in v[2] if isinstance(a, Decimal)] + [y for a in v[2] for y in kws(a)]
                        return []
                    kw = [KEYWORD[int(x)] for x in kws(r) if 0 < int(x) < len(KEYWORD)]
                up_vars, up_cost, up_kw = dict(vars), None, list(kw)
                if meths.get("OnUpgrade") is not None and meths["OnUpgrade"].Rva:
                    _, ev = dll.run(meths["OnUpgrade"].Rva)
                    for x in ev:
                        if x[0] == "up" and isinstance(x[2], Decimal):
                            up_vars[x[1]] = (up_vars.get(x[1]) or Decimal(0)) + x[2]
                        elif x[0] == "cost" and cost is not None:
                            up_cost = int(x[2]) if "Set" in x[1] else cost + int(x[2])
                        elif x[0] in ("AddKeyword", "RemoveKeyword") and isinstance(x[1], Decimal):
                            k = KEYWORD[int(x[1])] if int(x[1]) < len(KEYWORD) else ""
                            if x[0] == "AddKeyword" and k not in up_kw:
                                up_kw.append(k)
                            elif k in up_kw:
                                up_kw.remove(k)
                with_kw = lambda text, ks: " ".join([text] + [f"{k}." for k in ks if k and k.lower() not in text.lower()]).strip()
                text = with_kw(base_text, kw)
                up_text = with_kw(clean(render(desc, up_vars, True)), up_kw)
                if up_cost is not None and up_cost != cost:
                    up_text += f" (costs {up_cost})"
                if up_text != text:
                    text += f" Upgraded: {up_text}"
                e.update(text=text, character=card_pool.get(n, ""),
                         type=CARD_TYPE[typ] if typ is not None and typ < len(CARD_TYPE) else "",
                         cost="X" if xcost else ("" if cost is None or cost < 0 else str(cost)),
                         rarity=CARD_RARITY[rar] if rar is not None and rar < len(CARD_RARITY) else "")
            else:
                rar = None
                if meths.get("get_Rarity") is not None:
                    r, _ = dll.run(meths["get_Rarity"].Rva)
                    rar = int(r) if isinstance(r, Decimal) else None
                names = RELIC_RARITY if kind == "relic" else POTION_RARITY
                e.update(text=base_text, character=(relic_pool if kind == "relic" else potion_pool).get(n, ""),
                         rarity=names[rar] if rar is not None and rar < len(names) else "")
            out.append(e)
    return out


def main() -> None:
    game = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAME
    if not (game / "SlayTheSpire2.pck").exists():
        sys.exit(f"Can't find SlayTheSpire2.pck in {game}. Pass the game folder as the argument.")
    out = build(game)
    dest = Path(os.environ.get("SUNDIAL_HOME", Path.home() / ".sundial-sts2")) / "knowledge"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "game.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    by = {k: sum(e["kind"] == k for e in out) for k in ("card", "relic", "potion")}
    unread = sum("X" in re.findall(r"\bX\b", e.get("text", "")) for e in out)
    print(f"Wrote {len(out)} entries ({by}) to {dest / 'game.json'}; {unread} have a value shown as X.")


if __name__ == "__main__":
    main()
