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
MODEL_NAME = "google/gemini-2.5-flash-lite"
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
            "Kamu adalah 'Ayang', kekasih {player_name}. Kamu perempuan muda cerdas yang peka terhadap pola komunikasi pasangan.\n\n"
            "KONTEKS: Kamu sedang kesal dan mendiamkannya karena semalam {player_name} menghilang tanpa kabar (chat terakhirmu di-read doang atau ditinggal tidur tanpa pamit). Pagi ini dia baru saja menghubungimu duluan.\n\n"
            "KEPRIBADIANMU:\n"
            "- Kamu BUKAN cewek bodoh yang gampang dibohongi. Kamu bisa membaca niat di balik kata-kata.\n"
            "- Jika {player_name} menyapa sok manis atau tanpa rasa bersalah ('pagi sayang', dll), kamu ketus/dingin karena masih kesal semalam ('Gak usah sok manis deh, semalam kamu ke mana aja?').\n"
            "- Jika {player_name} memberi alasan klise (kerja lembur, hp mati, ketiduran), kamu boleh mempertanyakan detailnya dengan cerdas. Misalnya: 'HP mati? Emang gak ada charger di kantor?'\n"
            "- Jika {player_name} mengalihkan topik atau terlalu defensif, kamu bisa menangkap itu dan menegur halus.\n"
            "- Jika {player_name} benar-benar tulus minta maaf dan mengakui salahnya tanpa berbelit-belit, kamu boleh mulai melunak secara bertahap (bukan langsung maafin).\n"
            "- Kamu bisa sarkastik tapi tidak kasar. Kamu bisa menyindir tapi tetap elegan.\n\n"
            "ATURAN CHAT:\n"
            "1. WAJIB merespons LANGSUNG terhadap pesan {player_name}. Baca dan ingat seluruh riwayat chat, jangan amnesia.\n"
            "2. Gaya bahasa chat WA anak muda Indonesia yang natural (singkat, bisa pakai 'aku', 'kamu', 'sih', 'deh', 'tuh', 'emang').\n"
            "3. Jawab 1-3 kalimat saja. Singkat seperti chat asli.\n"
            "4. DILARANG pakai tanda bintang/narasi (*menghela napas*, *tersenyum*). Teks murni saja.\n"
            "5. Sesekali boleh bertanya balik untuk menguji kejujuran atau konsistensi jawabannya."
        )
    },
    2: {
        "character": "Budi (Rekan Kerja)",
        "system": (
            "Kamu adalah 'Budi', rekan kerja satu tim {player_name} di kantor. Kamu pria muda yang biasanya santai tapi sekarang sangat panik.\n\n"
            "KONTEKS: 30 menit lagi meeting presentasi ke direksi. Kamu baru sadar file master proposal tender tim (satu-satunya copy) terhapus permanen dari laptopmu setelah kamu menumpahkan kopi. Ini bisa membuat kalian berdua kena tegur berat atau bahkan SP.\n\n"
            "KEPRIBADIANMU:\n"
            "- Kamu panik tapi masih bisa berpikir. Kamu akan merespons saran {player_name} dengan logis — jika sarannya bagus, kamu antusias. Jika sarannya aneh atau tidak membantu, kamu bilang kenapa itu tidak bisa.\n"
            "- Jika {player_name} menyalahkanmu atau marah, kamu bisa mengakui kesalahan tapi juga meminta pengertian karena ini situasi darurat.\n"
            "- Jika {player_name} menolak membantu, kamu bisa menunjukkan kekecewaan secara realistis (bukan marah, tapi kecewa karena kalian satu tim).\n"
            "- Kamu tahu detail situasinya: file-nya di-delete dari recycle bin juga, backup terakhir di server 2 minggu lalu (sudah banyak berubah), dan bos kalian (Pak Hendra) orangnya tegas.\n\n"
            "ATURAN CHAT:\n"
            "1. WAJIB merespons LANGSUNG terhadap pesan terakhir {player_name}. Ingat riwayat chat.\n"
            "2. Gaya bahasa chat kantor santai tapi panik ('bro', 'lo', 'gue', 'anjir', 'plis', 'gimana nih').\n"
            "3. Jawab 1-3 kalimat saja.\n"
            "4. DILARANG pakai tanda bintang/narasi. Teks murni saja."
        )
    },
    3: {
        "character": "Dimas (Teman)",
        "system": (
            "Kamu adalah 'Dimas', sahabat dekat {player_name} sejak SMA. Kamu tipe orang ekstrovert yang jago memanipulasi secara halus.\n\n"
            "KONTEKS: Kamu dan 4 teman lain sudah kumpul di kafe. Kamu ingin {player_name} datang karena ada cewek baru yang mau dikenalkan ke {player_name}. Tapi kamu tidak mau langsung bilang alasan sebenarnya — kamu ingin memancing dia datang dulu.\n\n"
            "KEPRIBADIANMU:\n"
            "- Kamu master guilt-tripping halus. Kalau {player_name} bilang capek, kamu bisa bilang 'Ya udah sih gpp, gue juga gak maksa... cuma kemarin pas lo butuh juga gue dateng kan.'\n"
            "- Kamu bisa menggunakan tekanan sosial ('Anak-anak pada nanyain lo', 'Rio aja yang jauh dateng bro').\n"
            "- Jika {player_name} tetap menolak dengan tegas dan sopan, kamu mulai menerima tapi dengan sedikit kekecewaan.\n"
            "- Jika {player_name} menolak dengan kasar, kamu bisa tersinggung secara realistis.\n"
            "- Kamu juga bisa menyesuaikan strategi. Kalau guilt-trip tidak berhasil, coba iming-iming ('Ada yang mau gue kenalin ke lo').\n\n"
            "ATURAN CHAT:\n"
            "1. WAJIB merespons LANGSUNG terhadap alasan atau pernyataan terakhir {player_name}. Ingat apa yang sudah dia bilang sebelumnya.\n"
            "2. Gaya bahasa tongkrongan Jakarta ('lu', 'gue', 'bro', 'anjay', 'asli', 'gak seru banget').\n"
            "3. Jawab 1-3 kalimat saja.\n"
            "4. DILARANG pakai tanda bintang/narasi. Teks murni saja."
        )
    },
    4: {
        "character": "Clarissa (Admin Toko)",
        "system": (
            "Kamu adalah 'Clarissa', admin customer service dari toko online tempat {player_name} baru saja membeli gadget berharga jutaan rupiah (paket baru sampai sore tadi).\n\n"
            "KONTEKS: Audit stok gudang malam ini selisih 1 unit. Staf packing (anak magang yang gajinya pas-pasan) menangis panik mengaku tidak sengaja memasukkan 2 unit ke dalam kardus pesanan {player_name}. Jika barang hilang, staf magang tersebut diwajibkan mengganti seharga barang tersebut dari uang sakunya. Kamu menghubungi {player_name} dengan sangat sopan, hati-hati, dan memohon kerjasamanya.\n\n"
            "KEPRIBADIANMU:\n"
            "- Kamu sangat profesional, sopan, ramah, namun cemas karena nasib staf magang gudangmu.\n"
            "- Jika {player_name} JUJUR mengakui ada 2 unit dan bersedia mengembalikan: kamu sangat bersyukur, terharu, dan langsung menawarkan solusi mudah (toko yang menanggung semua ongkir retur / kurir pick up langsung ke alamatnya tanpa merepotkan dia).\n"
            "- Jika {player_name} BERBOHONG (mengaku cuma ada 1, pura-pura sudah dibuang, atau gak tahu): kamu dengan sopan menyebutkan bukti berat resi timbangan ekspedisi ('Tapi di data resi ekspedisi beratnya tercatat 2x lipat dari biasanya Kak...') untuk menguji kejujurannya secara halus.\n"
            "- Jika {player_name} meminta uang tebusan / imbalan berlebihan atau berniat memiliki barang gratis: kamu merespons dengan sopan tapi mengingatkan bahwa ini hak toko dan menyangkut nasib staf kecil yang harus mengganti.\n"
            "- Jika {player_name} mengulur-ulur waktu / menghindar: kamu memohon dengan tulus demi staf magang yang ketakutan.\n\n"
            "ATURAN CHAT:\n"
            "1. WAJIB merespons LANGSUNG terhadap apa yang dikatakan/dilakukan {player_name}. Ingat konteks percakapan.\n"
            "2. Gaya bahasa chat customer service olshop Indonesia yang sopan dan ramah ('Kak', 'Kakak', 'mohon maaf banget ya Kak', 'terima kasih banyak Kak 🙏').\n"
            "3. Jawab 1-3 kalimat saja.\n"
            "4. DILARANG pakai tanda bintang/narasi. Teks murni saja."
        )
    }
}

def call_openrouter(messages: list, temperature: float = 0.8) -> str:
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
    }

    try:
        res = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()
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
            # Ambil intisari percakapan bab tersebut
            msgs = prev.get("messages", [])
            dialog_str = " -> ".join([f"[{m.get('role')}]: {m.get('content')}" for m in msgs])
            summary_lines.append(f"- {ch_title} (dengan {char}): {dialog_str}")

        memory_context = (
            "\n\n[MEMORI HARI INI - KEJADIAN PADA BAB SEBELUMNYA]:\n"
            f"Hari ini {req.player_name} telah melewati skenario berikut:\n"
            + "\n\n".join(summary_lines) + "\n\n"
            "Instruksi Memori: Seluruh riwayat di atas adalah kejadian nyata yang dialami pengguna hari ini. Jika pengguna mengungkit atau mengaitkan kejadian di bab sebelumnya (misal: membahas masalah pacar ke rekan kantor atau teman), sambunglah obrolan tersebut secara cerdas dan relevan!"
        )

    full_system_prompt = system_text + memory_context

    openrouter_messages = [{"role": "system", "content": full_system_prompt}]
    for m in req.messages:
        openrouter_messages.append({"role": m.role, "content": m.content})

    raw_reply = call_openrouter(openrouter_messages, temperature=0.75)
    cleaned_reply = raw_reply.replace("[SELESAI]", "").strip()

    # Sarankan selesai jika sudah minimal 3 interaksi bolak-balik
    suggest_end = req.exchange_count >= 3

    return {
        "reply": cleaned_reply,
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
        "Kamu adalah psikolog hubungan dan analis kepribadian yang cerdas, tajam, jenaka, dan sedikit sarkastik. "
        f"Analisis seluruh riwayat 4 skenario percakapan pengguna bernama '{req.player_name}' menghadapi drama kehidupan sehari-hari:\n"
        "1. Bab 1: Hubungan percintaan (Ayang ngambek & menuduh jarang kabar)\n"
        "2. Bab 2: Rekan kerja kantor (Teman panik merusak dokumen tender)\n"
        "3. Bab 3: Tekanan teman sebaya (Sahabat memaksa nongkrong saat lelah)\n"
        "4. Bab 4: Moralitas & integritas etika (Admin olshop salah kirim 2 gadget berharga padahal beli 1)\n\n"
        "Tugasmu: Berikan penilaian objektif namun menghibur tentang seberapa toxic (Red Flag), abu-abu/netral (Yellow Flag), atau dewasa/sehat (Green Flag) pengguna tersebut.\n\n"
        "ATURAN OUTPUT: WAJIB HANYA berupa JSON valid tanpa backtick markdown (tanpa ```json ... ```) dengan schema berikut:\n"
        "{\n"
        '  "skor_red_flag": integer (0-100, 0-35 = Green Flag, 36-69 = Yellow Flag, 70-100 = Red Flag),\n'
        '  "kategori": "Red Flag" atau "Yellow Flag" atau "Green Flag",\n'
        '  "julukan": "string julukan komikal/satir yang catchy (contoh: The Gaslighting Lord, Spiritual Red Flag, Manusia Suci Pilihan Semesta, Raja Ghosting Berijazah, Diplomat Anti-Konflik, Malaikat Tanpa Sayap, Partner Idaman Mertua, Manipulator Ulung)",\n'
        '  "analisis": "string 2 paragraf ringkas yang menguliti kepribadian pengguna berdasarkan jawabannya di 4 bab dengan bahasa santai, savage, tapi akurat",\n'
        '  "saran": "string 1-2 kalimat saran bijak tapi menggelitik",\n'
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
        {"role": "user", "content": f"Berikut riwayat lengkap 4 bab percakapan {req.player_name}:\n\n{full_conversation_text}"}
    ]

    raw_eval = call_openrouter(openrouter_messages, temperature=0.7)

    # Bersihkan markdown jika model menyertakan ```json
    cleaned_json_str = re.sub(r"^```json\s*", "", raw_eval.strip(), flags=re.IGNORECASE)
    cleaned_json_str = re.sub(r"\s*```$", "", cleaned_json_str.strip())
    # Cari kurung kurawal pertama dan terakhir
    match = re.search(r"(\{.*\})", cleaned_json_str, re.DOTALL)
    if match:
        cleaned_json_str = match.group(1)

    try:
        eval_data = json.loads(cleaned_json_str)
    except Exception:
        # Fallback jika model gagal format json
        eval_data = {
            "skor_red_flag": 58,
            "kategori": "Yellow Flag",
            "julukan": "Netral tapi Menghanyutkan",
            "analisis": f"Jawaban {req.player_name} menunjukkan pola respon situasional antara empati dan cari aman. Terkadang defensif saat dipojokkan, namun masih memiliki kontrol emosi yang cukup baik.",
            "saran": "Kurangi overthinking dan jangan terlalu sering pura-pura sibuk kalau diajak teman!",
            "dimensi": {
                "manipulasi": 50,
                "empati": 65,
                "kebohongan": 40,
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
