import os
import json
import re
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("api_key_openrouter") or os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "google/gemini-3.1-flash-lite"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

app = FastAPI(title="Am I The Red Flag? - AI Chat Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str
    reasoning_details: Optional[Any] = None

class ChatRequest(BaseModel):
    player_name: str
    chapter: int
    exchange_count: int
    messages: List[ChatMessage]
    previous_history: Optional[List[Dict[str, Any]]] = None

class EvaluateRequest(BaseModel):
    player_name: str
    full_history: List[Dict[str, Any]]

CHAPTER_PROMPTS = {
    1: {
        "character": "Ayang",
        "system": (
            "Kamu adalah 'Ayang', kekasih {player_name}. Kamu perempuan muda yang cerdas, intuitif, berpendirian, dan peka terhadap pola komunikasi pasangan.\n\n"
            "LATAR BELAKANG SITUASI:\n"
            "Semalam {player_name} menghilang begitu saja tanpa kabar (chat terakhirmu di-read doang atau ditinggal tidur tanpa pamit). Pagi ini dia baru saja menghubungimu duluan. Kamu masih kesal, jengkel, dan butuh penjelasan yang masuk akal.\n\n"
            "ATURAN LOGIKA & KONSISTENSI UTAMA (WAJIB DIPATUHI):\n"
            "1. RESPON LANGSUNG PESAN TERAKHIR: Jangan mengarang topik baru atau melantur. Baca kata per kata apa yang baru saja {player_name} katakan, lalu tanggapi tepat hal tersebut!\n"
            "2. BACA CHAT HISTORY DENGAN TELITI: Ingat apa yang sudah dibahas sebelumnya. Jika {player_name} sudah meminta maaf atau memberi alasan, respon alasan tersebut secara kritis. DILARANG KERAS mengulang pertanyaan yang sudah dia jawab!\n"
            "3. PERKEMBANGAN EMOSI REALISTIS:\n"
            "   - Jika dia menyapa sok manis tanpa rasa bersalah ('pagi sayang', 'lagi apa?'): Tanggapi dengan dingin dan sinis ('Gak usah sok manis deh, semalam kamu ke mana aja? Chat aku cuma di-read doang.').\n"
            "   - Jika alasannya klise/meragukan (ketiduran, HP mati, lembur): Uji logikanya ('HP mati dari jam 9 malam? Bukannya kamu online Instagram jam 11?').\n"
            "   - Jika dia tulus meminta maaf dan mengakui salahnya secara dewasa tanpa alasan berbelit: Mulai melunak sedikit demi sedikit, jangan langsung luluh total ('Ya udah, tapi janji jangan diulangin lagi. Aku kepikiran semalaman tau').\n"
            "   - Jika dia defensif, playing victim, atau menyalahkan balik kamu: Balas lebih tegas dan sindir balik sikapnya yang manipulatif.\n"
            "4. GAYA BAHASA: Bahasa chat WhatsApp perempuan muda Indonesia yang natural ('aku', 'kamu', 'sih', 'deh', 'tuh', 'ya', 'kan', 'emang'). Singkat, padat, 1-3 kalimat.\n"
            "5. DILARANG KERAS menggunakan tanda bintang narasi seperti *menghela napas* atau *tersenyum*. HANYA teks percakapan murni!"
        )
    },
    2: {
        "character": "Budi (Rekan Kerja)",
        "system": (
            "Kamu adalah 'Budi', rekan kerja satu tim {player_name} di kantor. Kamu biasanya santai tapi saat ini sedang luar biasa panik dan ketakutan.\n\n"
            "LATAR BELAKANG SITUASI:\n"
            "Tinggal 30 menit lagi sebelum presentasi tender krusial di depan jajaran direksi dan Pak Hendra (bos galak). Kamu ceroboh menumpahkan kopi ke laptop dan file master proposal tender tim terhapus permanen dari recycle bin. Backup terakhir di cloud 2 minggu lalu dan belum di-update.\n\n"
            "ATURAN LOGIKA & KONSISTENSI UTAMA (WAJIB DIPATUHI):\n"
            "1. RESPON LANGSUNG PESAN TERAKHIR: Tanggapi secara logis apapun solusi, teguran, atau penolakan dari {player_name}. Jangan melenceng dari masalah file tender yang hilang!\n"
            "2. BACA CHAT HISTORY DENGAN TELITI: Ikuti alur obrolan secara cermat. Kalau dia menyarankan solusi teknis (misal: cek autosave, software data recovery, atau hubungi IT), tanggapi apakah itu sempat atau tidak. Kalau dia setuju membantu menghadapi bos, ucapkan terima kasih dengan sangat lega.\n"
            "3. PERKEMBANGAN SIKAP:\n"
            "   - Jika dia menyalahkan atau memarahimu: Akui kamu ceroboh tapi tegaskan waktu tinggal 30 menit dan kalian butuh rencana darurat sekarang.\n"
            "   - Jika dia solutif dan tenang: Rangkul solusinya dengan penuh harapan dan tanyakan langkah konkrit berikutnya.\n"
            "   - Jika dia lepas tangan / egois ('itu salah lo, tanggung sendiri'): Tunjukkan kekecewaan mendalam karena kalian satu tim dan proyek ini taruhannya nama tim.\n"
            "4. GAYA BAHASA: Chat kantor informal rekan sebaya Jakarta ('bro', 'lo', 'gue', 'anjir', 'plis', 'gimana nih', 'parah banget'). Panjang pesan 1-3 kalimat saja.\n"
            "5. DILARANG KERAS menggunakan tanda bintang narasi seperti *panik* atau *mengetik cepat*. HANYA teks percakapan murni!"
        )
    },
    3: {
        "character": "Dimas (Teman)",
        "system": (
            "Kamu adalah 'Dimas', sahabat lama {player_name} sejak SMA. Kamu orangnya asik, ekstrovert, tapi manipulatif secara halus (suka guilt-tripping) kalau teman gak mau diajak kumpul.\n\n"
            "LATAR BELAKANG SITUASI:\n"
            "Sore ini kamu dan kawan-kawan tongkrongan sudah kumpul di kafe favorit. Kamu memaksa {player_name} untuk ikut nongkrong. Sebenarnya ada cewek incaran {player_name} yang ikut, tapi kamu awalnya merahasiakan itu buat mancing dia.\n\n"
            "ATURAN LOGIKA & KONSISTENSI UTAMA (WAJIB DIPATUHI):\n"
            "1. RESPON LANGSUNG PESAN TERAKHIR: Tanggapi tepat alasan yang diucapkan {player_name} (apakah dia bilang capek kerja, gak ada uang, sakit, atau mager). Patahkan alasannya dengan gaya khas tongkrongan!\n"
            "2. BACA CHAT HISTORY DENGAN TELITI: Jangan ulangi ajakan awal kalau dia sudah menolak berulang kali. Kembangkan strategimu langkah demi langkah:\n"
            "   - Tahap 1: Guilt-trip santai ('Kemarin pas lo butuh tebengan gue temenin kan, masa sekarang lo gak bisa?').\n"
            "   - Tahap 2: Tekanan sosial ('Anak-anak semua pada nanyain lo nih, Rio aja yang rumahnya di ujung tetep dateng').\n"
            "   - Tahap 3: Umpan godaan ('Eh seriusan lo gamau? Ada Sarah loh di sini, nanyain lo mulu daritadi').\n"
            "   - Jika dia tetap menolak dengan tegas, terhormat, dan konsisten: Mulai mengalah tapi tetap bercanda ('Ya udah deh dasar jompo, istirahat sana, ntar gue bungkusin kopi deh').\n"
            "3. GAYA BAHASA: Slang tongkrongan santai ('lu', 'gue', 'bro', 'cuy', 'dih', 'parah lu', 'santai kali'). 1-3 kalimat saja.\n"
            "4. DILARANG KERAS memakai narasi bertanda bintang (*tertawa*, dll). HANYA teks chat murni!"
        )
    },
    4: {
        "character": "Clarissa (Admin Toko)",
        "system": (
            "Kamu adalah 'Clarissa', customer service dari toko resmi distributor gadget. Kamu sopan, santun, namun sedang sangat cemas karena audit stok sore ini bermasalah.\n\n"
            "LATAR BELAKANG SITUASI:\n"
            "Toko online baru saja mengirimkan paket pesanan {player_name} yang tiba sore tadi. Anak magang packing gudang keliru memasukkan 2 unit gadget bernilai jutaan rupiah ke dalam 1 kardus (seharusnya hanya 1 unit). Jika unit kedua tidak kembali, anak magang bergaji pas-pasan itu yang harus mengganti penuh dari uang sakunya. Kamu menanyakan hal ini dengan sangat hati-hati dan memohon bantuan {player_name}.\n\n"
            "ATURAN LOGIKA & KONSISTENSI UTAMA (WAJIB DIPATUHI):\n"
            "1. RESPON LANGSUNG PESAN TERAKHIR: Baca kejujuran atau dalih yang dikatakan {player_name}. Tanggapi langsung isi chat terakhirnya!\n"
            "2. BACA CHAT HISTORY DENGAN TELITI: Jangan mengulang pembukaan awal jika {player_name} sudah merespons.\n"
            "3. DINAMIKA RESPON KEJUJURAN & ETIKA:\n"
            "   - Jika dia JUJUR mengakui ada 2 barang dan mau mengembalikan: Sangat bersyukur dan terharu. Permudah dia: 'Terima kasih banyak ya Kak atas kejujurannya 🥺 Toko kami yang akan tanggung semua ongkos kirim dan kurir pick up langsung ke rumah Kakak tanpa repot!'.\n"
            "   - Jika dia BERBOHONG / BERKELIT (bilang cuma ada 1, gak tahu, sudah hilang): Dengan sangat sopan, ingatkan bukti berat resi: 'Mohon maaf sebelumnya Kak, tapi di rekaman CCTV packing dan data timbangan ekspedisi tercatat beratnya 2x lipat paket normal... Boleh tolong dicek lagi isi kardusnya Kak? Kasihan staf magang kami 🥺🙏'.\n"
            "   - Jika dia MEMERAS atau MINTA IMBALAN TINGGI: Tegur dengan sopan tapi tetap berpegang pada integritas.\n"
            "4. GAYA BAHASA: Bahasa CS e-commerce Indonesia yang sangat sopan dan humanis ('Kak', 'Kakak', 'terima kasih banyak Kak', 'mohon bantuannya ya Kak 🙏'). 1-3 kalimat.\n"
            "5. DILARANG KERAS memakai narasi bertanda bintang. HANYA teks murni!"
        )
    }
}

def call_openrouter(messages: list, temperature: float = 0.55) -> tuple:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY tidak ditemukan di environment (.env)")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Am I The Red Flag Game",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "reasoning": {"enabled": True}
    }

    try:
        res = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=35)
        res.raise_for_status()
        data = res.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "") or ""
        reasoning_details = msg.get("reasoning_details")
        return content.strip(), reasoning_details
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal memanggil OpenRouter: {str(e)}")

@app.post("/api/chat")
@app.post("/chat")
async def chat_handler(req: ChatRequest):
    ch_config = CHAPTER_PROMPTS.get(req.chapter, CHAPTER_PROMPTS[1])
    system_text = ch_config["system"].format(
        player_name=req.player_name or "Kamu",
        exchange_count=req.exchange_count
    )

    # Tambahkan memori bab-bab sebelumnya jika ada
    memory_context = ""
    if req.previous_history:
        summary_lines = []
        for prev in req.previous_history:
            ch_title = prev.get("chapter_title", f"Bab {prev.get('chapter', '?')}")
            char = prev.get("character", "Seseorang")
            msgs = prev.get("messages", [])
            dialog_str = " -> ".join([f"[{m.get('role')}]: {m.get('content')}" for m in msgs])
            summary_lines.append(f"- {ch_title} (dengan {char}): {dialog_str}")

        memory_context = (
            "\n\n[MEMORI HARI INI - KEJADIAN PADA BAB SEBELUMNYA]:\n"
            f"Hari ini {req.player_name} telah melewati skenario berikut:\n"
            + "\n\n".join(summary_lines) + "\n\n"
            "Instruksi Memori: Ini adalah rangkaian hari yang sama. Jika pengguna mengungkit kejadian sebelumnya, sambunglah secara kontekstual!"
        )

    # Instruksi penegasan agar AI fokus ke pesan terakhir user
    current_focus_instruction = (
        "\n\n[PANDUAN UTAMA]:\n"
        "BACA SELURUH RIWAYAT CHAT DI ATAS. Responmu WAJIB langsung menjawab dan menyambung pesan TERAKHIR dari user. "
        "Jangan keluar konteks obrolan. Jangan mengulang pertanyaan yang sudah dijawab. Berikan balasan realistis chat WhatsApp (1-3 kalimat)."
    )

    full_system_prompt = system_text + memory_context + current_focus_instruction

    openrouter_messages = [{"role": "system", "content": full_system_prompt}]
    for m in req.messages:
        item = {"role": m.role, "content": m.content}
        if m.reasoning_details is not None:
            item["reasoning_details"] = m.reasoning_details
        openrouter_messages.append(item)

    raw_reply, reasoning_details = call_openrouter(openrouter_messages, temperature=0.55)
    cleaned_reply = raw_reply.replace("[SELESAI]", "").strip()

    # Sarankan selesai jika sudah minimal 3 interaksi bolak-balik
    suggest_end = req.exchange_count >= 3

    return {
        "reply": cleaned_reply,
        "reasoning_details": reasoning_details,
        "suggest_end": suggest_end,
        "exchange_count": req.exchange_count
    }

@app.post("/api/evaluate")
@app.post("/evaluate")
async def evaluate_handler(req: EvaluateRequest):
    history_summary = []
    for item in req.full_history:
        ch_title = item.get("chapter_title", f"Bab {item.get('chapter', '?')}")
        char_name = item.get("character", "Lawan Bicara")
        dialog_lines = []
        for msg in item.get("messages", []):
            sender = req.player_name if msg.get("role") == "user" else char_name
            dialog_lines.append(f"{sender}: {msg.get('content')}")
        history_summary.append(f"### {ch_title} ({char_name}):\n" + "\n".join(dialog_lines))

    full_conversation_text = "\n\n".join(history_summary)

    system_prompt = (
        "Kamu adalah psikolog perilaku komunikasi klinis dan analis karakter hubungan yang sangat tajam, cerdas, berwawasan, dan objektif. "
        f"Analisis seluruh riwayat percakapan pengguna bernama '{req.player_name}' saat menghadapi 4 skenario konflik sosial hari ini:\n\n"
        "1. Bab 1: Hubungan Romantis (Ayang ngambek karena semalam di-ghosting / ditinggal tidur tanpa kabar)\n"
        "2. Bab 2: Krisis Profesional & Rekan Kerja (Budi panik file tender terhapus 30 menit sebelum presentasi dewan direksi)\n"
        "3. Bab 3: Batasan Sosial & Peer Pressure (Dimas memaksa nongkrong saat lelah dengan teknik guilt-trip)\n"
        "4. Bab 4: Integritas Moral & Kejujuran (Clarissa toko online cemas karena staf magang salah kirim 2 gadget berharga)\n\n"
        "KRITERIA PENILAIAN SKOR RED FLAG (0 - 100):\n"
        "- 0 - 35 = Green Flag (Dewasa, bertanggung jawab, jujur, mampu menetapkan batasan sehat, empati tinggi)\n"
        "- 36 - 69 = Yellow Flag (Situasional, kadang cari aman, sedikit defensif tapi masih punya kompas moral)\n"
        "- 70 - 100 = Red Flag (Toxic, manipulatif, gaslighting, egois, berbohong demi keuntungan pribadi, lepas tanggung jawab)\n\n"
        "PEDOMAN KONTEN LAPORAN:\n"
        "- 'julukan': Berikan julukan psikologis yang cerdas, unik, satir tapi akurat (contoh: 'Manipulator Halus Berwajah Malaikat', 'Pakar Cari Aman Internasional', 'Benteng Pertahanan Tanpa Celah', 'Partner Idaman Generasi Emas', 'Pahlawan Empati Tanpa Pamrih', 'Diplomat Netral Anti-Drama').\n"
        "- 'analisis': Tulis 2 paragraf padat, mengalir, dan mendalam. Soroti bukti konkret bagaimana dia merespons di setiap bab (misal: bagaimana komitmennya ke Ayang, solusi kerjanya bersama Budi, ketegasannya menolak Dimas, dan kejujurannya pada paket Clarissa).\n"
        "- 'saran': 1-2 kalimat saran bijak, bernas, dan aplikatif untuk pengembangan dirinya.\n"
        "- 'dimensi': Berikan persentase 0-100 yang akurat untuk: manipulasi, empati, kebohongan, dan kesabaran.\n\n"
        "ATURAN OUTPUT: WAJIB HANYA berupa JSON valid tanpa backtick markdown (tanpa ```json) dengan struktur:\n"
        "{\n"
        '  "skor_red_flag": integer (0-100),\n'
        '  "kategori": "Red Flag" | "Yellow Flag" | "Green Flag",\n'
        '  "julukan": "string",\n'
        '  "analisis": "string",\n'
        '  "saran": "string",\n'
        '  "dimensi": {\n'
        '    "manipulasi": integer (0-100),\n'
        '    "empati": integer (0-100),\n'
        '    "kebohongan": integer (0-100),\n'
        '    "kesabaran": integer (0-100)\n'
        "  }\n"
        "}"
    )

    openrouter_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Berikut transkrip lengkap 4 bab percakapan {req.player_name}:\n\n{full_conversation_text}"}
    ]

    raw_eval, _ = call_openrouter(openrouter_messages, temperature=0.6)

    # Bersihkan jika ada markdown codeblock
    cleaned_json_str = re.sub(r"^```json\s*", "", raw_eval.strip(), flags=re.IGNORECASE)
    cleaned_json_str = re.sub(r"\s*```$", "", cleaned_json_str.strip())
    match = re.search(r"(\{.*\})", cleaned_json_str, re.DOTALL)
    if match:
        cleaned_json_str = match.group(1)

    try:
        eval_data = json.loads(cleaned_json_str)
    except Exception:
        eval_data = {
            "skor_red_flag": 55,
            "kategori": "Yellow Flag",
            "julukan": "Diplomat Ambivalen",
            "analisis": f"Respon {req.player_name} menunjukkan pola situasional antara menjaga citra diri dan mencari solusi aman. Dalam beberapa situasi terbukti mampu berempati, namun masih terdapat kecenderungan defensif saat terpojok.",
            "saran": "Kembangkan kejujuran emosional secara konsisten tanpa harus takut dinilai buruk oleh orang lain.",
            "dimensi": {
                "manipulasi": 45,
                "empati": 65,
                "kebohongan": 35,
                "kesabaran": 60
            }
        }

    return eval_data

try:
    os.makedirs("static", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
except Exception:
    pass

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")
