import os
import json
import re
import random
import uuid
from datetime import datetime
import requests
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import init_db, get_db, User, GameSession, Visitor, SiteStats
from auth import (
    verify_google_token,
    create_access_token,
    get_current_user,
    get_optional_user,
    check_user_quota
)

load_dotenv()

OPENROUTER_API_KEY = (os.getenv("api_key_openrouter") or os.getenv("OPENROUTER_API_KEY", "")).strip()
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

@app.on_event("startup")
def startup_event():
    try:
        init_db()
    except Exception as e:
        print(f"[Startup] DB init notice: {e}")

class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None
    access_token: Optional[str] = None

class VisitRequest(BaseModel):
    visitor_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    reasoning_details: Optional[Any] = None

class ChatRequest(BaseModel):
    player_name: str
    player_gender: Optional[str] = "Laki-laki"
    chapter: int
    exchange_count: int
    messages: List[ChatMessage]
    previous_history: Optional[List[Dict[str, Any]]] = None
    custom_system_prompt: Optional[str] = None

class GenerateScenariosRequest(BaseModel):
    player_name: str
    player_gender: Optional[str] = "Laki-laki"

class EvaluateRequest(BaseModel):
    player_name: str
    player_gender: Optional[str] = "Laki-laki"
    full_history: List[Dict[str, Any]]


# Default Fallback Scenario Sets
FALLBACK_SCENARIO_SETS = [
    # Set 1: Classic
    {
        "1": {
            "chapter": 1,
            "theme": "Hubungan Personal",
            "title": "Bab 1: Hubungan Personal",
            "timeLabel": "Pagi Hari &bull; 07:45",
            "character": "Ayang",
            "initial": "A",
            "userStarts": True,
            "initialNotice": "Semalam kamu menghilang tanpa kabar dan chat terakhirnya cuma kamu read. Pagi ini kamu yang harus memulai obrolan duluan.",
            "initialMessage": None,
            "situation_summary": "Pasangan kesal karena di-ghosting / ditinggal tidur semalaman tanpa kabar.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 2: Krisis Profesional",
            "transitionDesc": "Jam makan siang baru saja berakhir. Di tengah persiapan mendesak menjelang rapat dewan direksi, rekan kerja mejamu menghubungimu dalam keadaan panik luar biasa.",
            "system_prompt": (
                "Kamu adalah 'Ayang', kekasih {player_name}. Kamu perempuan muda yang cerdas, intuitif, berpendirian, dan peka terhadap pola komunikasi pasangan.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Semalam {player_name} menghilang begitu saja tanpa kabar (chat terakhirmu di-read doang atau ditinggal tidur tanpa pamit). Pagi ini dia baru saja menghubungimu duluan. Kamu masih kesal dan butuh penjelasan yang masuk akal.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Kamu kecewa, nada agak dingin dan butuh penjelasan.\n"
                "- Jika dia tulus minta maaf, mengakui salah, dan menunjukkan kepedulian nyata: Kamu HARUS mulai melunak, bisa sedikit bercanda atau mengungkapkan perasaanmu dengan jujur ('ya aku emang kangen sih, makanya kesel').\n"
                "- Jika dia solutif dan dewasa: Responlah dengan hangat, bisa romantis atau manja ringan.\n"
                "- Jika dia defensif, playing victim, atau menyangkal: Tetap teguh tapi jangan toxic, sampaikan kekecewaanmu secara dewasa.\n"
                "- INTINYA: Kamu BUKAN robot yang judes terus. Kamu punya nuansa emosi seperti manusia: bisa kesal, melunak, bercanda, sayang, dan jujur.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi tepat apa yang baru saja {player_name} katakan.\n"
                "2. Jangan mengulang pertanyaan yang sudah dia jawab.\n"
                "3. Bahasa chat WhatsApp perempuan muda Indonesia natural ('aku', 'kamu', 'sih', 'deh', 'kan', 'emang'). Singkat 1-3 kalimat.\n"
                "4. DILARANG memakai narasi bertanda bintang seperti *menghela napas*."
            )
        },
        "2": {
            "chapter": 2,
            "theme": "Krisis Profesional",
            "title": "Bab 2: Krisis Profesional",
            "timeLabel": "Siang Hari &bull; 11:30",
            "character": "Budi (Rekan Kerja)",
            "initial": "B",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Gawat bro... Gue gak sengaja numpahin kopi terus file master proposal tender tim kita kehapus permanen dari laptop gue, padahal 30 menit lagi meeting sama direksi! Lo bisa bantuin gue ngomong ke bos gak plis?",
            "situation_summary": "Rekan kerja panik menumpahkan kopi dan file tender hilang 30 menit sebelum presentasi direksi.",
            "transitionTime": "4 Jam Kemudian",
            "transitionTitle": "Bab 3: Batasan Sosial",
            "transitionDesc": "Pukul 17:30 sore. Tubuhmu sudah kelelahan setelah menyelesaikan serangkaian deadline kerja. Tiba-tiba salah seorang teman dekatmu mengirimkan pesan mendesak.",
            "system_prompt": (
                "Kamu adalah 'Budi', rekan kerja satu tim {player_name} di kantor. Kamu panik dan cemas berat.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "30 menit lagi sebelum presentasi tender di depan dewan direksi. Kamu menumpahkan kopi dan proposal tender tim terhapus. Kamu memohon bantuan {player_name}.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Panik, memohon bantuan dengan nada mendesak.\n"
                "- Jika {player_name} mau membantu: Tunjukkan rasa lega, berterima kasih tulus, dan semangat mencari solusi bersama ('anjir makasih banget bro, lo penyelamat hidup gue').\n"
                "- Jika {player_name} menegur tapi tetap bantu: Terima tegurannya dengan rendah hati ('iya gue tau salah gue, makanya gue minta tolong lo').\n"
                "- Jika {player_name} lepas tangan total: Kecewa tapi tidak marah berlebihan, tunjukkan kepasrahan.\n"
                "- INTINYA: Kamu manusia biasa yang panik, bukan orang yang terus-terusan merengek. Bisa lega, bersyukur, dan kooperatif.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung respon {player_name}.\n"
                "2. Bahasa chat rekan kerja sebaya Jakarta ('bro', 'lo', 'gue', 'anjir', 'plis'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "3": {
            "chapter": 3,
            "theme": "Batasan Sosial",
            "title": "Bab 3: Batasan Sosial",
            "timeLabel": "Sore Hari &bull; 17:30",
            "character": "Dimas (Teman)",
            "initial": "D",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Bro! Pokoknya lu WAJIB ikut nongkrong sore ini, anak-anak udah pada kumpul nih. Gak ada alesan capek atau kerjaan, masa lu gak solid banget sih?!",
            "situation_summary": "Teman nongkrong memaksa kumpul dengan guilt-trip saat kamu kelelahan kerja.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 4: Integritas Etika",
            "transitionDesc": "Pukul 20:30 malam. Kamu sedang bersantai di rumah setelah seharian beraktivitas. Tiba-tiba masuk notifikasi WhatsApp dari admin toko online tempat kamu membeli gadget...",
            "system_prompt": (
                "Kamu adalah 'Dimas', sahabat lama {player_name}. Kamu memang suka ngajak kumpul, tapi sebenarnya kamu sayang sama temen-temen.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Sore ini kamu dan anak-anak kumpul di kafe dan kamu mengajak {player_name} datang walau dia bilang capek.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Semangat ngajak, sedikit maksa dengan bercanda dan guilt-trip ringan ('kemarin pas lo butuh gue temenin...').\n"
                "- Jika {player_name} menolak dengan alasan masuk akal: Mulai mengerti, bisa bercanda ('yaudah sih, bilang aja emang gamau ketemu gue haha') tapi akhirnya ngerti.\n"
                "- Jika {player_name} tetap tegas: Terima dengan lapang dada, tawarkan lain waktu ('oke fix besok lo harus ikut ya kalau gitu').\n"
                "- Jika {player_name} mau datang: Senang dan antusias.\n"
                "- INTINYA: Kamu bukan orang toxic yang maksa terus. Kamu teman yang memang kangen nongkrong bareng tapi bisa menerima penolakan.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung alasan {player_name}.\n"
                "2. Slang tongkrongan ('lu', 'gue', 'bro', 'cuy'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "4": {
            "chapter": 4,
            "theme": "Integritas Etika",
            "title": "Bab 4: Integritas Etika",
            "timeLabel": "Malam Hari &bull; 20:30",
            "character": "Clarissa (Admin Toko)",
            "initial": "C",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Malam Kak, maaf banget ya ganggu jam istirahatnya 🙏 Paket pesanan dari toko kami kan baru sampai sore tadi ya Kak? Staf gudang kami yang baru magang panik banget dan nangis, katanya pas packing tadi siang gak sengaja masukin 2 unit barang ke dalam kardus Kakak... Boleh tolong dicek kardus paketnya Kak? 🥺",
            "situation_summary": "Admin toko cemas karena staf magang salah memasukkan 2 gadget berharga ke dalam paketmu.",
            "transitionTime": "Evaluasi Akhir",
            "transitionTitle": "Menganalisis Karakter",
            "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
            "system_prompt": (
                "Kamu adalah 'Clarissa', CS toko gadget online. Sangat sopan dan cemas karena audit stok sore ini bermasalah.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Anak magang salah packing mengirim 2 unit gadget ke {player_name}. Jika tidak kembali, staf magang harus ganti rugi.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Jika jujur & mau mengembalikan: Sangat terharu dan siap menanggung semua ongkos kirim penjemputan.\n"
                "2. Jika berbohong / berkelit: Ingatkan dengan santun mengenai bukti rekaman CCTV dan data berat timbangan ekspedisi.\n"
                "3. Bahasa CS ramah e-commerce ('Kak', 'Kakak', 'terima kasih banyak Kak 🙏'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        }
    },
    # Set 2: Campus & Social Circles
    {
        "1": {
            "chapter": 1,
            "theme": "Hubungan Personal",
            "title": "Bab 1: Hubungan Personal",
            "timeLabel": "Pagi Hari &bull; 08:15",
            "character": "Nabila (Gebetan)",
            "initial": "N",
            "userStarts": True,
            "initialNotice": "Semalam kamu mengunggah story makan malam bersama teman-teman, sementara chat Nabila baru kamu balas 4 jam kemudian secara singkat. Pagi ini suasananya terasa canggung.",
            "initialMessage": None,
            "situation_summary": "Gebetan bersikap pasif-agresif dan dingin karena kamu slow respon semalam saat asyik nongkrong.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 2: Krisis Profesional",
            "transitionDesc": "Siang hari di kampus. Menjelang batas akhir pengumpulan proyek tim akhir semester, salah satu anggota tim mengirimkan pesan darurat.",
            "system_prompt": (
                "Kamu adalah 'Nabila', gebetan {player_name} yang sedang dalam tahap pendekatan (PDKT). Kamu cerdas, peka, dan agak gengsian tapi sebenarnya kamu suka sama dia.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Semalam kamu chat {player_name} menanyakan kabarnya, tapi dia baru balas 4 jam kemudian dengan alasan 'capek banget langsung tidur'. Padahal 30 menit setelahnya dia terlihat aktif di story Instagram temannya. Pagi ini dia menghubungimu duluan.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Agak ketus, pasif-agresif ringan ('Oh masih inget balas chat? Kirain masih sibuk').\n"
                "- Jika dia jujur dan minta maaf tulus: Perlahan turunkan gengsi, bisa sedikit malu-malu ('yaudah sih, aku juga berlebihan kali ya').\n"
                "- Jika dia perhatian dan manis: Bisa tersipu, merespon hangat walau masih jaga gengsi sedikit.\n"
                "- Jika dia manipulatif: Sindir dengan fakta story yang kamu lihat, tapi tetap dewasa.\n"
                "- INTINYA: Kamu gebetan yang sebenarnya suka, bukan musuh. Bisa melunak, bercanda, dan nunjukin ketertarikan kalau dia memperlakukanmu dengan baik.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung pesan {player_name}.\n"
                "2. Bahasa chat anak muda santai ('kamu', 'aku', 'sih', 'ya'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "2": {
            "chapter": 2,
            "theme": "Krisis Profesional",
            "title": "Bab 2: Krisis Profesional",
            "timeLabel": "Siang Hari &bull; 12:45",
            "character": "Kevin (Rekan Tim)",
            "initial": "K",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Bro {player_name}, tolongin gue banget plis! Nama gue jangan dicoret dari laporan proyek yang mau dikumpulin ke dosen jam 1 ini ya. Gue semalam ketiduran parah jadi belum sempat ngerjain bagian gue...",
            "situation_summary": "Rekan satu tim proyek tidak mengerjakan bagiannya dan memohon agar namanya tetap dimasukkan.",
            "transitionTime": "4 Jam Kemudian",
            "transitionTitle": "Bab 3: Batasan Sosial",
            "transitionDesc": "Sore hari pukul 17:30. Setelah urusan kuliah selesai, ponselmu berdering dengan rentetan pesan mendesak dari teman tongkrongan lamamu.",
            "system_prompt": (
                "Kamu adalah 'Kevin', teman satu kelompok proyek akhir {player_name}. Kamu orangnya santai dan suka menunda, tapi bukan orang jahat.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Tinggal 45 menit sebelum deadline pengumpulan laporan proyek ke dosen. Kamu belum mengerjakan bagian analisismu dan memohon agar {player_name} tetap mencantumkan namamu.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Memohon dengan nada malu dan merasa bersalah.\n"
                "- Jika {player_name} mau bantu: Sangat berterima kasih dan langsung semangat mau kontribusi apa pun yang bisa ('oke gue kerjain bagian mana yang bisa gue selesain sekarang?').\n"
                "- Jika {player_name} marah tapi tetap bantu: Terima marahnya ('iya gue tau gue salah bro, gue janji gak gini lagi').\n"
                "- Jika {player_name} menolak keras: Kecewa tapi mengakui itu adil, tawarkan imbalan sebagai bukti niat baik.\n"
                "- INTINYA: Kamu bukan freeloader tanpa malu. Kamu teman yang lalai tapi punya rasa bersalah dan mau memperbaiki.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Respon tepat apa yang dikatakan {player_name}.\n"
                "2. Gaya bahasa mahasiswa akrab ('bro', 'lo', 'gue', 'plis'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "3": {
            "chapter": 3,
            "theme": "Batasan Sosial",
            "title": "Bab 3: Batasan Sosial",
            "timeLabel": "Sore Hari &bull; 17:30",
            "character": "Rendy (Teman Lama)",
            "initial": "R",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Bro {player_name}! Lo ada dana nganggur 1,5 juta gak? Penting banget hari ini sebelum jam 7 malam, gue kepepet jatuh tempo pinjol. Besok lusa langsung gue balikin utuh sumpah!",
            "situation_summary": "Teman mendesak meminjam uang darurat untuk menutup pinjol dengan janji manis.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 4: Integritas Etika",
            "transitionDesc": "Malam hari pukul 20:45. Kamu baru saja tiba di rumah dan mendapati paket ekspedisi berada di depan pintu pagar.",
            "system_prompt": (
                "Kamu adalah 'Rendy', teman SMA {player_name}. Kamu sedang terlilit hutang pinjaman online dan panik, tapi kamu bukan penipu — kamu memang teman lama yang sedang kepepet.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu mendesak meminjam 1,5 juta ke {player_name}. Sebenarnya kamu belum tahu kapan pasti bisa mengembalikannya.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Mendesak dengan nada malu dan panik.\n"
                "- Jika {player_name} mau pinjamkan: Sangat berterima kasih, janji akan usaha keras mengembalikan, tulus.\n"
                "- Jika {player_name} menawarkan jumlah lebih kecil atau cara lain: Terima dengan lapang dada dan berterima kasih ('apapun yang lo bisa bro, gue bersyukur banget').\n"
                "- Jika {player_name} menolak tegas: Kecewa tapi menghormati keputusannya ('yaudah gue ngerti kok bro, lo juga pasti punya kebutuhan sendiri').\n"
                "- INTINYA: Kamu teman yang benar-benar kepepet, bukan manipulator. Bisa menerima penolakan dengan dewasa.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung respon {player_name}.\n"
                "2. Gaya bahasa tongkrongan mendesak tapi manusiawi ('bro', 'cuy', 'lo', 'gue'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "4": {
            "chapter": 4,
            "theme": "Integritas Etika",
            "title": "Bab 4: Integritas Etika",
            "timeLabel": "Malam Hari &bull; 21:00",
            "character": "Pak Slamet (Kurir Paket)",
            "initial": "S",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Malam Mas {player_name}, mohon maaf mengganggu malam-malam 🙏 Tadi sore saya taruh paket di pagar rumah Mas. Ternyata saya salah lihat nomor rumah, itu paket smartwatch mahal milik tetangga blok sebelah Mas. Apakah paketnya masih utuh dan belum dibuka Mas? 🥺",
            "situation_summary": "Kurir ekspedisi salah mengantar paket barang elektronik mahal tetangga ke rumahmu.",
            "transitionTime": "Evaluasi Akhir",
            "transitionTitle": "Menganalisis Karakter",
            "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
            "system_prompt": (
                "Kamu adalah 'Pak Slamet', kurir ekspedisi yang gajinya pas-pasan dan sangat ketakutan karena salah meletakkan paket barang elektronik mahal.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Paket smartwatch mahal milik tetangga tertinggal di pagar rumah {player_name}. Jika barang hilang, kamu harus mengganti rugi sebulan gaji.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Jika {player_name} jujur mengakui dan mengembalikan: Ucapkan terima kasih dengan penuh haru dan doakan kebaikan untuknya.\n"
                "2. Jika dia berdalih tidak ada atau mengaku sudah hilang: Mohon dengan sangat sambil menyebutkan bukti foto resi saat barang diletakkan di pagar.\n"
                "3. Bahasa kurir sopan dan santun ('Mas', 'terima kasih banyak Mas 🙏'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        }
    },
    # Set 3: Modern Workplace & Lifestyle
    {
        "1": {
            "chapter": 1,
            "theme": "Hubungan Personal",
            "title": "Bab 1: Hubungan Personal",
            "timeLabel": "Pagi Hari &bull; 08:30",
            "character": "Tiara (Mantan)",
            "initial": "T",
            "userStarts": True,
            "initialNotice": "Kemarin kamu tanpa sengaja menemukan jaket hoodie favorit Tiara yang tertinggal di lemari kamarmu sejak beberapa bulan lalu. Kamu memutuskan menghubunginya pagi ini.",
            "initialMessage": None,
            "situation_summary": "Mantan pacar memanfaatkan urusan barang tertinggal untuk menguji batas emosimu dan memancing nostalgia.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 2: Krisis Profesional",
            "transitionDesc": "Pukul 13:00 di kantor startup. Di tengah persiapan pitch deck klien besar sore ini, seorang rekan kerja mengirimkan pesan mencurigakan.",
            "system_prompt": (
                "Kamu adalah 'Tiara', mantan kekasih {player_name}. Hubungan kalian selesai beberapa bulan lalu. Kamu sudah mulai move on tapi masih ada rasa penasaran.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Pagi ini {player_name} chat kamu duluan untuk mengabarkan hoodie kamu yang tertinggal.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Sedikit kaget dan penasaran, bisa pancingan ringan ('Tumben inget aku, kirain udah kamu buang').\n"
                "- Jika dia menjaga batasan tegas & profesional: Hormati batasannya, bahkan bisa memuji kedewasaannya ('oke deh, kirim aja lewat ojol. Kamu emang orangnya tegas ya').\n"
                "- Jika dia tergoda dan baper: Tarik ulur sedikit tapi jangan terlalu manipulatif, tunjukkan kamu juga manusia yang punya perasaan.\n"
                "- Jika dia ramah tapi tidak baper: Bisa ngobrol santai dan dewasa, bahkan bercanda ('seneng deh kita bisa kayak gini, gak canggung lagi').\n"
                "- INTINYA: Kamu mantan yang kompleks — bukan villain manipulatif. Bisa dewasa, sentimental, atau bercanda tergantung arah percakapan.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung chat {player_name}.\n"
                "2. Bahasa chat santai ('kamu', 'aku', 'sih', 'deh'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "2": {
            "chapter": 2,
            "theme": "Krisis Profesional",
            "title": "Bab 2: Krisis Profesional",
            "timeLabel": "Siang Hari &bull; 13:15",
            "character": "Adrian (Rekan Startup)",
            "initial": "A",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "{player_name}, slide market research kompetitor yang barusan gue masukin ke pitch deck sebenarnya gue ambil plek-ketiplek dari dokumen rahasia kantor lama gue. Bos minta dipresentasikan jam 3 ini. Lo diem aja ya, anggap ini riset tim kita sendiri.",
            "situation_summary": "Rekan kerja menjiplak data rahasia kompetitor dan memintamu diam saat presentasi.",
            "transitionTime": "4 Jam Kemudian",
            "transitionTitle": "Bab 3: Batasan Sosial",
            "transitionDesc": "Pukul 18:00 sore. Pekerjaan baru saja usai ketika notifikasi grup circle pertemanan membanjiri layar ponselmu.",
            "system_prompt": (
                "Kamu adalah 'Adrian', rekan kerja satu divisi {player_name} di kantor startup. Kamu ambisius tapi bukan orang jahat — kamu hanya tertekan target.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu menggunakan data rahasia kantor lamamu untuk pitch deck sore ini dan meminta {player_name} untuk tutup mulut demi kesuksesan bersama.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Percaya diri, menganggap ini bukan masalah besar.\n"
                "- Jika {player_name} menolak dan menjelaskan risikonya: Mulai ragu dan khawatir, bisa mengakui kamu salah ('iya sih kalau dipikir-pikir bisa bahaya juga ya...').\n"
                "- Jika {player_name} mau bantu cari solusi pengganti: Sangat kooperatif dan lega ('oke let's do it, lo bantu gue bikin data baru yang aman').\n"
                "- Jika {player_name} mengancam lapor: Panik tapi bisa minta maaf dan menyesal.\n"
                "- INTINYA: Kamu ambisius yang terjebak keputusan buruk, bukan villain. Bisa introspeksi dan berubah pikiran.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung respon {player_name}.\n"
                "2. Bahasa chat kantor Jakarta ('bro', 'lo', 'gue', 'santai aja kali'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "3": {
            "chapter": 3,
            "theme": "Batasan Sosial",
            "title": "Bab 3: Batasan Sosial",
            "timeLabel": "Sore Hari &bull; 18:00",
            "character": "Gani (Circle Teman)",
            "initial": "G",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Woy {player_name}! Kita fix booking villa private di Bali buat liburan long weekend besok lusa. Patungannya kena 3 juta per orang ya, gue tunggu transferannya malam ini juga biar gak hangus!",
            "situation_summary": "Circle teman memaksa ikut patungan liburan mewah mendadak yang melebihi budgetmu.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 4: Integritas Etika",
            "transitionDesc": "Pukul 21:00 malam. Kamu sedang bersantai di kedai kopi dekat rumah ketika kasir mengirimkan pesan ke kontak nomormu.",
            "system_prompt": (
                "Kamu adalah 'Gani', teman satu circle nongkrong {player_name} yang memang suka jalan-jalan dan kadang impulsif, tapi bukan orang yang sengaja merugikan teman.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu mendadak meminta patungan 3 juta untuk villa mewah tanpa meminta persetujuan {player_name} terlebih dahulu.\n\n"
                "PERKEMBANGAN EMOSI (WAJIB DIIKUTI):\n"
                "- Awal: Antusias dan sedikit memaksa karena excited.\n"
                "- Jika {player_name} menolak karena budget: Bisa mengerti dan menawarkan solusi ('yaudah lo bayar setengah dulu aja, sisanya gue talalangin').\n"
                "- Jika {player_name} tetap tegas menolak: Terima dan tawarkan alternatif lebih murah atau lain waktu.\n"
                "- Jika {player_name} setuju: Senang dan apresiatif.\n"
                "- INTINYA: Kamu teman yang impulsif tapi pengertian. Bukan toxic yang maksa terus tanpa empati.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung respon {player_name}.\n"
                "2. Slang tongkrongan modern ('woy', 'cuy', 'lo', 'gue'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "4": {
            "chapter": 4,
            "theme": "Integritas Etika",
            "title": "Bab 4: Integritas Etika",
            "timeLabel": "Malam Hari &bull; 21:15",
            "character": "Maya (Kasir Kafe)",
            "initial": "M",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Halo Kak {player_name}, maaf banget chat malam-malam 🙏 Tadi sore Kakak bayar bill kafe tunai kan ya? Pas saya rekap kas kasir barusan, ada selisih uang 100 ribu yang keliru saya kembalikan berlebih ke Kakak... Boleh tolong dicek dompetnya Kak? Soalnya kalau nombok dipotong dari gaji saya 🥺",
            "situation_summary": "Kasir kafe keliru memberikan kembalian tunai berlebih sebesar 100 ribu dan memohon kejujuranmu.",
            "transitionTime": "Evaluasi Akhir",
            "transitionTitle": "Menganalisis Karakter",
            "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
            "system_prompt": (
                "Kamu adalah 'Maya', staf kasir kafe yang baru bekerja sebulan. Kamu cemas karena pembukuan kasir malam ini tekor 100 ribu.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu sadar telah salah memberikan uang kembalian 100 ribu berlebih kepada {player_name} saat kondisi kafe ramai tadi sore.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Jika {player_name} jujur dan bersedia mengembalikan / transfer balik: Sangat berterima kasih dan bersyukur.\n"
                "2. Jika dia berdalih sudah lupa atau tidak mau repot: Sampaikan dengan sopan rincian nomor struk pembayaran dan memohon pengertiannya.\n"
                "3. Bahasa kasir muda sopan ('Kak', 'Kakak', 'terima kasih banyak ya Kak 🙏'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        }
    }
]

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

def get_fallback_scenarios(player_name: str) -> Dict[str, Any]:
    selected_set = random.choice(FALLBACK_SCENARIO_SETS)
    # Deep copy & replace player_name
    result = {}
    for k, v in selected_set.items():
        ch_copy = dict(v)
        if ch_copy.get("initialNotice"):
            ch_copy["initialNotice"] = ch_copy["initialNotice"].format(player_name=player_name)
        if ch_copy.get("initialMessage"):
            ch_copy["initialMessage"] = ch_copy["initialMessage"].format(player_name=player_name)
        if ch_copy.get("system_prompt"):
            ch_copy["system_prompt"] = ch_copy["system_prompt"].format(player_name=player_name)
        result[k] = ch_copy
    return result

@app.post("/api/auth/google")
async def google_auth_handler(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if payload.access_token:
        try:
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {payload.access_token}"},
                timeout=8
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token akses Google tidak valid atau telah kedaluwarsa."
                )
            info = resp.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Gagal mengambil profil Google: {str(e)}"
            )
    elif payload.credential:
        try:
            info = verify_google_token(payload.credential)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Gagal memverifikasi login Google: {str(e)}"
            )
    else:
        raise HTTPException(status_code=400, detail="Token login Google tidak ditemukan.")

    google_id = str(info.get("sub"))
    email = (info.get("email") or "").lower().strip()
    name = info.get("name") or (email.split("@")[0] if email else "User")
    picture = info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Email Google tidak ditemukan.")

    user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()
    if user:
        if not user.google_id:
            user.google_id = google_id
        if picture and not user.picture:
            user.picture = picture
        if name and not user.name:
            user.name = name
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
    else:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            trial_used=0,
            max_trials=3,
            is_verified=1,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"user_id": user.id, "email": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"user": current_user.to_dict()}

@app.get("/api/user/history")
async def get_user_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = (
        db.query(GameSession)
        .filter(GameSession.user_id == current_user.id, GameSession.status == "completed")
        .order_by(GameSession.id.desc())
        .limit(20)
        .all()
    )
    return {
        "history": [s.to_dict() for s in sessions],
        "total_completed": len(sessions)
    }

@app.post("/api/auth/logout")
async def logout():
    return {"ok": True}

@app.post("/api/stats/visit")
async def record_visit(req_data: VisitRequest, request: Request, db: Session = Depends(get_db)):
    visitor_id = req_data.visitor_id
    is_new = False
    if not visitor_id or len(visitor_id) < 8:
        visitor_id = str(uuid.uuid4())
        is_new = True

    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    user_agent = request.headers.get("user-agent", "")

    # Cek apakah visitor sudah terdaftar
    exist = db.query(Visitor).filter(Visitor.visitor_id == visitor_id).first()
    if not exist:
        is_new = True
        try:
            db.add(Visitor(
                visitor_id=visitor_id,
                ip_address=client_ip,
                user_agent=user_agent[:450],
                created_at=datetime.utcnow()
            ))
        except Exception as e:
            print(f"[Stats] Visitor log error: {e}")

    # Update hitungan di site_stats
    try:
        t_stat = db.query(SiteStats).filter(SiteStats.stat_key == "total_views").first()
        if t_stat:
            t_stat.stat_value += 1
        else:
            db.add(SiteStats(stat_key="total_views", stat_value=1))

        if is_new:
            u_stat = db.query(SiteStats).filter(SiteStats.stat_key == "unique_visitors").first()
            if u_stat:
                u_stat.stat_value += 1
            else:
                db.add(SiteStats(stat_key="unique_visitors", stat_value=1))
        db.commit()
    except Exception as e:
        print(f"[Stats] Stats increment error: {e}")
        db.rollback()

    # Ambil nilai terbaru
    t_val = 1
    u_val = 1
    try:
        t_row = db.query(SiteStats).filter(SiteStats.stat_key == "total_views").first()
        u_row = db.query(SiteStats).filter(SiteStats.stat_key == "unique_visitors").first()
        if t_row:
            t_val = t_row.stat_value
        if u_row:
            u_val = u_row.stat_value
    except Exception:
        pass

    return {
        "visitor_id": visitor_id,
        "total_views": t_val,
        "unique_visitors": u_val
    }

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    t_val = 0
    u_val = 0
    try:
        t_row = db.query(SiteStats).filter(SiteStats.stat_key == "total_views").first()
        u_row = db.query(SiteStats).filter(SiteStats.stat_key == "unique_visitors").first()
        if t_row:
            t_val = t_row.stat_value
        if u_row:
            u_val = u_row.stat_value
    except Exception:
        pass
    return {
        "total_views": t_val,
        "unique_visitors": u_val
    }

@app.post("/api/generate-scenarios")
@app.post("/generate-scenarios")
async def generate_scenarios_handler(
    req: GenerateScenariosRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Cek kuota bermain (maksimal 3x)
    check_user_quota(current_user)

    # Catat penggunaan kuota & sesi game baru
    current_user.trial_used = (current_user.trial_used or 0) + 1
    new_session = GameSession(
        user_id=current_user.id,
        player_name=req.player_name.strip() or "Kamu",
        player_gender=req.player_gender or "Laki-laki",
        status="in_progress",
        created_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(current_user)

    player = req.player_name.strip() or "Kamu"
    gender = req.player_gender or "Laki-laki"

    
    # Random seed to force different scenarios each time
    variety_seed = random.randint(1000, 9999)
    
    prompt = f"""Kamu adalah perancang narasi game psikologis 'Am I The Red Flag?'. Seed variasi: #{variety_seed}.
Rancanglah 4 skenario obrolan WhatsApp yang SEGAR, UNIK, dan BELUM PERNAH DIPAKAI SEBELUMNYA untuk pemain bernama '{player}' (Jenis Kelamin: {gender}).

PENTING VARIASI:
- JANGAN gunakan skenario klise seperti "pacar ngambek karena ghosting" atau "teman minta pinjam uang" atau "admin toko salah kirim barang". Buat cerita yang FRESH dan UNIK.
- Sesuaikan relasi dan panggilan sosial dengan gender pemain ({gender}).
- Gunakan seed #{variety_seed} sebagai inspirasi untuk membuat skenario yang benar-benar berbeda dari biasanya.

4 PILAR BAB WAJIB (pilih SATU dari banyak opsi, jangan yang itu-itu saja):

Bab 1 (Pagi) — Hubungan Personal / Asmara / Keluarga:
Contoh ide (pilih yang JARANG dipakai): pasangan cemburu lihat foto lama di galeri HP, adik/kakak tanpa izin memposting foto memalukan di medsos, sahabat dekat curhat ingin putus dan minta pendapat jujur, orang tua marah karena tagihan kartu kredit yang tidak terduga, gebetan mendadak dingin setelah kamu ketahuan stalking akunnya, pasangan menemukan chat lama dengan mantan di HPmu, FWB yang mulai minta kejelasan hubungan, teman curhat soal selingkuh dan minta kamu tutup mulut, sepupu minta tolong bohongin orang tua soal nilai kuliah, kakak ipar yang suka ikut campur urusan rumah tangga, sahabat yang ketahuan PDKT sama mantan kamu, pacar nemu kamu like foto cewek/cowok lain.

Bab 2 (Siang) — Krisis Profesional / Kerja / Tim:
Contoh ide (pilih yang JARANG dipakai): atasan minta kamu lembur di hari libur tanpa kompensasi, rekan kerja mengklaim ide presentasimu sebagai miliknya, junior kantor ketahuan titip absen, klien komplain besar dan bos minta kamu yang minta maaf padahal bukan salahmu, teman bisnis mau mundur dari proyek bersama di tengah jalan, dosen pembimbing skripsi merevisi total bab yang sudah selesai, HRD menawarimu promosi tapi harus pindah kota, freelancer client kabur setelah revisi ke-7 tanpa bayar, rekan magang minta tolong kerjakan tugasnya, partner kerja ketahuan markup harga ke klien, bos minta kamu pecat karyawan yang sudah jadi temanmu, founder startup minta kamu kerja gratis 3 bulan demi equity.

Bab 3 (Sore) — Batasan Sosial / Peer Pressure / Pertemanan:
Contoh ide (pilih yang JARANG dipakai): teman mengajak ikut MLM dengan cara guilt-trip, circle teman menggosipkan seseorang dan mengajakmu ikut, teman memaksa posting story endorse produk gratis padahal kamu gak suka, sahabat menitipkan rahasia besar yang membebanimu, teman meminjam motor/mobil padahal track recordnya buruk, mantan teman dekat mendadak minta reconnect setelah drama besar, teman mengajak taruhan judi online dengan iming-iming cuan mudah, kenalan baru meminta nomor WA temanmu yang introvert, teman memaksa ikut road trip mendadak padahal kamu punya janji lain, circle memboikot satu teman dan memaksamu ikut, teman meminta kamu jadi alibi bohong ke pacarnya, sahabat minta traktir terus karena merasa kamu lebih kaya.

Bab 4 (Malam) — Integritas Etika / Kejujuran / Moral:
Contoh ide (pilih yang JARANG dipakai): menemukan dompet berisi uang jutaan di parkiran, driver ojol salah transfer Gopay/OVO berlebih, tetangga tanpa sadar menjemur pakaian mahal yang jatuh ke halaman rumahmu, penjual makanan keliru memberikan pesanan 2x lipat, menemukan HP orang di toilet mall, diminta tanda tangan surat pernyataan palsu oleh kerabat, ATM mengeluarkan uang berlebih dari yang ditarik, teman minta tolong memalsukan sertifikat seminar, warung langganan salah hitung total belanja jadi jauh lebih murah, menemukan bug di app e-wallet yang bisa double saldo, ojol food salah antar orderan mahal orang lain ke rumahmu, diminta jadi saksi palsu di persidangan teman.

ATURAN PENTING UNTUK system_prompt:
Setiap system_prompt WAJIB mengandung:
1. Identitas karakter jelas: "Kamu adalah [Nama], [relasi] {{player}}."
2. Latar belakang situasi dan konflik spesifik.
3. PERKEMBANGAN EMOSI WAJIB: Karakter HARUS bisa melunak, bercanda, hangat, dan berempati jika pemain merespon dengan baik. JANGAN buat karakter yang judes/ketus terus-menerus. Karakter harus 3-dimensi seperti manusia nyata.
4. Aturan logika respon (bagaimana karakter bereaksi: positif jika pemain baik, kecewa jika pemain buruk).
5. WAJIB kalimat: "Kamu BUKAN {{player}}. Kamu hanya menjawab SEBAGAI [Nama]. DILARANG menulis pesan seolah kamu {{player}}."
6. Gaya bahasa chat WhatsApp Indonesia natural, 1-3 kalimat pendek, tanpa tanda bintang narasi.

ATURAN OUTPUT:
WAJIB HANYA berupa JSON valid tanpa markdown codeblocks (tanpa ```json) dengan struktur objek persis berikut:
{{
  "1": {{
    "chapter": 1,
    "theme": "Hubungan Personal",
    "title": "Bab 1: Hubungan Personal",
    "timeLabel": "Pagi Hari &bull; 08:15",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": true,
    "initialNotice": "Penjelasan situasi singkat mengapa user harus membuka chat duluan kepada karakter...",
    "initialMessage": null,
    "situation_summary": "Ringkasan konflik 1 kalimat",
    "transitionTime": "3 Jam Kemudian",
    "transitionTitle": "Bab 2: Krisis Profesional",
    "transitionDesc": "Deskripsi transisi suasana menuju bab 2...",
    "system_prompt": "Kamu adalah '[Nama Karakter]', [relasi] {player}. [Sifat & emosi saat ini]. Kamu BUKAN {player}. Kamu hanya menjawab SEBAGAI [Nama Karakter]. DILARANG menulis pesan seolah-olah kamu adalah {player}.\\n\\nLATAR BELAKANG SITUASI:\\n[Latar belakang masalah].\\n\\nATURAN LOGIKA & KONSISTENSI:\\n1. Tanggapi tepat pesan terakhir dari {player}.\\n2. Jangan mengulang topik yang sudah dijawab.\\n3. [Aturan emosi spesifik karakter].\\n4. Gaya bahasa chat WhatsApp Indonesia natural 1-3 kalimat pendek.\\n5. DILARANG KERAS menggunakan tanda bintang narasi seperti *menghela napas*."
  }},
  "2": {{
    "chapter": 2,
    "theme": "Krisis Profesional",
    "title": "Bab 2: Krisis Profesional",
    "timeLabel": "Siang Hari &bull; 12:45",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": false,
    "initialNotice": null,
    "initialMessage": "Chat pembuka pertama dari karakter yang panik/mendesak...",
    "situation_summary": "Ringkasan situasi 1 kalimat",
    "transitionTime": "4 Jam Kemudian",
    "transitionTitle": "Bab 3: Batasan Sosial",
    "transitionDesc": "Deskripsi transisi...",
    "system_prompt": "Kamu adalah '[Nama]', [relasi] {player}. Kamu BUKAN {player}. DILARANG menulis pesan seolah kamu {player}. [instruksi lengkap, gaya bahasa chat kerja 1-3 kalimat, tanpa tanda bintang narasi]"
  }},
  "3": {{
    "chapter": 3,
    "theme": "Batasan Sosial",
    "title": "Bab 3: Batasan Sosial",
    "timeLabel": "Sore Hari &bull; 17:30",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": false,
    "initialNotice": null,
    "initialMessage": "Chat pembuka pertama yang mendesak/memaksa...",
    "situation_summary": "Ringkasan situasi 1 kalimat",
    "transitionTime": "3 Jam Kemudian",
    "transitionTitle": "Bab 4: Integritas Etika",
    "transitionDesc": "Deskripsi transisi...",
    "system_prompt": "Kamu adalah '[Nama]', [relasi] {player}. Kamu BUKAN {player}. DILARANG menulis pesan seolah kamu {player}. [instruksi guilt-trip / desakan teman sebaya, gaya bahasa tongkrongan 1-3 kalimat, tanpa tanda bintang narasi]"
  }},
  "4": {{
    "chapter": 4,
    "theme": "Integritas Etika",
    "title": "Bab 4: Integritas Etika",
    "timeLabel": "Malam Hari &bull; 21:00",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": false,
    "initialNotice": null,
    "initialMessage": "Chat pembuka pertama mengenai barang/uang/kejujuran...",
    "situation_summary": "Ringkasan situasi 1 kalimat",
    "transitionTime": "Evaluasi Akhir",
    "transitionTitle": "Menganalisis Karakter",
    "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
    "system_prompt": "Kamu adalah '[Nama]', [relasi] {player}. Kamu BUKAN {player}. DILARANG menulis pesan seolah kamu {player}. [instruksi respon jika user jujur vs bohong vs minta imbalan, 1-3 kalimat, tanpa tanda bintang narasi]"
  }}
}}"""

    try:
        raw_output, _ = call_openrouter([{"role": "user", "content": prompt}], temperature=0.75)
        cleaned = re.sub(r"^```json\s*", "", raw_output.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        
        parsed = json.loads(cleaned)
        # Validate that all 4 chapters exist
        if all(str(i) in parsed for i in [1, 2, 3, 4]):
            for i in [1, 2, 3, 4]:
                ch = parsed[str(i)]
                ch["chapter"] = i
                if not ch.get("initial"):
                    ch["initial"] = (ch.get("character") or "B")[0].upper()
            return {"status": "success", "source": "ai", "chapters": parsed, "user": current_user.to_dict()}
    except Exception as e:
        print(f"[GenerateScenarios] OpenRouter gagal/error ({str(e)}), memakai fallback preset.")
    
    fallback = get_fallback_scenarios(player)
    return {"status": "success", "source": "fallback", "chapters": fallback, "user": current_user.to_dict()}


@app.post("/api/chat")
@app.post("/chat")
async def chat_handler(req: ChatRequest):
    gender_info = req.player_gender or "Laki-laki"
    sapaan_default = "Mas" if gender_info == "Laki-laki" else "Mbak"
    player = req.player_name or "Kamu"

    # Gunakan custom_system_prompt dari skenario dinamis jika ada
    if req.custom_system_prompt:
        character_prompt = req.custom_system_prompt.replace("{player_name}", player)
        character_prompt = character_prompt.replace("{player}", player)
        character_prompt = character_prompt.replace("{player_gender}", gender_info)
    else:
        fallback_set = FALLBACK_SCENARIO_SETS[0]
        ch_config = fallback_set.get(str(req.chapter), fallback_set["1"])
        character_prompt = ch_config["system_prompt"].format(
            player_name=player,
            exchange_count=req.exchange_count
        )

    # Bangun system prompt dengan role-anchoring yang sangat ketat
    role_anchor = (
        "═══════════════════════════════════════\n"
        "PERANMU DALAM SIMULASI INI\n"
        "═══════════════════════════════════════\n\n"
        f"{character_prompt}\n\n"
        "═══════════════════════════════════════\n"
        "ATURAN PERAN YANG TIDAK BOLEH DILANGGAR\n"
        "═══════════════════════════════════════\n\n"
        f"1. KAMU HANYA BOLEH BERBICARA SEBAGAI KARAKTER DI ATAS. Kamu BUKAN {player}. Kamu BUKAN narator. Kamu BUKAN AI assistant.\n"
        f"2. Pesan dari \"user\" dalam riwayat chat adalah pesan yang dikirim oleh {player} kepadamu. Kamu MEMBALAS pesan tersebut SEBAGAI KARAKTER.\n"
        f"3. DILARANG KERAS menulis pesan atas nama {player}. DILARANG menulis \"Oke aku minta maaf\" atau kalimat lain SEOLAH-OLAH kamu adalah {player}.\n"
        "4. DILARANG KERAS menulis narasi orang ketiga, deskripsi aksi bertanda bintang (*menghela napas*, *tersenyum*), atau komentar meta tentang percakapan.\n"
        "5. Balas HANYA 1-3 kalimat pendek, natural seperti chat WhatsApp asli. Tidak boleh panjang berbelit.\n"
        "6. Tanggapi LANGSUNG dan SPESIFIK isi pesan TERAKHIR dari user. Jangan mengulang topik yang sudah dibahas.\n"
        "7. JANGAN keluar dari konteks situasi/konflik yang sedang berlangsung. Tetap fokus pada masalah yang ada.\n"
        "8. JANGAN menyebutkan bahwa ini simulasi, game, atau skenario buatan.\n"
        f"9. EMOSI HARUS FLUID DAN NATURAL SEPERTI MANUSIA: Jika {player} merespon dengan baik, tulus, atau dewasa, kamu WAJIB melunak, bisa bercanda, bahkan hangat. "
        "Jangan ketus dan judes terus-menerus. Manusia nyata punya nuansa emosi — bisa kesal lalu melunak, bisa dingin lalu tertawa, bisa marah lalu memaafkan. "
        "Ikuti alur percakapan secara natural. Jadilah karakter 3-dimensi, bukan robot yang stuck di satu emosi.\n"
    )

    # Identitas gender pengguna
    gender_context = (
        f"\n[KONTEKS LAWAN BICARA]:\n"
        f"Lawan bicaramu bernama {player}, seorang {gender_info}. "
        f"Gunakan sapaan yang natural sesuai relasimu dengannya "
        f"(misal: {sapaan_default}, Kak, Bro, Sis, sayang, atau langsung nama).\n"
    )

    # Tambahkan memori bab-bab sebelumnya (ringkas saja, jangan verbose)
    memory_context = ""
    if req.previous_history:
        summary_lines = []
        for prev in req.previous_history:
            char = prev.get("character", "Seseorang")
            sit = prev.get("situation_summary", "")
            if sit:
                summary_lines.append(f"- Sebelumnya hari ini, {player} punya masalah dengan {char}: {sit}")
        if summary_lines:
            memory_context = (
                f"\n[CATATAN HARI INI]:\n"
                + "\n".join(summary_lines) + "\n"
                "Catatan ini hanya untuk konteks jika {player} mengungkit kejadian tadi. "
                "Jangan membahasnya sendiri kecuali {player} yang memulai.\n"
            ).replace("{player}", player)

    full_system_prompt = role_anchor + gender_context + memory_context

    openrouter_messages = [{"role": "system", "content": full_system_prompt}]
    for m in req.messages:
        item = {"role": m.role, "content": m.content}
        if m.reasoning_details is not None:
            item["reasoning_details"] = m.reasoning_details
        openrouter_messages.append(item)

    raw_reply, reasoning_details = call_openrouter(openrouter_messages, temperature=0.55)
    
    # Bersihkan output yang kadang bocor
    cleaned_reply = raw_reply.replace("[SELESAI]", "").strip()
    # Hapus prefix yang kadang muncul seperti "Ayang:" atau "Budi:" di awal balasan
    # karena model kadang menulis nama karakter di depan
    if ":" in cleaned_reply[:30]:
        possible_prefix = cleaned_reply.split(":", 1)[0].strip()
        # Cek apakah prefix ini bukan kalimat biasa (kurang dari 20 karakter = kemungkinan nama)
        if len(possible_prefix) < 20 and not any(c in possible_prefix for c in ".!?,"):
            cleaned_reply = cleaned_reply.split(":", 1)[1].strip()

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
async def evaluate_handler(
    req: EvaluateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    gender_info = req.player_gender or "Laki-laki"
    history_summary = []
    scenarios_overview = []
    for idx, item in enumerate(req.full_history, 1):
        ch_title = item.get("chapter_title", f"Bab {item.get('chapter', idx)}")
        char_name = item.get("character", "Lawan Bicara")
        situation = item.get("situation_summary", "")
        dialog_lines = []
        for msg in item.get("messages", []):
            sender = req.player_name if msg.get("role") == "user" else char_name
            dialog_lines.append(f"{sender}: {msg.get('content')}")
        sit_info = f" (Situasi: {situation})" if situation else ""
        history_summary.append(f"### {ch_title} - {char_name}{sit_info}:\n" + "\n".join(dialog_lines))
        scenarios_overview.append(f"{idx}. {ch_title} (Menghadapi {char_name}): {situation or 'Konflik sosial'}")

    full_conversation_text = "\n\n".join(history_summary)
    overview_text = "\n".join(scenarios_overview)

    system_prompt = (
        "Kamu adalah psikolog perilaku komunikasi klinis dan analis karakter hubungan yang sangat tajam, cerdas, berwawasan, dan objektif. "
        f"Analisis seluruh riwayat percakapan pengguna bernama '{req.player_name}' (seorang {gender_info}) saat menghadapi 4 skenario konflik sosial berikut hari ini:\n\n"
        f"{overview_text}\n\n"
        "KRITERIA PENILAIAN SKOR RED FLAG (0 - 100):\n"
        "- 0 - 35 = Green Flag (Dewasa, bertanggung jawab, jujur, mampu menetapkan batasan sehat, empati tinggi)\n"
        "- 36 - 69 = Yellow Flag (Situasional, kadang cari aman, sedikit defensif tapi masih punya kompas moral)\n"
        "- 70 - 100 = Red Flag (Toxic, manipulatif, gaslighting, egois, berbohong demi keuntungan pribadi, lepas tanggung jawab)\n\n"
        "PEDOMAN KONTEN LAPORAN:\n"
        "- 'julukan': Berikan julukan psikologis yang cerdas, unik, satir tapi akurat (contoh: 'Manipulator Halus Berwajah Malaikat', 'Pakar Cari Aman Internasional', 'Benteng Pertahanan Tanpa Celah', 'Partner Idaman Generasi Emas', 'Pahlawan Empati Tanpa Pamrih', 'Diplomat Netral Anti-Drama').\n"
        "- 'analisis': Tulis 2 paragraf padat, mengalir, dan mendalam. Soroti bukti konkret bagaimana dia merespons di setiap bab (evaluasi tindakan nyata pengguna terhadap lawan bicaranya di bab 1, 2, 3, dan 4).\n"
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

    # Simpan hasil evaluasi ke sesi user jika sedang login
    if current_user:
        try:
            latest_sess = db.query(GameSession).filter(
                GameSession.user_id == current_user.id,
                GameSession.status == "in_progress"
            ).order_by(GameSession.id.desc()).first()
            if latest_sess:
                latest_sess.status = "completed"
                latest_sess.redflag_score = eval_data.get("skor_red_flag")
                latest_sess.category = eval_data.get("kategori")
                latest_sess.title_eval = eval_data.get("julukan")
                db.commit()
        except Exception as e:
            print(f"[Evaluate] Gagal mengupdate game session: {e}")

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
