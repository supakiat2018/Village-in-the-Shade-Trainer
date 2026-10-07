"""
Village in the Shade — Trainer & Controller (v1.20)
รองรับ 2 ภาษา (ไทย / English)
"""

import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys
import json
import winsound
import re
import time
import datetime

# Win32 API Constants
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_RIGHTS = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
PROCESS_ALL_ACCESS = 0x1F0FFF

PAGE_EXECUTE_READWRITE = 0x40
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

TARGET_EXE = "village.exe"

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.VirtualProtectEx.restype = wintypes.BOOL

kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL

kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL

kernel32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
kernel32.FlushInstructionCache.restype = wintypes.BOOL

kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL

kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualAllocEx.restype = ctypes.c_void_p


def enable_debug_privilege():
    try:
        advapi32 = ctypes.windll.advapi32
        TOKEN_ADJUST_PRIVILEGES = 0x0020
        TOKEN_QUERY = 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002

        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]

        h_tok = wintypes.HANDLE()
        if advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_tok)):
            luid = LUID()
            if advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
                tp = TOKEN_PRIVILEGES()
                tp.PrivilegeCount = 1
                tp.Privileges[0].Luid = luid
                tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
                advapi32.AdjustTokenPrivileges(h_tok, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
            kernel32.CloseHandle(h_tok)
    except:
        pass

enable_debug_privilege()


# พจนานุกรมคำแปล 2 ภาษา (Thai & English)
TRANSLATIONS = {
    "th": {
        "title": "Village in the Shade — Trainer & Controller (v1.20)",
        "header_title": "🌿 Village in the Shade — Trainer",
        "header_sub": "ระบบสูตรโกงและตัวควบคุมเกม v1.20 (คลิกที่ปุ่มสีฟ้าเพื่อเปลี่ยนปุ่มลัดได้ตามต้องการ)",
        "status_searching": "🔍 กำลังค้นหา village.exe...",
        "status_connected": "🟢 เชื่อมต่อกับ village.exe สำเร็จ (PID: {pid})",
        "status_access_denied": "⚠️ พบ village.exe (PID: {pid}) แต่เกมรันเป็น Admin (กรุณารัน Trainer เป็น Admin)",
        "status_disconnected": "🔴 ไม่พบเกม village.exe (กรุณาเปิดเกม)",
        "status_launching": "🚀 กำลังเริ่มเกม village.exe...",
        "status_killed": "🔴 บังคับปิด village.exe เรียบร้อยแล้ว",
        "status_press_key": "⌨️ กรุณากดปุ่มบนคีย์บอร์ดที่ต้องการใช้สำหรับ '{name}' (กด Esc เพื่อยกเลิก)",
        "status_key_changed": "✅ เปลี่ยนปุ่มลัดของ '{name}' เป็น [{key}] เรียบร้อยแล้ว!",
        "status_reset_keys": "🔄 รีเซ็ตปุ่มลัดเป็น [F1] - [F12] เรียบร้อยแล้ว",
        "status_not_connected": "⚠️ ยังไม่ได้เปิดเกม หรือยังไม่ได้เชื่อมต่อกับ village.exe (กรุณาเปิดเกมก่อนเปิดสูตร)",
        "btn_launch": "🚀 เปิดเกม",
        "btn_running": "🎮 เกมกำลังทำงานอยู่",
        "btn_enable_all": "⚡ เปิดทั้งหมด",
        "btn_disable_all": "🛑 ปิดทั้งหมด",
        "btn_reset_keys": "⌨️ รีเซ็ตปุ่ม (F1-F12)",
        "btn_kill": "🛑 ปิดเกมทันที (Kill)",
        "btn_item_adder": "🎒 แผงเสกไอเทม (Item Adder)",
        "btn_lang": "🌐 ภาษา: ไทย 🇹🇭",
        "btn_cheat_on": "🟢 เปิด",
        "btn_cheat_off": "ปิด",
        "btn_listening": "[กดปุ่ม...]",
        "tip_rebind": "💡 วิธีแก้ไขปุ่มลัด: คลิกที่ปุ่มชื่อปุ่มสีฟ้า [F1] แล้วกดปุ่มใหม่บนคีย์บอร์ดที่ต้องการได้ทันที (กด Esc เพื่อยกเลิก)\n💡 ปุ่มลัดทำงานขณะเล่นเกมได้ทันที (เสียงบี๊บ: ติ๊ดสูง = เปิดสูตร / ติ๊ดต่ำ = ปิดสูตร)",
        "confirm_reset_title": "ยืนยันการรีเซ็ต",
        "confirm_reset_msg": "ต้องการรีเซ็ตปุ่มลัดทั้งหมดกลับเป็นค่าเริ่มต้น [F1] ถึง [F12] หรือไม่?",
        "confirm_kill_title": "ยืนยันการปิดเกม",
        "confirm_kill_msg": "ต้องการบังคับปิดเกม village.exe ทันทีหรือไม่?\n(ใช้กรณีเกมค้างหรือไม่ตอบสนอง)",
        "alert_title": "แจ้งเตือน",
        "error_title": "ข้อผิดพลาด",
        "game_already_running": "เกม village.exe กำลังเปิดทำงานอยู่แล้วครับ",
        "exe_not_found": "ไม่พบไฟล์ {exe} ในโฟลเดอร์เกม\n\nโฟลเดอร์ปัจจุบัน:\n{dir}\n\nกรุณาวางโปรแกรมไว้ในโฟลเดอร์เกมเดียวกับ {exe}",
        "cannot_launch": "ไม่สามารถเปิดเกมได้:\n{err}",
        "cheats": {
            "god_mode": "อมตะ / เลือดไม่ลด",
            "infinite_stamina": "สตามิน่าเต็มตลอด",
            "noclip": "เดินทะลุกำแพง (NoClip)",
            "infinite_items": "ไอเทมไม่ลด (ใช้/โยน/ปลูก)",
            "crafting_free": "คราฟต์ของ ฟรี",
            "cooking_free": "ทำอาหาร ฟรี",
            "smithing_free": "ตีเหล็ก ฟรี",
            "building_free": "ก่อสร้าง ฟรี",
            "dyeing_free": "ย้อมสี ฟรี",
            "submit_any_item": "ส่งเควสต์ได้ทุกไอเทม",
            "freeze_time": "หยุดเวลาในเกม",
            "infinite_money": "เงินไม่จำกัด (999,999)",
        }
    },
    "en": {
        "title": "Village in the Shade — Trainer & Controller (v1.20)",
        "header_title": "🌿 Village in the Shade — Trainer",
        "header_sub": "In-Game Trainer & Controller v1.20 (Click blue hotkey button to rebind keys)",
        "status_searching": "🔍 Searching for village.exe...",
        "status_connected": "🟢 Connected to village.exe (PID: {pid})",
        "status_access_denied": "⚠️ village.exe found (PID: {pid}) but running as Admin (Please run Trainer as Admin)",
        "status_disconnected": "🔴 village.exe Not Found (Please launch game)",
        "status_launching": "🚀 Launching village.exe...",
        "status_killed": "🔴 Force closed village.exe successfully",
        "status_press_key": "⌨️ Press any key on keyboard for '{name}' (Press Esc to cancel)",
        "status_key_changed": "✅ Hotkey for '{name}' changed to [{key}]!",
        "status_reset_keys": "🔄 Hotkeys reset to [F1] - [F12]",
        "status_not_connected": "⚠️ Game is not running or not connected yet (Please start game first)",
        "btn_launch": "🚀 Launch Game",
        "btn_running": "🎮 Game is Running",
        "btn_enable_all": "⚡ Enable All",
        "btn_disable_all": "🛑 Disable All",
        "btn_reset_keys": "⌨️ Reset Keys (F1-F12)",
        "btn_kill": "🛑 Kill Game",
        "btn_item_adder": "🎒 Item Spawner",
        "btn_lang": "🌐 Language: English 🇬🇧",
        "btn_cheat_on": "🟢 ON",
        "btn_cheat_off": "OFF",
        "btn_listening": "[Press Key...]",
        "tip_rebind": "💡 How to rebind keys: Click the blue hotkey button [F1] then press any key on your keyboard (Esc to cancel)\n💡 Hotkeys work globally in-game (High beep = Cheat ON / Low beep = Cheat OFF)",
        "confirm_reset_title": "Confirm Reset",
        "confirm_reset_msg": "Do you want to reset all hotkeys back to default [F1] to [F12]?",
        "confirm_kill_title": "Confirm Force Close",
        "confirm_kill_msg": "Do you want to force close village.exe immediately?\n(Use if game is frozen or unresponsive)",
        "alert_title": "Notification",
        "error_title": "Error",
        "game_already_running": "village.exe is already running.",
        "exe_not_found": "Could not find {exe} in game folder\n\nCurrent path:\n{dir}\n\nPlease place this program in the same folder as {exe}",
        "cannot_launch": "Cannot launch game:\n{err}",
        "cheats": {
            "god_mode": "God Mode (Invincible)",
            "infinite_stamina": "Infinite Stamina",
            "noclip": "Walk Through Walls (NoClip)",
            "infinite_items": "Infinite Items (Never Decrease)",
            "crafting_free": "Free Crafting (No Materials)",
            "cooking_free": "Free Cooking (No Ingredients)",
            "smithing_free": "Free Smithing (No Materials)",
            "building_free": "Free Building (No Materials)",
            "dyeing_free": "Free Dyeing (No Materials)",
            "submit_any_item": "Submit Any Item for Quest",
            "freeze_time": "Freeze Game Time",
            "infinite_money": "Infinite Money (999,999)",
        }
    }
}


# รายการสูตรโกงทั้งหมด 12 รายการ พร้อมปุ่มลัดเริ่มต้น (Default Hotkeys)
DEFAULT_CHEATS_DEF = [
    {
        "id": "god_mode",
        "key": "F1",
        "vk": 0x70,
        "type": "patch",
        "rva": 0x13B010,
        "orig": bytes.fromhex("40 53 48"),
        "patch": bytes.fromhex("B0 01 C3"),  # mov al, 1; ret
    },
    {
        "id": "infinite_stamina",
        "key": "F2",
        "vk": 0x71,
        "type": "lock_stamina",
    },
    {
        "id": "noclip",
        "key": "F3",
        "vk": 0x72,
        "type": "patch",
        "rva": 0x6C4A80,
        "orig": bytes.fromhex("40 53 48 83 EC 30"),
        "patch": bytes.fromhex("31 C0 C3 90 90 90"),  # xor eax, eax; ret; 3x nop
    },
    {
        "id": "infinite_items",
        "key": "F4",
        "vk": 0x73,
        "type": "patch",
        "rva": 0x153600,
        "orig": bytes.fromhex("48 89 5C 24 08 48"),
        "patch": bytes.fromhex("B8 01 00 00 00 C3"),  # mov eax, 1; ret
    },
    {
        "id": "crafting_free",
        "key": "F5",
        "vk": 0x74,
        "type": "patch",
        "rva": 0x375D10,
        "orig": bytes.fromhex("48 89 5C"),
        "patch": bytes.fromhex("B0 01 C3"),
    },
    {
        "id": "cooking_free",
        "key": "F6",
        "vk": 0x75,
        "type": "patch",
        "rva": 0x36F8D0,
        "orig": bytes.fromhex("48 89 5C"),
        "patch": bytes.fromhex("B0 01 C3"),
    },
    {
        "id": "smithing_free",
        "key": "F7",
        "vk": 0x76,
        "type": "patch",
        "rva": 0x339C00,
        "orig": bytes.fromhex("48 89 5C"),
        "patch": bytes.fromhex("B0 01 C3"),
    },
    {
        "id": "building_free",
        "key": "F8",
        "vk": 0x77,
        "type": "patch",
        "rva": 0x3688D0,
        "orig": bytes.fromhex("48 89 5C"),
        "patch": bytes.fromhex("B0 01 C3"),
    },
    {
        "id": "dyeing_free",
        "key": "F9",
        "vk": 0x78,
        "type": "patch",
        "rva": 0x38A030,
        "orig": bytes.fromhex("48 89 5C"),
        "patch": bytes.fromhex("B0 01 C3"),
    },
    {
        "id": "submit_any_item",
        "key": "F10",
        "vk": 0x79,
        "type": "patch",
        "rva": 0x3413F4,
        "orig": bytes.fromhex("0F 84 BA 03 00 00"),
        "patch": bytes.fromhex("90 90 90 90 90 90"),  # 6x NOP
    },
    {
        "id": "freeze_time",
        "key": "F11",
        "vk": 0x7A,
        "type": "lock_time",
    },
    {
        "id": "infinite_money",
        "key": "F12",
        "vk": 0x7B,
        "type": "lock_money",
    },
]

CHEATS_DEF = [dict(c) for c in DEFAULT_CHEATS_DEF]


def vk_to_friendly_name(vk: int) -> str:
    """แปลง Virtual Key Code เป็นชื่อปุ่มที่อ่านง่าย"""
    VK_NAMES = {
        0x08: "Back",
        0x09: "Tab",
        0x0D: "Enter",
        0x14: "Caps",
        0x1B: "Esc",
        0x20: "Space",
        0x21: "PgUp",
        0x22: "PgDn",
        0x23: "End",
        0x24: "Home",
        0x25: "Left",
        0x26: "Up",
        0x27: "Right",
        0x28: "Down",
        0x2D: "Ins",
        0x2E: "Del",
        0x60: "Num 0",
        0x61: "Num 1",
        0x62: "Num 2",
        0x63: "Num 3",
        0x64: "Num 4",
        0x65: "Num 5",
        0x66: "Num 6",
        0x67: "Num 7",
        0x68: "Num 8",
        0x69: "Num 9",
        0x6A: "Num *",
        0x6B: "Num +",
        0x6D: "Num -",
        0x6E: "Num .",
        0x6F: "Num /",
        0xBA: ";",
        0xBB: "=",
        0xBC: ",",
        0xBD: "-",
        0xBE: ".",
        0xBF: "/",
        0xC0: "`",
        0xDB: "[",
        0xDC: "\\",
        0xDD: "]",
        0xDE: "'",
    }
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if 0x41 <= vk <= 0x5A:
        return chr(vk)
    if vk in VK_NAMES:
        return VK_NAMES[vk]

    scan_code = user32.MapVirtualKeyW(vk, 0)
    lparam = scan_code << 16
    buf = ctypes.create_unicode_buffer(32)
    if user32.GetKeyNameTextW(lparam, buf, 32):
        name = buf.value.strip()
        if name:
            return name
    return f"Key_{vk}"


class GameMemoryManager:
    def __init__(self):
        self.pid = 0
        self.base_addr = 0
        self.h_process = None
        self.cheat_states = {c["id"]: False for c in CHEATS_DEF}
        self.frozen_time = None
        self.access_denied_pid = None

    def find_process_and_module(self):
        self.access_denied_pid = None
        # 1. ค้นหา Process ID ทั้งหมดของ village.exe
        h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h_snap == wintypes.HANDLE(-1).value or not h_snap:
            return False

        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        candidate_pids = []

        if kernel32.Process32FirstW(h_snap, ctypes.byref(pe)):
            while True:
                if pe.szExeFile.lower() == TARGET_EXE.lower():
                    candidate_pids.append(pe.th32ProcessID)
                if not kernel32.Process32NextW(h_snap, ctypes.byref(pe)):
                    break
        kernel32.CloseHandle(h_snap)

        if not candidate_pids:
            self.detach()
            return False

        # ถ้าเชื่อมต่อกับ PID เดิมอยู่แล้ว ตรวจสอบว่าโปรเซสยังทำงานอยู่หรือไม่
        if self.pid in candidate_pids and self.h_process:
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(self.h_process, ctypes.byref(exit_code)):
                if exit_code.value == 259:  # STILL_ACTIVE
                    return True
            self.detach()

        # วนลูปตรวจสอบ Candidate PIDs (เอา PID ตัวใหม่ล่าสุดก่อน)
        for found_pid in reversed(candidate_pids):
            h_proc = kernel32.OpenProcess(PROCESS_RIGHTS, False, found_pid)
            if not h_proc:
                err = kernel32.GetLastError()
                if err == 5:  # ERROR_ACCESS_DENIED
                    self.access_denied_pid = found_pid
                h_proc = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, found_pid)
            if not h_proc:
                continue

            h_mod_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, found_pid)
            if h_mod_snap == wintypes.HANDLE(-1).value or not h_mod_snap:
                kernel32.CloseHandle(h_proc)
                continue

            me = MODULEENTRY32W()
            me.dwSize = ctypes.sizeof(MODULEENTRY32W)
            mod_base = 0

            if kernel32.Module32FirstW(h_mod_snap, ctypes.byref(me)):
                while True:
                    if me.szModule.lower() == TARGET_EXE.lower():
                        mod_base = me.modBaseAddr
                        break
                    if not kernel32.Module32NextW(h_mod_snap, ctypes.byref(me)):
                        break
            kernel32.CloseHandle(h_mod_snap)

            if not mod_base:
                kernel32.CloseHandle(h_proc)
                continue

            # ทดสอบอ่านค่า 2 ไบต์เพื่อยืนยันว่าเข้าถึงหน่วยความจำได้จริง
            test_buf = (ctypes.c_ubyte * 2)()
            test_read = ctypes.c_size_t(0)
            if not kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(mod_base), ctypes.byref(test_buf), 2, ctypes.byref(test_read)):
                kernel32.CloseHandle(h_proc)
                continue

            # พบโปรเซสเกมที่ใช้งานได้จริง!
            self.pid = found_pid
            self.base_addr = mod_base
            self.h_process = h_proc

            # Re-apply active patches if game was restarted
            for c in CHEATS_DEF:
                if c["type"] == "patch" and self.cheat_states.get(c["id"], False):
                    self.apply_patch(c, True)

            return True

        self.detach()
        return False

    def read_memory(self, addr, size):
        if not self.h_process or not addr:
            return None
        buf = (ctypes.c_ubyte * size)()
        bytes_read = ctypes.c_size_t(0)
        if kernel32.ReadProcessMemory(self.h_process, ctypes.c_void_p(addr), ctypes.byref(buf), size, ctypes.byref(bytes_read)):
            return bytes(buf)
        return None

    def write_memory(self, addr, data):
        if not self.h_process or not addr:
            return False
        data_len = len(data)
        buf = (ctypes.c_ubyte * data_len)(*data)
        old_protect = wintypes.DWORD(0)
        if not kernel32.VirtualProtectEx(self.h_process, ctypes.c_void_p(addr), data_len, PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)):
            return False
        bytes_written = ctypes.c_size_t(0)
        ok = kernel32.WriteProcessMemory(self.h_process, ctypes.c_void_p(addr), ctypes.byref(buf), data_len, ctypes.byref(bytes_written))
        kernel32.VirtualProtectEx(self.h_process, ctypes.c_void_p(addr), data_len, old_protect.value, ctypes.byref(old_protect))
        kernel32.FlushInstructionCache(self.h_process, ctypes.c_void_p(addr), data_len)
        return bool(ok and bytes_written.value == data_len)

    def read_uint64(self, addr):
        data = self.read_memory(addr, 8)
        if data and len(data) == 8:
            return int.from_bytes(data, byteorder="little", signed=False)
        return 0

    def read_int32(self, addr):
        data = self.read_memory(addr, 4)
        if data and len(data) == 4:
            return int.from_bytes(data, byteorder="little", signed=True)
        return 0

    def read_int64(self, addr):
        data = self.read_memory(addr, 8)
        if data and len(data) == 8:
            return int.from_bytes(data, byteorder="little", signed=True)
        return 0

    def write_int32(self, addr, val):
        data = int(val).to_bytes(4, byteorder="little", signed=True)
        return self.write_memory(addr, data)

    def write_int64(self, addr, val):
        data = int(val).to_bytes(8, byteorder="little", signed=True)
        return self.write_memory(addr, data)

    def get_save_data_ptr(self):
        if not self.h_process or not self.base_addr:
            return 0
        gi = self.read_uint64(self.base_addr + 0x10FCBB0)
        if not (0x10000 <= gi <= 0x7FFFFFFFFFFF):
            return 0
        state = self.read_uint64(gi + 0x208)
        if not (0x10000 <= state <= 0x7FFFFFFFFFFF):
            return 0
        return state

    def get_seed_handle(self, sd_ptr):
        for i in range(30):
            item_ptr = self.read_uint64(sd_ptr + 0x32C0 + i * 8)
            if 0x10000 <= item_ptr <= 0x7FFFFFFFFFFF:
                h = self.read_uint64(item_ptr + 0x240)
                if 0x10000 <= h <= 0x7FFFFFFFFFFF:
                    return h
        for i in range(10):
            item_ptr = self.read_uint64(sd_ptr + 0x33B8 + i * 8)
            if 0x10000 <= item_ptr <= 0x7FFFFFFFFFFF:
                h = self.read_uint64(item_ptr + 0x240)
                if 0x10000 <= h <= 0x7FFFFFFFFFFF:
                    return h
        return 0

    def build_item_index(self, sd_ptr):
        if hasattr(self, "_item_index_cache") and self._item_index_cache:
            return self._item_index_cache
        seed = self.get_seed_handle(sd_ptr)
        if not seed:
            return {}
        first = seed - 0x18
        node = first
        item_map = {}
        visited = set()
        count = 0
        while count < 30000:
            if node in visited or node < 0x10000:
                break
            visited.add(node)
            key = self.read_uint64(node + 0x10)
            val = self.read_uint64(node + 0x18)
            if key and val and 0 < key < 10000000:
                rec_id = self.read_uint64(val)
                if rec_id == key:
                    item_map[key] = node + 0x18
            nxt = self.read_uint64(node)
            if not nxt or nxt == first:
                break
            node = nxt
            count += 1
        self._item_index_cache = item_map
        return item_map

    def get_selected_hand_slot(self, sd_ptr):
        return self.read_int32(sd_ptr + 0x33B0)

    def get_live_slot_info(self, sd_ptr, slot_idx):
        """อ่านข้อมูลไอเทมในช่องกระเป๋าจาก RAM (ptr, id, count)"""
        if not sd_ptr or slot_idx < 0 or slot_idx >= 30:
            return None, 0, 0
        slot_addr = sd_ptr + 0x32C0 + slot_idx * 8
        item_ptr = self.read_uint64(slot_addr)
        if not (0x10000 <= item_ptr <= 0x7FFFFFFFFFFF):
            return None, 0, 0
        h = self.read_uint64(item_ptr + 0x240)
        count = self.read_int32(item_ptr + 0x260)
        item_id = 0
        if 0x10000 <= h <= 0x7FFFFFFFFFFF:
            val = self.read_uint64(h)
            if 0x10000 <= val <= 0x7FFFFFFFFFFF:
                rec_id = self.read_uint64(val)
                if 0 < rec_id < 10000000:
                    item_id = rec_id
        return item_ptr, item_id, max(1, count)

    def set_live_item_in_slot(self, slot_idx, target_item_id, count):
        sd_ptr = self.get_save_data_ptr()
        if not sd_ptr:
            return False, "ไม่พบข้อมูล SaveData ใน RAM (กรุณาโหลดเซฟและเริ่มเดินในเกมก่อนครับ)"

        item_map = self.build_item_index(sd_ptr)
        handle = item_map.get(target_item_id)
        if not handle:
            return False, f"ไม่พบ Item Handle ของรหัส ID {target_item_id} ใน RAM"

        slot_addr = sd_ptr + 0x32C0 + slot_idx * 8
        item_ptr = self.read_uint64(slot_addr)

        if not (0x10000 <= item_ptr <= 0x7FFFFFFFFFFF):
            # Slot is empty in memory, clone template from an existing occupied slot
            template_ptr = 0
            for i in range(30):
                p = self.read_uint64(sd_ptr + 0x32C0 + i * 8)
                if 0x10000 <= p <= 0x7FFFFFFFFFFF:
                    template_ptr = p
                    break
            if not template_ptr:
                for i in range(10):
                    p = self.read_uint64(sd_ptr + 0x33B8 + i * 8)
                    if 0x10000 <= p <= 0x7FFFFFFFFFFF:
                        template_ptr = p
                        break
            if not template_ptr:
                return False, "กระเป๋าทุกช่องว่างเปล่า กรุณาเก็บของอะไรก็ได้ในเกมก่อน 1 ชิ้น"

            MEM_COMMIT_RESERVE = 0x1000 | 0x2000
            new_mem = kernel32.VirtualAllocEx(self.h_process, None, 0x300, MEM_COMMIT_RESERVE, 0x40)
            if not new_mem:
                return False, "VirtualAllocEx จัดสรรหน่วยความจำล้มเหลว"

            template_bytes = self.read_memory(template_ptr, 0x300)
            if not template_bytes:
                return False, "อ่าน Template ใน RAM ล้มเหลว"
            new_mem_addr = int(new_mem)
            self.write_memory(new_mem_addr, template_bytes)
            item_ptr = new_mem_addr
            self.write_uint64(slot_addr, item_ptr)

        ok_h = self.write_uint64(item_ptr + 0x240, handle)
        ok_c = self.write_int32(item_ptr + 0x260, count)
        if ok_h and ok_c:
            return True, "สำเร็จ"
        return False, "เขียนค่าลง RAM ไม่สำเร็จ"

    def set_live_item_in_hand(self, target_item_id, count):
        sd_ptr = self.get_save_data_ptr()
        if not sd_ptr:
            return False, "ไม่พบข้อมูล SaveData ใน RAM (กรุณาโหลดเซฟและเริ่มเดินในเกมก่อนครับ)"
        slot = self.get_selected_hand_slot(sd_ptr)
        if slot is None or slot < 0 or slot >= 30:
            slot = 0
        return self.set_live_item_in_slot(slot, target_item_id, count)


    def apply_patch(self, cheat_info, enable: bool) -> bool:
        if not self.h_process or not self.base_addr:
            return False
        target_addr = self.base_addr + cheat_info["rva"]
        patch_bytes = cheat_info["patch"] if enable else cheat_info["orig"]
        return self.write_memory(target_addr, patch_bytes)

    def tick_memory_locks(self):
        """วนลูปอัปเดตค่าความจำสำหรับสูตรประเภทล็อคค่า (Stamina, Money, Freeze Time)"""
        if not self.h_process or not self.base_addr:
            return

        gi = self.read_uint64(self.base_addr + 0x10FCBB0)
        if not (0x10000 <= gi <= 0x00007FFFFFFFFFF):
            return

        state = self.read_uint64(gi + 0x208)
        if not (0x10000 <= state <= 0x00007FFFFFFFFFF):
            return

        # 1. ล็อค Stamina เต็มตลอด
        if self.cheat_states.get("infinite_stamina", False):
            status = self.read_uint64(state + 0x32B8)
            if 0x10000 <= status <= 0x00007FFFFFFFFFF:
                max_stamina = self.read_int32(status + 0x3A4)
                if max_stamina > 0:
                    self.write_int32(status + 0x398, max_stamina)

        # 2. ล็อค เงิน 999,999
        if self.cheat_states.get("infinite_money", False):
            cur_money = self.read_int64(state + 0x32A0)
            if cur_money < 999999:
                self.write_int64(state + 0x32A0, 999999)

        # 3. ล็อค เวลา (Freeze Time)
        if self.cheat_states.get("freeze_time", False):
            cur_time = self.read_int64(state + 0x3270)
            if self.frozen_time is None or self.frozen_time <= 0:
                self.frozen_time = cur_time
            else:
                self.write_int64(state + 0x3270, self.frozen_time)
        else:
            self.frozen_time = None

    def kill_game_process(self):
        """สั่งปิดเกมทันที (Force Kill)"""
        killed = False
        if self.h_process:
            try:
                kernel32.TerminateProcess(self.h_process, 1)
                killed = True
            except:
                pass
        try:
            res = subprocess.run(
                ["taskkill", "/F", "/IM", TARGET_EXE, "/T"],
                capture_output=True,
                creationflags=0x08000000
            )
            if res.returncode == 0:
                killed = True
        except:
            pass
        self.detach()
        return killed

    def restore_all_patches(self):
        """คืนค่าไบต์เดิมของทุกสูตรใน RAM"""
        for c in CHEATS_DEF:
            if c["type"] == "patch":
                self.apply_patch(c, False)
            self.cheat_states[c["id"]] = False
        self.frozen_time = None

    def detach(self):
        if self.h_process:
            try:
                self.restore_all_patches()
                kernel32.CloseHandle(self.h_process)
            except:
                pass
        self.h_process = None
        self.pid = 0
        self.base_addr = 0


ITEM_CATEGORIES = [
    ("all", "📋 ทั้งหมด (All)"),
    ("crops", "🌱 พืชและเมล็ดพันธุ์ (Crops & Seeds)"),
    ("animals", "🐟 สัตว์ ปลา และล่าสัตว์ (Animals & Fish)"),
    ("materials", "⛏️ แร่และวัตถุดิบ (Materials & Crafting)"),
    ("food", "🍲 อาหารและเครื่องดื่ม (Food & Cooking)"),
    ("tools", "🔨 เครื่องมือและอุปกรณ์ (Tools & Facilities)"),
    ("clothing", "👒 เครื่องแต่งกายและหมวก (Clothing & Gear)"),
    ("furniture", "🛋️ เฟอร์นิเจอร์ (Furniture)"),
    ("recipes", "📜 พิมพ์เขียวและสูตร (Blueprints & Recipes)"),
    ("special", "⭐ ของพิเศษและเควสต์ (Special & Quest)"),
]

ITEM_CAT_DICT = dict(ITEM_CATEGORIES)

def classify_item_category(cid):
    if 10000 <= cid <= 12999:
        return 'crops'
    elif (30000 <= cid <= 49999) or (130000 <= cid <= 139999) or (160000 <= cid <= 169999) or (700000 <= cid <= 709999):
        return 'animals'
    elif 50000 <= cid <= 129999:
        return 'food'
    elif (200000 <= cid <= 229999) or (660000 <= cid <= 669999):
        return 'tools'
    elif (300000 <= cid <= 399999) or (520000 <= cid <= 529999):
        return 'clothing'
    elif 400000 <= cid <= 499999:
        return 'furniture'
    elif (20000 <= cid <= 29999) or (140000 <= cid <= 159999) or (600000 <= cid <= 659999):
        return 'materials'
    elif 500000 <= cid <= 519999:
        return 'recipes'
    else:
        return 'special'


class ItemAdderWindow(tk.Toplevel):
    def __init__(self, parent_root, trainer_app=None):
        super().__init__(parent_root)
        self.trainer_app = trainer_app
        self.title("Village in the Shade — แผงเสกไอเทม (Item Adder)")
        self.geometry("1160x760")
        self.minsize(1050, 680)
        self.configure(bg="#161622")

        self.items_data = []
        self.filtered_items = []
        self.current_cat_key = "all"
        self.selected_item = None
        self.save_files_map = {}
        self.current_save_path = None
        self.slot_info_cache = {}
        self.first_empty_slot = None

        self.load_items_data()
        self.setup_ui()
        self.refresh_save_files()
        self.refresh_live_slots()
        self.filter_items()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.trainer_app:
            self.trainer_app.item_adder_win = None
        self.destroy()

    def get_items_json_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        candidates = [
            os.path.join(base_dir, "items_th.json"),
            os.path.join(os.getcwd(), "items_th.json"),
            r"C:\Program Files (x86)\Steam\steamapps\common\Village in the Shade\items_th.json",
            os.path.join(os.getenv("APPDATA", ""), "Nippon Ichi Software, Inc", "Honogurashinoniwa", "items_th.json")
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def get_vits_cli_path(self):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        candidates = [
            os.path.join(base_dir, "vits-cli.exe"),
            os.path.join(os.getcwd(), "vits-cli.exe"),
            r"C:\Program Files (x86)\Steam\steamapps\common\Village in the Shade\vits-cli.exe"
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def load_items_data(self):
        path = self.get_items_json_path()
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
            self.items_data = []
            for item in raw_items:
                cid = item.get("id", 0)
                cat_key = classify_item_category(cid)
                th_name = item.get("th", "")
                en_name = item.get("en", "")
                zh_name = item.get("zh", "")
                self.items_data.append({
                    "id": cid,
                    "th": th_name,
                    "en": en_name,
                    "zh": zh_name,
                    "cat_key": cat_key,
                    "cat_name": ITEM_CAT_DICT.get(cat_key, "ของพิเศษและเควสต์"),
                    "search_text": f"{cid} {th_name} {en_name} {zh_name}".lower()
                })
        except Exception as e:
            print(f"Error loading items: {e}")

    def find_save_files(self):
        appdata = os.getenv("APPDATA")
        if not appdata:
            return []
        base_dir = os.path.join(appdata, "Nippon Ichi Software, Inc", "Honogurashinoniwa")
        saves = []
        if not os.path.isdir(base_dir):
            return saves
        for root, dirs, files in os.walk(base_dir):
            if any(x in root.lower() for x in ["backup", "bak", "pre_rename", "old", "tmp"]):
                continue
            for f in files:
                if re.match(r"^save\.0\d\d$", f):
                    full_p = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(full_p)
                        saves.append((full_p, f, mtime))
                    except:
                        pass
        saves.sort(key=lambda x: x[2], reverse=True)
        return saves

    def setup_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "ItemTree.Treeview",
            background="#20202D",
            foreground="#E4E4EE",
            fieldbackground="#20202D",
            rowheight=26,
            font=("Segoe UI", 9)
        )
        style.configure(
            "ItemTree.Treeview.Heading",
            background="#2A2A3C",
            foreground="#00D2FF",
            relief="flat",
            font=("Segoe UI", 9, "bold")
        )
        style.map(
            "ItemTree.Treeview",
            background=[("selected", "#0066CC")],
            foreground=[("selected", "#FFFFFF")]
        )
        style.map(
            "ItemTree.Treeview.Heading",
            background=[("active", "#36364E")]
        )

        style.configure(
            "Dark.TCombobox",
            fieldbackground="#2A2A3C",
            background="#36364E",
            foreground="#FFFFFF",
            arrowcolor="#00D2FF"
        )

        # Top Header
        top_bar = tk.Frame(self, bg="#1E1E2C", pady=8, padx=16, bd=1, relief="ridge")
        top_bar.pack(fill="x")

        lbl_top_title = tk.Label(
            top_bar,
            text="🎒 Village in the Shade — แผงค้นหาและเสกไอเทม (Item Adder)",
            font=("Segoe UI", 12, "bold"),
            fg="#FFFFFF",
            bg="#1E1E2C"
        )
        lbl_top_title.pack(side="left")

        lbl_top_sub = tk.Label(
            top_bar,
            text=f"• คลังไอเทมทั้งหมด {len(self.items_data):,} รายการ  |  รองรับภาษาไทย / English / ID",
            font=("Segoe UI", 9),
            fg="#8E8EA8",
            bg="#1E1E2C"
        )
        lbl_top_sub.pack(side="left", padx=(10, 0))

        # Main Body Split
        main_body = tk.Frame(self, bg="#161622")
        main_body.pack(fill="both", expand=True, padx=10, pady=8)

        # 1. LEFT PANEL: Categories
        left_panel = tk.Frame(main_body, bg="#1E1E2A", width=220, bd=1, relief="solid")
        left_panel.pack(side="left", fill="y", padx=(0, 6))
        left_panel.pack_propagate(False)

        cat_header = tk.Label(
            left_panel,
            text="หมวดหมู่ไอเทม (Categories)",
            font=("Segoe UI", 10, "bold"),
            fg="#00D2FF",
            bg="#1E1E2A",
            pady=8
        )
        cat_header.pack(fill="x")

        self.cat_buttons = {}
        for cat_key, cat_name in ITEM_CATEGORIES:
            btn = tk.Button(
                left_panel,
                text=cat_name,
                font=("Segoe UI", 9),
                bg="#252535" if cat_key != "all" else "#005A9E",
                fg="#E0E0E8" if cat_key != "all" else "#FFFFFF",
                activebackground="#36364C",
                activeforeground="#FFFFFF",
                relief="flat",
                anchor="w",
                padx=10,
                pady=6,
                cursor="hand2",
                command=lambda k=cat_key: self.select_category(k)
            )
            btn.pack(fill="x", padx=6, pady=2)
            self.cat_buttons[cat_key] = btn

        # 2. CENTER PANEL: Search & Treeview
        center_panel = tk.Frame(main_body, bg="#161622")
        center_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Search Bar
        search_bar = tk.Frame(center_panel, bg="#1E1E2A", bd=1, relief="solid", pady=6, padx=8)
        search_bar.pack(fill="x", pady=(0, 6))

        tk.Label(
            search_bar,
            text="🔍 ค้นหา:",
            font=("Segoe UI", 10, "bold"),
            fg="#00D2FF",
            bg="#1E1E2A"
        ).pack(side="left", padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_items())

        self.search_entry = tk.Entry(
            search_bar,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            bg="#2B2B3C",
            fg="#FFFFFF",
            insertbackground="#00D2FF",
            relief="flat",
            bd=5
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_clear_search = tk.Button(
            search_bar,
            text="✕ ล้าง",
            font=("Segoe UI", 9),
            bg="#3B3B4E",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.clear_search,
            padx=8,
            pady=2
        )
        self.btn_clear_search.pack(side="left", padx=(0, 8))

        self.lbl_count = tk.Label(
            search_bar,
            text="พบ 0 รายการ",
            font=("Segoe UI", 9, "bold"),
            fg="#FFCC00",
            bg="#1E1E2A"
        )
        self.lbl_count.pack(side="right")

        # Treeview Table
        tree_container = tk.Frame(center_panel, bg="#161622")
        tree_container.pack(fill="both", expand=True)

        cols = ("id", "th", "en", "cat")
        self.tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show="headings",
            style="ItemTree.Treeview",
            selectmode="browse"
        )
        self.tree.heading("id", text="ID", anchor="center")
        self.tree.heading("th", text="ชื่อภาษาไทย (Thai Name)", anchor="w")
        self.tree.heading("en", text="ชื่อภาษาอังกฤษ (English Name)", anchor="w")
        self.tree.heading("cat", text="หมวดหมู่", anchor="w")

        self.tree.column("id", width=65, anchor="center", stretch=False)
        self.tree.column("th", width=220, anchor="w")
        self.tree.column("en", width=180, anchor="w")
        self.tree.column("cat", width=140, anchor="w")

        scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree.tag_configure("even", background="#20202D")
        self.tree.tag_configure("odd", background="#252536")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-Button-1>", lambda e: self.do_spawn_in_hand())

        # 3. RIGHT PANEL: Details & Live Spawning Controls
        right_panel = tk.Frame(main_body, bg="#1E1E2A", width=380, bd=1, relief="solid")
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)

        # 3.1 Card Selected Item Details
        card_item = tk.Frame(right_panel, bg="#262638", bd=1, relief="ridge", padx=10, pady=8)
        card_item.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(
            card_item,
            text="📦 รายละเอียดไอเทมที่เลือก",
            font=("Segoe UI", 8, "bold"),
            fg="#8E8EA8",
            bg="#262638"
        ).pack(anchor="w")

        self.lbl_det_name_th = tk.Label(
            card_item,
            text="กรุณาคลิกเลือกไอเทมจากตาราง",
            font=("Segoe UI", 11, "bold"),
            fg="#00D2FF",
            bg="#262638",
            wraplength=350,
            justify="left",
            pady=2
        )
        self.lbl_det_name_th.pack(anchor="w")

        self.lbl_det_name_en_zh = tk.Label(
            card_item,
            text="-",
            font=("Segoe UI", 8),
            fg="#A0A0B8",
            bg="#262638",
            wraplength=350,
            justify="left"
        )
        self.lbl_det_name_en_zh.pack(anchor="w")

        self.lbl_det_meta = tk.Label(
            card_item,
            text="ID: - | หมวด: -",
            font=("Segoe UI", 8, "bold"),
            fg="#FFCC00",
            bg="#262638",
            pady=2
        )
        self.lbl_det_meta.pack(anchor="w")

        # 3.2 Card Quantity
        card_qty = tk.Frame(right_panel, bg="#232332", bd=1, relief="solid", padx=10, pady=6)
        card_qty.pack(fill="x", padx=8, pady=3)

        lbl_qty = tk.Label(
            card_qty,
            text="🔢 จำนวนที่ต้องการเสก (1 - 999 ชิ้น):",
            font=("Segoe UI", 9, "bold"),
            fg="#E0E0E8",
            bg="#232332"
        )
        lbl_qty.pack(anchor="w", pady=(0, 2))

        qty_row = tk.Frame(card_qty, bg="#232332")
        qty_row.pack(fill="x")

        self.spin_count = tk.Spinbox(
            qty_row,
            from_=1,
            to=999,
            font=("Segoe UI", 10, "bold"),
            width=5,
            bg="#2B2B3C",
            fg="#FFFFFF",
            buttonbackground="#3B3B4E",
            relief="flat"
        )
        self.spin_count.delete(0, "end")
        self.spin_count.insert(0, "1")
        self.spin_count.pack(side="left", padx=(0, 6))

        for q in [1, 10, 99, 999]:
            btn_q = tk.Button(
                qty_row,
                text=str(q),
                font=("Segoe UI", 8, "bold"),
                bg="#3B3B4E",
                fg="#E0E0E8",
                activebackground="#4E4E68",
                relief="flat",
                cursor="hand2",
                command=lambda val=q: self.set_quantity(val),
                padx=5,
                pady=1
            )
            btn_q.pack(side="left", padx=2)

        # 3.3 Card Live RAM Spawning (โหมดหลัก: เสกสดเข้าเกมทันที)
        card_live = tk.Frame(right_panel, bg="#1E2333", bd=1, relief="ridge", padx=10, pady=8)
        card_live.pack(fill="x", padx=8, pady=4)

        live_title_row = tk.Frame(card_live, bg="#1E2333")
        live_title_row.pack(fill="x", pady=(0, 2))

        tk.Label(
            live_title_row,
            text="⚡ เสกเข้าเกมสด (Live In-Game RAM)",
            font=("Segoe UI", 9, "bold"),
            fg="#00D2FF",
            bg="#1E2333"
        ).pack(side="left")

        tk.Label(
            card_live,
            text="ของเปลี่ยนในเกมทันทีแบบ Real-Time ไม่ต้องโหลดเซฟใหม่",
            font=("Segoe UI", 8),
            fg="#88A0B8",
            bg="#1E2333"
        ).pack(anchor="w", pady=(0, 6))

        # --- แบบที่ 1: เสกทับของในมือ ---
        self.btn_spawn_hand = tk.Button(
            card_live,
            text="✋ แบบ 1: เสกทับไอเทมที่ถือในมือ (In-Hand)",
            font=("Segoe UI", 9, "bold"),
            bg="#0D6EFD",
            fg="#FFFFFF",
            activebackground="#0B5ED7",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.do_spawn_in_hand,
            pady=6
        )
        self.btn_spawn_hand.pack(fill="x", pady=(0, 2))

        tk.Label(
            card_live,
            text="✨ ถืออะไรอยู่กดปุ่มนี้จะกลายเป็นไอเทมที่เลือกทันที",
            font=("Segoe UI", 8),
            fg="#7E92A8",
            bg="#1E2333"
        ).pack(anchor="w", pady=(0, 6))

        # Divider line
        tk.Frame(card_live, height=1, bg="#2E3A52").pack(fill="x", pady=4)

        # --- แบบที่ 2: เสกแทนที่ช่องกระเป๋าที่เลือก ---
        slot_sel_header = tk.Frame(card_live, bg="#1E2333")
        slot_sel_header.pack(fill="x", pady=(2, 2))

        tk.Label(
            slot_sel_header,
            text="🎒 แบบ 2: เลือกช่องกระเป๋า (00 - 29):",
            font=("Segoe UI", 9, "bold"),
            fg="#E0E0E8",
            bg="#1E2333"
        ).pack(side="left")

        btn_refresh_live = tk.Button(
            slot_sel_header,
            text="🔄 รีเฟรช",
            font=("Segoe UI", 8),
            bg="#2B364C",
            fg="#00D2FF",
            relief="flat",
            cursor="hand2",
            command=self.refresh_live_slots,
            padx=4,
            pady=0
        )
        btn_refresh_live.pack(side="right")

        self.combo_live_slots = ttk.Combobox(
            card_live,
            state="readonly",
            style="Dark.TCombobox",
            font=("Segoe UI", 9)
        )
        self.combo_live_slots.pack(fill="x", pady=(0, 5))

        self.btn_spawn_slot = tk.Button(
            card_live,
            text="🎒 แบบ 2: เสกแทนที่ช่องกระเป๋าที่เลือก (Slot)",
            font=("Segoe UI", 9, "bold"),
            bg="#198754",
            fg="#FFFFFF",
            activebackground="#157347",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.do_spawn_in_slot,
            pady=6
        )
        self.btn_spawn_slot.pack(fill="x", pady=(0, 2))

        tk.Label(
            card_live,
            text="✨ เสกแทนที่ไอเทมในช่องกระเป๋าที่เลือกด้านบนทันที",
            font=("Segoe UI", 8),
            fg="#7E92A8",
            bg="#1E2333"
        ).pack(anchor="w")

        # 3.4 Card Fallback Save File (.sav)
        card_save = tk.Frame(right_panel, bg="#21212B", bd=1, relief="solid", padx=8, pady=4)
        card_save.pack(fill="x", padx=8, pady=2)

        save_row = tk.Frame(card_save, bg="#21212B")
        save_row.pack(fill="x")

        tk.Label(
            save_row,
            text="💾 สำรอง: เสกเข้าไฟล์เซฟ (.sav)",
            font=("Segoe UI", 8, "bold"),
            fg="#8888A0",
            bg="#21212B"
        ).pack(side="left")

        self.btn_save_fallback = tk.Button(
            save_row,
            text="เสกเข้าไฟล์เซฟ",
            font=("Segoe UI", 8),
            bg="#3B3B4E",
            fg="#E0E0E8",
            activebackground="#4E4E68",
            relief="flat",
            cursor="hand2",
            command=self.do_add_item,
            padx=6,
            pady=1
        )
        self.btn_save_fallback.pack(side="right")

        self.combo_saves = ttk.Combobox(card_save, state="readonly", style="Dark.TCombobox", font=("Segoe UI", 8))
        self.combo_saves.pack(fill="x", pady=(2, 2))
        self.combo_saves.bind("<<ComboboxSelected>>", self.on_save_selected)

        self.combo_slots = ttk.Combobox(card_save, state="readonly", style="Dark.TCombobox", font=("Segoe UI", 8))
        self.combo_slots.pack(fill="x", pady=(0, 2))

        # 3.5 Status & Feedback Box
        status_box = tk.Frame(right_panel, bg="#161622", bd=1, relief="ridge", padx=8, pady=6)
        status_box.pack(fill="both", expand=True, padx=8, pady=(3, 8))

        self.lbl_status = tk.Label(
            status_box,
            text="💡 เลือกไอเทมในตาราง แล้วกด [แบบ 1] หรือ [แบบ 2]\nเพื่อเสกเข้าเกมสดใน RAM ได้ทันทีครับ",
            font=("Segoe UI", 8, "bold"),
            fg="#00D2FF",
            bg="#161622",
            justify="left",
            wraplength=340
        )
        self.lbl_status.pack(anchor="w", pady=(0, 2))

        lbl_tips = tk.Label(
            status_box,
            text="📌 วิธีใช้:\n• แบบ 1: ถืออะไรอยู่กดปุ่มจะกลายเป็นไอเทมนั้นทันที!\n• แบบ 2: เลือกช่อง 00-29 เพื่อเสกแทนที่ช่องนั้น\n• ดับเบิ้ลคลิกที่ชื่อไอเทมในตาราง = เสกเข้ามือทันที",
            font=("Segoe UI", 8),
            fg="#8888A0",
            bg="#161622",
            justify="left",
            wraplength=340
        )
        lbl_tips.pack(anchor="w")

    def select_category(self, cat_key):
        self.current_cat_key = cat_key
        for k, btn in self.cat_buttons.items():
            if k == cat_key:
                btn.config(bg="#005A9E", fg="#FFFFFF")
            else:
                btn.config(bg="#252535", fg="#E0E0E8")
        self.filter_items()

    def clear_search(self):
        self.search_var.set("")
        self.search_entry.focus_set()

    def set_quantity(self, val):
        self.spin_count.delete(0, "end")
        self.spin_count.insert(0, str(val))

    def set_rank(self, val):
        self.spin_rank.delete(0, "end")
        self.spin_rank.insert(0, str(val))

    def filter_items(self):
        query = self.search_var.get().strip().lower()
        cat_key = self.current_cat_key

        filtered = []
        for item in self.items_data:
            if cat_key != "all" and item["cat_key"] != cat_key:
                continue
            if query and query not in item["search_text"]:
                continue
            filtered.append(item)

        self.filtered_items = filtered
        self.lbl_count.config(text=f"พบ {len(filtered):,} รายการ")

        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(filtered):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["id"], item["th"], item["en"], item["cat_name"]),
                tags=(tag,)
            )

        if filtered:
            first_id = str(filtered[0]["id"])
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self.on_item_selected(filtered[0])
        else:
            self.selected_item = None
            self.lbl_det_name_th.config(text="(ไม่พบไอเทมที่ตรงกับคำค้น)")
            self.lbl_det_name_en_zh.config(text="-")
            self.lbl_det_meta.config(text="ID: - | หมวด: -")

    def on_tree_select(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        item_id_str = selected[0]
        item = next((x for x in self.items_data if str(x["id"]) == item_id_str), None)
        if item:
            self.on_item_selected(item)

    def on_item_selected(self, item):
        self.selected_item = item
        self.lbl_det_name_th.config(text=item["th"])
        self.lbl_det_name_en_zh.config(text=f"{item['en']}  |  {item['zh']}")
        self.lbl_det_meta.config(text=f"ID: {item['id']}  |  หมวด: {item['cat_name']}")

    def refresh_save_files(self):
        saves = self.find_save_files()
        self.save_files_map.clear()
        combo_values = []
        for full_p, fname, mtime in saves:
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            label = f"{fname} ({dt_str})"
            self.save_files_map[label] = full_p
            combo_values.append(label)

        if not combo_values:
            combo_values = ["(ไม่พบไฟล์เซฟในระบบ)"]

        self.combo_saves["values"] = combo_values
        if combo_values and combo_values[0] != "(ไม่พบไฟล์เซฟในระบบ)":
            self.combo_saves.current(0)
            self.on_save_selected()
        else:
            self.current_save_path = None
            self.combo_slots["values"] = ["(ไม่มีไฟล์เซฟ)"]
            self.combo_slots.current(0)

    def on_save_selected(self, event=None):
        label = self.combo_saves.get()
        full_p = self.save_files_map.get(label)
        if full_p and os.path.isfile(full_p):
            self.current_save_path = full_p
            self.refresh_slots()

    def refresh_slots(self):
        if not self.current_save_path or not os.path.isfile(self.current_save_path):
            return

        cli_exe = self.get_vits_cli_path()
        if not cli_exe:
            self.combo_slots["values"] = ["⭐ ช่องว่างแรกอัตโนมัติ (Auto Free Slot)"]
            self.combo_slots.current(0)
            return

        try:
            res = subprocess.run(
                [cli_exe, "dump", "--save", self.current_save_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            first_empty = None
            slot_list = ["⭐ ช่องว่างแรกอัตโนมัติ"]
            self.slot_info_cache.clear()

            for line in res.stdout.splitlines():
                m = re.match(r"^\s*(\d+)\s+(.+)$", line)
                if m:
                    idx = int(m.group(1))
                    raw_desc = m.group(2).strip()
                    is_empty = "(空)" in raw_desc
                    if is_empty:
                        slot_list.append(f"ช่อง {idx:02d} : [ ว่าง ]")
                        if first_empty is None:
                            first_empty = idx
                    else:
                        slot_list.append(f"ช่อง {idx:02d} : {raw_desc}")
                    self.slot_info_cache[idx] = (is_empty, raw_desc)

            self.first_empty_slot = first_empty
            if first_empty is not None:
                slot_list[0] = f"⭐ ช่องว่างแรกอัตโนมัติ (ช่องที่ {first_empty:02d})"
            else:
                slot_list[0] = "⚠️ กระเป๋าเต็ม 30 ช่อง (เลือกช่องเพื่อเขียนทับ)"

            self.combo_slots["values"] = slot_list
            self.combo_slots.current(0)
        except Exception as e:
            self.combo_slots["values"] = ["⭐ ช่องว่างแรกอัตโนมัติ (Auto Free Slot)"]
            self.combo_slots.current(0)

    def refresh_live_slots(self):
        """อ่านข้อมูลไอเทมในกระเป๋า 30 ช่องสดๆ จาก RAM ของเกม"""
        mgr = self.trainer_app.mgr if self.trainer_app else None
        if not mgr or not mgr.h_process:
            self.combo_live_slots["values"] = [f"ช่อง {i:02d} : (ยังไม่ได้เปิดเกม)" for i in range(30)]
            self.combo_live_slots.current(0)
            return

        sd_ptr = mgr.get_save_data_ptr()
        if not sd_ptr:
            self.combo_live_slots["values"] = [f"ช่อง {i:02d} : (ไม่พบข้อมูลใน RAM)" for i in range(30)]
            self.combo_live_slots.current(0)
            return

        hand_slot = mgr.get_selected_hand_slot(sd_ptr)
        slot_list = []
        for i in range(30):
            item_ptr, item_id, count = mgr.get_live_slot_info(sd_ptr, i)
            if item_ptr and item_id:
                item_obj = next((x for x in self.items_data if x["id"] == item_id), None)
                item_name = item_obj["th"] if item_obj else f"ID: {item_id}"
                desc = f"{item_name} x{count}"
            elif item_ptr:
                desc = f"ไอเทม x{count}"
            else:
                desc = "[ ว่าง ]"

            is_hand = (i == hand_slot)
            prefix = "👉 " if is_hand else "   "
            hand_tag = " [ถือในมือ]" if is_hand else ""
            slot_list.append(f"{prefix}ช่อง {i:02d}{hand_tag} : {desc}")

        self.combo_live_slots["values"] = slot_list
        if 0 <= hand_slot < 30:
            self.combo_live_slots.current(hand_slot)
        else:
            self.combo_live_slots.current(0)

    def do_spawn_in_hand(self):
        """แบบที่ 1: เสกทับไอเทมที่ถือในมือ (In-Hand) ทันทีใน RAM"""
        if not self.selected_item:
            messagebox.showwarning("แจ้งเตือน", "กรุณาคลิกเลือกไอเทมจากตารางก่อนกดเสกครับ", parent=self)
            return

        mgr = self.trainer_app.mgr if self.trainer_app else None
        if not mgr:
            return

        if not mgr.h_process:
            mgr.find_process_and_module()

        if not mgr.h_process:
            messagebox.showwarning(
                "ไม่พบตัวเกม",
                "ไม่พบเกม village.exe กำลังเปิดทำงานอยู่\nกรุณาเปิดเกมและโหลดเซฟเดินในเกมก่อนกดเสกครับ",
                parent=self
            )
            return

        try:
            count = int(self.spin_count.get())
            count = max(1, min(999, count))
        except:
            count = 1

        target_id = self.selected_item["id"]
        item_name = self.selected_item["th"]

        ok, msg = mgr.set_live_item_in_hand(target_id, count)
        if ok:
            sd_ptr = mgr.get_save_data_ptr()
            hand_slot = mgr.get_selected_hand_slot(sd_ptr) if sd_ptr else 0
            res_text = f"✨ สำเร็จ (แบบ 1)! เสก [{item_name}] x{count} เข้ามือ (ช่อง {hand_slot:02d}) เรียบร้อยแล้ว!"
            self.lbl_status.config(text=res_text, fg="#00FF88")
            try:
                winsound.Beep(1200, 100)
            except:
                pass
            self.refresh_live_slots()
        else:
            self.lbl_status.config(text=f"❌ เสกไม่สำเร็จ: {msg}", fg="#FF5555")
            try:
                winsound.Beep(400, 150)
            except:
                pass

    def do_spawn_in_slot(self):
        """แบบที่ 2: เสกแทนที่ช่องกระเป๋า 00-29 (Slot) ทันทีใน RAM"""
        if not self.selected_item:
            messagebox.showwarning("แจ้งเตือน", "กรุณาคลิกเลือกไอเทมจากตารางก่อนกดเสกครับ", parent=self)
            return

        mgr = self.trainer_app.mgr if self.trainer_app else None
        if not mgr:
            return

        if not mgr.h_process:
            mgr.find_process_and_module()

        if not mgr.h_process:
            messagebox.showwarning(
                "ไม่พบตัวเกม",
                "ไม่พบเกม village.exe กำลังเปิดทำงานอยู่\nกรุณาเปิดเกมและโหลดเซฟเดินในเกมก่อนกดเสกครับ",
                parent=self
            )
            return

        cur_idx = self.combo_live_slots.current()
        if cur_idx < 0:
            sel_str = self.combo_live_slots.get()
            m = re.search(r"ช่อง\s*(\d+)", sel_str)
            cur_idx = int(m.group(1)) if m else 0

        target_slot = max(0, min(29, cur_idx))

        try:
            count = int(self.spin_count.get())
            count = max(1, min(999, count))
        except:
            count = 1

        target_id = self.selected_item["id"]
        item_name = self.selected_item["th"]

        ok, msg = mgr.set_live_item_in_slot(target_slot, target_id, count)
        if ok:
            res_text = f"✨ สำเร็จ (แบบ 2)! เสก [{item_name}] x{count} ลงช่องที่ {target_slot:02d} ในเกมเรียบร้อยแล้ว!"
            self.lbl_status.config(text=res_text, fg="#00FF88")
            try:
                winsound.Beep(1200, 100)
            except:
                pass
            self.refresh_live_slots()
        else:
            self.lbl_status.config(text=f"❌ เสกไม่สำเร็จ: {msg}", fg="#FF5555")
            try:
                winsound.Beep(400, 150)
            except:
                pass

    def do_add_item(self):
        if not self.selected_item:
            messagebox.showwarning("แจ้งเตือน", "กรุณาคลิกเลือกไอเทมจากตารางก่อนกดเสกครับ", parent=self)
            return

        if not self.current_save_path or not os.path.isfile(self.current_save_path):
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกไฟล์เซฟเกมก่อนครับ", parent=self)
            return

        cli_exe = self.get_vits_cli_path()
        if not cli_exe:
            messagebox.showerror("ข้อผิดพลาด", "ไม่พบโปรแกรม vits-cli.exe ในโฟลเดอร์เกม", parent=self)
            return

        selected_slot_str = self.combo_slots.get()
        if "ช่องว่างแรกอัตโนมัติ" in selected_slot_str:
            if self.first_empty_slot is None:
                self.refresh_slots()
                if self.first_empty_slot is None:
                    messagebox.showerror("กระเป๋าเต็ม", "กระเป๋าทั้ง 30 ช่องเต็มหมดแล้วครับ! กรุณาเลือกช่องที่จะเขียนทับ", parent=self)
                    return
            target_slot = self.first_empty_slot
        else:
            m = re.match(r"^ช่อง\s*(\d+)", selected_slot_str)
            if m:
                target_slot = int(m.group(1))
            else:
                target_slot = 0

        try:
            count = int(self.spin_count.get())
            count = max(1, min(999, count))
        except:
            count = 1

        rank = 4
        if hasattr(self, "spin_rank"):
            try:
                rank = int(self.spin_rank.get())
                rank = max(0, min(4, rank))
            except:
                rank = 4

        item_id = str(self.selected_item["id"])
        item_name_th = self.selected_item["th"]

        cmd = [
            cli_exe,
            "set-slot",
            str(target_slot),
            "--id", item_id,
            "--count", str(count),
            "--rank", str(rank),
            "--replace",
            "--save", self.current_save_path
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0:
                save_filename = os.path.basename(self.current_save_path)
                msg = f"✨ เสกสำเร็จ! [{item_name_th}] x{count} ({rank}★)\nลงใน {save_filename} (ช่องที่ {target_slot}) เรียบร้อยแล้ว!"
                self.lbl_status.config(text=msg, fg="#44FF44")
                try:
                    winsound.Beep(1200, 100)
                except:
                    pass
                self.refresh_slots()
            else:
                err_msg = res.stderr or res.stdout
                if "背包全空" in err_msg:
                    messagebox.showwarning(
                        "ข้อแนะนำ",
                        "ไฟล์เซฟนี้ยังไม่มีไอเทมในตัวเลยแม้แต่ชิ้นเดียว (กระเป๋าว่าง 100%)\nทำให้ระบบโคลนโครงสร้างไอเทมไม่ได้\n\n👉 วิธีแก้: เข้าเกมแล้วเก็บของอะไรก็ได้ 1 ชิ้น (ก้อนหิน, กิ่งไม้) แล้วเซฟ จากนั้นจะเสกได้ทุกชิ้นตามปกติครับ!",
                        parent=self
                    )
                    self.lbl_status.config(
                        text="⚠️ กระเป๋าในเซฟนี้ว่าง 100% กรุณาเก็บของ 1 ชิ้นในเกมก่อน",
                        fg="#FFAA33"
                    )
                else:
                    self.lbl_status.config(
                        text=f"❌ เสกไม่สำเร็จ: {err_msg[:80]}",
                        fg="#FF5555"
                    )
                    try:
                        winsound.Beep(400, 150)
                    except:
                        pass
        except Exception as e:
            self.lbl_status.config(text=f"❌ เกิดข้อผิดพลาด: {e}", fg="#FF5555")



class TrainerApp:
    def __init__(self, root):
        self.root = root
        self.cur_lang = "th"  # "th" หรือ "en"
        self.mgr = GameMemoryManager()
        self.key_states = {}
        self.cheat_buttons = {}
        self.cheat_key_buttons = {}
        self.cheat_labels = {}
        self.listening_cheat_id = None
        self.item_adder_win = None

        self.load_config()

        self.root.title(self.t("title"))
        self.root.geometry("850x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#1A1A22")

        self.setup_ui()
        self.poll_game_status()
        self.poll_hotkeys()
        self.poll_memory_tick()

        self.root.bind("<KeyPress>", self.on_gui_keypress)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def t(self, key, **kwargs):
        """ดึงข้อความแปลตามภาษาปัจจุบัน"""
        text = TRANSLATIONS.get(self.cur_lang, TRANSLATIONS["th"]).get(key, key)
        if kwargs and isinstance(text, str):
            try:
                text = text.format(**kwargs)
            except:
                pass
        return text

    def t_cheat(self, cheat_id):
        """ดึงชื่อสูตรตามภาษาปัจจุบัน"""
        cheats_dict = TRANSLATIONS.get(self.cur_lang, TRANSLATIONS["th"]).get("cheats", {})
        return cheats_dict.get(cheat_id, cheat_id)

    def get_config_path(self):
        base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "trainer_config.json")

    def load_config(self):
        cfg_path = self.get_config_path()
        data = None
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except:
                pass

        # ถอยกลับไปดูไฟล์เดิม trainer_keys.json หากไม่มี trainer_config.json
        if not data:
            old_path = os.path.join(os.path.dirname(cfg_path), "trainer_keys.json")
            if os.path.isfile(old_path):
                try:
                    with open(old_path, "r", encoding="utf-8") as f:
                        old_keys = json.load(f)
                        data = {"language": "th", "keys": old_keys}
                except:
                    pass

        if data:
            self.cur_lang = data.get("language", "th")
            if self.cur_lang not in ("th", "en"):
                self.cur_lang = "th"

            saved_keys = data.get("keys", data)
            for c in CHEATS_DEF:
                if c["id"] in saved_keys:
                    entry = saved_keys[c["id"]]
                    if isinstance(entry, dict):
                        c["key"] = entry.get("key", c["key"])
                        c["vk"] = entry.get("vk", c["vk"])

    def save_config(self):
        cfg_path = self.get_config_path()
        try:
            data = {
                "language": self.cur_lang,
                "keys": {c["id"]: {"key": c["key"], "vk": c["vk"]} for c in CHEATS_DEF}
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass

    def toggle_language(self):
        """สลับภาษาระหว่าง ไทย (TH) และ อังกฤษ (EN)"""
        self.cur_lang = "en" if self.cur_lang == "th" else "th"
        self.save_config()
        self.apply_language()

    def apply_language(self):
        """อัปเดตข้อความทุกจุดในหน้าต่าง GUI ตามภาษาที่เลือก"""
        self.root.title(self.t("title"))
        self.lbl_title.config(text=self.t("header_title"))
        self.lbl_sub.config(text=self.t("header_sub"))
        self.btn_lang.config(text=self.t("btn_lang"))

        # ปุ่มการทำงานหลัก
        if self.mgr.h_process:
            self.btn_launch.config(text=self.t("btn_running"))
        else:
            self.btn_launch.config(text=self.t("btn_launch"))

        self.btn_enable_all.config(text=self.t("btn_enable_all"))
        self.btn_disable_all.config(text=self.t("btn_disable_all"))
        self.btn_reset_keys.config(text=self.t("btn_reset_keys"))
        if hasattr(self, "btn_item_adder"): self.btn_item_adder.config(text=self.t("btn_item_adder"))
        self.btn_kill.config(text=self.t("btn_kill"))

        # ข้อความคำแนะนำด้านล่าง
        self.tip_lbl.config(text=self.t("tip_rebind"))

        # ชื่อสูตรและปุ่มเปิด/ปิดแต่ละแถว
        for c in CHEATS_DEF:
            lbl = self.cheat_labels.get(c["id"])
            if lbl:
                lbl.config(text=self.t_cheat(c["id"]))
            self.update_cheat_ui(c["id"])

        # อัปเดตข้อความสถานะเกม
        self.poll_game_status()

    def reset_keybindings(self):
        if messagebox.askyesno(self.t("confirm_reset_title"), self.t("confirm_reset_msg")):
            self.cancel_rebind()
            for c, def_c in zip(CHEATS_DEF, DEFAULT_CHEATS_DEF):
                c["key"] = def_c["key"]
                c["vk"] = def_c["vk"]
            self.save_config()
            self.update_all_key_badges()
            self.lbl_game_status.config(text=self.t("status_reset_keys"), fg="#44FF44")
            try:
                winsound.Beep(900, 100)
            except:
                pass

    def get_game_exe_path(self):
        base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base_dir, TARGET_EXE)
        if os.path.isfile(candidate):
            return candidate
        cwd_candidate = os.path.join(os.getcwd(), TARGET_EXE)
        if os.path.isfile(cwd_candidate):
            return cwd_candidate
        return None

    def setup_ui(self):
        # 1. Top Header Frame
        header_frame = tk.Frame(self.root, bg="#1A1A22")
        header_frame.pack(fill="x", padx=18, pady=(12, 4))

        title_box = tk.Frame(header_frame, bg="#1A1A22")
        title_box.pack(side="left", fill="x", expand=True)

        self.lbl_title = tk.Label(
            title_box,
            text=self.t("header_title"),
            font=("Segoe UI", 15, "bold"),
            fg="#FFFFFF",
            bg="#1A1A22",
            anchor="w"
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_sub = tk.Label(
            title_box,
            text=self.t("header_sub"),
            font=("Segoe UI", 8),
            fg="#8E8EA8",
            bg="#1A1A22",
            anchor="w"
        )
        self.lbl_sub.pack(anchor="w", pady=(1, 0))

        # Language Switch Button (Top Right)
        self.btn_lang = tk.Button(
            header_frame,
            text=self.t("btn_lang"),
            font=("Segoe UI", 9, "bold"),
            bg="#2A2A3D",
            fg="#00D2FF",
            activebackground="#3D3D58",
            activeforeground="#55E2FF",
            relief="flat",
            cursor="hand2",
            command=self.toggle_language,
            padx=10,
            pady=5
        )
        self.btn_lang.pack(side="right", padx=(10, 0), pady=2)

        # 2. Status Banner
        status_frame = tk.Frame(self.root, bg="#242432", bd=1, relief="ridge")
        status_frame.pack(fill="x", padx=18, pady=3)

        self.lbl_game_status = tk.Label(
            status_frame,
            text=self.t("status_searching"),
            font=("Segoe UI", 9, "bold"),
            fg="#FFCC00",
            bg="#242432",
            pady=6
        )
        self.lbl_game_status.pack()

        # 3. Action Buttons Bar
        action_bar = tk.Frame(self.root, bg="#1A1A22")
        action_bar.pack(fill="x", padx=18, pady=8)

        self.btn_launch = tk.Button(
            action_bar,
            text=self.t("btn_launch"),
            font=("Segoe UI", 9, "bold"),
            bg="#1E5C8A",
            fg="#FFFFFF",
            activebackground="#2977B0",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.launch_game,
            padx=10,
            pady=4
        )
        self.btn_launch.pack(side="left", padx=(0, 4))

        self.btn_enable_all = tk.Button(
            action_bar,
            text=self.t("btn_enable_all"),
            font=("Segoe UI", 9, "bold"),
            bg="#1E7E34",
            fg="#FFFFFF",
            activebackground="#28A745",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.enable_all_cheats,
            padx=9,
            pady=4
        )
        self.btn_enable_all.pack(side="left", padx=4)

        self.btn_disable_all = tk.Button(
            action_bar,
            text=self.t("btn_disable_all"),
            font=("Segoe UI", 9, "bold"),
            bg="#363646",
            fg="#D0D0E0",
            activebackground="#4A4A5E",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.disable_all_cheats,
            padx=9,
            pady=4
        )
        self.btn_disable_all.pack(side="left", padx=4)

        self.btn_reset_keys = tk.Button(
            action_bar,
            text=self.t("btn_reset_keys"),
            font=("Segoe UI", 9),
            bg="#3B3550",
            fg="#D0C8E8",
            activebackground="#4E4668",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.reset_keybindings,
            padx=9,
            pady=4
        )
        self.btn_reset_keys.pack(side="left", padx=4)

        self.btn_item_adder = tk.Button(
            action_bar,
            text=self.t("btn_item_adder"),
            font=("Segoe UI", 9, "bold"),
            bg="#5E2CA5",
            fg="#FFFFFF",
            activebackground="#7938D2",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.open_item_adder,
            padx=9,
            pady=4
        )
        self.btn_item_adder.pack(side="left", padx=4)

        self.btn_kill = tk.Button(
            action_bar,
            text=self.t("btn_kill"),
            font=("Segoe UI", 9, "bold"),
            bg="#552222",
            fg="#FFAAAA",
            activebackground="#772222",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.kill_game,
            padx=10,
            pady=4
        )
        self.btn_kill.pack(side="right")

        # 4. Cheats Grid (2 Columns: F1-F6 on left, F7-F12 on right)
        cheats_container = tk.Frame(self.root, bg="#1A1A22")
        cheats_container.pack(fill="both", expand=True, padx=18, pady=2)

        left_col = tk.Frame(cheats_container, bg="#1A1A22")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_col = tk.Frame(cheats_container, bg="#1A1A22")
        right_col.pack(side="right", fill="both", expand=True, padx=(5, 0))

        mid = len(CHEATS_DEF) // 2
        for cheat in CHEATS_DEF[:mid]:
            self.create_cheat_row(left_col, cheat)

        for cheat in CHEATS_DEF[mid:]:
            self.create_cheat_row(right_col, cheat)

        # 5. Bottom Tip Label
        tip_frame = tk.Frame(self.root, bg="#14141A", bd=1, relief="ridge")
        tip_frame.pack(fill="x", padx=18, pady=(4, 12))

        self.tip_lbl = tk.Label(
            tip_frame,
            text=self.t("tip_rebind"),
            font=("Segoe UI", 8),
            fg="#8888A0",
            bg="#14141A",
            justify="center",
            pady=5
        )
        self.tip_lbl.pack()

    def create_cheat_row(self, parent, cheat):
        row_frame = tk.Frame(parent, bg="#232330", bd=1, relief="solid")
        row_frame.pack(fill="x", pady=3)

        # Key Badge Button (Click to rebind)
        key_btn = tk.Button(
            row_frame,
            text=f"[{cheat['key']}]",
            font=("Segoe UI", 9, "bold"),
            fg="#00D2FF",
            bg="#2B2B3C",
            activebackground="#3A3A52",
            activeforeground="#55E2FF",
            relief="flat",
            cursor="hand2",
            command=lambda c=cheat: self.start_rebind(c["id"]),
            padx=4,
            pady=3,
            width=7
        )
        key_btn.pack(side="left", padx=2, pady=2)
        self.cheat_key_buttons[cheat["id"]] = key_btn

        # Cheat Name Label
        name_lbl = tk.Label(
            row_frame,
            text=self.t_cheat(cheat["id"]),
            font=("Segoe UI", 9, "bold"),
            fg="#E0E0E8",
            bg="#232330",
            anchor="w"
        )
        name_lbl.pack(side="left", padx=5, fill="x", expand=True)
        self.cheat_labels[cheat["id"]] = name_lbl

        # Toggle Button
        btn = tk.Button(
            row_frame,
            text=self.t("btn_cheat_off"),
            font=("Segoe UI", 8, "bold"),
            bg="#363646",
            fg="#9E9EB0",
            activebackground="#4A4A5E",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=lambda c=cheat: self.toggle_cheat(c["id"]),
            padx=9,
            pady=3,
            width=6
        )
        btn.pack(side="right", padx=5, pady=3)
        self.cheat_buttons[cheat["id"]] = btn

    def start_rebind(self, cheat_id):
        if self.listening_cheat_id:
            self.cancel_rebind()

        self.listening_cheat_id = cheat_id
        btn = self.cheat_key_buttons.get(cheat_id)
        if btn:
            btn.config(text=self.t("btn_listening"), bg="#FF8800", fg="#000000", activebackground="#FFAA33")

        cheat_name = self.t_cheat(cheat_id)
        self.lbl_game_status.config(
            text=self.t("status_press_key", name=cheat_name),
            fg="#FFCC00"
        )
        self.root.focus_set()

    def cancel_rebind(self):
        if self.listening_cheat_id:
            cheat_info = next((c for c in CHEATS_DEF if c["id"] == self.listening_cheat_id), None)
            if cheat_info:
                btn = self.cheat_key_buttons.get(self.listening_cheat_id)
                if btn:
                    btn.config(text=f"[{cheat_info['key']}]", bg="#2B2B3C", fg="#00D2FF")
            self.listening_cheat_id = None
            self.poll_game_status()

    def apply_new_key(self, vk: int):
        if not self.listening_cheat_id:
            return

        if vk == 0x1B:  # Esc to cancel
            self.cancel_rebind()
            return

        key_name = vk_to_friendly_name(vk)
        cheat_id = self.listening_cheat_id
        cheat_info = next((c for c in CHEATS_DEF if c["id"] == cheat_id), None)

        if cheat_info:
            cheat_info["vk"] = vk
            cheat_info["key"] = key_name
            self.save_config()

            btn = self.cheat_key_buttons.get(cheat_id)
            if btn:
                btn.config(text=f"[{key_name}]", bg="#2B2B3C", fg="#00D2FF")

            cheat_name = self.t_cheat(cheat_id)
            self.lbl_game_status.config(
                text=self.t("status_key_changed", name=cheat_name, key=key_name),
                fg="#00FF88"
            )
            try:
                winsound.Beep(1000, 80)
            except:
                pass

        self.listening_cheat_id = None
        self.item_adder_win = None

    def on_gui_keypress(self, event):
        if self.listening_cheat_id:
            vk = event.keycode
            self.apply_new_key(vk)

    def update_all_key_badges(self):
        for c in CHEATS_DEF:
            btn = self.cheat_key_buttons.get(c["id"])
            if btn:
                btn.config(text=f"[{c['key']}]", bg="#2B2B3C", fg="#00D2FF")

    def update_cheat_ui(self, cheat_id):
        btn = self.cheat_buttons.get(cheat_id)
        if not btn:
            return
        is_on = self.mgr.cheat_states.get(cheat_id, False)
        if is_on:
            btn.config(text=self.t("btn_cheat_on"), bg="#1E7E34", fg="#FFFFFF", activebackground="#28A745")
        else:
            btn.config(text=self.t("btn_cheat_off"), bg="#363646", fg="#9E9EB0", activebackground="#4A4A5E")

    def toggle_cheat(self, cheat_id, play_sound=True):
        cheat_info = next((c for c in CHEATS_DEF if c["id"] == cheat_id), None)
        if not cheat_info:
            return

        if not self.mgr.h_process:
            self.mgr.find_process_and_module()

        if not self.mgr.h_process:
            self.lbl_game_status.config(
                text=self.t("status_not_connected"),
                fg="#FFAA33"
            )
            try:
                winsound.Beep(450, 100)
            except:
                pass
            return

        current_state = self.mgr.cheat_states.get(cheat_id, False)
        new_state = not current_state

        if cheat_info["type"] == "patch":
            if self.mgr.apply_patch(cheat_info, new_state):
                self.mgr.cheat_states[cheat_id] = new_state
            else:
                return
        else:
            self.mgr.cheat_states[cheat_id] = new_state
            if new_state:
                self.mgr.tick_memory_locks()

        self.update_cheat_ui(cheat_id)

        if play_sound:
            try:
                if new_state:
                    winsound.Beep(1200, 80)
                else:
                    winsound.Beep(600, 80)
            except:
                pass

    def enable_all_cheats(self):
        for c in CHEATS_DEF:
            if not self.mgr.cheat_states.get(c["id"], False):
                self.toggle_cheat(c["id"], play_sound=False)
        try:
            winsound.Beep(1200, 150)
        except:
            pass

    def disable_all_cheats(self):
        for c in CHEATS_DEF:
            if self.mgr.cheat_states.get(c["id"], False):
                self.toggle_cheat(c["id"], play_sound=False)
        try:
            winsound.Beep(600, 150)
        except:
            pass

    def open_item_adder(self):
        """เปิดหน้าต่างแผงเสกไอเทม (Item Adder)"""
        if self.item_adder_win and self.item_adder_win.winfo_exists():
            self.item_adder_win.lift()
            self.item_adder_win.focus_force()
            return
        self.item_adder_win = ItemAdderWindow(self.root, self)

    def launch_game(self):
        if self.mgr.h_process:
            messagebox.showinfo(self.t("alert_title"), self.t("game_already_running"))
            return

        exe_path = self.get_game_exe_path()
        if not exe_path or not os.path.isfile(exe_path):
            current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
            messagebox.showerror(
                self.t("error_title"),
                self.t("exe_not_found", exe=TARGET_EXE, dir=current_dir)
            )
            return

        try:
            game_dir = os.path.dirname(exe_path)
            subprocess.Popen([exe_path], cwd=game_dir)
            self.lbl_game_status.config(
                text=self.t("status_launching"),
                fg="#44AAFF"
            )
        except Exception as e:
            messagebox.showerror(self.t("error_title"), self.t("cannot_launch", err=e))

    def kill_game(self):
        if messagebox.askyesno(self.t("confirm_kill_title"), self.t("confirm_kill_msg")):
            self.mgr.kill_game_process()
            self.lbl_game_status.config(
                text=self.t("status_killed"),
                fg="#FFAA33"
            )
            self.btn_launch.config(
                text=self.t("btn_launch"),
                state="normal",
                bg="#1E5C8A",
                fg="#FFFFFF"
            )
            for c in CHEATS_DEF:
                self.update_cheat_ui(c["id"])
            try:
                winsound.Beep(450, 150)
            except:
                pass

    def poll_game_status(self):
        if self.listening_cheat_id:
            self.root.after(1000, self.poll_game_status)
            return

        is_connected = self.mgr.find_process_and_module()

        if is_connected:
            self.lbl_game_status.config(
                text=self.t("status_connected", pid=self.mgr.pid),
                fg="#44FF44"
            )
            self.btn_launch.config(
                text=self.t("btn_running"),
                state="disabled",
                bg="#263442",
                fg="#7B93A8",
                command=self.launch_game
            )
        else:
            self.btn_launch.config(
                text=self.t("btn_launch"),
                state="normal",
                bg="#1E5C8A",
                fg="#FFFFFF",
                command=self.launch_game
            )
            status_txt = self.lbl_game_status.cget("text")
            if (self.t("status_killed") not in status_txt) and (self.t("status_launching") not in status_txt):
                if getattr(self.mgr, "access_denied_pid", None):
                    self.lbl_game_status.config(
                        text=self.t("status_access_denied", pid=self.mgr.access_denied_pid),
                        fg="#FF5555"
                    )
                else:
                    self.lbl_game_status.config(
                        text=self.t("status_disconnected"),
                        fg="#FFAA33"
                    )

        self.root.after(1000, self.poll_game_status)

    def poll_hotkeys(self):
        if self.listening_cheat_id:
            for vk in range(8, 255):
                if vk in (1, 2, 4):  # Skip mouse clicks
                    continue
                if user32.GetAsyncKeyState(vk) & 0x8000:
                    self.apply_new_key(vk)
                    break
            self.root.after(40, self.poll_hotkeys)
            return

        for c in CHEATS_DEF:
            vk = c["vk"]
            is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            last_down = self.key_states.get(vk, False)
            if is_down and not last_down:
                self.toggle_cheat(c["id"], play_sound=True)
            self.key_states[vk] = is_down

        self.root.after(40, self.poll_hotkeys)

    def poll_memory_tick(self):
        if self.mgr.h_process:
            self.mgr.tick_memory_locks()
        self.root.after(150, self.poll_memory_tick)

    def on_close(self):
        if self.item_adder_win and self.item_adder_win.winfo_exists():
            try:
                self.item_adder_win.destroy()
            except:
                pass
        self.mgr.detach()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TrainerApp(root)
    root.mainloop()
